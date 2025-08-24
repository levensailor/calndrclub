import boto3
import uuid
from typing import Optional
from botocore.exceptions import ClientError, NoCredentialsError
from core.config import settings
from core.logging import logger

class EmailService:
    """Service for sending emails using AWS SES."""
    
    def __init__(self):
        # AWS SES configuration
        self.aws_region = getattr(settings, 'AWS_REGION', 'us-east-1')
        self.sender_email = getattr(settings, 'SES_SENDER_EMAIL', 'noreply@calndr.club')
        self.sender_name = getattr(settings, 'SES_SENDER_NAME', 'Calndr Club')
        
        # Initialize SES client
        try:
            self.ses_client = boto3.client(
                'ses',
                region_name=self.aws_region,
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
            )
            logger.info(f"SES client initialized for region: {self.aws_region}")
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to initialize SES client: {e}")
            self.ses_client = None
    
    async def send_coparent_invitation(self, coparent_email: str, inviter_name: str, family_id: uuid.UUID) -> bool:
        """Send an email invitation to a coparent to join the app."""
        if not self.ses_client:
            logger.warning("SES client not configured. Cannot send coparent invitation email.")
            return False
        
        try:
            # Create the email content
            subject = f"{inviter_name} has invited you to join Calndr!"
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h1 style="color: #4A90E2; margin: 0;">Calndr Club</h1>
                        </div>
                        
                        <h2 style="color: #333; margin-bottom: 20px;">You're Invited to Join Calndr!</h2>
                        
                        <p>Hi there,</p>
                        
                        <p><strong>{inviter_name}</strong> has invited you to join their family calendar on Calndr Club!</p>
                        
                        <p>Calndr Club helps co-parents coordinate schedules, share important information, and stay organized together.</p>
                        
                        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #4A90E2;">What you can do with Calndr:</h3>
                            <ul style="margin: 0;">
                                <li>📅 Share custody schedules and coordinate handoffs</li>
                                <li>📝 Create shared events and reminders</li>
                                <li>👶 Track children's activities and school events</li>
                                <li>🌤️ Get weather updates for planning</li>
                                <li>📱 Stay connected with real-time notifications</li>
                            </ul>
                        </div>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="https://app.calndr.club/signup?invite={family_id}" 
                               style="background-color: #4A90E2; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                                Accept Invitation
                            </a>
                        </div>
                        
                        <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; color: #666;">https://app.calndr.club/signup?invite={family_id}</p>
                        
                        <p><strong>To join {inviter_name}'s family:</strong></p>
                        <ol>
                            <li>Click the link above or visit the app</li>
                            <li>Create your account using this email address: <strong>{coparent_email}</strong></li>
                            <li>You'll automatically be connected to {inviter_name}'s family calendar</li>
                        </ol>
                        
                        <p style="color: #666; font-size: 14px; margin-top: 30px;">
                            This invitation was sent by {inviter_name}. If you didn't expect this invitation, you can safely ignore this email.
                        </p>
                        
                        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #666; font-size: 12px;">
                            <p>© 2024 Calndr Club. All rights reserved.</p>
                            <p>Making co-parenting easier, one day at a time.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            text_body = f"""
            Calndr Club - You're Invited!
            
            Hi there,
            
            {inviter_name} has invited you to join their family calendar on Calndr Club!
            
            Calndr Club helps co-parents coordinate schedules, share important information, and stay organized together.
            
            What you can do with Calndr:
            • Share custody schedules and coordinate handoffs
            • Create shared events and reminders
            • Track children's activities and school events
            • Get weather updates for planning
            • Stay connected with real-time notifications
            
            To accept this invitation, visit: https://app.calndr.club/signup?invite={family_id}
            
            To join {inviter_name}'s family:
            1. Click the link above or visit the app
            2. Create your account using this email address: {coparent_email}
            3. You'll automatically be connected to {inviter_name}'s family calendar
            
            This invitation was sent by {inviter_name}. If you didn't expect this invitation, you can safely ignore this email.
            
            © 2024 Calndr Club. All rights reserved.
            Making co-parenting easier, one day at a time.
            """
            
            # Send email using SES
            response = self.ses_client.send_email(
                Source=f"{self.sender_name} <{self.sender_email}>",
                Destination={
                    'ToAddresses': [coparent_email]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': text_body,
                            'Charset': 'UTF-8'
                        },
                        'Html': {
                            'Data': html_body,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
            
            message_id = response.get('MessageId', 'unknown')
            logger.info(f"Coparent invitation email sent to {coparent_email} from {inviter_name} (MessageId: {message_id})")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES ClientError sending coparent invitation to {coparent_email}: {error_code} - {error_message}")
            return False
        except Exception as e:
            logger.error(f"Failed to send coparent invitation email to {coparent_email}: {e}")
            return False
    
    async def send_verification_email(self, email: str, name: str, verification_code: str) -> bool:
        """Send an email verification code to the user."""
        if not self.ses_client:
            logger.warning("SES client not configured. Cannot send verification email.")
            return False
        
        try:
            # Create the email content
            subject = "Verify your Calndr Club account"
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h1 style="color: #4A90E2; margin: 0;">Calndr Club</h1>
                        </div>
                        
                        <h2 style="color: #333; margin-bottom: 20px;">Verify Your Email Address</h2>
                        
                        <p>Hi {name},</p>
                        
                        <p>Thank you for signing up for Calndr Club! To complete your registration, please verify your email address using the code below:</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <div style="background-color: #f8f9fa; border: 2px solid #4A90E2; border-radius: 8px; padding: 20px; display: inline-block;">
                                <span style="font-size: 32px; font-weight: bold; color: #4A90E2; letter-spacing: 4px;">{verification_code}</span>
                            </div>
                        </div>
                        
                        <p>Enter this code in the app to verify your email address and complete your registration.</p>
                        
                        <p style="color: #666; font-size: 14px; margin-top: 30px;">
                            This code will expire in 10 minutes. If you didn't request this verification, please ignore this email.
                        </p>
                        
                        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #666; font-size: 12px;">
                            <p>© 2024 Calndr Club. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            text_body = f"""
            Calndr Club - Verify Your Email Address
            
            Hi {name},
            
            Thank you for signing up for Calndr Club! To complete your registration, please verify your email address using this code:
            
            {verification_code}
            
            Enter this code in the app to verify your email address and complete your registration.
            
            This code will expire in 10 minutes. If you didn't request this verification, please ignore this email.
            
            © 2024 Calndr Club. All rights reserved.
            """
            
            # Send email using SES
            response = self.ses_client.send_email(
                Source=f"{self.sender_name} <{self.sender_email}>",
                Destination={
                    'ToAddresses': [email]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': text_body,
                            'Charset': 'UTF-8'
                        },
                        'Html': {
                            'Data': html_body,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
            
            message_id = response.get('MessageId', 'unknown')
            logger.info(f"Verification email sent to {email} (MessageId: {message_id})")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES ClientError sending verification email to {email}: {error_code} - {error_message}")
            return False
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}")
            return False

# Global instance
email_service = EmailService()