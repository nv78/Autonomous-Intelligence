#!/usr/bin/env python3
"""
Run database migration for leaderboard tables
Usage: python run_migration.py
"""

import mysql.connector
import sys
import os

# Add the backend directory to path to import from database modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migration():
    """Run the leaderboard tables migration"""
    try:
        # For Docker environment - connect to db container
        conn = mysql.connector.connect(
            host='db',
            user='root', 
            password='',
            database='agents'
        )
        cursor = conn.cursor()
        
        # Read migration file
        migration_file = os.path.join(os.path.dirname(__file__), 'migrations', '001_add_leaderboard_tables.sql')
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Split and execute each statement
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        print("🔄 Running leaderboard tables migration...")
        
        for i, statement in enumerate(statements):
            if statement:
                print(f"  Executing statement {i+1}/{len(statements)}...")
                try:
                    cursor.execute(statement)
                except mysql.connector.Error as e:
                    # Ignore errors for things that already exist (like indexes)
                    if e.errno in [1007, 1050, 1061]:  # Database exists, table exists, duplicate key name
                        print(f"    ⚠️  Skipped (already exists): {e.msg}")
                    else:
                        raise
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Migration completed successfully!")
        print("📊 Leaderboard tables are now available:")
        print("  - benchmark_datasets")
        print("  - model_submissions") 
        print("  - evaluation_results")
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {str(e)}")
        print("💡 Make sure Docker containers are running: docker-compose ps")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration() 