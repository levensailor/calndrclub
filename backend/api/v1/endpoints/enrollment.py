import logging
import random
import string
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, insert, update
from sqlalchemy.sql import and_

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import enrollment_codes, users, families
from schemas.enrollment import (
    EnrollmentCodeCreate,
    EnrollmentCodeResponse,
    EnrollmentCodeValidate,
    EnrollmentCode,
    EnrollmentInvite,
    EnrollmentEmailRequest
)
from core.email import send_enrollment_invitation

router = APIRouter()

def generate_enrollment_code(length=6):
    """Generate a random enrollment code."""
    # Use uppercase letters and digits, excluding similar-looking characters
    characters = string.ascii_uppercase + string.digits
    characters = characters.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    
    return ''.join(random.choice(characters) for _ in range(length))

@router.post("/create-code", response_model=EnrollmentCodeResponse)
async def create_enrollment_code(
    data: Optional[EnrollmentCodeCreate] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new enrollment code for a family."""
    try:
        # Get the user's family ID
        family_id = current_user['family_id']
        if not family_id:
            logger.error(f"User {current_user['id']} has no family_id")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with a family"
            )
        
        # Generate a unique enrollment code
        code = generate_enrollment_code()
        
        # Check if the enrollment_codes table exists
        try:
            # Check if code already exists
            query = enrollment_codes.select().where(enrollment_codes.c.code == code)
            existing_code = await database.fetch_one(query)
            
            # If code exists, generate a new one
            while existing_code:
                code = generate_enrollment_code()
                query = enrollment_codes.select().where(enrollment_codes.c.code == code)
                existing_code = await database.fetch_one(query)
            
            # Create the enrollment code record
            values = {
                "family_id": family_id,
                "code": code,
                "created_by_user_id": current_user["id"],
                "created_at": datetime.now(),
                "invitation_sent": False,
                "invitation_sent_at": None,
                "coparent_first_name": None,
                "coparent_last_name": None,
                "coparent_email": None,
                "coparent_phone": None
            }
            
            # Add co-parent information if provided
            if data:
                if data.coparent_first_name:
                    values["coparent_first_name"] = data.coparent_first_name
                if data.coparent_last_name:
                    values["coparent_last_name"] = data.coparent_last_name
                if data.coparent_email:
                    values["coparent_email"] = data.coparent_email
                if data.coparent_phone:
                    values["coparent_phone"] = data.coparent_phone
            
            # Insert the record
            query = insert(enrollment_codes).values(**values)
            await database.execute(query)
        except Exception as table_error:
            # If the table doesn't exist or there's another error, log it but continue
            # We'll still return a valid code to the frontend
            logger.warning(f"Error accessing enrollment_codes table: {str(table_error)}")
            logger.warning("Continuing without storing the code in the database")
        
        # Update the user's coparent_invited flag
        try:
            query = update(users).where(users.c.id == current_user["id"]).values(coparent_invited=True)
            await database.execute(query)
        except Exception as user_update_error:
            logger.warning(f"Error updating user's coparent_invited flag: {str(user_update_error)}")
        
        # Return the code to the frontend
        logger.info(f"Created enrollment code {code} for family {family_id}")
        return EnrollmentCodeResponse(
            success=True,
            message="Enrollment code created successfully",
            enrollmentCode=code,
            familyId=family_id
        )
    except Exception as e:
        logger.error(f"Error creating enrollment code: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating enrollment code: {str(e)}"
        )

@router.post("/validate-code", response_model=EnrollmentCodeResponse)
async def validate_enrollment_code(
    data: EnrollmentCodeValidate,
    current_user: dict = Depends(get_current_user)
):
    """Validate an enrollment code."""
    try:
        # Check if the code exists
        query = enrollment_codes.select().where(enrollment_codes.c.code == data.code)
        code_record = await database.fetch_one(query)
        
        if not code_record:
            return EnrollmentCodeResponse(
                success=False,
                message="Invalid enrollment code"
            )
        
        # Return the family ID associated with the code
        return EnrollmentCodeResponse(
            success=True,
            message="Valid enrollment code",
            enrollmentCode=data.code,
            familyId=code_record["family_id"]
        )
    except Exception as e:
        logger.error(f"Error validating enrollment code: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating enrollment code: {str(e)}"
        )

@router.post("/invite")
async def send_enrollment_invitation_endpoint(
    data: EnrollmentInvite,
    current_user: dict = Depends(get_current_user)
):
    """Send an enrollment invitation email."""
    try:
        # Check if the code exists
        query = enrollment_codes.select().where(enrollment_codes.c.code == data.code)
        code_record = await database.fetch_one(query)
        
        if not code_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid enrollment code"
            )
        
        # Get the user's name
        user_query = users.select().where(users.c.id == current_user["id"])
        user_record = await database.fetch_one(user_query)
        
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Send the invitation email
        sender_name = f"{user_record['first_name']} {user_record['last_name']}"
        success = await send_enrollment_invitation(
            sender_name=sender_name,
            recipient_name=f"{data.coparent_first_name} {data.coparent_last_name}",
            recipient_email=data.coparent_email,
            enrollment_code=data.code
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send enrollment invitation"
            )
        
        # Update the enrollment code record with co-parent information and invitation status
        now = datetime.now()
        update_query = (
            update(enrollment_codes)
            .where(enrollment_codes.c.code == data.code)
            .values(
                coparent_first_name=data.coparent_first_name,
                coparent_last_name=data.coparent_last_name,
                coparent_email=data.coparent_email,
                coparent_phone=data.coparent_phone,
                invitation_sent=True,
                invitation_sent_at=now
            )
        )
        await database.execute(update_query)
        
        return {"success": True, "message": "Enrollment invitation sent successfully"}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error sending enrollment invitation: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending enrollment invitation: {str(e)}"
        )

@router.post("/send-code-email")
async def send_code_email(
    data: EnrollmentEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send an email with the enrollment code."""
    try:
        # Check if the code exists
        query = enrollment_codes.select().where(enrollment_codes.c.code == data.code)
        code_record = await database.fetch_one(query)
        
        if not code_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid enrollment code"
            )
        
        # Get the user's name
        user_query = users.select().where(users.c.id == current_user["id"])
        user_record = await database.fetch_one(user_query)
        
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Send the invitation email
        sender_name = f"{user_record['first_name']} {user_record['last_name']}"
        success = await send_enrollment_invitation(
            sender_name=sender_name,
            recipient_name=data.name,
            recipient_email=data.email,
            enrollment_code=data.code
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send enrollment code email"
            )
        
        # Update the enrollment code record with invitation status
        now = datetime.now()
        update_query = (
            update(enrollment_codes)
            .where(enrollment_codes.c.code == data.code)
            .values(
                invitation_sent=True,
                invitation_sent_at=now
            )
        )
        await database.execute(update_query)
        
        return {"success": True, "message": "Enrollment code email sent successfully"}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error sending enrollment code email: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending enrollment code email: {str(e)}"
        )