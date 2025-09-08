import logging
import traceback
from datetime import datetime, timedelta
from typing import Optional
import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.sql import func

from core.config import settings
from core.database import database
from core.security import verify_password, create_access_token, get_password_hash, uuid_to_string, get_current_user
from core.logging import logger
from db.models import users, families
from schemas.user import UserProfile, UserRegistration, UserRegistrationResponse, UserRegistrationWithFamily
from services.apple_auth_service import exchange_code as apple_exchange_code
from services.google_auth_service import exchange_code as google_exchange_code, get_user_info as google_get_user_info
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Token URL (used by Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    family_id: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserProfile

router = APIRouter()

@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return access token and user profile."""
    try:
        async with database.transaction():
            query = users.select().where(users.c.email == form_data.username)
            user_record = await database.fetch_one(query)
            
            if not user_record:
                logger.warning(f"Login attempt with non-existent email: {form_data.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not verify_password(form_data.password, user_record["password_hash"]):
                logger.warning(f"Login attempt with incorrect password for user: {form_data.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if user account is active (email verified)
            user_status = getattr(user_record, 'status', 'active')
                
            if user_status == "pending":
                logger.warning(f"Login attempt with unverified email: {form_data.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Please verify your email address before logging in",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Update last_signed_in timestamp
            update_query = users.update().where(users.c.id == user_record['id']).values(last_signed_in=func.now())
            await database.execute(update_query)
            
            # Create access token
            family_id = getattr(user_record, 'family_id', None)
            access_token = create_access_token(
                data={"sub": uuid_to_string(user_record["id"]), "family_id": uuid_to_string(family_id) if family_id else None}
            )

            # Convert user record to a dictionary that can be used by Pydantic
            user_dict = dict(user_record)
            
            # Ensure UUIDs are converted to strings for the UserProfile schema
            user_dict['id'] = uuid_to_string(user_dict.get('id'))
            user_dict['family_id'] = uuid_to_string(user_dict.get('family_id'))

            # Handle nullable boolean fields by providing default values if they are None
            user_dict['enrolled'] = user_dict.get('enrolled') or False
            user_dict['coparent_enrolled'] = user_dict.get('coparent_enrolled') or False
            user_dict['coparent_invited'] = user_dict.get('coparent_invited') or False
            
            # Convert datetime objects to strings
            if user_dict.get('last_signed_in'):
                user_dict['last_signed_in'] = str(user_dict['last_signed_in'])
            if user_dict.get('created_at'):
                user_dict['created_at'] = str(user_dict['created_at'])
            
            # Handle updated_at if it exists in the database
            if 'updated_at' in user_dict:
                if user_dict['updated_at']:
                    user_dict['updated_at'] = str(user_dict['updated_at'])
            
            # Remove updated_at from user_dict if it's not in UserProfile schema
            # This prevents errors if the column exists in DB but not in the schema
            user_dict_filtered = {k: v for k, v in user_dict.items() if k != 'updated_at'}
            
            user_profile = UserProfile(**user_dict_filtered)
            
            return {
                "access_token": access_token, 
                "token_type": "bearer",
                "user": user_profile
            }
            
    except HTTPException:
        # Re-raise HTTP exceptions (like 401) without modification
        raise
    except Exception as db_error:
        logger.error(f"Login database error: {db_error}")
        logger.error(f"Error type: {type(db_error).__name__}")
        logger.error(f"Error details: {str(db_error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Database error during login")

@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(registration_data: UserRegistration):
    """
    Register a new user and create a family if family_name is provided.
    """
    logger.info(f"User registration attempt for email: {registration_data.email}")
    
    try:
        # Add transaction management for user registration database operations
        async with database.transaction():
            # Check if user already exists
            existing_user_query = users.select().where(users.c.email == registration_data.email)
            existing_user = await database.fetch_one(existing_user_query)
            
            if existing_user:
                logger.warning(f"Registration attempt with existing email: {registration_data.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create a new family
            family_id = uuid.uuid4()
            family_name = f"{registration_data.first_name}'s Family"
            
            family_values = {
                "id": family_id,
                "name": family_name
            }
            
            await database.execute(families.insert().values(**family_values))
            logger.info(f"Created new family: {family_name} with ID: {family_id}")
            
            # Create the user
            user_id = uuid.uuid4()
            hashed_password = get_password_hash(registration_data.password)
            
            user_values = {
                "id": user_id,
                "family_id": family_id,
                "first_name": registration_data.first_name,
                "last_name": registration_data.last_name,
                "email": registration_data.email,
                "password_hash": hashed_password,
                "phone_number": registration_data.phone_number,
                "status": "active",  # Default to active since we're not requiring email verification yet
                "enrolled": False,  # New users need to complete onboarding
                "created_at": datetime.utcnow()
            }
            
            await database.execute(users.insert().values(**user_values))
            logger.info(f"Created new user with ID: {user_id}")
            
            # Create access token for the new user
            access_token = create_access_token(
                data={"sub": str(user_id), "family_id": str(family_id)}
            )
            
            # Return the registration response
            return {
                "user_id": str(user_id),
                "family_id": str(family_id),
                "access_token": access_token,
                "token_type": "bearer",
                "message": "User registered successfully",
                "should_skip_onboarding": False,
                "requires_email_verification": False
            }
            
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error during registration")

@router.post("/register-with-family", response_model=UserRegistrationResponse)
async def register_with_family(registration_data: UserRegistrationWithFamily):
    """
    Register a new user with an existing family using an enrollment code.
    """
    logger.info(f"Family registration attempt for email: {registration_data.email}")
    
    try:
        # Add transaction management for user registration database operations
        async with database.transaction():
            # Check if user already exists
            existing_user_query = users.select().where(users.c.email == registration_data.email)
            existing_user = await database.fetch_one(existing_user_query)
            
            if existing_user:
                logger.warning(f"Registration attempt with existing email: {registration_data.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Validate enrollment code
            from db.models import enrollment_codes
            
            if not registration_data.enrollment_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Enrollment code is required"
                )
            
            # Query the enrollment code
            enrollment_code_query = enrollment_codes.select().where(
                enrollment_codes.c.code == registration_data.enrollment_code
            )
            enrollment_code_record = await database.fetch_one(enrollment_code_query)
            
            if not enrollment_code_record:
                logger.warning(f"Invalid enrollment code: {registration_data.enrollment_code}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid enrollment code"
                )
            
            # Get the family ID from the enrollment code
            family_id = enrollment_code_record["family_id"]
            
            # Check if a family ID was provided and it matches the enrollment code's family ID
            if registration_data.family_id and str(family_id) != registration_data.family_id:
                logger.warning(f"Family ID mismatch: provided {registration_data.family_id}, expected {family_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Family ID does not match enrollment code"
                )
            
            # Create the user
            user_id = uuid.uuid4()
            hashed_password = get_password_hash(registration_data.password)
            
            user_values = {
                "id": user_id,
                "family_id": family_id,
                "first_name": registration_data.first_name,
                "last_name": registration_data.last_name,
                "email": registration_data.email,
                "password_hash": hashed_password,
                "phone_number": registration_data.phone_number,
                "status": "active",  # Default to active since we're not requiring email verification yet
                "enrolled": True,  # Users joining with enrollment code are already enrolled
                "coparent_enrolled": True,
                "created_at": datetime.utcnow()
            }
            
            await database.execute(users.insert().values(**user_values))
            logger.info(f"Created new user with ID: {user_id} in family: {family_id}")
            
            # Update the primary user's coparent_enrolled status
            creator_user_id = enrollment_code_record["created_by_user_id"]
            await database.execute(
                users.update()
                .where(users.c.id == creator_user_id)
                .values(coparent_enrolled=True)
            )
            logger.info(f"Updated coparent_enrolled status for user: {creator_user_id}")
            
            # Create access token for the new user
            access_token = create_access_token(
                data={"sub": str(user_id), "family_id": str(family_id)}
            )
            
            # Return the registration response
            return {
                "user_id": str(user_id),
                "family_id": str(family_id),
                "access_token": access_token,
                "token_type": "bearer",
                "message": "User registered successfully and joined family",
                "should_skip_onboarding": True,  # Skip onboarding for users joining with enrollment code
                "requires_email_verification": False
            }
            
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Family registration error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error during registration with family")

@router.post("/verify-enrollment-code")
async def verify_enrollment_code(enrollment_code: str):
    """
    Verify an enrollment code and return the associated family ID.
    """
    try:
        from db.models import enrollment_codes
        
        # Query the enrollment code
        enrollment_code_query = enrollment_codes.select().where(
            enrollment_codes.c.code == enrollment_code
        )
        enrollment_code_record = await database.fetch_one(enrollment_code_query)
        
        if not enrollment_code_record:
            logger.warning(f"Invalid enrollment code verification attempt: {enrollment_code}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid enrollment code"
            )
        
        # Return the family ID associated with the enrollment code
        family_id = enrollment_code_record["family_id"]
        
        return {
            "valid": True,
            "family_id": str(family_id),
            "message": "Valid enrollment code"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Enrollment code verification error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error verifying enrollment code")

@router.post("/refresh-token", response_model=Token)
async def refresh_token(current_token: str):
    """
    Refresh an existing token.
    """
    try:
        # Decode the current token
        payload = jwt.decode(current_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        family_id = payload.get("family_id")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if the user exists
        user_query = users.select().where(users.c.id == user_id)
        user_record = await database.fetch_one(user_query)
        
        if not user_record:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Create a new token
        new_token = create_access_token(data={"sub": user_id, "family_id": family_id})
        
        return {"access_token": new_token, "token_type": "bearer"}
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error refreshing token")

@router.post("/verify-token")
async def verify_token(token: str):
    """
    Verify a token and return the user ID and family ID.
    """
    try:
        # Decode the token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        family_id = payload.get("family_id")
        
        if user_id is None:
            return {"valid": False, "message": "Invalid token"}
        
        # Check if the user exists
        user_query = users.select().where(users.c.id == user_id)
        user_record = await database.fetch_one(user_query)
        
        if not user_record:
            return {"valid": False, "message": "User not found"}
        
        return {
            "valid": True,
            "user_id": user_id,
            "family_id": family_id,
            "message": "Valid token"
        }
        
    except JWTError:
        return {"valid": False, "message": "Invalid token"}
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return {"valid": False, "message": "Error verifying token"}

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user = Depends(get_current_user)
):
    """
    Change the password for the current user.
    """
    try:
        # Get the current user's password hash
        user_query = users.select().where(users.c.id == current_user["id"])
        user_record = await database.fetch_one(user_query)
        
        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify the current password
        if not verify_password(current_password, user_record["password_hash"]):
            raise HTTPException(status_code=400, detail="Incorrect current password")
        
        # Hash the new password
        new_password_hash = get_password_hash(new_password)
        
        # Update the password
        await database.execute(
            users.update()
            .where(users.c.id == current_user["id"])
            .values(password_hash=new_password_hash)
        )
        
        return {"message": "Password updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error changing password")

@router.post("/forgot-password")
async def forgot_password(email: str):
    """
    Send a password reset link to the user's email.
    """
    try:
        # Check if the user exists
        user_query = users.select().where(users.c.email == email)
        user_record = await database.fetch_one(user_query)
        
        if not user_record:
            # Don't reveal that the user doesn't exist for security reasons
            return {"message": "If your email is registered, you will receive a password reset link"}
        
        # Generate a password reset token
        reset_token = create_access_token(
            data={"sub": str(user_record["id"]), "purpose": "password_reset"},
            expires_delta=timedelta(hours=1)  # Short expiration for security
        )
        
        # In a real implementation, send an email with the reset link
        # For now, just log it
        logger.info(f"Password reset token for {email}: {reset_token}")
        
        # TODO: Implement email sending
        
        return {"message": "If your email is registered, you will receive a password reset link"}
        
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        # Don't reveal errors for security reasons
        return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/reset-password")
async def reset_password(token: str, new_password: str):
    """
    Reset a user's password using a reset token.
    """
    try:
        # Decode the token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        purpose = payload.get("purpose")
        
        if user_id is None or purpose != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid token")
        
        # Check if the user exists
        user_query = users.select().where(users.c.id == user_id)
        user_record = await database.fetch_one(user_query)
        
        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Hash the new password
        new_password_hash = get_password_hash(new_password)
        
        # Update the password
        await database.execute(
            users.update()
            .where(users.c.id == user_id)
            .values(password_hash=new_password_hash)
        )
        
        return {"message": "Password reset successfully"}
        
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error resetting password")

@router.post("/apple/callback", include_in_schema=False)
async def apple_callback(request: Request):
    """
    Handles the callback from Apple's sign-in process.
    """
    form_data = await request.form()
    code = form_data.get("code")
    id_token_jwt = form_data.get("id_token")
    user_data_str = form_data.get("user")
    
    if not code:
        logger.error("Apple callback missing authorization code.")
        raise HTTPException(status_code=400, detail="Authorization code is missing.")

    try:
        # Exchange the authorization code for tokens
        token_response = await apple_exchange_code(code)
        
        if "error" in token_response:
            logger.error(f"Apple token exchange failed: {token_response.get('error_description')}")
            raise HTTPException(status_code=400, detail="Apple token exchange failed.")

        apple_id_token = token_response.get("id_token")
        apple_access_token = token_response.get("access_token")
        
        # Decode the ID token to get user information
        decoded_token = jwt.decode(
            apple_id_token, 
            "", 
            options={"verify_signature": False},
            audience=settings.APPLE_CLIENT_ID,
            issuer="https://appleid.apple.com",
            access_token=apple_access_token
        )
        
        apple_user_id = decoded_token.get("sub")
        email = decoded_token.get("email")

        # Handle user data if provided (only on first sign-in)
        first_name, last_name = None, None
        if user_data_str:
            user_data = json.loads(user_data_str)
            if "name" in user_data:
                first_name = user_data["name"].get("firstName")
                last_name = user_data["name"].get("lastName")

        # Check if user exists
        user = await get_user_by_apple_id(apple_user_id)
        if not user:
            # If user not found by Apple ID, check by email
            if email:
                user = await get_user_by_email(email)
                if user:
                    # Link Apple ID to existing account
                    await link_apple_id_to_user(user.id, apple_user_id)
                else:
                    # Create a new user
                    user = await create_social_user(
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        apple_user_id=apple_user_id
                    )
            else:
                # This case happens if Apple doesn't provide an email (e.g., user chose to hide it)
                # and it's their first time signing in. We can't proceed without an email.
                logger.error("Apple sign-in failed: email not provided for a new user.")
                raise HTTPException(status_code=400, detail="Email is required for new users.")

        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "family_id": str(user.family_id) if user.family_id else None}
        )

        # Build redirect URL with token
        redirect_url = f"calndr://login?token={access_token}"
        
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        logger.error(f"Error during Apple callback: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An unexpected error occurred during Apple sign-in.")

@router.post("/google/ios-login", response_model=LoginResponse)
async def google_ios_login(request: Request):
    """
    Handles Google sign-in from the iOS app.
    """
    form_data = await request.form()
    id_token_str = form_data.get("id_token")

    if not id_token_str:
        logger.error("Google iOS login missing ID token.")
        raise HTTPException(status_code=400, detail="ID token is missing.")

    try:
        # Verify the ID token
        id_info = id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID_IOS
        )
        
        google_user_id = id_info.get("sub")
        email = id_info.get("email")
        first_name = id_info.get("given_name")
        last_name = id_info.get("family_name")

        if not email:
            logger.error("Google sign-in failed: email not provided.")
            raise HTTPException(status_code=400, detail="Email is required.")

        # Check if user exists
        user = await get_user_by_google_id(google_user_id)
        if not user:
            user = await get_user_by_email(email)
            if user:
                # Link Google ID to existing account
                await link_google_id_to_user(user.id, google_user_id)
            else:
                # Create new user
                user = await create_social_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    google_user_id=google_user_id
                )

        # Create access token and user profile
        family_id = getattr(user, 'family_id', None)
        access_token = create_access_token(
            data={"sub": uuid_to_string(user.id), "family_id": uuid_to_string(family_id) if family_id else None}
        )
        
        user_dict = dict(user)
        user_dict['id'] = uuid_to_string(user_dict.get('id'))
        user_dict['family_id'] = uuid_to_string(user_dict.get('family_id'))
        user_profile = UserProfile(**user_dict)

        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": user_profile
        }

    except ValueError as e:
        # This can be raised by id_token.verify_oauth2_token
        logger.error(f"Invalid Google ID token: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google ID token.")
    except Exception as e:
        logger.error(f"Error during Google iOS login: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An unexpected error occurred during Google sign-in.")

async def get_user_by_email(email: str):
    query = users.select().where(users.c.email == email)
    return await database.fetch_one(query)

async def get_user_by_apple_id(apple_id: str):
    query = users.select().where(users.c.apple_user_id == apple_id)
    return await database.fetch_one(query)

async def link_apple_id_to_user(user_id: str, apple_id: str):
    query = users.update().where(users.c.id == user_id).values(apple_user_id=apple_id)
    await database.execute(query)

async def get_user_by_google_id(google_id: str):
    query = users.select().where(users.c.google_user_id == google_id)
    return await database.fetch_one(query)

async def link_google_id_to_user(user_id: str, google_id: str):
    query = users.update().where(users.c.id == user_id).values(google_user_id=google_id)
    await database.execute(query)

async def create_social_user(email: str, first_name: str, last_name: str, apple_user_id: str = None, google_user_id: str = None):
    """
    Creates a new user from social login information and a new family for them.
    """
    async with database.transaction():
        # Create a new family for the user
        family_id = uuid.uuid4()
        family_name = f"{first_name}'s Family" if first_name else "New Family"
        family_values = {"id": family_id, "name": family_name}
        await database.execute(families.insert().values(**family_values))
        logger.info(f"Created new family: {family_name} with ID: {family_id}")

        # Create the new user
        user_id = uuid.uuid4()
        user_values = {
            "id": user_id,
            "family_id": family_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "apple_user_id": apple_user_id,
            "google_user_id": google_user_id,
            "status": "active",
            "enrolled": False,
            "created_at": datetime.utcnow()
        }
        await database.execute(users.insert().values(**user_values))
        logger.info(f"Created new user with ID: {user_id} for email: {email}")
        
        # Fetch the newly created user to return it
        query = users.select().where(users.c.id == user_id)
        new_user = await database.fetch_one(query)
        return new_user