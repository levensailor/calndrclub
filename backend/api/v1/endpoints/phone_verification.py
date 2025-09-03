from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from backend.core.logging import logger
from backend.services.phone_verification_service import phone_verification_service

router = APIRouter()

class SendPinRequest(BaseModel):
    phone_number: str

class VerifyPinRequest(BaseModel):
    phone_number: str
    pin: str

@router.post("/send-pin")
async def send_verification_pin(request: SendPinRequest) -> Dict[str, Any]:
    """
    Send a verification PIN to the provided phone number.
    """
    try:
        logger.info(f"Sending verification PIN to phone ending in {request.phone_number[-4:]}****")
        
        result = await phone_verification_service.send_verification_pin(request.phone_number)
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "expires_in": result.get("expires_in")
            }
        else:
            # Return error but don't raise HTTP exception for rate limiting
            if "retry_after" in result:
                return {
                    "success": False,
                    "message": result["message"],
                    "retry_after": result["retry_after"]
                }
            else:
                raise HTTPException(status_code=400, detail=result["message"])
                
    except Exception as e:
        logger.error(f"Error sending verification PIN: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification code")

@router.post("/verify-pin")
async def verify_phone_pin(request: VerifyPinRequest) -> Dict[str, Any]:
    """
    Verify the PIN for a phone number.
    """
    try:
        logger.info(f"Verifying PIN for phone ending in {request.phone_number[-4:]}****")
        
        result = await phone_verification_service.verify_pin(request.phone_number, request.pin)
        
        return {
            "success": result["success"],
            "message": result["message"]
        }
        
    except Exception as e:
        logger.error(f"Error verifying PIN: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify code")

@router.post("/cleanup-expired")
async def cleanup_expired_pins():
    """
    Admin endpoint to clean up expired PINs.
    """
    try:
        phone_verification_service.cleanup_expired_pins()
        return {"message": "Expired PINs cleaned up successfully"}
    except Exception as e:
        logger.error(f"Error cleaning up expired PINs: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup expired PINs") 