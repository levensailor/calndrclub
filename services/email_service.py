import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from core.config import settings
from core.logging import logger

class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST if hasattr(settings, 'SMTP_HOST') else None
        self.smtp_port = settings.SMTP_PORT if hasattr(settings, 'SMTP_PORT') else None
        self.smtp_user = settings.SMTP_USER if hasattr(settings, 'SMTP_USER') else None
        self.smtp_password = settings.SMTP_PASSWORD if hasattr(settings, 'SMTP_PASSWORD') else None
    
    async def send_coparent_invitation(self, coparent_email: str, inviter_name: str, family_id: uuid.UUID) -> bool:
        """Send an email invitation to a coparent to join the app."""
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Cannot send coparent invitation email.")
            return False
        
        try:
            # Create the email content
            subject = f"{inviter_name} has invited you to join Calndr!"
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #007AFF;">You're invited to join Calndr!</h2>
                        
                        <p>Hi there!</p>
                        
                        <p><strong>{inviter_name}</strong> has invited you to join their family calendar on Calndr - the app designed specifically for co-parents to coordinate schedules, custody, and family events.</p>
                        
                        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #007AFF;">What you can do with Calndr:</h3>
                            <ul style="margin: 0;">
                                <li>📅 Share custody schedules and coordinate handoffs</li>
                                <li>📝 Create shared events and reminders</li>
                                <li>👶 Track children's activities and school events</li>
                                <li>🌤️ Get weather updates for planning</li>
                                <li>📱 Stay connected with real-time notifications</li>
                            </ul>
                        </div>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="https://calndr.club" style="display: inline-block; background-color: #007AFF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">Download Calndr</a>
                        </div>
                        
                        <p><strong>To join {inviter_name}'s family:</strong></p>
                        <ol>
                            <li>Download the Calndr app from the App Store or visit <a href="https://calndr.club">calndr.club</a></li>
                            <li>Create your account using this email address: <strong>{coparent_email}</strong></li>
                            <li>You'll automatically be connected to {inviter_name}'s family calendar</li>
                        </ol>
                        
                        <p style="margin-top: 30px; font-size: 14px; color: #666;">
                            This invitation was sent because {inviter_name} entered your email address when setting up their Calndr account. 
                            If you don't want to receive these emails, you can safely ignore this message.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                        <p style="font-size: 12px; color: #999; text-align: center;">
                            Calndr - Making co-parenting easier, one day at a time.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            # Create the email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = coparent_email
            
            # Add HTML content
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send the email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Coparent invitation email sent to {coparent_email} from {inviter_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send coparent invitation email to {coparent_email}: {e}")
            return False

# Global instance
email_service = EmailService() 