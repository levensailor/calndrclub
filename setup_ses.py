#!/usr/bin/env python3
"""
AWS SES Setup Script for Calndr Club

This script helps set up AWS SES for sending emails from the Calndr Club application.
It verifies email addresses, checks SES configuration, and provides setup guidance.
"""

import boto3
import os
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_ses_client():
    """Initialize and return SES client"""
    try:
        return boto3.client(
            'ses',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
    except (ClientError, NoCredentialsError) as e:
        print(f"❌ Failed to initialize SES client: {e}")
        print("\n📋 Required environment variables:")
        print("   - AWS_ACCESS_KEY_ID")
        print("   - AWS_SECRET_ACCESS_KEY")
        print("   - AWS_REGION (optional, defaults to us-east-1)")
        return None

def check_ses_status(ses_client):
    """Check SES account status and limits"""
    try:
        # Get sending quota
        quota = ses_client.get_send_quota()
        print(f"📊 SES Sending Quota:")
        print(f"   - Max 24 Hour Send: {quota['Max24HourSend']}")
        print(f"   - Max Send Rate: {quota['MaxSendRate']} emails/second")
        print(f"   - Sent Last 24h: {quota['SentLast24Hours']}")
        
        # Get sending statistics
        stats = ses_client.get_send_statistics()
        if stats['SendDataPoints']:
            latest = stats['SendDataPoints'][-1]
            print(f"📈 Recent Statistics:")
            print(f"   - Bounces: {latest.get('Bounces', 0)}")
            print(f"   - Complaints: {latest.get('Complaints', 0)}")
            print(f"   - Delivery Attempts: {latest.get('DeliveryAttempts', 0)}")
            print(f"   - Rejects: {latest.get('Rejects', 0)}")
        
        return True
    except ClientError as e:
        print(f"❌ Error checking SES status: {e}")
        return False

def list_verified_emails(ses_client):
    """List all verified email addresses"""
    try:
        response = ses_client.list_verified_email_addresses()
        verified_emails = response.get('VerifiedEmailAddresses', [])
        
        print(f"✅ Verified Email Addresses ({len(verified_emails)}):")
        for email in verified_emails:
            print(f"   - {email}")
        
        return verified_emails
    except ClientError as e:
        print(f"❌ Error listing verified emails: {e}")
        return []

def verify_email_address(ses_client, email):
    """Send verification email to an address"""
    try:
        ses_client.verify_email_identity(EmailAddress=email)
        print(f"✅ Verification email sent to {email}")
        print("   Check your inbox and click the verification link.")
        return True
    except ClientError as e:
        print(f"❌ Error verifying email {email}: {e}")
        return False

def check_domain_verification(ses_client, domain):
    """Check if a domain is verified"""
    try:
        response = ses_client.get_identity_verification_attributes(Identities=[domain])
        attrs = response.get('VerificationAttributes', {})
        
        if domain in attrs:
            status = attrs[domain]['VerificationStatus']
            print(f"🌐 Domain {domain} verification status: {status}")
            return status == 'Success'
        else:
            print(f"❌ Domain {domain} not found in SES")
            return False
    except ClientError as e:
        print(f"❌ Error checking domain {domain}: {e}")
        return False

def setup_configuration_set(ses_client, config_set_name="calndr-club-emails"):
    """Create a configuration set for tracking"""
    try:
        ses_client.create_configuration_set(
            ConfigurationSet={'Name': config_set_name}
        )
        print(f"✅ Created configuration set: {config_set_name}")
        
        # Add event destination for tracking
        ses_client.create_configuration_set_event_destination(
            ConfigurationSetName=config_set_name,
            EventDestination={
                'Name': 'cloudwatch-event-destination',
                'Enabled': True,
                'MatchingEventTypes': ['send', 'bounce', 'complaint', 'delivery'],
                'CloudWatchDestination': {
                    'DimensionConfigurations': [
                        {
                            'DimensionName': 'MessageTag',
                            'DimensionValueSource': 'messageTag',
                            'DefaultDimensionValue': 'default'
                        }
                    ]
                }
            }
        )
        print(f"✅ Added CloudWatch event destination to {config_set_name}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'AlreadyExistsException':
            print(f"ℹ️  Configuration set {config_set_name} already exists")
            return True
        else:
            print(f"❌ Error creating configuration set: {e}")
            return False

def main():
    print("🚀 AWS SES Setup for Calndr Club")
    print("=" * 40)
    
    # Initialize SES client
    ses_client = get_ses_client()
    if not ses_client:
        return
    
    print("\n1️⃣  Checking SES Status...")
    if not check_ses_status(ses_client):
        return
    
    print("\n2️⃣  Listing Verified Emails...")
    verified_emails = list_verified_emails(ses_client)
    
    # Check for required sender email
    sender_email = os.getenv('SES_SENDER_EMAIL', 'no-reply@calndr.club')
    print(f"\n3️⃣  Checking Sender Email: {sender_email}")
    
    if sender_email not in verified_emails:
        print(f"⚠️  Sender email {sender_email} is not verified!")
        
        # Check if it's a domain-based email
        domain = sender_email.split('@')[1] if '@' in sender_email else None
        if domain:
            print(f"🔍 Checking domain verification for {domain}...")
            if not check_domain_verification(ses_client, domain):
                print(f"\n📧 To verify {sender_email}, you can:")
                print("   1. Verify the individual email address:")
                response = input(f"      Verify {sender_email}? (y/n): ")
                if response.lower() == 'y':
                    verify_email_address(ses_client, sender_email)
                
                print(f"\n   2. Or verify the entire domain {domain} (recommended for production)")
                print(f"      This requires DNS configuration in your domain settings.")
    else:
        print(f"✅ Sender email {sender_email} is verified!")
    
    print("\n4️⃣  Setting up Configuration Set...")
    setup_configuration_set(ses_client)
    
    print("\n🎉 SES Setup Complete!")
    print("\n📋 Environment Variables for .env:")
    print(f"AWS_REGION={os.getenv('AWS_REGION', 'us-east-1')}")
    print(f"SES_SENDER_EMAIL={sender_email}")
    print(f"SES_SENDER_NAME=Calndr Club")
    print("AWS_ACCESS_KEY_ID=your_access_key_id")
    print("AWS_SECRET_ACCESS_KEY=your_secret_access_key")
    
    print("\n⚠️  Important Notes:")
    print("   - If you're in SES Sandbox mode, you can only send to verified addresses")
    print("   - Request production access to send to any email address")
    print("   - Monitor your bounce and complaint rates to maintain good reputation")
    print("   - Consider setting up SNS notifications for bounces and complaints")

if __name__ == "__main__":
    main()
