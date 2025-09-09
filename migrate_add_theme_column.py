#!/usr/bin/env python3
"""
Migration script to add the theme column to the user_preferences table.
"""
import asyncio
import logging
import sys
import os
import getpass

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Prompt for credentials if not set in environment
if not os.getenv("DB_USER"):
    os.environ["DB_USER"] = input("Enter DB User: ")
if not os.getenv("DB_PASSWORD"):
    os.environ["DB_PASSWORD"] = getpass.getpass("Enter DB Password: ")
if not os.getenv("DB_HOST"):
    os.environ["DB_HOST"] = input("Enter DB Host (default: localhost): ") or "localhost"
if not os.getenv("DB_NAME"):
    os.environ["DB_NAME"] = input("Enter DB Name: ")

from sqlalchemy import text
from backend.core.database import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %I:%M:%S %p %Z"
)
logger = logging.getLogger(__name__)

async def check_column_exists(table_name: str, column_name: str):
    """Check if a column already exists in a table."""
    query = text(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND column_name = '{column_name}'
    """)
    result = await database.fetch_one(query)
    return result is not None

async def add_theme_column():
    """Add the theme column to the user_preferences table."""
    try:
        if not await check_column_exists('user_preferences', 'theme'):
            await database.execute(text("ALTER TABLE user_preferences ADD COLUMN theme VARCHAR(255) DEFAULT 'default'"))
            logger.info("Successfully added 'theme' column to user_preferences table.")
        else:
            logger.info("Column 'theme' already exists in user_preferences table.")

    except Exception as e:
        logger.error(f"Error adding theme column: {str(e)}")
        raise

async def main():
    """Main migration function."""
    logger.info("Starting migration to add theme column to user_preferences table")
    
    try:
        await database.connect()
        logger.info("Connected to database")
        
        async with database.transaction():
            await add_theme_column()
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        await database.disconnect()
        logger.info("Disconnected from database")

if __name__ == "__main__":
    asyncio.run(main())
