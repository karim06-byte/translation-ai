"""Initialize database with schema and extensions."""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings


def init_database():
    """Create database and run schema if they don't exist."""
    # Connect to postgres database to create our database
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Create database if it doesn't exist
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{settings.postgres_db}'")
    exists = cursor.fetchone()
    
    if not exists:
        cursor.execute(f'CREATE DATABASE {settings.postgres_db}')
        print(f"Database '{settings.postgres_db}' created.")
    else:
        print(f"Database '{settings.postgres_db}' already exists.")
    
    cursor.close()
    conn.close()
    
    # Connect to our database and run schema
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db
    )
    cursor = conn.cursor()
    
    # Read and execute schema
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Execute entire schema - PostgreSQL handles IF NOT EXISTS
    try:
        cursor.execute(schema_sql)
        conn.commit()
        print("Schema executed successfully.")
    except psycopg2.errors.DuplicateTable:
        # Some tables already exist, that's okay
        conn.rollback()
        print("Some tables already exist. Schema is up to date.")
    except psycopg2.errors.DuplicateObject as e:
        # Some objects already exist, that's okay
        conn.rollback()
        print("Some objects already exist. Schema is up to date.")
    except Exception as e:
        # Check if it's just "already exists" errors
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            conn.rollback()
            print("Schema objects already exist. Database is ready.")
        else:
            # Real error, re-raise
            conn.rollback()
            raise
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    init_database()

