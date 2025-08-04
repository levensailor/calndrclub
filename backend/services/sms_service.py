import boto3
import uuid
from core.config import settings
from core.logging import logger

class SMSService:
    """Service for sending SMS messages via AWS SNS."""
    def __init__(self):
        try:
            self.sns_client = boto3.client('sns', region_name=settings.AWS_REGION)
        except Exception as e:
            logger.error(f"Failed to initialize AWS SNS client for SMS: {e}")
            self.sns_client = None

    async def send_coparent_invitation(self, coparent_phone: str, inviter_name: str, family_id: uuid.UUID) -> bool:
        """Send SMS invitation to coparent."""
        if not self.sns_client:
            logger.warning("SNS client not configured. Cannot send SMS invitation.")
            return False
        
        try:
            message = (
                f"{inviter_name} invited you to join their family on Calndr! "
                "Download the Calndr app and sign up with this phone number to be linked automatically."
            )
            logger.info(f"Sending SMS invitation to {coparent_phone}...")
            self.sns_client.publish(PhoneNumber=coparent_phone, Message=message)
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS invitation to {coparent_phone}: {e}")
            return False

sms_service = SMSService() 