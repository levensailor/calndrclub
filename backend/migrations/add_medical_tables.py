#!/usr/bin/env python3

"""
Database Migration: Add Medical Tables
Adds medical_providers and medications tables to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from core.database import DATABASE_URL
from core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_medical_tables():
    """Create medical providers and medications tables"""
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Create medical_providers table
            logger.info("Creating medical_providers table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS medical_providers (
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create medications table
            logger.info("Creating medications table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS medications (
                    id SERIAL PRIMARY KEY,
                    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    dosage VARCHAR(100),
                    frequency VARCHAR(100),
                    instructions TEXT,
                    start_date DATE,
                    end_date DATE,
                    is_active BOOLEAN DEFAULT true,
                    reminder_enabled BOOLEAN DEFAULT false,
                    reminder_time TIME,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create indexes for better performance
            logger.info("Creating indexes...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_medical_providers_family_id 
                ON medical_providers(family_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_medical_providers_name 
                ON medical_providers(name);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_medical_providers_specialty 
                ON medical_providers(specialty);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_medical_providers_coordinates 
                ON medical_providers(latitude, longitude);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_medications_family_id 
                ON medications(family_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_medications_name 
                ON medications(name);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_medications_active 
                ON medications(is_active);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_medications_reminder_enabled 
                ON medications(reminder_enabled);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_medications_dates 
                ON medications(start_date, end_date);
            """))
            
            # Commit the transaction
            conn.commit()
            
            logger.info("✅ Medical tables created successfully!")
            
            # Verify tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('medical_providers', 'medications')
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"✅ Verified tables: {tables}")
            
        except Exception as e:
            logger.error(f"❌ Error creating medical tables: {e}")
            conn.rollback()
            raise

def main():
    """Main migration function"""
    logger.info("🚀 Starting medical tables migration...")
    
    try:
        create_medical_tables()
        logger.info("🎉 Migration completed successfully!")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 