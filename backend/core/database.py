import databases
import sqlalchemy
from sqlalchemy import create_engine
from core.config import settings

# Database setup with connection pooling
# Configure the database with proper connection limits
database = databases.Database(
    settings.DATABASE_URL,
    min_size=1,      # Minimum number of connections in the pool
    max_size=5,      # Maximum number of connections per worker
    force_rollback=True,  # Force rollback on connection close
    ssl="prefer"     # Use SSL if available
)

metadata = sqlalchemy.MetaData()

# SQLAlchemy engine for migrations and non-async operations
engine = create_engine(
    settings.DATABASE_URL.replace("+asyncpg", ""),
    pool_size=5,          # Connection pool size
    max_overflow=10,      # Additional connections beyond pool_size
    pool_timeout=30,      # Timeout for getting connection from pool
    pool_recycle=3600,    # Recycle connections after 1 hour
    pool_pre_ping=True    # Verify connections before use
)
