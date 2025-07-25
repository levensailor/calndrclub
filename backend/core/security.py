import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings
from core.database import database
from db.models import users

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    # Use UTC timezone explicitly and convert to timestamp
    now_utc = datetime.now(timezone.utc)
    expire_utc = now_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Convert to Unix timestamp for JWT standard
    expire_timestamp = expire_utc.timestamp()
    
    to_encode.update({
        "exp": expire_timestamp,
        "iat": now_utc.timestamp(),  # Issued at time
        "iss": "calndr-backend"  # Issuer
    })
    
    print(f"🔐 Backend: Creating token - issued: {now_utc}, expires: {expire_utc} (timestamp: {expire_timestamp})")
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def uuid_to_string(uuid_obj) -> str:
    """Convert UUID to standardized lowercase string format for consistent comparisons."""
    return str(uuid_obj).lower()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Enhanced logging for debugging
        print(f"🔐 Backend: Validating token (length: {len(token)})")
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        
        print(f"🔐 Backend: Token decoded successfully, user_id: {user_id}")
        print(f"🔐 Backend: Token payload: {payload}")
        
        if user_id is None:
            print("🔐❌ Backend: No 'sub' field in token payload")
            raise credentials_exception
            
    except JWTError as e:
        print(f"🔐❌ Backend: JWT validation failed: {type(e).__name__}: {e}")
        raise credentials_exception
    
    try:
        # Convert string UUID to UUID object for database query
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError as e:
            print(f"🔐❌ Backend: Invalid UUID format for user_id '{user_id}': {e}")
            raise credentials_exception
        
        query = users.select().where(users.c.id == user_uuid)
        user = await database.fetch_one(query)
        
        if user is None:
            print(f"🔐❌ Backend: User {user_id} not found in database")
            raise credentials_exception
        
        print(f"🔐✅ Backend: User {user_id} authenticated successfully")
        return user
        
    except Exception as e:
        print(f"🔐❌ Backend: Database error during user lookup: {e}")
        raise credentials_exception
