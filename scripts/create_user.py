"""Create a default user for login."""
import sys
import psycopg2
import bcrypt
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings


def create_user(username: str = "admin", email: str = "admin@example.com", 
                password: str = "admin123", full_name: str = "Administrator"):
    """Create a user in the database."""
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db
    )
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute(
            "SELECT username, email FROM users WHERE username = %s OR email = %s",
            (username, email)
        )
        existing = cursor.fetchone()
        
        if existing:
            print(f"User '{username}' or email '{email}' already exists!")
            print(f"Username: {existing[0]}")
            print(f"Email: {existing[1]}")
            return
        
        # Hash password using bcrypt
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        # Create new user
        cursor.execute("""
            INSERT INTO users (username, email, hashed_password, full_name, is_active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, username, email
        """, (username, email, hashed_password, full_name, True))
        
        user_data = cursor.fetchone()
        conn.commit()
        
        print("=" * 50)
        print("User created successfully!")
        print("=" * 50)
        print(f"User ID: {user_data[0]}")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Full Name: {full_name}")
        print("=" * 50)
        print("\nYou can now login at http://localhost:3000/login")
        print(f"Use these credentials to login:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print("=" * 50)
    
    except Exception as e:
        conn.rollback()
        print(f"Error creating user: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a user account")
    parser.add_argument("--username", default="admin", help="Username (default: admin)")
    parser.add_argument("--email", default="admin@example.com", help="Email (default: admin@example.com)")
    parser.add_argument("--password", default="admin123", help="Password (default: admin123)")
    parser.add_argument("--full-name", default="Administrator", help="Full name (default: Administrator)")
    
    args = parser.parse_args()
    
    create_user(
        username=args.username,
        email=args.email,
        password=args.password,
        full_name=args.full_name
    )

