import sqlite3
import os

db_path = 'signly.db'
if not os.path.exists(db_path):
    db_path = 'snlag.db' # Fallback
    if not os.path.exists(db_path):
        print("Database not found.")
        exit(1)

print(f"Using database: {db_path}")
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

def create_table_settings():
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value JSON,
                description TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Ensured app_settings table exists.")
    except Exception as e:
        print(f"Error creating app_settings: {e}")

# Apply soft-delete support across all entities
for table in ['users', 'sign_datasets', 'training_jobs', 'model_versions', 'gesture_libraries', 'collected_data']:
    add_column(table, 'is_deleted', 'BOOLEAN DEFAULT 0')

# New SignDatasetModel fields
add_column('sign_datasets', 'file_hash', 'TEXT')
add_column('sign_datasets', 'parent_id', 'TEXT')
add_column('sign_datasets', 'source_type', "TEXT DEFAULT 'video'")
add_column('sign_datasets', 'file_path', 'TEXT')
add_column('sign_datasets', 'is_validated', 'BOOLEAN DEFAULT 0')
add_column('sign_datasets', 'version', 'INTEGER DEFAULT 1')
add_column('sign_datasets', 'category', 'TEXT')
add_column('sign_datasets', 'description', 'TEXT')
add_column('sign_datasets', 'difficulty', "TEXT DEFAULT 'Easy'")
add_column('sign_datasets', 'tags', 'JSON DEFAULT "[]"')
add_column('sign_datasets', 'status', "TEXT DEFAULT 'pending'")
add_column('sign_datasets', 'progress', "INTEGER DEFAULT 0")
add_column('sign_datasets', 'quality_score', "FLOAT DEFAULT 0.0")
add_column('sign_datasets', 'extraction_metadata', 'JSON DEFAULT "{}"')

# New TrainingJobModel fields
add_column('training_jobs', 'progress', "INTEGER DEFAULT 0")
add_column('training_jobs', 'current_epoch', "INTEGER DEFAULT 0")
add_column('training_jobs', 'total_epochs', "INTEGER DEFAULT 0")
add_column('training_jobs', 'metrics', 'JSON DEFAULT "{}"')

# New SystemLogModel fields
add_column('system_logs', 'service', "TEXT DEFAULT 'kernel'")
add_column('system_logs', 'category', 'TEXT')
add_column('system_logs', 'details', 'JSON')
add_column('system_logs', 'request_id', 'TEXT')
add_column('system_logs', 'user_id', 'INTEGER')
add_column('system_logs', 'dataset_id', 'INTEGER')
add_column('system_logs', 'duration', 'FLOAT')

create_table_settings()

conn.commit()
conn.close()
print("Migration complete.")
