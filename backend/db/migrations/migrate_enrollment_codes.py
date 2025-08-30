import os
import sys
import logging
from datetime import datetime
import uuid

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.core.database import engine, metadata
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    logger.info("Starting enrollment_codes table migration")
    
    # Define the enrollment_codes table
    enrollment_codes = sa.Table(
        "enrollment_codes",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("family_id", UUID(as_uuid=True), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(6), unique=True, nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("coparent_first_name", sa.String(100), nullable=True),
        sa.Column("coparent_last_name", sa.String(100), nullable=True),
        sa.Column("coparent_email", sa.String(255), nullable=True),
        sa.Column("coparent_phone", sa.String(20), nullable=True),
        sa.Column("invitation_sent", sa.Boolean, default=False, nullable=False),
        sa.Column("invitation_sent_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=datetime.now),
    )
    
    # Create the table
    try:
        conn = engine.connect()
        
        # Check if the table already exists
        inspector = sa.inspect(engine)
        if "enrollment_codes" in inspector.get_table_names():
            logger.info("Table enrollment_codes already exists, skipping creation")
            return
        
        # Create the table
        enrollment_codes.create(engine)
        logger.info("Successfully created enrollment_codes table")
        
    except Exception as e:
        logger.error(f"Error creating enrollment_codes table: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
