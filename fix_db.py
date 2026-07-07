import sqlite3
import os

db_path = 'signly.db'
if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column(table, column, definition):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"Added column {column} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {column} already exists in {table}")
        else:
            print(f"Error adding {column} to {table}: {e}")

# Fix users table
add_column('users', 'phone', 'TEXT')
add_column('users', 'bio', 'TEXT')
add_column('users', 'banner_url', 'TEXT')

# Fix system_logs table (from previous errors in log)
add_column('system_logs', 'service', "TEXT DEFAULT 'kernel'")
add_column('system_logs', 'category', 'TEXT')
add_column('system_logs', 'details', 'JSON')
add_column('system_logs', 'request_id', 'TEXT')
add_column('system_logs', 'user_id', 'TEXT')
add_column('system_logs', 'dataset_id', 'TEXT')
add_column('system_logs', 'duration', 'FLOAT')

conn.commit()
conn.close()
print("Database fix complete.")
