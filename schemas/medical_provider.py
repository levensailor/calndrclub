from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
import re

class MedicalProviderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Provider name")
    specialty: Optional[str] = Field(None, max_length=255, description="Medical specialty")
    address: Optional[str] = Field(None, description="Full address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    website: Optional[str] = Field(None, max_length=500, description="Website URL")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    zip_code: Optional[str] = Field(None, max_length=20, description="ZIP code")
    notes: Optional[str] = Field(None, description="Additional notes")
    google_place_id: Optional[str] = Field(None, max_length=255, description="Google Place ID")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Rating from 0 to 5")

    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            # Remove all non-digit characters
            digits_only = re.sub(r'\D', '', v)
            if len(digits_only) < 10:
                raise ValueError('Phone number must have at least 10 digits')
            # Format as (XXX) XXX-XXXX
            if len(digits_only) == 10:
                return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
            elif len(digits_only) == 11 and digits_only[0] == '1':
                return f"({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
            else:
                raise ValueError('Invalid phone number format')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid email format')
        return v

    @validator('website')
    def validate_website(cls, v):
        if v is not None:
            if not v.startswith(('http://', 'https://')):
                v = 'https://' + v
        return v

class MedicalProviderCreate(MedicalProviderBase):
    pass  # No need for explicit family_id as it's set from current_user

class MedicalProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    specialty: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    zip_code: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    google_place_id: Optional[str] = Field(None, max_length=255)
    rating: Optional[float] = Field(None, ge=0, le=5)

    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            digits_only = re.sub(r'\D', '', v)
            if len(digits_only) < 10:
                raise ValueError('Phone number must have at least 10 digits')
            if len(digits_only) == 10:
                return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
            elif len(digits_only) == 11 and digits_only[0] == '1':
                return f"({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
            else:
                raise ValueError('Invalid phone number format')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid email format')
        return v

    @validator('website')
    def validate_website(cls, v):
        if v is not None:
            if not v.startswith(('http://', 'https://')):
                v = 'https://' + v
        return v

class MedicalProviderResponse(MedicalProviderBase):
    id: int
    family_id: str
    created_by_user_id: str
    created_at: str
    updated_at: str
    distance: Optional[float] = Field(None, description="Distance in miles from search location")

    class Config:
        from_attributes = True

class MedicalProviderSearchParams(BaseModel):
    q: Optional[str] = Field(None, description="Search query for name, specialty, or address")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitude for distance search")
    lng: Optional[float] = Field(None, ge=-180, le=180, description="Longitude for distance search")
    radius: Optional[float] = Field(25.0, gt=0, le=100, description="Search radius in miles")
    specialty: Optional[str] = Field(None, description="Filter by medical specialty")
    page: Optional[int] = Field(1, ge=1, description="Page number")
    limit: Optional[int] = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field("name", description="Sort by: name, distance, created_at")
    sort_order: Optional[str] = Field("asc", description="Sort order: asc, desc")

class MedicalSearchRequest(BaseModel):
    location_type: str  # "current" or "zipcode"
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[int] = 5000  # meters, default 5km
    specialty: Optional[str] = None
    query: Optional[str] = None  # search term for name/specialty

class MedicalSearchResult(BaseModel):
    id: str
    name: str
    specialty: Optional[str] = None
    address: str
    phone_number: Optional[str] = Field(None, alias="phoneNumber")
    website: Optional[str] = None
    rating: Optional[float] = None
    place_id: Optional[str] = Field(None, alias="placeId")
    distance: Optional[float] = None  # distance in miles
    
    class Config:
        populate_by_name = True  # Allow both original field names and aliases

class MedicalSearchResponse(BaseModel):
    results: List[MedicalSearchResult]
    total: int

class MedicalProviderListResponse(BaseModel):
    providers: List[MedicalProviderResponse]
    total: int
    page: int
    limit: int
    total_pages: int 