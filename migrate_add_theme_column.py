#!/usr/bin/env python3
"""
Migration script to add the theme column to the user_preferences table.
"""
import asyncio
import logging
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
