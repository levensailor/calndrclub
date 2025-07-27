from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
import uuid

from core.database import database
from core.security import verify_password, create_access_token, get_password_hash, uuid_to_string
from core.logging import logger
from db.models import users, families
from schemas.auth import Token
from schemas.user import UserRegistration, UserRegistrationResponse
from services.email_service import email_service
from services.sms_service import sms_service
import traceback
from fastapi import Request
from jose import jwt
from services.apple_auth_service import exchange_code as apple_exchange_code
from services.google_auth_service import exchange_code as google_exchange_code, get_user_info as google_get_user_info
# from services.facebook_auth_service import get_user_info as facebook_get_user_info
from urllib.parse import urlencode
from core.config import settings
from google.oauth2 import id_token
from google.auth.transport import requests

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return access token."""
    query = users.select().where(users.c.email == form_data.username)
    user = await database.fetch_one(query)
    
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last_signed_in timestamp
    await database.execute(
        users.update().where(users.c.id == user['id']).values(last_signed_in=datetime.now())
    )
    
    access_token = create_access_token(
        data={"sub": uuid_to_string(user["id"]), "family_id": uuid_to_string(user["family_id"])}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(registration_data: UserRegistration):
    """
    Register a new user and create a family if family_name is provided.
    """
    logger.info(f"User registration attempt for email: {registration_data.email}")
    
    try:
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
            
            # Create the user
            user_insert = users.insert().values(
                id=user_id,
                family_id=family_id,
                first_name=registration_data.first_name,
                last_name=registration_data.last_name,
                email=registration_data.email,
                password_hash=password_hash,
                phone_number=registration_data.phone_number,
                subscription_type="Free",
                subscription_status="Active"
            )
            
            await database.execute(user_insert)
            logger.info(f"Created user with ID: {user_id}")
        
        # Create access token for the new user
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

@router.post("/google/ios-login", response_model=Token)
async def google_ios_login(request: Request):
    form = await request.form()
    token = form.get("id_token")
    
    if not token:
        raise HTTPException(status_code=400, detail="id_token is missing")

    try:
        # The library will fetch Google's public keys to verify the signature
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
        
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in Google token")

        first_name = idinfo.get("given_name", "Google")
        last_name = idinfo.get("family_name", "User")

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

    except Exception as e:
        logger.error(f"Google iOS login failed during token verification: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")
