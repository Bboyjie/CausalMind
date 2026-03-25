import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'app.db')

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE collection_tasks ADD COLUMN extracted_facts INTEGER NOT NULL DEFAULT 0;")
    conn.commit()
    print(f"Column added successfully to {db_path}.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Column already exists.")
    else:
        print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
