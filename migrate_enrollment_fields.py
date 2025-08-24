#!/usr/bin/env python3
"""
Migration script to add enrollment fields to users table.

Adds three new boolean fields:
- enrolled: True when user completes enrollment process
- coparent_enrolled: True when coparent completes enrollment 
- coparent_invited: True when user generates code for coparent
"""

import os
import sys
import asyncio
from datetime import datetime, timezone

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'backend'))

from core.database import database
from core.logging import logger

async def add_enrollment_fields():
    """Add enrollment fields to users table"""
    try:
        await database.connect()
        
        # Add enrolled field
        await database.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS enrolled BOOLEAN DEFAULT FALSE
        """)
        logger.info("Added 'enrolled' column to users table")
        
        # Add coparent_enrolled field  
        await database.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS coparent_enrolled BOOLEAN DEFAULT FALSE
        """)
        logger.info("Added 'coparent_enrolled' column to users table")
        
        # Add coparent_invited field
        await database.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS coparent_invited BOOLEAN DEFAULT FALSE
        """)
        logger.info("Added 'coparent_invited' column to users table")
        
        # Create index for enrollment status queries
        await database.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_enrolled ON users(enrolled)
        """)
        logger.info("Created index on 'enrolled' column")
        
        # Create index for coparent enrollment queries
        await database.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_coparent_enrolled ON users(coparent_enrolled)
        """)
        logger.info("Created index on 'coparent_enrolled' column")
        
        logger.info("✅ Successfully added enrollment fields to users table")
        
    except Exception as e:
        logger.error(f"❌ Failed to add enrollment fields: {e}")
        raise
    finally:
        await database.disconnect()

async def main():
    """Main migration function"""
    print("🚀 Starting enrollment fields migration...")
    await add_enrollment_fields()
    print("🎉 Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
