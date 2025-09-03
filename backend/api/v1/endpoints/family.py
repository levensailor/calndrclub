from typing import List
from fastapi import APIRouter, Depends, HTTPException

from backend.core.database import database
from backend.core.security import get_current_user, uuid_to_string
from backend.core.logging import logger
from backend.db.models import users
from backend.schemas.user import FamilyMember, FamilyMemberEmail, CoParentCreate, UserResponse
from backend.schemas.custody import Custodian
import secrets
import uuid

router = APIRouter()

@router.post("/invite", response_model=UserResponse)
async def invite_co_parent(co_parent_data: CoParentCreate, current_user = Depends(get_current_user)):
    """
    Invites a co-parent to the current user's family.
    """
    from backend.core.security import get_password_hash

    family_id = current_user['family_id']
    
    # Check if email already exists in the family
    query = users.select().where((users.c.email == co_parent_data.email) & (users.c.family_id == family_id))
    existing_user = await database.fetch_one(query)
    if existing_user:
        raise HTTPException(status_code=400, detail="A user with this email already exists in your family.")

    # Generate a temporary, secure password. 
    # The user will be required to change this upon first login.
    temporary_password = secrets.token_urlsafe(16)
    hashed_password = get_password_hash(temporary_password)
    
    user_id = uuid.uuid4()
    
    insert_query = users.insert().values(
        id=user_id,
        first_name=co_parent_data.first_name,
        last_name=co_parent_data.last_name,
        email=co_parent_data.email,
        phone_number=co_parent_data.phone_number,
        password_hash=hashed_password,
        family_id=family_id,
        status="invited"
    )
    
    await database.execute(insert_query)
    
    # Fetch the created user to return in the response
    created_user = await database.fetch_one(users.select().where(users.c.id == user_id))

    # Here you would typically trigger an email to the invited user.
    # For now, we'll just log it.
    logger.info(f"Co-parent invited: {co_parent_data.email}. Temporary password: {temporary_password}")
    
    return UserResponse(
        id=uuid_to_string(created_user['id']),
        first_name=created_user['first_name'],
        last_name=created_user['last_name'],
        email=created_user['email'],
        phone_number=created_user['phone_number'],
        family_id=uuid_to_string(created_user['family_id']),
        status=created_user['status']
    )


@router.get("/custodians", response_model=List[Custodian])
async def get_family_custodians(current_user = Depends(get_current_user)):
    """
    Returns the two primary custodians (parents) for the current user's family as an array.
    """
    try:
        family_id = current_user['family_id']
        logger.info(f"Fetching custodians for family_id: {family_id}")
        
        # Order by created_at, but handle NULLs properly
        query = users.select().where(users.c.family_id == family_id).order_by(
            users.c.created_at.asc().nulls_last()
        )
        family_members = await database.fetch_all(query)
        
        logger.info(f"Found {len(family_members)} family members")
        
        if len(family_members) < 1:
            logger.warning(f"No family members found")
            raise HTTPException(status_code=404, detail="No family members found")
            
        custodian_one = family_members[0]
        
        if len(family_members) >= 2:
            custodian_two = family_members[1]
            logger.info(f"Custodian 1: {custodian_one['first_name']} (ID: {custodian_one['id']})")
            logger.info(f"Custodian 2: {custodian_two['first_name']} (ID: {custodian_two['id']})")
            
            result = [
                Custodian(
                    id=uuid_to_string(custodian_one['id']),
                    first_name=custodian_one['first_name']
                ),
                Custodian(
                    id=uuid_to_string(custodian_two['id']),
                    first_name=custodian_two['first_name']
                )
            ]
        else:
            # Only one family member exists, return it as the first custodian
            # and a placeholder for the second custodian
            logger.info(f"Only one family member found: {custodian_one['first_name']} (ID: {custodian_one['id']})")
            logger.info(f"Creating placeholder for second custodian")
            
            result = [
                Custodian(
                    id=uuid_to_string(custodian_one['id']),
                    first_name=custodian_one['first_name']
                ),
                Custodian(
                    id="placeholder",
                    first_name="Parent 2"
                )
            ]
        
        logger.info(f"Returning custodians: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching custodians: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching custodians: {str(e)}")

@router.get("/emails", response_model=List[FamilyMemberEmail])
async def get_family_member_emails(current_user = Depends(get_current_user)):
    """
    Returns the email addresses of all family members (parents) for automatic population in alerts.
    """
    query = users.select().where(users.c.family_id == current_user['family_id']).order_by(users.c.first_name)
    family_members = await database.fetch_all(query)
    
    return [
        FamilyMemberEmail(
            id=str(member['id']),
            first_name=member['first_name'],
            email=member['email']
        )
        for member in family_members
    ]

@router.get("/members", response_model=List[FamilyMember])
async def get_family_members(current_user = Depends(get_current_user)):
    """
    Returns all family members with their contact information including phone numbers.
    """
    family_id = current_user['family_id']
    query = users.select().where(users.c.family_id == family_id)
    family_members_records = await database.fetch_all(query)
    
    return [
        FamilyMember(
            id=str(member['id']),
            first_name=member['first_name'],
            last_name=member['last_name'],
            email=member['email'],
            phone_number=member['phone_number'],
            status=member['status'],
            last_signed_in=member['last_signed_in'].isoformat() if member['last_signed_in'] else None,
            last_known_location=member['last_known_location'],
            last_known_location_timestamp=member['last_known_location_timestamp'].isoformat() if member['last_known_location_timestamp'] else None
        ) for member in family_members_records
    ]

@router.post("/request-location/{target_user_id}")
async def request_location(target_user_id: str, current_user = Depends(get_current_user)):
    """
    Send a silent push notification to request a user's location.
    """
    import json
    import uuid as uuid_module
    import boto3
    from backend.core.config import settings
    
    if not settings.SNS_PLATFORM_APPLICATION_ARN:
        logger.warning("SNS client not configured. Cannot send location request.")
        raise HTTPException(status_code=500, detail="Notification service is not configured.")

    try:
        target_user_uuid = uuid_module.UUID(target_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid target user ID format.")

    # Fetch the target user's SNS endpoint ARN
    user_query = users.select().where(users.c.id == target_user_uuid)
    target_user = await database.fetch_one(user_query)

    if not target_user or not target_user['sns_endpoint_arn']:
        logger.warning(f"Target user {target_user_id} not found or has no SNS endpoint.")
        raise HTTPException(status_code=404, detail="Target user not found or not registered for notifications.")

    # Construct the special APNS payload for a silent location request
    aps_payload = {
        "aps": {
            "content-available": 1
        },
        "type": "location_request",
        "requester_name": current_user['first_name']
    }

    platform_key = "APNS_SANDBOX" if "APNS_SANDBOX" in settings.SNS_PLATFORM_APPLICATION_ARN else "APNS"
    message = {
        platform_key: json.dumps(aps_payload)
    }

    try:
        sns_client = boto3.client('sns', region_name='us-east-1')
        logger.info(f"Sending location request to user {target_user_id} from user {current_user['id']}")
        sns_client.publish(
            TargetArn=target_user['sns_endpoint_arn'],
            Message=json.dumps(message),
            MessageStructure='json'
        )
        return {"status": "success", "message": "Location request sent."}
    except Exception as e:
        logger.error(f"Failed to send location request via SNS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to send location request.")
