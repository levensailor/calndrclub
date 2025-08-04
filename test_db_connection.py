#!/usr/bin/env python3
"""
Simple database connection test script for debugging.
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize logging first
from core.logging import setup_logging
logger = setup_logging()

async def test_database_connection():
    """Test database connection with detailed logging."""
    logger.info("=== DATABASE CONNECTION TEST ===")
    
    try:
        # Import and test configuration
        from core.config import settings
        logger.info(f"Configuration loaded successfully")
        
        # Log URL encoding information
        from urllib.parse import quote_plus
        if settings.DB_PASSWORD:
            has_special_chars = any(char in settings.DB_PASSWORD for char in ['[', ']', '!', '@', '#', '$', '%', '^', '&', '*'])
            logger.info(f"Password contains special characters: {has_special_chars}")
            if has_special_chars:
                logger.info(f"Original password length: {len(settings.DB_PASSWORD)}")
                logger.info(f"URL-encoded password length: {len(quote_plus(settings.DB_PASSWORD))}")
        
        # Import database
        from core.database import database
        logger.info("Database module imported successfully")
        
        # Attempt connection
        logger.info("Attempting to connect to database...")
        await database.connect()
        logger.info("Database connection successful!")
        
        # Test query
        logger.info("Testing database with simple query...")
        result = await database.fetch_one("SELECT version() as version")
        logger.info(f"Database version: {result}")
        
        # Test another query
        result = await database.fetch_one("SELECT 1 as test")
        logger.info(f"Test query result: {result}")
        
        # Disconnect
        await database.disconnect()
        logger.info("Database disconnected successfully")
        
        logger.info("=== DATABASE CONNECTION TEST PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        logger.error("=== DATABASE CONNECTION TEST FAILED ===")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_database_connection())
    sys.exit(0 if result else 1) 