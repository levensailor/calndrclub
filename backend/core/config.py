import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Settings(BaseSettings):
    """
    Application settings.
    """
    
    # Application
    PROJECT_NAME: str = "Calndr API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Family Calendar Management API"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_random_secret_key_for_development")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://calndr.club",
        "https://www.calndr.club",
        "http://localhost:8080",
        "capacitor://localhost",
        "ionic://localhost",
        "http://localhost",
        "http://localhost:8100",
        "https://localhost:8100"
    ]
    
    # Database
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "calndr")
    
    @property
    def DATABASE_URL(self) -> str:
        # URL-encode the username and password to handle special characters
        encoded_user = quote_plus(self.DB_USER)
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+asyncpg://{encoded_user}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # AWS
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET_NAME: str = os.getenv("AWS_S3_BUCKET_NAME", "")
    
    # Push Notifications
    SNS_PLATFORM_APPLICATION_ARN: Optional[str] = os.getenv("SNS_PLATFORM_APPLICATION_ARN")
    
    # External APIs
    GOOGLE_PLACES_API_KEY: Optional[str] = os.getenv("GOOGLE_PLACES_API_KEY")
    
    # Email Configuration
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: Optional[int] = os.getenv("SMTP_PORT")
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "noreply@calndr.club")

    # Apple Sign-In
    APPLE_CLIENT_ID: Optional[str] = os.getenv("APPLE_CLIENT_ID")
    APPLE_TEAM_ID: Optional[str] = os.getenv("APPLE_TEAM_ID")
    APPLE_KEY_ID: Optional[str] = os.getenv("APPLE_KEY_ID")
    APPLE_PRIVATE_KEY: Optional[str] = os.getenv("APPLE_PRIVATE_KEY")
    APPLE_REDIRECT_URI: Optional[str] = os.getenv("APPLE_REDIRECT_URI")

    # Google Sign-In
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    
    # Facebook settings
    # FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "your_facebook_app_id")
    # FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "your_facebook_app_secret")
    
    # Redis Cache Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))  # Increased from 10 to 20
    REDIS_SOCKET_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))  # Reduced from 10 to 5 seconds
    
    # Cache TTL settings (in seconds)
    CACHE_TTL_WEATHER_FORECAST: int = int(os.getenv("CACHE_TTL_WEATHER_FORECAST", "3600"))  # 1 hour
    CACHE_TTL_WEATHER_HISTORIC: int = int(os.getenv("CACHE_TTL_WEATHER_HISTORIC", "259200"))  # 3 days
    CACHE_TTL_EVENTS: int = int(os.getenv("CACHE_TTL_EVENTS", "900"))  # 15 minutes
    CACHE_TTL_CUSTODY: int = int(os.getenv("CACHE_TTL_CUSTODY", "7200"))  # 2 hours (increased from 15 minutes)
    CACHE_TTL_USER_PROFILE: int = int(os.getenv("CACHE_TTL_USER_PROFILE", "1800"))  # 30 minutes
    CACHE_TTL_FAMILY_DATA: int = int(os.getenv("CACHE_TTL_FAMILY_DATA", "1800"))  # 30 minutes
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()
