from fastapi import APIRouter, Depends, HTTPException
from typing import List

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import notification_emails
from schemas.notification import NotificationEmail, AddNotificationEmail

router = APIRouter()

@router.get("/emails", response_model=List[NotificationEmail])
async def get_notification_emails(current_user = Depends(get_current_user)):
    """
    Returns all notification emails for the current user's family.
    """
    query = notification_emails.select().where(notification_emails.c.family_id == current_user['family_id'])
    emails = await database.fetch_all(query)
    return [NotificationEmail(id=email['id'], email=email['email']) for email in emails]

@router.post("/emails", response_model=NotificationEmail)
async def add_notification_email(email_data: AddNotificationEmail, current_user = Depends(get_current_user)):
    """
    Adds a new notification email for the current user's family.
    """
    query = notification_emails.insert().values(
        family_id=current_user['family_id'],
        email=email_data.email
    )
    email_id = await database.execute(query)
    return NotificationEmail(id=email_id, email=email_data.email)

@router.put("/emails/{email_id}")
async def update_notification_email(email_id: int, email_data: AddNotificationEmail, current_user = Depends(get_current_user)):
    """
    Updates an existing notification email for the current user's family.
    """
    query = notification_emails.update().where(
        (notification_emails.c.id == email_id) & 
        (notification_emails.c.family_id == current_user['family_id'])
    ).values(email=email_data.email)
    await database.execute(query)
    return {"status": "success"}

@router.delete("/emails/{email_id}")
async def delete_notification_email(email_id: int, current_user = Depends(get_current_user)):
    """
    Deletes a notification email for the current user's family.
    """
    query = notification_emails.delete().where(
        (notification_emails.c.id == email_id) & 
        (notification_emails.c.family_id == current_user['family_id'])
    )
    await database.execute(query)
    return {"status": "success"}
