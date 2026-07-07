import sys
import os
import sqlite3
from sqlalchemy import String, Integer, Boolean, DateTime, Float, JSON

# Set up project root in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from database_layer.db_manager import Base

# DB files to repair
db_files = ["signly.db", "snlag.db"]

def map_type(sqlalchemy_type):
    # Fallback mappings to sqlite types
    type_str = str(sqlalchemy_type).upper()
    if "INT" in type_str:
        return "INTEGER"
    elif "BOOL" in type_str:
        return "BOOLEAN"
    elif "FLOAT" in type_str or "NUM" in type_str:
        return "FLOAT"
    elif "DATETIME" in type_str:
        return "DATETIME"
    elif "JSON" in type_str:
        return "JSON"
    else:
        return "TEXT"

def repair_db(db_path):
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Skipping.")
        return

    print(f"\nRepairing database: {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check all tables defined in Base
        for table_name, table_obj in Base.metadata.tables.items():
            # Check if table exists in sqlite
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                print(f"Table '{table_name}' does not exist in {db_path}. It will be created by SQLAlchemy on startup.")
                continue

            # Get existing columns in SQLite table
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {row[1]: row[2] for row in cursor.fetchall()}

            # Check for missing columns
            for col_obj in table_obj.columns:
                col_name = col_obj.name
                if col_name not in existing_columns:
                    sqlite_type = map_type(col_obj.type)
                    # Handle default values if needed
                    default_clause = ""
                    if col_obj.default is not None and not callable(col_obj.default.arg):
                        default_val = col_obj.default.arg
                        if isinstance(default_val, bool):
                            default_clause = f" DEFAULT {1 if default_val else 0}"
                        elif isinstance(default_val, (int, float)):
                            default_clause = f" DEFAULT {default_val}"
                        elif isinstance(default_val, str):
                            default_clause = f" DEFAULT '{default_val}'"

                    alter_query = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {sqlite_type}{default_clause}"
                    print(f"  Running: {alter_query}")
                    try:
                        cursor.execute(alter_query)
                    except Exception as e:
                        print(f"  Error: {e}")

        conn.commit()
        print(f"Database {db_path} schema repair complete.")
    except Exception as e:
        print(f"Critical error during repair of {db_path}: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    for db_file in db_files:
        repair_db(db_file)
