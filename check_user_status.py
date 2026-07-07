import sqlite3
import os

for db_file in ["signly.db", "snlag.db"]:
    if os.path.exists(db_file):
        print(f"\n--- {db_file} Users ---")
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(users)")
                cols = [row[1] for row in cursor.fetchall()]
                cursor.execute("SELECT * FROM users")
                rows = cursor.fetchall()
                for row in rows:
                    user_dict = dict(zip(cols, row))
                    # Print without password_hash for security, but print the rest
                    if "password_hash" in user_dict:
                        user_dict["password_hash"] = "HASHED"
                    print(user_dict)
            else:
                print("No 'users' table found.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            conn.close()
