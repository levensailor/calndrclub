#!/usr/bin/env python3
"""
Simple Migration: Create medical tables with all required columns

This migration creates the medical_providers and medications tables with all necessary columns
including google_place_id and rating.

Date: 2025-08-04
Author: Database Schema Fix
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

async def create_medical_tables():
    """Create medical_providers and medications tables with all columns."""
    
    # Get database configuration from environment
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    
    # Build connection string
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print("🔧 Starting medical tables creation")
    print(f"📊 Connecting to database: {db_host}:{db_port}/{db_name}")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("✅ Database connection established")
        
        # Check if medical_providers table exists
        providers_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'medical_providers'
            )
        """)
        
        if providers_exists:
            print("✅ medical_providers table already exists")
        else:
            print("➕ Creating medical_providers table...")
            await conn.execute("""
                CREATE TABLE medical_providers (
                    id SERIAL PRIMARY KEY,
                    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    specialty VARCHAR(255),
                    address TEXT,
                    phone VARCHAR(50),
                    email VARCHAR(255),
                    website VARCHAR(500),
                    latitude DECIMAL(10, 8),
                    longitude DECIMAL(11, 8),
                    zip_code VARCHAR(20),
                    notes TEXT,
                    google_place_id VARCHAR(255),
                    rating NUMERIC(3, 2),
                    created_by_user_id UUID NOT NULL REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ medical_providers table created")
        
        # Check if medications table exists
        medications_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'medications'
            )
        """)
        
        if medications_exists:
            print("✅ medications table already exists")
        else:
            print("➕ Creating medications table...")
            await conn.execute("""
                CREATE TABLE medications (
                    id SERIAL PRIMARY KEY,
                    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    dosage VARCHAR(100),
                    frequency VARCHAR(100),
                    instructions TEXT,
                    start_date DATE,
                    end_date DATE,
                    is_active BOOLEAN DEFAULT TRUE,
                    reminder_enabled BOOLEAN DEFAULT FALSE,
                    reminder_time TIME,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ medications table created")
        
        # Create indexes for better performance
        print("📊 Creating indexes...")
        
        # Medical providers indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medical_providers_family_id 
            ON medical_providers(family_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medical_providers_name 
            ON medical_providers(name)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medical_providers_specialty 
            ON medical_providers(specialty)
        """)
        
        # Medications indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medications_family_id 
            ON medications(family_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medications_name 
            ON medications(name)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medications_active 
            ON medications(is_active)
        """)
        
        print("✅ Indexes created")
        
        # Verify tables and show structure
        providers_check = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'medical_providers'
            )
        """)
        
        medications_check = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'medications'
            )
        """)
        
        if providers_check and medications_check:
            print("✅ Medical tables creation completed successfully!")
            
            # Show table structures
            print("📋 medical_providers table structure:")
            providers_columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'medical_providers'
                ORDER BY ordinal_position
            """)
            
            for col in providers_columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
            
            print("📋 medications table structure:")
            medications_columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'medications'
                ORDER BY ordinal_position
            """)
            
            for col in medications_columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
            
        else:
            print("❌ Table creation verification failed")
            await conn.close()
            return False
        
        await conn.close()
        print("🔒 Database connection closed")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

def main():
    """Main function to run migration."""
    
    print("⬆️  Running medical tables creation...")
    success = asyncio.run(create_medical_tables())
    
    if success:
        print("✅ Migration completed successfully!")
        return 0
    else:
        print("❌ Migration failed!")
        return 1

if __name__ == "__main__":
    exit(main())