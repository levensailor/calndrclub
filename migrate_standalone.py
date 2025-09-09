#!/usr/bin/env python3
"""
(Standalone) Migration script to update the users and user_preferences tables.
"""
import asyncio
import logging
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %I:%M:%S %p %Z"
)
logger = logging.getLogger(__name__)

# --- Database Connection ---
async def get_database_engine():
    """Creates a new async database engine."""
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")

    if not all([db_user, db_password, db_host, db_name]):
        logger.error("❌ Missing one or more required database environment variables.")
        return None
        
    db_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}/{db_name}"
    return create_async_engine(db_url)

# --- Helper Functions ---
async def check_column_exists(engine, table_name: str, column_name: str):
    """Checks if a column already exists in a specific table."""
    query = text(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND column_name = '{column_name}'
    """)
    async with engine.connect() as connection:
        result = await connection.execute(query)
        return result.scalar_one_or_none() is not None

async def is_column_nullable(engine, table_name: str, column_name: str):
    """Checks if a column is nullable."""
    query = text(f"""
        SELECT is_nullable 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND column_name = '{column_name}'
    """)
    async with engine.connect() as connection:
        result = await connection.execute(query)
        is_nullable_str = result.scalar_one_or_none()
    return is_nullable_str == 'YES'

# --- Migration Logic ---
async def update_users_table(engine):
    """Adds social login columns and makes password hash nullable."""
    logger.info("Checking 'users' table schema...")
    async with engine.connect() as connection:
        async with connection.begin():
            if not await check_column_exists(engine, 'users', 'apple_user_id'):
                await connection.execute(text('ALTER TABLE users ADD COLUMN apple_user_id VARCHAR UNIQUE'))
                logger.info("✅ Successfully added 'apple_user_id' column to 'users' table.")
            else:
                logger.info("➡️ Column 'apple_user_id' already exists.")

            if not await check_column_exists(engine, 'users', 'google_user_id'):
                await connection.execute(text('ALTER TABLE users ADD COLUMN google_user_id VARCHAR UNIQUE'))
                logger.info("✅ Successfully added 'google_user_id' column to 'users' table.")
            else:
                logger.info("➡️ Column 'google_user_id' already exists.")

            if not await is_column_nullable(engine, 'users', 'password_hash'):
                await connection.execute(text('ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL'))
                logger.info("✅ Successfully made 'password_hash' column nullable.")
            else:
                logger.info("➡️ Column 'password_hash' is already nullable.")

async def update_user_preferences_table(engine):
    """Adds theme and notification_preferences columns."""
    logger.info("Checking 'user_preferences' table schema...")
    async with engine.connect() as connection:
        async with connection.begin():
            if not await check_column_exists(engine, 'user_preferences', 'theme'):
                await connection.execute(text("ALTER TABLE user_preferences ADD COLUMN theme VARCHAR(255) DEFAULT 'default'"))
                logger.info("✅ Successfully added 'theme' column.")
            else:
                logger.info("➡️ Column 'theme' already exists.")
                
            if not await check_column_exists(engine, 'user_preferences', 'notification_preferences'):
                await connection.execute(text("ALTER TABLE user_preferences ADD COLUMN notification_preferences JSON"))
                logger.info("✅ Successfully added 'notification_preferences' column.")
            else:
                logger.info("➡️ Column 'notification_preferences' already exists.")

async def create_user_profiles_table(engine):
    """Creates the user_profiles table if it doesn't exist."""
    logger.info("Checking 'user_profiles' table...")
    query = text("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            bio TEXT,
            profile_photo_url VARCHAR(255),
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
        )
    """)
    async with engine.connect() as connection:
        async with connection.begin():
            await connection.execute(query)
            logger.info("✅ Table 'user_profiles' is present and correct.")

# --- Main Execution ---
async def main():
    """Main migration function."""
    logger.info("🚀 Starting standalone schema migration...")
    engine = await get_database_engine()
    
    if not engine:
        return
        
    try:
        await update_users_table(engine)
        await update_user_preferences_table(engine)
        await create_user_profiles_table(engine)
        logger.info("🎉 Migration completed successfully!")
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
    finally:
        await engine.dispose()
        logger.info("🔌 Database connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
