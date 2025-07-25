import boto3
import random
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from core.config import settings
from core.logging import logger

class PhoneVerificationService:
    """Service for phone number verification via SMS PIN."""
    
    def __init__(self):
        try:
            self.sns_client = boto3.client('sns', region_name=settings.AWS_REGION)
        except Exception as e:
            logger.error(f"Failed to initialize AWS SNS client for phone verification: {e}")
            self.sns_client = None
        
        # In-memory storage for PINs (in production, use Redis or database)
        # Format: {phone_number: {"pin": "123456", "expires_at": datetime, "attempts": 0}}
        self.pin_storage: Dict[str, Dict] = {}
        
        # Configuration
        self.pin_length = 6
        self.pin_expiry_minutes = 10
        self.max_attempts = 3
        self.resend_cooldown_seconds = 60

    def _generate_pin(self) -> str:
        """Generate a random 6-digit PIN."""
        return ''.join([str(random.randint(0, 9)) for _ in range(self.pin_length)])

    def _clean_phone_number(self, phone_number: str) -> str:
        """Clean and format phone number."""
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, phone_number))
        
        # Add country code if not present (assuming US +1)
        if len(cleaned) == 10:
            cleaned = f"1{cleaned}"
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            pass  # Already has country code
        else:
            raise ValueError("Invalid phone number format")
        
        return f"+{cleaned}"

    def _is_rate_limited(self, phone_number: str) -> bool:
        """Check if phone number is rate limited for resending."""
        if phone_number not in self.pin_storage:
            return False
            
        pin_data = self.pin_storage[phone_number]
        last_sent = pin_data.get('last_sent')
        
        if last_sent:
            time_since_last = datetime.now(timezone.utc) - last_sent
            return time_since_last.total_seconds() < self.resend_cooldown_seconds
        
        return False

    async def send_verification_pin(self, phone_number: str) -> Dict[str, any]:
        """
        Send a verification PIN to the phone number.
        Returns success status and message.
        """
        try:
            # Clean phone number
            cleaned_phone = self._clean_phone_number(phone_number)
            
            # Check rate limiting
            if self._is_rate_limited(cleaned_phone):
                return {
                    "success": False,
                    "message": f"Please wait {self.resend_cooldown_seconds} seconds before requesting another PIN",
                    "retry_after": self.resend_cooldown_seconds
                }
            
            # Check SNS client
            if not self.sns_client:
                logger.error("SNS client not configured for phone verification")
                return {
                    "success": False,
                    "message": "SMS service not available"
                }
            
            # Generate PIN
            pin = self._generate_pin()
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.pin_expiry_minutes)
            
            # Store PIN data
            self.pin_storage[cleaned_phone] = {
                "pin": pin,
                "expires_at": expires_at,
                "attempts": 0,
                "last_sent": datetime.now(timezone.utc)
            }
            
            # Send SMS
            message = f"Your Calndr verification code is: {pin}. This code expires in {self.pin_expiry_minutes} minutes."
            
            try:
                response = self.sns_client.publish(
                    PhoneNumber=cleaned_phone,
                    Message=message
                )
                
                logger.info(f"Verification PIN sent to {cleaned_phone[-4:]}****")
                
                return {
                    "success": True,
                    "message": f"Verification code sent to {cleaned_phone[-4:]}****",
                    "expires_in": self.pin_expiry_minutes * 60  # seconds
                }
                
            except Exception as e:
                logger.error(f"Failed to send SMS to {cleaned_phone}: {e}")
                return {
                    "success": False,
                    "message": "Failed to send verification code. Please try again."
                }
                
        except ValueError as e:
            return {
                "success": False,
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"Error in send_verification_pin: {e}")
            return {
                "success": False,
                "message": "An error occurred. Please try again."
            }

    async def verify_pin(self, phone_number: str, pin: str) -> Dict[str, any]:
        """
        Verify the PIN for a phone number.
        Returns success status and message.
        """
        try:
            # Clean phone number
            cleaned_phone = self._clean_phone_number(phone_number)
            
            # Check if PIN exists
            if cleaned_phone not in self.pin_storage:
                return {
                    "success": False,
                    "message": "No verification code found. Please request a new one."
                }
            
            pin_data = self.pin_storage[cleaned_phone]
            
            # Check if PIN has expired
            if datetime.now(timezone.utc) > pin_data["expires_at"]:
                # Clean up expired PIN
                del self.pin_storage[cleaned_phone]
                return {
                    "success": False,
                    "message": "Verification code has expired. Please request a new one."
                }
            
            # Check attempt limit
            if pin_data["attempts"] >= self.max_attempts:
                # Clean up PIN after max attempts
                del self.pin_storage[cleaned_phone]
                return {
                    "success": False,
                    "message": "Too many failed attempts. Please request a new verification code."
                }
            
            # Verify PIN
            if pin_data["pin"] == pin.strip():
                # Success - clean up PIN
                del self.pin_storage[cleaned_phone]
                logger.info(f"Phone number {cleaned_phone[-4:]}**** verified successfully")
                return {
                    "success": True,
                    "message": "Phone number verified successfully!"
                }
            else:
                # Increment attempts
                pin_data["attempts"] += 1
                remaining_attempts = self.max_attempts - pin_data["attempts"]
                
                if remaining_attempts > 0:
                    return {
                        "success": False,
                        "message": f"Invalid verification code. {remaining_attempts} attempts remaining."
                    }
                else:
                    # Clean up after final attempt
                    del self.pin_storage[cleaned_phone]
                    return {
                        "success": False,
                        "message": "Invalid verification code. Please request a new one."
                    }
                    
        except ValueError as e:
            return {
                "success": False,
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"Error in verify_pin: {e}")
            return {
                "success": False,
                "message": "An error occurred. Please try again."
            }

    def cleanup_expired_pins(self):
        """Clean up expired PINs from storage."""
        now = datetime.now(timezone.utc)
        expired_phones = [
            phone for phone, data in self.pin_storage.items()
            if now > data["expires_at"]
        ]
        
        for phone in expired_phones:
            del self.pin_storage[phone]
        
        if expired_phones:
            logger.info(f"Cleaned up {len(expired_phones)} expired verification PINs")

# Global instance
phone_verification_service = PhoneVerificationService() 