import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError
import os
from core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

async def send_enrollment_invitation(
    sender_name: str,
    recipient_name: str,
    recipient_email: str,
    enrollment_code: str
) -> bool:
    """
    Send an enrollment invitation email to a co-parent.
    
    Args:
        sender_name: The name of the person sending the invitation
        recipient_name: The name of the recipient
        recipient_email: The recipient's email address
        enrollment_code: The enrollment code to include in the email
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    try:
        # Log the email that would be sent
        logger.info(f"Sending enrollment invitation to {recipient_email}")
        
        # Create the email subject and body
        subject = f"You've been invited to join Calndr by {sender_name}"
        
        # Plain text version
        text_body = f"""
Hi {recipient_name},

{sender_name} has invited you to join Calndr, the co-parenting calendar app.

Your enrollment code is: {enrollment_code}

Download the app from the App Store and enter this code to get started.

Thank you,
The Calndr Team
        """
        
        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calndr Invitation</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .code {{
            font-size: 24px;
            font-weight: bold;
            color: #4a90e2;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            background-color: #f9f9f9;
            display: inline-block;
            letter-spacing: 2px;
        }}
        .button {{
            display: inline-block;
            padding: 10px 20px;
            background-color: #4a90e2;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h2>You've been invited to join Calndr!</h2>
    <p>Hi {recipient_name},</p>
    <p>{sender_name} has invited you to join Calndr, the co-parenting calendar app.</p>
    <p>Your enrollment code is:</p>
    <div class="code">{enrollment_code}</div>
    <p>Download the app from the App Store and enter this code to get started.</p>
    <a href="https://apps.apple.com/us/app/calndr/id1234567890" class="button">Download Calndr</a>
    <p>Thank you,<br>The Calndr Team</p>
</body>
</html>
        """
        
        # Use AWS SES if configured, otherwise just log the email
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            ses_client = boto3.client(
                'ses',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            
            response = ses_client.send_email(
                Source=f"Calndr <{settings.EMAIL_SENDER}>",
                Destination={
                    'ToAddresses': [recipient_email]
                },
                Message={
                    'Subject': {'Data': subject},
                    'Body': {
                        'Text': {'Data': text_body},
                        'Html': {'Data': html_body}
                    }
                }
            )
            
            logger.info(f"Email sent! Message ID: {response['MessageId']}")
        else:
            # Just log the email if AWS SES is not configured
            logger.info("AWS SES not configured. Would send email with:")
            logger.info(f"Subject: {subject}")
            logger.info(f"To: {recipient_email}")
            logger.info(f"Body: {text_body}")
        
        return True
    except Exception as e:
        logger.error(f"Error sending enrollment invitation email: {str(e)}")
        return False