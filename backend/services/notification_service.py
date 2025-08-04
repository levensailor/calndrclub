import uuid
from datetime import date
import json
import boto3
from botocore.exceptions import ClientError
from core.database import database
from core.config import settings
from core.logging import logger
from db.models import users, custody
import os

# Initialize SNS client
sns_client = None
if settings.SNS_PLATFORM_APPLICATION_ARN:
    try:
        sns_client = boto3.client('sns', region_name='us-east-1')
        logger.info("AWS SNS client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize AWS SNS client: {e}", exc_info=True)
else:
    logger.warning("SNS_PLATFORM_APPLICATION_ARN not set. Push notifications will be disabled.")


async def send_custody_change_notification(sender_id: uuid.UUID, family_id: uuid.UUID, event_date: date):
    """Send push notification when custody is changed."""
    if not sns_client:
        logger.warning("SNS client not configured. Skipping push notification.")
        return

    other_user_query = users.select().where(
        (users.c.family_id == family_id) & 
        (users.c.id != sender_id) &
        (users.c.sns_endpoint_arn.isnot(None))
    )
    other_user = await database.fetch_one(other_user_query)

    if not other_user:
        logger.warning(f"Could not find another user in family '{family_id}' with an SNS endpoint to notify.")
        return
        
    sender = await database.fetch_one(users.select().where(users.c.id == sender_id))
    sender_name = sender['first_name'] if sender else "Someone"
    
    custodian_query = custody.select().where(
        (custody.c.family_id == family_id) & 
        (custody.c.date == event_date)
    )
    custody_record = await database.fetch_one(custodian_query)
    
    custodian_name = "Unknown"
    if custody_record:
        custodian = await database.fetch_one(users.select().where(users.c.id == custody_record['custodian_id']))
        custodian_name = custodian['first_name'] if custodian else "Unknown"
    
    formatted_date = event_date.strftime('%A, %B %-d')
    
    # Construct the APNS payload for SNS
    aps_payload = {
        "aps": {
            "alert": {
                "title": "📅 Schedule Updated",
                "subtitle": f"{custodian_name} now has custody",
                "body": f"{sender_name} changed the schedule for {formatted_date}. Tap to manage your schedule."
            },
            "sound": "default",
            "badge": 1,
            "category": "CUSTODY_CHANGE"
        },
        "type": "custody_change",
        "date": event_date.isoformat(),
        "custodian": custodian_name,
        "sender": sender_name,
        "deep_link": "calndr://schedule"
    }

    # The ARN determines if it's sandbox or production, so we use the generic "APNS" key
    message = {
        "APNS": json.dumps(aps_payload)
    }
    
    try:
        logger.info(f"Sending custody change notification to endpoint for user {other_user['first_name']}")
        sns_client.publish(
            TargetArn=other_user['sns_endpoint_arn'],
            Message=json.dumps(message),
            MessageStructure='json'
        )
        logger.info("Custody change push notification sent successfully via SNS.")
    except Exception as e:
        logger.error(f"Failed to send push notification via SNS: {e}", exc_info=True)
