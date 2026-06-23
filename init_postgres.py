from database_layer.db_manager import init_db
import sys
import os

# Add current directory to path so it can find database_layer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Connecting to PostgreSQL and creating tables...")
    try:
        init_db()
        print("Success! Tables created in 'snlag' database.")
    except Exception as e:
        print(f"Error creating tables: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running.")
        print("2. The 'snlag' database exists.")
        print("3. You have 'psycopg2-binary' installed (pip install psycopg2-binary).")
