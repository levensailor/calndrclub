from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile, Body
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError
import re
import traceback
import logging
import uuid
from backend.core.config import settings
from backend.core.security import get_current_user, get_password_hash, verify_password
from backend.core.database import database
from backend.db.models import users, user_preferences, user_profiles, families
from backend.schemas.user import UserCreate, UserUpdate, UserResponse, UserProfile, UserProfileUpdate, UserPreferences, EnrollmentStatusUpdate
from backend.schemas.family import FamilyCreate, FamilyResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user."""
    # Check if email already exists
    existing_user = await database.fetch_one(
        users.select().where(users.c.email == user.email)
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create a new family for the user
    family_id = str(uuid.uuid4())
    await database.execute(
        families.insert().values(
            id=family_id,
            name=f"{user.first_name}'s Family",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    )

    # Hash the password
    hashed_password = get_password_hash(user.password)

    # Create the user
    user_id = str(uuid.uuid4())
    await database.execute(
        users.insert().values(
            id=user_id,
            email=user.email,
            password_hash=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            family_id=family_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_signed_in=datetime.now(),
            enrolled=False
        )
    )

    # Create default user preferences
    await database.execute(
        user_preferences.insert().values(
            user_id=user_id,
            theme="default",
            notification_preferences={"email": True, "push": True, "sms": False},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    )

    # Create user profile
    await database.execute(
        user_profiles.insert().values(
            user_id=user_id,
            bio="",
            profile_photo_url="",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    )

    # Return the created user
    return {
        "id": user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "family_id": family_id,
        "status": "active"
    }

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user = Depends(get_current_user)):
    """Get current user profile."""
    user_data = await database.fetch_one(
        users.select().where(users.c.id == current_user['id'])
    )
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user preferences
    preferences_data = await database.fetch_one(
        user_preferences.select().where(user_preferences.c.user_id == current_user['id'])
    )
    
    # Get user profile
    profile_data = await database.fetch_one(
        user_profiles.select().where(user_profiles.c.user_id == current_user['id'])
    )
    
    # Combine data
    user_profile = {
        "id": user_data['id'],
        "email": user_data['email'],
        "first_name": user_data['first_name'],
        "last_name": user_data['last_name'],
        "phone_number": user_data['phone_number'],
        "family_id": user_data['family_id'],
        "enrolled": user_data['enrolled'],
        "coparent_enrolled": user_data.get('coparent_enrolled', False),
        "coparent_invited": user_data.get('coparent_invited', False),
        "bio": profile_data['bio'] if profile_data else "",
        "profile_photo_url": user_data['profile_photo_url'] or (profile_data['profile_photo_url'] if profile_data else ""),
        "theme": preferences_data['theme'] if preferences_data else "default",
        "notification_preferences": preferences_data['notification_preferences'] if preferences_data else {"email": True, "push": True, "sms": False},
        "created_at": user_data['created_at'],
        "updated_at": user_data['updated_at']
    }
    
    return user_profile

@router.put("/profile", response_model=UserProfile)
async def update_user_profile(user_update: UserProfileUpdate, current_user = Depends(get_current_user)):
    """Update user profile."""
    # Update user table
    user_update_values = {}
    if user_update.first_name is not None:
        user_update_values["first_name"] = user_update.first_name
    if user_update.last_name is not None:
        user_update_values["last_name"] = user_update.last_name
    if user_update.phone_number is not None:
        user_update_values["phone_number"] = user_update.phone_number
    if user_update.enrolled is not None:
        user_update_values["enrolled"] = user_update.enrolled
    
    if user_update_values:
        user_update_values["updated_at"] = datetime.now()
        await database.execute(
            users.update().where(users.c.id == current_user['id']).values(**user_update_values)
        )
    
    # Update user_profiles table
    profile_update_values = {}
    if user_update.bio is not None:
        profile_update_values["bio"] = user_update.bio
    if user_update.profile_photo_url is not None:
        profile_update_values["profile_photo_url"] = user_update.profile_photo_url
    
    if profile_update_values:
        profile_update_values["updated_at"] = datetime.now()
        # Check if profile exists
        profile = await database.fetch_one(
            user_profiles.select().where(user_profiles.c.user_id == current_user['id'])
        )
        
        if profile:
            await database.execute(
                user_profiles.update().where(user_profiles.c.user_id == current_user['id']).values(**profile_update_values)
            )
        else:
            profile_update_values["user_id"] = current_user['id']
            profile_update_values["created_at"] = datetime.now()
            await database.execute(
                user_profiles.insert().values(**profile_update_values)
            )
    
    # Update user_preferences table
    preferences_update_values = {}
    if user_update.theme is not None:
        preferences_update_values["theme"] = user_update.theme
    if user_update.notification_preferences is not None:
        preferences_update_values["notification_preferences"] = user_update.notification_preferences
    
    if preferences_update_values:
        preferences_update_values["updated_at"] = datetime.now()
        # Check if preferences exist
        preferences = await database.fetch_one(
            user_preferences.select().where(user_preferences.c.user_id == current_user['id'])
        )
        
        if preferences:
            await database.execute(
                user_preferences.update().where(user_preferences.c.user_id == current_user['id']).values(**preferences_update_values)
            )
        else:
            preferences_update_values["user_id"] = current_user['id']
            preferences_update_values["created_at"] = datetime.now()
            await database.execute(
                user_preferences.insert().values(**preferences_update_values)
            )
    
    # Return updated profile
    return await get_current_user_profile(current_user)

@router.put("/password")
async def update_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user = Depends(get_current_user)
):
    """Update user password."""
    # Get current user with password hash
    user_data = await database.fetch_one(
        users.select().where(users.c.id == current_user['id'])
    )
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(current_password, user_data['password_hash']):
        raise HTTPException(status_code=403, detail="Invalid current password")
    
    # Hash new password
    new_password_hash = get_password_hash(new_password)
    
    # Update password
    await database.execute(
        users.update().where(users.c.id == current_user['id']).values(password_hash=new_password_hash)
    )
    
    return {"status": "success", "message": "Password updated successfully"}

@router.post("/me/device-token")
async def update_device_token(token: str = Form(...), current_user = Depends(get_current_user)):
    """Update device token for push notifications."""
    if not settings.SNS_PLATFORM_APPLICATION_ARN:
        logger.error("SNS client or Platform Application ARN not configured. Cannot update device token.")
        raise HTTPException(status_code=500, detail="Notification service is not configured.")
    
    try:
        sns_client = boto3.client('sns', region_name='us-east-1')
        logger.info(f"Creating platform endpoint for user {current_user['id']} with token {token[:10]}...")
        response = sns_client.create_platform_endpoint(
            PlatformApplicationArn=settings.SNS_PLATFORM_APPLICATION_ARN,
            Token=token,
            CustomUserData=f"User ID: {current_user['id']}"
        )
        endpoint_arn = response.get('EndpointArn')
        
        if not endpoint_arn:
            logger.error("Failed to create platform endpoint: 'EndpointArn' not in response.")
            raise HTTPException(status_code=500, detail="Failed to register device for notifications.")

        logger.info(f"Successfully created endpoint ARN: {endpoint_arn}")
        await database.execute(
            users.update().where(users.c.id == current_user['id']).values(sns_endpoint_arn=endpoint_arn)
        )
        return {"status": "success", "endpoint_arn": endpoint_arn}

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        error_message = e.response.get("Error", {}).get("Message")
        
        # This regex finds an existing EndpointArn in the error message
        import re
        match = re.search(r'(arn:aws:sns:.*)', error_message)
        if error_code == 'InvalidParameter' and 'Endpoint already exists' in error_message and match:
            endpoint_arn = match.group(1)
            logger.warning(f"Endpoint already exists. Updating token for existing ARN: {endpoint_arn}")
            
            try:
                # Update the token for the existing endpoint
                sns_client.set_endpoint_attributes(
                    EndpointArn=endpoint_arn,
                    Attributes={'Token': token, 'Enabled': 'true'}
                )
                await database.execute(
                    users.update().where(users.c.id == current_user['id']).values(sns_endpoint_arn=endpoint_arn)
                )
                return {"status": "success", "endpoint_arn": endpoint_arn}
            except ClientError as update_e:
                logger.error(f"Failed to update existing endpoint attributes: {update_e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to update device registration.")
        
        logger.error(f"Boto3 ClientError in update_device_token: {e}", exc_info=True)
        # Return a specific error for the frontend to handle
        if error_code == 'InvalidParameter' and 'Endpoint already exists' in error_message:
            raise HTTPException(status_code=409, detail=f"Endpoint already exists with the same Token, but different attributes: {error_message}")
        else:
            raise HTTPException(status_code=500, detail=f"An error occurred while registering the device: {error_message}")
    except Exception as e:
        logger.error(f"Generic error in update_device_token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while registering the device.")

@router.post("/me/update-endpoint")
async def update_platform_endpoint(endpoint_arn: str = Body(...), token: str = Body(...), current_user = Depends(get_current_user)):
    """Update an existing SNS platform endpoint and associate it with the current user."""
    if not settings.SNS_PLATFORM_APPLICATION_ARN:
        logger.error("SNS client or Platform Application ARN not configured.")
        raise HTTPException(status_code=500, detail="Notification service is not configured.")
    
    try:
        sns_client = boto3.client('sns', region_name='us-east-1')
        logger.info(f"Updating platform endpoint {endpoint_arn} for user {current_user['id']} with token {token[:10]}...")
        
        # Update the endpoint attributes
        sns_client.set_endpoint_attributes(
            EndpointArn=endpoint_arn,
            Attributes={
                'Token': token,
                'Enabled': 'true',
                'CustomUserData': f"User ID: {current_user['id']}"
            }
        )
        
        # Update the user's record with the endpoint ARN
        await database.execute(
            users.update().where(users.c.id == current_user['id']).values(sns_endpoint_arn=endpoint_arn)
        )
        
        return {"status": "success", "message": "Endpoint updated successfully", "endpoint_arn": endpoint_arn}
    
    except ClientError as e:
        logger.error(f"Boto3 ClientError in update_platform_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update endpoint: {str(e)}")
    except Exception as e:
        logger.error(f"Generic error in update_platform_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while updating the device endpoint.")

@router.post("/me/last-signin")
async def update_last_signin(current_user = Depends(get_current_user)):
    """
    Update the user's last_signed_in timestamp to the current time.
    This should be called when the app becomes active.
    """
    try:
        await database.execute(
            users.update().where(users.c.id == current_user['id']).values(last_signed_in=datetime.now())
        )
        return {"message": "Last signin time updated successfully"}
    except Exception as e:
        logger.error(f"Error updating last signin time: {e}")
        raise HTTPException(status_code=500, detail="Failed to update last signin time")

@router.put("/preferences")
async def update_user_preferences(
    preferences: UserPreferences,
    current_user = Depends(get_current_user)
):
    """Update user preferences."""
    try:
        # Check if preferences exist
        existing_preferences = await database.fetch_one(
            user_preferences.select().where(user_preferences.c.user_id == current_user['id'])
        )
        
        update_values = {
            "theme": preferences.theme,
            "notification_preferences": preferences.notification_preferences,
            "updated_at": datetime.now()
        }
        
        if existing_preferences:
            await database.execute(
                user_preferences.update()
                .where(user_preferences.c.user_id == current_user['id'])
                .values(**update_values)
            )
        else:
            update_values["user_id"] = current_user['id']
            update_values["created_at"] = datetime.now()
            await database.execute(
                user_preferences.insert().values(**update_values)
            )
        
        return {"status": "success", "message": "Preferences updated successfully"}
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update preferences")

@router.put("/enrollment-status")
async def update_enrollment_status(status_update: EnrollmentStatusUpdate, current_user = Depends(get_current_user)):
    """
    Update the user's enrollment status.
    """
    try:
        await database.execute(
            users.update().where(users.c.id == current_user['id']).values(enrolled=status_update.enrolled)
        )
        logger.info(f"Updated enrollment status for user {current_user['id']} to {status_update.enrolled}")
        return {"status": "success", "message": "Enrollment status updated successfully"}
    except Exception as e:
        logger.error(f"Error updating enrollment status: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to update enrollment status")

@router.post("/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload a profile photo."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read the file content
        contents = await file.read()
        
        # Generate a unique filename
        filename = f"{current_user['id']}-{uuid.uuid4()}-{file.filename}"
        
        # Upload to S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=f"profile-photos/{filename}",
            Body=contents,
            ContentType=file.content_type
        )
        
        # Generate the URL
        photo_url = f"https://{settings.S3_BUCKET_NAME}.s3.amazonaws.com/profile-photos/{filename}"
        
        # Update the user's profile in the users table
        await database.execute(
            users.update()
            .where(users.c.id == current_user['id'])
            .values(profile_photo_url=photo_url, updated_at=datetime.now())
        )
        
        # Also update user_profiles if it exists
        profile = await database.fetch_one(
            user_profiles.select().where(user_profiles.c.user_id == current_user['id'])
        )
        
        if profile:
            await database.execute(
                user_profiles.update()
                .where(user_profiles.c.user_id == current_user['id'])
                .values(profile_photo_url=photo_url, updated_at=datetime.now())
            )
        else:
            await database.execute(
                user_profiles.insert().values(
                    user_id=current_user['id'],
                    profile_photo_url=photo_url,
                    bio="",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            )
        
        return {"url": photo_url}
    except Exception as e:
        logger.error(f"Error uploading profile photo: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload profile photo")