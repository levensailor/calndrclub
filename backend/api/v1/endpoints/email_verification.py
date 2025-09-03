from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import random
import string
from datetime import datetime, timedelta, timezone

from core.database import database
from core.logging import logger
from schemas.email_verification import EmailVerificationRequest, EmailVerificationResponse, EmailVerificationConfirm
from services.email_service import email_service

router = APIRouter()

def generate_verification_code() -> str:
    """Generate a 6-digit numeric verification code"""
    return ''.join(random.choices(string.digits, k=6))

@router.post("/send-code", response_model=EmailVerificationResponse)
async def send_verification_code(
    request: EmailVerificationRequest
) -> Dict[str, Any]:
    """
    Send a 6-digit verification code to the user's email address.
    This is used during signup to verify email ownership.
    """
    try:
        # Check if user exists and is not yet verified
        user_query = """
            SELECT id, email, first_name, status 
            FROM users 
            WHERE email = :email
        """
        user = await database.fetch_one(user_query, {"email": request.email})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.status == "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )
        
        # Generate verification code
        code = generate_verification_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)  # 10 minute expiration
        
        # Store or update verification code
        await database.execute(
            """
            INSERT INTO email_verifications (user_id, email, code, expires_at, created_at, updated_at)
            VALUES (:user_id, :email, :code, :expires_at, NOW(), NOW())
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                code = :code, 
                expires_at = :expires_at, 
                updated_at = NOW(),
                attempts = 0
            """,
            {
                "user_id": user.id,
                "email": request.email,
                "code": code,
                "expires_at": expires_at
            }
        )
        
        # Send verification email
        try:
            await email_service.send_verification_email(
                email=request.email,
                name=user.first_name,
                verification_code=code
            )
            
            logger.info(f"Sent verification email to {request.email}")
            
            return {
                "success": True,
                "message": "Verification code sent to your email",
                "expires_in": 600  # 10 minutes in seconds
            }
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {request.email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send verification code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code"
        )

@router.post("/verify-code", response_model=EmailVerificationResponse)
async def verify_email_code(
    request: EmailVerificationConfirm
) -> Dict[str, Any]:
    """
    Verify the 6-digit email verification code and activate the user account.
    """
    try:
        async with database.transaction():
            # Get verification record
            verification_query = """
                SELECT ev.id, ev.user_id, ev.code, ev.expires_at, ev.attempts,
                       u.email, u.status
                FROM email_verifications ev
                JOIN users u ON ev.user_id = u.id
                WHERE ev.email = :email
                ORDER BY ev.created_at DESC
                LIMIT 1
            """
            verification = await database.fetch_one(verification_query, {"email": request.email})
            
            if not verification:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No verification code found for this email"
                )
            
            # Check if code is expired
            if verification.expires_at < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code has expired"
                )
            
            # Check attempt limit
            if verification.attempts >= 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Too many failed attempts. Please request a new code"
                )
            
            # Verify the code
            if verification.code != request.code:
                # Increment attempts
                await database.execute(
                    "UPDATE email_verifications SET attempts = attempts + 1, updated_at = NOW() WHERE id = :id",
                    {"id": verification.id}
                )
                
                remaining_attempts = 3 - (verification.attempts + 1)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid verification code. {remaining_attempts} attempts remaining"
                )
            
            # Code is valid - activate user account
            await database.execute(
                "UPDATE users SET status = 'active' WHERE id = :user_id",
                {"user_id": verification.user_id}
            )
            
            # Mark verification as used
            await database.execute(
                "UPDATE email_verifications SET is_verified = TRUE, verified_at = NOW(), updated_at = NOW() WHERE id = :id",
                {"id": verification.id}
            )
            
            logger.info(f"Email verified successfully for user {verification.user_id}")
            
            return {
                "success": True,
                "message": "Email verified successfully",
                "user_id": str(verification.user_id)
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify email code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email code"
        )

@router.post("/resend-code", response_model=EmailVerificationResponse)
async def resend_verification_code(
    request: EmailVerificationRequest
) -> Dict[str, Any]:
    """
    Resend verification code to the user's email.
    """
    try:
        # Check rate limiting - only allow resend every 60 seconds
        last_sent_query = """
            SELECT created_at 
            FROM email_verifications 
            WHERE email = :email 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        last_sent = await database.fetch_one(last_sent_query, {"email": request.email})
        
        if last_sent and (datetime.now(timezone.utc) - last_sent.created_at).total_seconds() < 60:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait 60 seconds before requesting another code"
            )
        
        # Reuse the send_code logic
        return await send_verification_code(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend verification code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification code"
        )
