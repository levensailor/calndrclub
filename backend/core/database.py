import databases
import sqlalchemy
from sqlalchemy import create_engine
import os
import logging
from urllib.parse import urlparse
from core.config import settings

# Get logger
logger = logging.getLogger(__name__)

def log_database_config():
    """Log database configuration details for debugging."""
    logger.info("=== DATABASE CONFIGURATION DEBUG ===")
    
    # Log individual environment variables
    logger.info(f"DB_USER: {os.getenv('DB_USER', 'NOT_SET')}")
    logger.info(f"DB_PASSWORD: {'SET' if os.getenv('DB_PASSWORD') else 'NOT_SET'} (length: {len(os.getenv('DB_PASSWORD', ''))})")
    logger.info(f"DB_HOST: {os.getenv('DB_HOST', 'NOT_SET')}")
    logger.info(f"DB_PORT: {os.getenv('DB_PORT', 'NOT_SET')}")
    logger.info(f"DB_NAME: {os.getenv('DB_NAME', 'NOT_SET')}")
    
    # Log settings values
    logger.info(f"settings.DB_USER: {settings.DB_USER}")
    logger.info(f"settings.DB_PASSWORD: {'SET' if settings.DB_PASSWORD else 'NOT_SET'} (length: {len(settings.DB_PASSWORD)})")
    logger.info(f"settings.DB_HOST: {settings.DB_HOST}")
    logger.info(f"settings.DB_PORT: {settings.DB_PORT}")
    logger.info(f"settings.DB_NAME: {settings.DB_NAME}")
    
    # Show URL encoding for special characters
    from urllib.parse import quote_plus
    if settings.DB_PASSWORD:
        logger.info(f"DB_PASSWORD contains special chars: {'[' in settings.DB_PASSWORD or ']' in settings.DB_PASSWORD or '!' in settings.DB_PASSWORD or '@' in settings.DB_PASSWORD}")
        logger.info(f"URL-encoded password length: {len(quote_plus(settings.DB_PASSWORD))}")
    
    # Construct and log the DATABASE_URL
    constructed_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    logger.info(f"Raw DATABASE_URL (unencoded): {constructed_url}")
    logger.info(f"Final DATABASE_URL (encoded): {settings.DATABASE_URL}")
    
    # Parse and validate URL
    try:
        parsed = urlparse(settings.DATABASE_URL)
        logger.info(f"Parsed URL scheme: {parsed.scheme}")
        logger.info(f"Parsed URL netloc: {parsed.netloc}")
        logger.info(f"Parsed URL hostname: {parsed.hostname}")
        logger.info(f"Parsed URL port: {parsed.port}")
        logger.info(f"Parsed URL path: {parsed.path}")
        logger.info(f"Parsed URL username: {parsed.username}")
        logger.info(f"Parsed URL password: {'SET' if parsed.password else 'NOT_SET'}")
        logger.info("URL parsing successful - no special character issues")
    except Exception as e:
        logger.error(f"Failed to parse DATABASE_URL: {e}")
    
    logger.info("=== END DATABASE CONFIGURATION DEBUG ===")

def validate_database_config():
    """Validate database configuration and log issues."""
    logger.info("Validating database configuration...")
    
    issues = []
    
    if not settings.DB_USER:
        issues.append("DB_USER is empty or not set")
    if not settings.DB_PASSWORD:
        issues.append("DB_PASSWORD is empty or not set")
    if not settings.DB_HOST:
        issues.append("DB_HOST is empty or not set")
    if not settings.DB_PORT:
        issues.append("DB_PORT is empty or not set")
    if not settings.DB_NAME:
        issues.append("DB_NAME is empty or not set")
    
    if issues:
        logger.error("Database configuration issues found:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    else:
        logger.info("Database configuration validation passed")
        return True

# Log configuration at module load time
log_database_config()
validate_database_config()

# Database setup with connection pooling
logger.info("Initializing database connection...")
try:
    # Configure the database with proper connection limits
    database = databases.Database(
        settings.DATABASE_URL,
        min_size=2,      # Minimum number of connections in the pool
        max_size=15,     # Increased for concurrent auth operations (was 5)
        force_rollback=True,  # Force rollback on connection close
        ssl="prefer"     # Use SSL if available
    )
    logger.info("Database object created successfully")
except Exception as e:
    logger.error(f"Failed to create database object: {e}")
    logger.error(f"Exception type: {type(e).__name__}")
    raise

metadata = sqlalchemy.MetaData()

# SQLAlchemy engine for migrations and non-async operations
logger.info("Initializing SQLAlchemy engine...")
try:
    engine_url = settings.DATABASE_URL.replace("+asyncpg", "")
    logger.info(f"Engine URL (without +asyncpg): {engine_url}")
    
    engine = create_engine(
        engine_url,
        pool_size=5,          # Connection pool size
        max_overflow=10,      # Additional connections beyond pool_size
        pool_timeout=30,      # Timeout for getting connection from pool
        pool_recycle=3600,    # Recycle connections after 1 hour
        pool_pre_ping=True    # Verify connections before use
    )
    logger.info("SQLAlchemy engine created successfully")
except Exception as e:
    logger.error(f"Failed to create SQLAlchemy engine: {e}")
    logger.error(f"Exception type: {type(e).__name__}")
    raise

logger.info("Database module initialization completed")
