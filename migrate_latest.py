#!/usr/bin/env python3
"""
Migration script to update the users and user_preferences tables to the latest schema.

This script is idempotent and can be run multiple times safely. It will:
- Add 'apple_user_id' and 'google_user_id' columns to the 'users' table.
- Make the 'password_hash' column in 'users' nullable.
- Add the 'theme' column to the 'user_preferences' table.
- Add the 'notification_preferences' column to the 'user_preferences' table.
"""
import asyncio
import logging
import sys
import os
from sqlalchemy import text
from backend.core.database import database

# --- Path Setup ---
# Add the project root to the Python path to allow importing 'backend'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %I:%M:%S %p %Z"
)
logger = logging.getLogger(__name__)

# --- Helper Functions ---
async def check_column_exists(table_name: str, column_name: str):
    """Checks if a column already exists in a specific table."""
    query = text(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND column_name = '{column_name}'
    """)
    async with database.connection() as connection:
        result = await connection.fetch_one(query)
    return result is not None

async def is_column_nullable(table_name: str, column_name: str):
    """Checks if a column is nullable."""
    query = text(f"""
        SELECT is_nullable 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND column_name = '{column_name}'
    """)
    async with database.connection() as connection:
        result = await connection.fetch_one(query)
    return result and result['is_nullable'] == 'YES'

# --- Migration Logic ---
async def update_users_table():
    """Adds social login columns and makes password hash nullable."""
    logger.info("Checking 'users' table schema...")
    # Add apple_user_id column
    if not await check_column_exists('users', 'apple_user_id'):
        await database.execute(text('ALTER TABLE users ADD COLUMN apple_user_id VARCHAR UNIQUE'))
        logger.info("✅ Successfully added 'apple_user_id' column to 'users' table.")
    else:
        logger.info("➡️ Column 'apple_user_id' already exists in 'users' table.")

    # Add google_user_id column
    if not await check_column_exists('users', 'google_user_id'):
        await database.execute(text('ALTER TABLE users ADD COLUMN google_user_id VARCHAR UNIQUE'))
        logger.info("✅ Successfully added 'google_user_id' column to 'users' table.")
    else:
        logger.info("➡️ Column 'google_user_id' already exists in 'users' table.")

    # Make password_hash nullable
    if not await is_column_nullable('users', 'password_hash'):
        await database.execute(text('ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL'))
        logger.info("✅ Successfully made 'password_hash' column nullable.")
    else:
        logger.info("➡️ Column 'password_hash' is already nullable.")

async def update_user_preferences_table():
    """Adds theme and notification_preferences columns."""
    logger.info("Checking 'user_preferences' table schema...")
    # Add theme column
    if not await check_column_exists('user_preferences', 'theme'):
        await database.execute(text("ALTER TABLE user_preferences ADD COLUMN theme VARCHAR(255) DEFAULT 'default'"))
        logger.info("✅ Successfully added 'theme' column to 'user_preferences' table.")
    else:
        logger.info("➡️ Column 'theme' already exists in 'user_preferences' table.")
        
    # Add notification_preferences column
    if not await check_column_exists('user_preferences', 'notification_preferences'):
        await database.execute(text("ALTER TABLE user_preferences ADD COLUMN notification_preferences JSON"))
        logger.info("✅ Successfully added 'notification_preferences' column to 'user_preferences' table.")
    else:
        logger.info("➡️ Column 'notification_preferences' already exists in 'user_preferences' table.")

# --- Main Execution ---
async def main():
    """Main migration function."""
    logger.info("🚀 Starting comprehensive schema migration...")
    
    try:
        if not all(os.getenv(k) for k in ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"]):
            logger.error("❌ Missing one or more required database environment variables.")
            logger.error("   Please set DB_USER, DB_PASSWORD, DB_HOST, and DB_NAME.")
            return

        await database.connect()
        logger.info("🔗 Connected to database.")
        
        async with database.transaction():
            await update_users_table()
            await update_user_preferences_table()
        
        logger.info("🎉 Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        # raise # Commented out to prevent crash on expected errors
    finally:
        if database.is_connected:
            await database.disconnect()
            logger.info("🔌 Disconnected from database.")

if __name__ == "__main__":
    asyncio.run(main())
