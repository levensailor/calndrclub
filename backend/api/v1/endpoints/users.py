import os
import uuid
import boto3
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from botocore.exceptions import ClientError
import traceback

from core.database import database
from core.security import get_current_user, verify_password, get_password_hash, uuid_to_string
from core.logging import logger
from core.config import settings
from db.models import users, user_preferences
from schemas.user import (
    UserProfile, UserUpdate, PasswordUpdate, UserPreferenceUpdate, 
    LocationUpdateRequest, FamilyMember, FamilyMemberEmail
)

router = APIRouter()

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user = Depends(get_current_user)):
    """
    Fetch the current user's profile information.
    """
    try:
        # Get user data from database
        user_record = await database.fetch_one(users.select().where(users.c.id == current_user['id']))
        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Get user preferences
        prefs_query = user_preferences.select().where(user_preferences.c.user_id == current_user['id'])
        user_prefs = await database.fetch_one(prefs_query)
        
        user_dict = dict(user_record)
            
        return UserProfile(
            id=uuid_to_string(user_dict.get('id')),
            first_name=user_dict.get('first_name'),
            last_name=user_dict.get('last_name'),
            email=user_dict.get('email'),
            phone_number=user_dict.get('phone_number'),
            subscription_type=user_dict.get('subscription_type') or "Free",
            subscription_status=user_dict.get('subscription_status') or "Active",
            profile_photo_url=user_dict.get('profile_photo_url'),
            status=user_dict.get('status') or "active",
            enrolled=user_dict.get('enrolled') or False,
            coparent_enrolled=user_dict.get('coparent_enrolled') or False,
            coparent_invited=user_dict.get('coparent_invited') or False,
            last_signed_in=str(user_dict.get('last_signed_in')) if user_dict.get('last_signed_in') else None,
            selected_theme_id=user_prefs['selected_theme_id'] if user_prefs else None,
            created_at=str(user_dict.get('created_at')) if user_dict.get('created_at') else None,
            family_id=uuid_to_string(user_dict.get('family_id'))
        )
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/me", response_model=UserProfile)
async def get_user_profile_legacy(current_user = Depends(get_current_user)):
    """
    Legacy endpoint for backward compatibility.
    """
    return await get_user_profile(current_user)

@router.put("/profile", response_model=UserProfile)
async def update_user_profile(user_update: UserUpdate, current_user = Depends(get_current_user)):
    """
    Update the current user's profile information.
    """
    try:
        # Build update values dictionary with only provided fields
        update_values = {}
        if user_update.first_name is not None:
            update_values['first_name'] = user_update.first_name
        if user_update.last_name is not None:
            update_values['last_name'] = user_update.last_name
        if user_update.email is not None:
            update_values['email'] = user_update.email
        if user_update.phone_number is not None:
            update_values['phone_number'] = user_update.phone_number
        
        # Only perform update if there are fields to update
        if update_values:
            await database.execute(
                users.update().where(users.c.id == current_user['id']).values(**update_values)
            )
            logger.info(f"Updated user profile for user {current_user['id']}: {list(update_values.keys())}")
        
        # Return updated profile
        return await get_user_profile(current_user)
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to update user profile")

@router.put("/me/password")
async def update_user_password(password_update: PasswordUpdate, current_user = Depends(get_current_user)):
    """
    Updates the password for the current authenticated user.
    """
    # Verify current password
    user_record = await database.fetch_one(users.select().where(users.c.id == current_user['id']))
    if not user_record or not verify_password(password_update.current_password, user_record['password_hash']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid current password")
    
    # Hash new password and update
    new_password_hash = get_password_hash(password_update.new_password)
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
        raise HTTPException(status_code=500, detail="An error occurred while registering the device.")
    except Exception as e:
        logger.error(f"Generic error in update_device_token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while registering the device.")

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
    preferences_data: UserPreferenceUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update user preferences, such as selected theme.
    """
    user_id = current_user['id']
    
    try:
        # Validate that the theme exists and is accessible to the user
        from db.models import themes
        theme_query = themes.select().where(
            (themes.c.id == preferences_data.selected_theme_id) & 
            ((themes.c.is_public == True) | (themes.c.created_by_user_id == user_id))
        )
        theme_exists = await database.fetch_one(theme_query)
        
        if theme_exists is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Theme with ID {preferences_data.selected_theme_id} not found or not accessible"
            )
        
        # Check if preferences already exist for this user
        existing_prefs_query = user_preferences.select().where(user_preferences.c.user_id == user_id)
        existing_prefs = await database.fetch_one(existing_prefs_query)
        
        if existing_prefs:
            # Update existing preferences
            update_query = user_preferences.update().where(
                user_preferences.c.user_id == user_id
            ).values(
                selected_theme_id=preferences_data.selected_theme_id
            )
            await database.execute(update_query)
            logger.info(f"Updated theme for user {user_id} to {preferences_data.selected_theme_id}")
        else:
            # Insert new preferences
            insert_query = user_preferences.insert().values(
                user_id=user_id,
                selected_theme_id=preferences_data.selected_theme_id
            )
            await database.execute(insert_query)
            logger.info(f"Set initial theme for user {user_id} to {preferences_data.selected_theme_id}")
            
        return {"status": "success", "message": "Preferences updated successfully"}
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for invalid theme)
        raise
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to update preferences")

@router.post("/location")
async def update_user_location(location_data: LocationUpdateRequest, current_user = Depends(get_current_user)):
    """
    Update the current user's last known location.
    """
    location_str = f"{location_data.latitude},{location_data.longitude}"
    timestamp = datetime.now(timezone.utc)
    
    update_query = users.update().where(users.c.id == current_user['id']).values(
        last_known_location=location_str,
        last_known_location_timestamp=timestamp
    )
    
    try:
        await database.execute(update_query)
        return {"status": "success", "message": "Location updated successfully."}
    except Exception as e:
        logger.error(f"Failed to update user location for user {current_user['id']}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user location.")

@router.post("/profile/photo", response_model=UserProfile)
async def upload_profile_photo(
    photo: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """
    Uploads a profile photo for the current user.
    """
    try:
        # Validate file type
        if not photo.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Generate a unique filename
        file_extension = os.path.splitext(photo.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        object_name = f"profile_photos/{unique_filename}"

        # Upload to S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

        # Read file content
        file_content = await photo.read()

        # Upload to S3
        s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=object_name,
            Body=file_content,
            ContentType=photo.content_type,
            ACL='public-read'  # Make the file publicly accessible
        )

        # Construct the S3 URL
        s3_url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{object_name}"

        # Update user's profile_photo_url in the database
        await database.execute(
            users.update().where(users.c.id == current_user['id']).values(profile_photo_url=s3_url)
        )

        # Re-fetch user to return updated profile
        return await get_user_profile(current_user)
        
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload profile photo: {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"Error uploading profile photo: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to upload profile photo")
