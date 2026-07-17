#!/usr/bin/env python3
"""
Add admin_role column to users table if it doesn't exist
"""

import sqlite3

db_file = 'finanza.db'

try:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "admin_role" in columns:
        print("✅ Column admin_role already exists")
    else:
        # Add the column
        cursor.execute("ALTER TABLE users ADD COLUMN admin_role VARCHAR DEFAULT 'STANDARD'")
        conn.commit()
        print("✅ Column admin_role added to users table")
    
    conn.close()
except Exception as e:
    print(f"❌ Error updating database: {e}")
    exit(1)
