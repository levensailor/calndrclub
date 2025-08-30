import uuid
import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from core.database import metadata

# Users table
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id")),
    sqlalchemy.Column("first_name", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("last_name", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True, nullable=False),
    sqlalchemy.Column("password_hash", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("phone_number", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("sns_endpoint_arn", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("last_known_location", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("last_known_location_timestamp", sqlalchemy.DateTime, nullable=True),
    sqlalchemy.Column("subscription_type", sqlalchemy.String, nullable=True, default="Free"),
    sqlalchemy.Column("subscription_status", sqlalchemy.String, nullable=True, default="Active"),
    sqlalchemy.Column("profile_photo_url", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("status", sqlalchemy.String, nullable=True, default="active"),
    sqlalchemy.Column("enrolled", sqlalchemy.Boolean, nullable=True, default=False),
    sqlalchemy.Column("coparent_enrolled", sqlalchemy.Boolean, nullable=True, default=False),
    sqlalchemy.Column("coparent_invited", sqlalchemy.Boolean, nullable=True, default=False),
    sqlalchemy.Column("last_signed_in", sqlalchemy.DateTime, nullable=True, default=datetime.now),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
)

# Families table
families = sqlalchemy.Table(
    "families",
    metadata,
    sqlalchemy.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("daycare_sync_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("daycare_calendar_syncs.id", ondelete="SET NULL"), nullable=True),
    sqlalchemy.Column("school_sync_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("school_calendar_syncs.id", ondelete="SET NULL"), nullable=True),
)

# Events table
events = sqlalchemy.Table(
    "events",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id"), nullable=False),
    sqlalchemy.Column("date", sqlalchemy.Date, nullable=False),
    sqlalchemy.Column("content", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("position", sqlalchemy.Integer, nullable=True),
    sqlalchemy.Column("event_type", sqlalchemy.String, default='regular', nullable=False),
)

# Custody table
custody = sqlalchemy.Table(
    "custody",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id"), nullable=False),
    sqlalchemy.Column("date", sqlalchemy.Date, nullable=False),
    sqlalchemy.Column("actor_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("custodian_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("handoff_day", sqlalchemy.Boolean, default=False, nullable=True),
    sqlalchemy.Column("handoff_time", sqlalchemy.Time, nullable=True),
    sqlalchemy.Column("handoff_location", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
)

# Notification emails table
notification_emails = sqlalchemy.Table(
    "notification_emails",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id"), nullable=False),
    sqlalchemy.Column("email", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
)

# Babysitters table
babysitters = sqlalchemy.Table(
    "babysitters",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("first_name", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("last_name", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("phone_number", sqlalchemy.String(20), nullable=False),
    sqlalchemy.Column("rate", sqlalchemy.Numeric(6, 2), nullable=True),
    sqlalchemy.Column("notes", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("created_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
)

# Babysitter families table
babysitter_families = sqlalchemy.Table(
    "babysitter_families",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("babysitter_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("babysitters.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("added_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("added_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
    sqlalchemy.UniqueConstraint("babysitter_id", "family_id", name="unique_babysitter_family"),
)

# Emergency contacts table
emergency_contacts = sqlalchemy.Table(
    "emergency_contacts",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("first_name", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("last_name", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("phone_number", sqlalchemy.String(20), nullable=False),
    sqlalchemy.Column("relationship", sqlalchemy.String(100), nullable=True),
    sqlalchemy.Column("notes", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("created_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
)

# Group chats table
group_chats = sqlalchemy.Table(
    "group_chats",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("contact_type", sqlalchemy.String(20), nullable=False),
    sqlalchemy.Column("contact_id", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("group_identifier", sqlalchemy.String(255), unique=True, nullable=True),
    sqlalchemy.Column("created_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
)

# Children table
children = sqlalchemy.Table(
    "children",
    metadata,
    sqlalchemy.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("first_name", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("last_name", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("dob", sqlalchemy.Date, nullable=False),
)

# Reminders table
reminders = sqlalchemy.Table(
    "reminders",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("date", sqlalchemy.Date, nullable=False),
    sqlalchemy.Column("text", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("notification_enabled", sqlalchemy.Boolean, nullable=False, default=False),
    sqlalchemy.Column("notification_time", sqlalchemy.Time, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, nullable=True, default=datetime.now, onupdate=datetime.now),
    sqlalchemy.UniqueConstraint("family_id", "date", name="unique_family_date_reminder"),
)

themes = sqlalchemy.Table(
    "themes",
    metadata,
    sqlalchemy.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("mainBackgroundColor", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("secondaryBackgroundColor", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("textColor", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("headerTextColor", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("iconColor", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("iconActiveColor", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("accentColor", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("parentOneColor", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("parentTwoColor", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("is_public", sqlalchemy.Boolean, nullable=False, default=False),
    sqlalchemy.Column("created_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id")),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow, nullable=False),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
)

user_preferences = sqlalchemy.Table(
    "user_preferences",
    metadata,
    sqlalchemy.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    sqlalchemy.Column("user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
    sqlalchemy.Column("selected_theme_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("themes.id")),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow, nullable=True),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True),
)

# Daycare providers table
daycare_providers = sqlalchemy.Table(
    "daycare_providers",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("address", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("phone_number", sqlalchemy.String(20), nullable=True),
    sqlalchemy.Column("email", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("hours", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("notes", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("google_place_id", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("rating", sqlalchemy.Numeric(3, 2), nullable=True),
    sqlalchemy.Column("website", sqlalchemy.String(500), nullable=True),
    sqlalchemy.Column("created_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, nullable=True, default=datetime.now, onupdate=datetime.now),
)

# Daycare calendar syncs table
daycare_calendar_syncs = sqlalchemy.Table(
    "daycare_calendar_syncs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("daycare_provider_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("daycare_providers.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("calendar_url", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("last_sync_at", sqlalchemy.DateTime(timezone=True), nullable=True),
    sqlalchemy.Column("last_sync_success", sqlalchemy.Boolean, nullable=True),
    sqlalchemy.Column("last_sync_error", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("events_count", sqlalchemy.Integer, default=0),
    sqlalchemy.Column("sync_enabled", sqlalchemy.Boolean, default=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=True, default=datetime.now, onupdate=datetime.now),
)

# School providers table
school_providers = sqlalchemy.Table(
    "school_providers",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("address", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("phone_number", sqlalchemy.String(20), nullable=True),
    sqlalchemy.Column("email", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("hours", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("notes", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("google_place_id", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("rating", sqlalchemy.Numeric(3, 2), nullable=True),
    sqlalchemy.Column("website", sqlalchemy.String(500), nullable=True),
    sqlalchemy.Column("created_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, nullable=True, default=datetime.now, onupdate=datetime.now),
)

# School calendar syncs table
school_calendar_syncs = sqlalchemy.Table(
    "school_calendar_syncs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("school_provider_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("school_providers.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("calendar_url", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("last_sync_at", sqlalchemy.DateTime(timezone=True), nullable=True),
    sqlalchemy.Column("last_sync_success", sqlalchemy.Boolean, nullable=True),
    sqlalchemy.Column("last_sync_error", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("events_count", sqlalchemy.Integer, default=0),
    sqlalchemy.Column("sync_enabled", sqlalchemy.Boolean, default=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=True, default=datetime.now, onupdate=datetime.now),
)

# Schedule templates table
schedule_templates = sqlalchemy.Table(
    "schedule_templates",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("description", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("pattern_type", sqlalchemy.String(50), nullable=False),  # weekly, alternatingWeeks, alternatingDays, custom
    sqlalchemy.Column("weekly_pattern", sqlalchemy.JSON, nullable=True),  # Store as JSON
    sqlalchemy.Column("alternating_weeks_pattern", sqlalchemy.JSON, nullable=True),  # Store as JSON
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, default=True, nullable=False),
    sqlalchemy.Column("created_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, nullable=True, default=datetime.now, onupdate=datetime.now),
)

# School events table
school_events = sqlalchemy.Table(
    "school_events",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("school_provider_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("school_providers.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("event_date", sqlalchemy.Date, nullable=False),
    sqlalchemy.Column("title", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("description", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("event_type", sqlalchemy.String(50), nullable=True),  # holiday, closure, early_dismissal, event, etc.
    sqlalchemy.Column("start_time", sqlalchemy.Time, nullable=True),
    sqlalchemy.Column("end_time", sqlalchemy.Time, nullable=True),
    sqlalchemy.Column("all_day", sqlalchemy.Boolean, default=False, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=True, default=datetime.now, onupdate=datetime.now),
    sqlalchemy.UniqueConstraint("school_provider_id", "event_date", "title", name="unique_school_event"),
)

# Daycare events table
daycare_events = sqlalchemy.Table(
    "daycare_events",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("daycare_provider_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("daycare_providers.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("event_date", sqlalchemy.Date, nullable=False),
    sqlalchemy.Column("title", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("description", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("event_type", sqlalchemy.String(50), nullable=True),  # holiday, closure, early_dismissal, event, etc.
    sqlalchemy.Column("start_time", sqlalchemy.Time, nullable=True),
    sqlalchemy.Column("end_time", sqlalchemy.Time, nullable=True),
    sqlalchemy.Column("all_day", sqlalchemy.Boolean, default=False, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=True, default=datetime.now, onupdate=datetime.now),
    sqlalchemy.UniqueConstraint("daycare_provider_id", "event_date", "title", name="unique_daycare_event"),
)

# Journal entries table
journal_entries = sqlalchemy.Table(
    "journal_entries",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("title", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("content", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("entry_date", sqlalchemy.Date, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, nullable=True, default=datetime.now, onupdate=datetime.now),
)

# Medical providers table
medical_providers = sqlalchemy.Table(
    "medical_providers",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("specialty", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("address", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("phone", sqlalchemy.String(50), nullable=True),
    sqlalchemy.Column("email", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("website", sqlalchemy.String(500), nullable=True),
    sqlalchemy.Column("latitude", sqlalchemy.DECIMAL(10, 8), nullable=True),
    sqlalchemy.Column("longitude", sqlalchemy.DECIMAL(11, 8), nullable=True),
    sqlalchemy.Column("zip_code", sqlalchemy.String(20), nullable=True),
    sqlalchemy.Column("notes", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("google_place_id", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("rating", sqlalchemy.Numeric(3, 2), nullable=True),
    sqlalchemy.Column("created_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, nullable=True, default=datetime.now, onupdate=datetime.now),
)

# Medications table
medications = sqlalchemy.Table(
    "medications",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("dosage", sqlalchemy.String(100), nullable=True),
    sqlalchemy.Column("frequency", sqlalchemy.String(100), nullable=True),
    sqlalchemy.Column("instructions", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("start_date", sqlalchemy.Date, nullable=True),
    sqlalchemy.Column("end_date", sqlalchemy.Date, nullable=True),
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, default=True, nullable=True),
    sqlalchemy.Column("reminder_enabled", sqlalchemy.Boolean, default=False, nullable=True),
    sqlalchemy.Column("reminder_time", sqlalchemy.Time, nullable=True),
    sqlalchemy.Column("notes", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=True, default=datetime.now),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, nullable=True, default=datetime.now, onupdate=datetime.now),
)

# Enrollment codes table
enrollment_codes = sqlalchemy.Table(
    "enrollment_codes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sqlalchemy.Column("code", sqlalchemy.String(6), unique=True, nullable=False),
    sqlalchemy.Column("created_by_user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("coparent_first_name", sqlalchemy.String(100), nullable=True),
    sqlalchemy.Column("coparent_last_name", sqlalchemy.String(100), nullable=True),
    sqlalchemy.Column("coparent_email", sqlalchemy.String(255), nullable=True),
    sqlalchemy.Column("coparent_phone", sqlalchemy.String(20), nullable=True),
    sqlalchemy.Column("invitation_sent", sqlalchemy.Boolean, default=False, nullable=False),
    sqlalchemy.Column("invitation_sent_at", sqlalchemy.DateTime, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=False, default=datetime.now),
)
