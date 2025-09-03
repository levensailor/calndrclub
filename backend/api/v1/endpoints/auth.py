from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timezone
import uuid
import asyncio
from pydantic import BaseModel
from sqlalchemy import func

from backend.core.database import database
from backend.core.security import verify_password, create_access_token, get_password_hash, uuid_to_string
from backend.core.logging import logger
from backend.db.models import users, families
from backend.schemas.auth import Token
from backend.schemas.user import UserProfile, UserRegistration, UserRegistrationResponse, UserRegistrationWithFamily
from backend.schemas.auth import LoginAfterVerificationRequest
from backend.services.email_service import email_service
from backend.services.sms_service import sms_service
import traceback
from fastapi import Request
from jose import jwt
from backend.services.apple_auth_service import exchange_code as apple_exchange_code
from backend.services.google_auth_service import exchange_code as google_exchange_code, get_user_info as google_get_user_info
# from backend.services.facebook_auth_service import get_user_info as facebook_get_user_info
from urllib.parse import urlencode
from backend.core.config import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from typing import Dict, Any

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

            user_profile = UserProfile(**user_dict)
            
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
            
            # If user exists and is not invited, return conflict
            if existing_user and existing_user.get('status') != 'invited':
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists"
                )
            
            # Hash the password
            password_hash = get_password_hash(registration_data.password)
            
            should_skip_onboarding = False
            
            if existing_user and existing_user.get('status') == 'invited':
                # User was invited - update their record with password and mark as active
                user_id = existing_user['id']
                family_id = existing_user['family_id']
                should_skip_onboarding = True
                
                user_update = users.update().where(users.c.id == user_id).values(
                    password_hash=password_hash,
                    phone_number=registration_data.phone_number,
                    status="active",
                    subscription_type="Free",
                    subscription_status="Active"
                )
                await database.execute(user_update)
                logger.info(f"Updated invited user with ID: {user_id}")
            else:
                # New user - create new family and user
                family_id = uuid.uuid4()
                family_name = f"{registration_data.last_name} Family"
                family_insert = families.insert().values(id=family_id, name=family_name)
                await database.execute(family_insert)
                logger.info(f"Created new family: {family_name} with ID: {family_id}")
                
                # Generate UUID for the user
                user_id = uuid.uuid4()
                
                # Create the user in pending status (requires email verification)
                user_insert = users.insert().values(
                    id=user_id,
                    family_id=family_id,
                    first_name=registration_data.first_name,
                    last_name=registration_data.last_name,
                    email=registration_data.email,
                    password_hash=password_hash,
                    phone_number=registration_data.phone_number,
                    status="pending",  # Requires email verification
                    subscription_type="Free",
                    subscription_status="Active"
                )
                
                await database.execute(user_insert)
                logger.info(f"Created user with ID: {user_id}")
        
        # Handle different user statuses
        if existing_user and existing_user.get('status') == 'invited':
            # Invited users are immediately active - create access token
            access_token = create_access_token(
                data={"sub": uuid_to_string(user_id), "family_id": uuid_to_string(family_id)}
            )
            
            return UserRegistrationResponse(
                token_type="bearer",
                user_id=uuid_to_string(user_id),
                family_id=uuid_to_string(family_id),
                access_token=access_token,
                message="User registered successfully",
                should_skip_onboarding=should_skip_onboarding
            )
        else:
            # New users need email verification - don't create access token yet
            return UserRegistrationResponse(
                token_type="bearer",
                user_id=uuid_to_string(user_id),
                family_id=uuid_to_string(family_id),
                access_token="",  # Empty token - requires verification
                message="Please check your email for a verification code",
                should_skip_onboarding=False,
                requires_email_verification=True
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )

@router.post("/apple/server-notify", status_code=204)
async def apple_server_notification(request: Request):
    """Endpoint that Apple calls for server-to-server notifications (e.g., subscription events)."""
    # For now, we'll just log the request and return a 204
    body = await request.body()
    logger.info(f"Received Apple server-to-server notification: {body.decode()}")
    return

@router.get("/apple/login")
async def apple_login():
    """Return the Apple auth URL for the frontend."""
    params = {
        "client_id": settings.APPLE_CLIENT_ID,
        "redirect_uri": settings.APPLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "name email",
        "response_mode": "form_post",
    }
    url = "https://appleid.apple.com/auth/authorize?" + urlencode(params)
    return {"auth_url": url}

@router.post("/apple/callback", response_model=Token)
async def apple_callback(request: Request):
    form = await request.form()
    code = form.get("code")
    
    logger.info(f"Received Apple auth code: {code}")
    
    try:
        tokens = await apple_exchange_code(code)
        logger.info(f"Received tokens from Apple: {tokens}")
    except Exception as e:
        logger.error(f"Error exchanging Apple auth code: {e}")
        raise HTTPException(status_code=500, detail="Error exchanging Apple auth code")

    id_token = tokens.get("id_token")
    if not id_token:
        logger.error("No id_token in Apple response")
        raise HTTPException(status_code=500, detail="No id_token in Apple response")
        
    claims = jwt.get_unverified_claims(id_token)

    email      = claims.get("email")
    first_name = claims.get("given_name", "Apple")
    last_name  = claims.get("family_name", "User")

    # 1) Lookup existing user by email
    query = users.select().where(users.c.email == email)
    existing = await database.fetch_one(query)

    if existing:
        user_id   = existing["id"]
        family_id = existing["family_id"]
    else:
        # 2) Create new user & family
        family_id = uuid.uuid4()
        await database.execute(families.insert().values(id=family_id, name=f"{last_name} Family"))
        user_id = uuid.uuid4()
        await database.execute(users.insert().values(
            id=user_id,
            family_id=family_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash="",          # unused
            subscription_type="Free"
        ))

    access_token = create_access_token(data={"sub": uuid_to_string(user_id),
                                             "family_id": uuid_to_string(family_id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/google/login")
async def google_login():
    """Return the Google auth URL for the frontend."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return {"auth_url": url}

@router.post("/google/callback", response_model=Token)
async def google_callback(request: Request):
    form = await request.form()
    id_token_value = form.get("id_token")
    
    if not id_token_value:
        raise HTTPException(status_code=400, detail="id_token is missing")
    
    logger.info(f"Received Google ID token")
    
    try:
        # Verify the ID token directly (same as ios-login endpoint)
        idinfo = id_token.verify_oauth2_token(id_token_value, requests.Request(), settings.GOOGLE_CLIENT_ID)
        logger.info(f"Received user info from Google ID token: {idinfo}")
        
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in Google token")

        first_name = idinfo.get("given_name", "Google")
        last_name = idinfo.get("family_name", "User")
        
    except Exception as e:
        logger.error(f"Google callback failed during token verification: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    # Add transaction management for Google callback database operations
    try:
        async with database.transaction():
            # 1) Lookup existing user by email
            query = users.select().where(users.c.email == email)
            existing = await database.fetch_one(query)

            if existing:
                user_id   = existing["id"]
                family_id = existing["family_id"]
            else:
                # 2) Create new user & family
                family_id = uuid.uuid4()
                await database.execute(families.insert().values(id=family_id, name=f"{last_name} Family"))
                user_id = uuid.uuid4()
                await database.execute(users.insert().values(
                    id=user_id,
                    family_id=family_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password_hash="",          # unused
                    subscription_type="Free"
                ))
    except Exception as db_error:
        logger.error(f"Google callback database error: {db_error}")
        raise HTTPException(status_code=500, detail="Database error during Google authentication")

    access_token = create_access_token(data={"sub": uuid_to_string(user_id),
                                             "family_id": uuid_to_string(family_id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/google/ios-login", response_model=Token)
async def google_ios_login(request: Request):
    form = await request.form()
    token = form.get("id_token")
    
    if not token:
        raise HTTPException(status_code=400, detail="id_token is missing")

    try:
        # The library will fetch Google's public keys to verify the signature
        # Wrap in asyncio.wait_for to prevent hanging on slow Google API responses
        idinfo = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
            ),
            timeout=20.0  # 20 second timeout for Google token verification
        )
        
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in Google token")

        first_name = idinfo.get("given_name", "Google")
        last_name = idinfo.get("family_name", "User")

        # Add transaction management for Google iOS login database operations
        try:
            async with database.transaction():
                # 1) Lookup existing user by email
                query = users.select().where(users.c.email == email)
                existing = await database.fetch_one(query)

                if existing:
                    user_id   = existing["id"]
                    family_id = existing["family_id"]
                else:
                    # 2) Create new user & family
                    family_id = uuid.uuid4()
                    await database.execute(families.insert().values(id=family_id, name=f"{last_name} Family"))
                    user_id = uuid.uuid4()
                    await database.execute(users.insert().values(
                        id=user_id,
                        family_id=family_id,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        password_hash="",          # unused
                        subscription_type="Free"
                    ))
        except Exception as db_error:
            logger.error(f"Google iOS login database error: {db_error}")
            raise HTTPException(status_code=500, detail="Database error during Google authentication")

        access_token = create_access_token(data={"sub": uuid_to_string(user_id),
                                                 "family_id": uuid_to_string(family_id)})
        return {"access_token": access_token, "token_type": "bearer"}

    except asyncio.TimeoutError:
        logger.error("Google iOS login failed: Google token verification timed out after 20 seconds")
        raise HTTPException(status_code=504, detail="Google authentication service temporarily unavailable. Please try again.")
    except Exception as e:
        logger.error(f"Google iOS login failed during token verification: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

@router.post("/register-with-family", response_model=UserRegistrationResponse)
async def register_user_with_family(registration_data: UserRegistrationWithFamily):
    """
    Register a new user and link them to an existing family using an enrollment code.
    """
    logger.info(f"Family registration attempt for email: {registration_data.email}")
    
    try:
        async with database.transaction():
            # Check if user already exists
            existing_user_query = users.select().where(users.c.email == registration_data.email)
            existing_user = await database.fetch_one(existing_user_query)
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists"
                )
            
            # Validate and use the enrollment code
            code_query = """
                SELECT ec.id, ec.family_id, ec.created_by_user_id, ec.is_used, ec.expires_at,
                       f.id as family_exists
                FROM enrollment_codes ec
                LEFT JOIN families f ON ec.family_id = f.id
                WHERE ec.code = :code
            """
            code_record = await database.fetch_one(code_query, {"code": registration_data.enrollment_code.upper()})
            
            if not code_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invalid enrollment code"
                )
            
            # Check if code is expired
            if code_record.expires_at < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Enrollment code has expired"
                )
            
            # Check if code is already used
            if code_record.is_used:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Enrollment code has already been used"
                )
            
            # Check if family still exists
            if not code_record.family_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Associated family no longer exists"
                )
            
            # Hash the password
            password_hash = get_password_hash(registration_data.password)
            
            # Create new user with family_id from enrollment code
            user_id = uuid.uuid4()
            user_insert = users.insert().values(
                id=user_id,
                email=registration_data.email,
                password_hash=password_hash,
                first_name=registration_data.first_name,
                last_name=registration_data.last_name,
                phone_number=registration_data.phone_number,
                family_id=code_record.family_id,
                status="active",
                subscription_type="Free",
                subscription_status="Active"
            )
            await database.execute(user_insert)
            
            # Mark the enrollment code as used
            update_code_query = """
                UPDATE enrollment_codes 
                SET is_used = TRUE, used_by_user_id = :user_id, updated_at = NOW()
                WHERE code = :code
            """
            await database.execute(update_code_query, {
                "user_id": user_id,
                "code": registration_data.enrollment_code.upper()
            })
            
            logger.info(f"Created user with family enrollment: {user_id}")
            
            # Create access token
            access_token = create_access_token(
                data={"sub": uuid_to_string(user_id), "family_id": uuid_to_string(code_record.family_id)}
            )
            
            # Family enrollment users should skip onboarding since they're joining existing family
            should_skip_onboarding = True
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "shouldSkipOnboarding": should_skip_onboarding
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Family registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login-after-verification")
async def login_after_verification(request: LoginAfterVerificationRequest):
    """
    Create access token for user after email verification is complete.
    """
    try:
        # Get user details
        user_query = """
            SELECT id, family_id, status, first_name, last_name
            FROM users 
            WHERE email = :email
        """
        user = await database.fetch_one(user_query, {"email": request.email})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email verification required"
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": uuid_to_string(user.id), "family_id": uuid_to_string(user.family_id)}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "shouldSkipOnboarding": False  # New users go through onboarding
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login after verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )
