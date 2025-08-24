#!/usr/bin/env python3
"""
Database migration script to create the enrollment_codes table for family linking.
This script should be run on the server after deploying the updated backend code.
"""

import os
import databases
import sqlalchemy
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# Load environment variables
load_dotenv()

# Database configuration
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

async def create_enrollment_codes_table():
    """Create enrollment_codes table for family linking"""
    
    try:
        await database.connect()
        print("🔗 Connected to database")
        
        # Create enrollment_codes table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS enrollment_codes (
            id SERIAL PRIMARY KEY,
            code VARCHAR(6) UNIQUE NOT NULL,
            family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
            created_by_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            is_used BOOLEAN DEFAULT FALSE,
            used_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '7 days'),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        await database.execute(create_table_sql)
        print("✅ Created enrollment_codes table")
        
        # Create indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_enrollment_codes_code ON enrollment_codes(code);",
            "CREATE INDEX IF NOT EXISTS idx_enrollment_codes_family_id ON enrollment_codes(family_id);",
            "CREATE INDEX IF NOT EXISTS idx_enrollment_codes_created_by ON enrollment_codes(created_by_user_id);",
            "CREATE INDEX IF NOT EXISTS idx_enrollment_codes_expires_at ON enrollment_codes(expires_at);",
            "CREATE INDEX IF NOT EXISTS idx_enrollment_codes_is_used ON enrollment_codes(is_used);"
        ]
        
        for index_sql in indexes:
            await database.execute(index_sql)
        
        print("✅ Created indexes for enrollment_codes table")
        
        # Create trigger to update updated_at timestamp
        trigger_sql = """
        CREATE OR REPLACE FUNCTION update_enrollment_codes_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        DROP TRIGGER IF EXISTS update_enrollment_codes_updated_at ON enrollment_codes;
        CREATE TRIGGER update_enrollment_codes_updated_at
            BEFORE UPDATE ON enrollment_codes
            FOR EACH ROW
            EXECUTE FUNCTION update_enrollment_codes_updated_at();
        """
        
        await database.execute(trigger_sql)
        print("✅ Created trigger for enrollment_codes table")
        
        print("✅ Successfully created enrollment_codes table with indexes and triggers")
        return True
        
    except Exception as e:
        print(f"❌ Error creating enrollment_codes table: {e}")
        return False
    finally:
        await database.disconnect()

async def main():
    print("🚀 Starting enrollment codes table migration...")
    
    success = await create_enrollment_codes_table()
    
    if success:
        print("✅ Enrollment codes migration completed successfully!")
        return 0
    else:
        print("❌ Enrollment codes migration failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
