#!/usr/bin/env python3

"""
Database Index Optimization for Custody Performance
Adds specific indexes to dramatically improve handoff times query performance
"""

import asyncio
import asyncpg
import os
import time
from datetime import datetime
from urllib.parse import quote_plus

# Database connection configuration
DB_USER = "calndr_user"
DB_PASSWORD = "MChksLq[i2W4OEkxAC8dPKVNzPpaNgI!"
DB_HOST = "calndr-staging-db.cjy8vmu6rtrc.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "calndr"

# URL encode the password to handle special characters
DB_PASSWORD_ENCODED = quote_plus(DB_PASSWORD)

# Connection string with properly encoded password
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"🔌 Connecting to: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Indexes to create for custody performance optimization
CUSTODY_INDEXES = [
    {
        'name': 'idx_custody_family_date_optimized',
        'table': 'custody',
        'columns': 'family_id, date',
        'description': 'Optimized index for custody date range queries'
    },
    {
        'name': 'idx_custody_family_custodian',
        'table': 'custody', 
        'columns': 'family_id, custodian_id',
        'description': 'Index for custody queries by family and custodian'
    },
    {
        'name': 'idx_users_family_id_optimized',
        'table': 'users',
        'columns': 'family_id',
        'description': 'Optimized index for family member lookups'
    },
    {
        'name': 'idx_custody_handoff_queries',
        'table': 'custody',
        'columns': 'family_id, date, handoff_day',
        'description': 'Composite index for handoff day queries'
    }
]

async def check_index_exists(conn, index_name):
    """Check if an index already exists."""
    query = """
    SELECT indexname 
    FROM pg_indexes 
    WHERE indexname = $1
    """
    result = await conn.fetchval(query, index_name)
    return result is not None

async def create_index(conn, index_config):
    """Create a single index with error handling."""
    index_name = index_config['name']
    table_name = index_config['table']
    columns = index_config['columns']
    description = index_config['description']
    
    # Check if index already exists
    if await check_index_exists(conn, index_name):
        print(f"⏭️  Index {index_name} already exists, skipping...")
        return True
    
    # Create the index
    sql = f"CREATE INDEX CONCURRENTLY {index_name} ON {table_name} ({columns})"
    
    print(f"🔨 Creating {table_name}: {description}...")
    start_time = time.time()
    
    try:
        await conn.execute(sql)
        duration = time.time() - start_time
        print(f"✅ {description} ({duration:.1f}s)")
        return True
    except Exception as e:
        print(f"❌ Failed to create {index_name}: {str(e)}")
        return False

async def show_existing_indexes(conn):
    """Show existing indexes on custody and users tables."""
    query = """
    SELECT 
        schemaname,
        tablename,
        indexname,
        indexdef
    FROM pg_indexes 
    WHERE tablename IN ('custody', 'users')
    AND schemaname = 'public'
    ORDER BY tablename, indexname
    """
    
    indexes = await conn.fetch(query)
    
    print("\n📋 Current Indexes on Custody and Users Tables:")
    print("=" * 80)
    
    current_table = None
    for index in indexes:
        if current_table != index['tablename']:
            current_table = index['tablename']
            print(f"\n📊 {current_table.upper()} table:")
        
        print(f"  • {index['indexname']}")
        print(f"    {index['indexdef']}")

async def analyze_query_performance(conn):
    """Show query execution plans for common custody queries."""
    print("\n🔍 Query Performance Analysis:")
    print("=" * 80)
    
    # Test query 1: Monthly custody records
    test_query_1 = """
    EXPLAIN ANALYZE 
    SELECT c.*, u.first_name 
    FROM custody c 
    JOIN users u ON c.custodian_id = u.id 
    WHERE c.family_id = (SELECT id FROM families LIMIT 1) 
    AND c.date BETWEEN '2024-01-01' AND '2024-01-31'
    """
    
    try:
        print("\n📈 Test Query 1: Monthly custody records with user names")
        result = await conn.fetch(test_query_1)
        for row in result:
            print(f"   {row[0]}")
    except Exception as e:
        print(f"   ⚠️  Could not analyze query: {e}")

async def test_connection():
    """Test database connection before running optimization."""
    try:
        print("🔍 Testing database connection...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Test basic query
        result = await conn.fetchval('SELECT 1')
        if result == 1:
            print("✅ Database connection test successful!")
        else:
            print("❌ Database connection test failed!")
            return False
            
        # Test table access
        custody_count = await conn.fetchval('SELECT COUNT(*) FROM custody')
        users_count = await conn.fetchval('SELECT COUNT(*) FROM users')
        print(f"📊 Found {custody_count} custody records and {users_count} users")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("   • Check if database host is reachable")
        print("   • Verify username and password are correct")
        print("   • Ensure database name exists")
        print("   • Check if SSL is required")
        return False

async def main():
    """Main function to optimize custody query performance."""
    print("🚀 Starting Custody Performance Optimization")
    print("=" * 80)
    
    # Test connection first
    if not await test_connection():
        print("\n❌ Connection test failed. Please fix connection issues before proceeding.")
        return False
    
    try:
        # Connect to database
        print(f"\n🔌 Connecting to database for optimization...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Show current indexes
        await show_existing_indexes(conn)
        
        # Create performance indexes
        print(f"\n🔧 Creating {len(CUSTODY_INDEXES)} performance indexes...")
        print("=" * 80)
        
        success_count = 0
        for index_config in CUSTODY_INDEXES:
            if await create_index(conn, index_config):
                success_count += 1
            await asyncio.sleep(0.1)  # Brief pause between index creations
        
        print(f"\n🎉 Index Optimization Completed!")
        print("=" * 80)
        print(f"📊 Indexes created: {success_count}/{len(CUSTODY_INDEXES)}")
        
        # Analyze performance
        await analyze_query_performance(conn)
        
        print("\n📈 Expected Performance Improvements:")
        print("   • Handoff times loading: 70-90% faster")
        print("   • Monthly custody queries: 60-80% faster") 
        print("   • Family member lookups: 50-70% faster")
        print("   • iOS app responsiveness: Significantly improved")
        
        print(f"\n✅ Optimization completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error during optimization: {e}")
        print(f"📋 Full error details: {repr(e)}")
        return False
    finally:
        if 'conn' in locals():
            await conn.close()
    
    return True

if __name__ == "__main__":
    asyncio.run(main()) 