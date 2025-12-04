import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr
from schemas.base import BaseSchema

class UserBase(BaseSchema):
    """Base schema for user data."""
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str

class CoParentCreate(UserBase):
    """Schema for creating a new co-parent."""
    pass

class UserUpdate(BaseSchema):
    """Schema for updating user data."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None

class UserProfileUpdate(BaseSchema):
    """Schema for updating user profile data."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    enrolled: Optional[bool] = None

class UserResponse(UserBase):
    """Schema for user response data."""
    id: str
    family_id: str
    subscription_type: Optional[str] = "Free"
    subscription_status: Optional[str] = "Active"
    profile_photo_url: Optional[str] = None
    status: Optional[str] = "active"
    last_signed_in: Optional[str] = None
    created_at: Optional[str] = None
    selected_theme_id: Optional[uuid.UUID] = None

class UserRegistration(BaseSchema):
    """Schema for user registration."""
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None

class UserRegistrationWithFamily(BaseSchema):
    """Schema for user registration with family enrollment code."""
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    enrollment_code: str
    family_id: Optional[str] = None  # Changed from int to str to match UUID format

class UserRegistrationResponse(BaseSchema):
    """Schema for user registration response."""
    user_id: str
    family_id: str
    access_token: str
    token_type: str
    message: str
    should_skip_onboarding: bool = False
    requires_email_verification: bool = False

class UserProfile(BaseSchema):
    """Schema for user profile information."""
    id: str
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    subscription_type: Optional[str] = "Free"
    subscription_status: Optional[str] = "Active"
    profile_photo_url: Optional[str] = None
    status: Optional[str] = "active"
    enrolled: Optional[bool] = False
    coparent_enrolled: Optional[bool] = False
    coparent_invited: Optional[bool] = False
    last_signed_in: Optional[str] = None
    created_at: Optional[str] = None
    family_id: str
    selected_theme_id: Optional[str] = None  # Changed from UUID to str for iOS compatibility
    theme: Optional[str] = None

class UserPreferences(BaseSchema):
    """Schema for user preferences."""
    selected_theme_id: Optional[uuid.UUID] = None
    theme: Optional[str] = None
    notification_preferences: Optional[dict] = None

class UserPreferenceUpdate(BaseSchema):
    """Schema for updating user preferences."""
    selected_theme_id: uuid.UUID

class PasswordUpdate(BaseSchema):
    """Schema for password update."""
    current_password: str
    new_password: str

class LocationUpdateRequest(BaseSchema):
    """Schema for location update requests."""
    latitude: float
    longitude: float

class FamilyMember(BaseSchema):
    """Schema for family member information."""
    id: str
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    status: Optional[str] = "active"
    last_signed_in: Optional[str] = None
    last_known_location: Optional[str] = None
    last_known_location_timestamp: Optional[str] = None

class FamilyMemberEmail(BaseSchema):
    """Schema for family member email invitation."""
    id: str
    first_name: str
    email: str

class EnrollmentStatusUpdate(BaseSchema):
    """Schema for updating user enrollment status."""
    enrolled: bool