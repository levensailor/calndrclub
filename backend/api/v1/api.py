from fastapi import APIRouter

from .endpoints import (
    auth, users, family, events, custody, notifications, profile, reminders,
    babysitters, emergency_contacts, group_chat, children, daycare_providers, school_providers,
    weather, school_events, themes, schedule_templates, journal, phone_verification,
    medical_providers, medications
)

api_router = APIRouter()

# Note: These routes will be mounted under /api by main.py
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(family.router, prefix="/family", tags=["family"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(custody.router, prefix="/custody", tags=["custody"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(profile.router, prefix="/user/profile", tags=["profile"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["reminders"])
api_router.include_router(babysitters.router, prefix="/babysitters", tags=["babysitters"])
api_router.include_router(emergency_contacts.router, prefix="/emergency-contacts", tags=["emergency_contacts"])
api_router.include_router(group_chat.router, prefix="/group-chat", tags=["group_chat"])
api_router.include_router(children.router, prefix="/children", tags=["children"])
api_router.include_router(daycare_providers.router, prefix="/daycare-providers", tags=["daycare_providers"])
api_router.include_router(school_providers.router, prefix="/school-providers", tags=["school_providers"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(school_events.router, prefix="/school-events", tags=["school_events"])
api_router.include_router(themes.router, prefix="/themes", tags=["themes"])
api_router.include_router(schedule_templates.router, prefix="/schedule-templates", tags=["schedule_templates"])
api_router.include_router(journal.router, prefix="/journal", tags=["journal"])
api_router.include_router(phone_verification.router, prefix="/phone-verification", tags=["phone_verification"])
api_router.include_router(medical_providers.router, prefix="/medical-providers", tags=["medical_providers"])
api_router.include_router(medications.router, prefix="/medications", tags=["medications"])
