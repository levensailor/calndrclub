#!/usr/bin/env python3
"""
Migration script to add social login fields to the users table.
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

async def add_social_login_columns():
    """Add apple_user_id and google_user_id columns to the users table."""
    try:
        # Add apple_user_id column
        if not await check_column_exists('users', 'apple_user_id'):
            await database.execute(text('ALTER TABLE users ADD COLUMN apple_user_id VARCHAR UNIQUE'))
            logger.info("Successfully added 'apple_user_id' column to users table.")
        else:
            logger.info("Column 'apple_user_id' already exists in users table.")

        # Add google_user_id column
        if not await check_column_exists('users', 'google_user_id'):
            await database.execute(text('ALTER TABLE users ADD COLUMN google_user_id VARCHAR UNIQUE'))
            logger.info("Successfully added 'google_user_id' column to users table.")
        else:
            logger.info("Column 'google_user_id' already exists in users table.")

    except Exception as e:
        logger.error(f"Error adding social login columns: {str(e)}")
        raise

async def modify_password_hash_column():
    """Modify the password_hash column to be nullable."""
    try:
        # Check if column is already nullable
        query = text("""
            SELECT is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'password_hash'
        """)
        result = await database.fetch_one(query)
        
        if result and result['is_nullable'] == 'YES':
            logger.info("Column 'password_hash' is already nullable.")
            return

        await database.execute(text('ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL'))
        logger.info("Successfully made 'password_hash' column nullable.")

    except Exception as e:
        logger.error(f"Error modifying password_hash column: {str(e)}")
        raise

async def main():
    """Main migration function."""
    logger.info("Starting migration to add social login fields to users table")
    
    try:
        await database.connect()
        logger.info("Connected to database")
        
        async with database.transaction():
            await add_social_login_columns()
            await modify_password_hash_column()
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        await database.disconnect()
        logger.info("Disconnected from database")

if __name__ == "__main__":
    asyncio.run(main())
