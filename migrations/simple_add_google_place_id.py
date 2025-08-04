#!/usr/bin/env python3
"""
Simple Migration: Add google_place_id column to medical_providers table

This migration adds the missing google_place_id column to the medical_providers table
using direct environment variable access.

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

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

async def migrate_add_google_place_id():
    """Add google_place_id column to medical_providers table if it doesn't exist."""
    
    # Get database configuration from environment
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    
    # Build connection string
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print("🔧 Starting migration: Add google_place_id to medical_providers table")
    print(f"📊 Connecting to database: {db_host}:{db_port}/{db_name}")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("✅ Database connection established")
        
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
            print("✅ Column 'google_place_id' already exists in medical_providers table")
            await conn.close()
            return True
            
        print("➕ Adding 'google_place_id' column to medical_providers table...")
        
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
            print("➕ Adding 'rating' column to medical_providers table...")
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
            print("✅ Migration completed successfully!")
            print("✅ Column 'google_place_id' added to medical_providers table")
            print("✅ Column 'rating' verified in medical_providers table")
        else:
            print("❌ Migration failed - columns were not added properly")
            await conn.close()
            return False
            
        # Show current table structure
        print("📋 Current medical_providers table structure:")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'medical_providers'
            ORDER BY ordinal_position
        """)
        
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            print(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
        
        await conn.close()
        print("🔒 Database connection closed")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

def main():
    """Main function to run migration."""
    
    print("⬆️  Running migration...")
    success = asyncio.run(migrate_add_google_place_id())
    
    if success:
        print("✅ Migration completed successfully!")
        return 0
    else:
        print("❌ Migration failed!")
        return 1

if __name__ == "__main__":
    exit(main())