#!/usr/bin/env python3
"""
Migration script to add updated_at column to users table.
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import text

from backend.core.database import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %I:%M:%S %p %Z"
)
logger = logging.getLogger(__name__)

async def check_column_exists():
    """Check if updated_at column already exists in users table."""
    query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'updated_at'
    """)
    
    result = await database.fetch_one(query)
    return result is not None

async def add_updated_at_column():
    """Add updated_at column to users table."""
    try:
        # Check if column already exists
        column_exists = await check_column_exists()
        
        if column_exists:
            logger.info("Column 'updated_at' already exists in users table.")
            return
        
        # Add the column
        query = text("""
            ALTER TABLE users 
            ADD COLUMN updated_at TIMESTAMP DEFAULT NOW()
        """)
        
        await database.execute(query)
        logger.info("Successfully added 'updated_at' column to users table.")
        
        # Update the column with created_at values
        update_query = text("""
            UPDATE users 
            SET updated_at = created_at 
            WHERE updated_at IS NULL
        """)
        
        await database.execute(update_query)
        logger.info("Successfully updated 'updated_at' values based on 'created_at'.")
        
    except Exception as e:
        logger.error(f"Error adding updated_at column: {str(e)}")
        raise

async def main():
    """Main migration function."""
    logger.info("Starting migration to add updated_at column to users table")
    
    try:
        # Connect to the database
        await database.connect()
        logger.info("Connected to database")
        
        # Run the migration
        await add_updated_at_column()
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        # Disconnect from the database
        await database.disconnect()
        logger.info("Disconnected from database")

if __name__ == "__main__":
    asyncio.run(main())
