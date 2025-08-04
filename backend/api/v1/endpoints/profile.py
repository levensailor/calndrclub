from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
import os
import uuid
import boto3
from botocore.exceptions import ClientError
import traceback

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import users
from schemas.user import UserProfile

router = APIRouter()

@router.post("/photo", response_model=UserProfile)
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
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )

        # Read file content
        file_content = await photo.read()

        # Upload to S3
        s3_client.put_object(
            Bucket=os.getenv("AWS_S3_BUCKET_NAME"),
            Key=object_name,
            Body=file_content,
            ContentType=photo.content_type,
            ACL='public-read'  # Make the file publicly accessible
        )

        # Construct the S3 URL
        s3_url = f"https://{os.getenv('AWS_S3_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{object_name}"

        # Update user's profile_photo_url in the database
        await database.execute(
            users.update().where(users.c.id == current_user['id']).values(profile_photo_url=s3_url)
        )

        # Re-fetch user to get updated profile_photo_url
        user_record = await database.fetch_one(users.select().where(users.c.id == current_user['id']))
        
        # Get user preferences for selected theme
        from db.models import user_preferences
        prefs_query = user_preferences.select().where(user_preferences.c.user_id == current_user['id'])
        user_prefs = await database.fetch_one(prefs_query)
        
        return UserProfile(
            id=str(user_record['id']),
            first_name=user_record['first_name'],
            last_name=user_record['last_name'],
            email=user_record['email'],
            phone_number=user_record['phone_number'],
            subscription_type=user_record['subscription_type'] or "Free",
            subscription_status=user_record['subscription_status'] or "Active",
            profile_photo_url=user_record['profile_photo_url'],
            status=user_record['status'] or "active",
            last_signed_in=str(user_record['last_signed_in']) if user_record['last_signed_in'] else None,
            selected_theme=user_prefs['selected_theme'] if user_prefs else None,
            created_at=str(user_record['created_at']) if user_record['created_at'] else None
        )
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload profile photo: {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"Error uploading profile photo: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
