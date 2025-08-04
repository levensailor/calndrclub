#!/usr/bin/env python3
"""
Migration: Add google_place_id column to medical_providers table

This migration adds the missing google_place_id column to the medical_providers table
to support storing Google Places API place IDs for enhanced search functionality.

Run this migration to fix the database schema error:
    column "google_place_id" of relation "medical_providers" does not exist

Date: 2025-08-04
Author: Enhanced Medical Search Implementation
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from backend
sys.path.append(str(Path(__file__).parent.parent))

from core.config import get_settings
from core.logging import setup_logging

# Setup logging
logger = setup_logging(__name__)

async def migrate_add_google_place_id():
    """Add google_place_id column to medical_providers table if it doesn't exist."""
    
    settings = get_settings()
    
    # Build connection string
    db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    
    logger.info("Starting migration: Add google_place_id to medical_providers table")
    logger.info(f"Connecting to database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        logger.info("✅ Database connection established")
        
        # Check if column already exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'medical_providers' 
                AND column_name = 'google_place_id'
            )
        """)
        
        if column_exists:
            logger.info("✅ Column 'google_place_id' already exists in medical_providers table")
            await conn.close()
            return True
            
        logger.info("➕ Adding 'google_place_id' column to medical_providers table...")
        
        # Add the column
        await conn.execute("""
            ALTER TABLE medical_providers 
            ADD COLUMN google_place_id VARCHAR(255) NULL
        """)
        
        # Also add the rating column if it doesn't exist (in case it's missing too)
        rating_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'medical_providers' 
                AND column_name = 'rating'
            )
        """)
        
        if not rating_exists:
            logger.info("➕ Adding 'rating' column to medical_providers table...")
            await conn.execute("""
                ALTER TABLE medical_providers 
                ADD COLUMN rating NUMERIC(3, 2) NULL
            """)
        
        # Verify the columns were added
        google_place_id_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'medical_providers' 
                AND column_name = 'google_place_id'
            )
        """)
        
        rating_exists_after = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'medical_providers' 
                AND column_name = 'rating'
            )
        """)
        
        if google_place_id_exists and rating_exists_after:
            logger.info("✅ Migration completed successfully!")
            logger.info("✅ Column 'google_place_id' added to medical_providers table")
            logger.info("✅ Column 'rating' verified in medical_providers table")
        else:
            logger.error("❌ Migration failed - columns were not added properly")
            await conn.close()
            return False
            
        # Show current table structure
        logger.info("📋 Current medical_providers table structure:")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'medical_providers'
            ORDER BY ordinal_position
        """)
        
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            logger.info(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
        
        await conn.close()
        logger.info("🔒 Database connection closed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed with error: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        return False

async def rollback_google_place_id():
    """Remove google_place_id column from medical_providers table (rollback)."""
    
    settings = get_settings()
    
    # Build connection string
    db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    
    logger.info("Starting rollback: Remove google_place_id from medical_providers table")
    logger.info(f"Connecting to database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        logger.info("✅ Database connection established")
        
        # Check if column exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'medical_providers' 
                AND column_name = 'google_place_id'
            )
        """)
        
        if not column_exists:
            logger.info("✅ Column 'google_place_id' does not exist - rollback not needed")
            await conn.close()
            return True
            
        logger.info("➖ Removing 'google_place_id' column from medical_providers table...")
        
        # Remove the column
        await conn.execute("""
            ALTER TABLE medical_providers 
            DROP COLUMN google_place_id
        """)
        
        # Verify the column was removed
        column_exists_after = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'medical_providers' 
                AND column_name = 'google_place_id'
            )
        """)
        
        if not column_exists_after:
            logger.info("✅ Rollback completed successfully!")
            logger.info("✅ Column 'google_place_id' removed from medical_providers table")
        else:
            logger.error("❌ Rollback failed - column was not removed")
            await conn.close()
            return False
            
        await conn.close()
        logger.info("🔒 Database connection closed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Rollback failed with error: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        return False

def main():
    """Main function to run migration or rollback."""
    
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        print("🔄 Running rollback migration...")
        success = asyncio.run(rollback_google_place_id())
    else:
        print("⬆️  Running forward migration...")
        success = asyncio.run(migrate_add_google_place_id())
    
    if success:
        print("✅ Migration completed successfully!")
        return 0
    else:
        print("❌ Migration failed!")
        return 1

if __name__ == "__main__":
    exit(main())