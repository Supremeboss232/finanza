#!/usr/bin/env python3
"""
Database Data Inspector
Connects to PostgreSQL RDS and displays all data in each table
"""

import os
import sys
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def sync_check_database():
    """Check database using synchronous connection"""
    try:
        import psycopg2
        from psycopg2 import sql
        
        print("\n" + "="*70)
        print("📊 DATABASE INSPECTOR - PostgreSQL RDS")
        print("="*70)
        
        # Connection parameters
        conn_params = {
            'host': 'finbank-db.cxo2eume87bz.eu-north-1.rds.amazonaws.com',
            'port': 5432,
            'database': 'finbank',
            'user': 'postgres_admin',
            'password': 'Supposedbe5',
            'sslmode': 'require',
            'connect_timeout': 10
        }
        
        print("\n🔗 Attempting to connect...")
        print(f"   Host: {conn_params['host']}")
        print(f"   Database: {conn_params['database']}")
        
        # Connect
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        print("✅ Connected successfully!\n")
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("❌ No tables found in database\n")
            conn.close()
            return
        
        print(f"📋 Found {len(tables)} table(s):\n")
        
        for table in tables:
            print(f"\n{'='*70}")
            print(f"📑 TABLE: {table.upper()}")
            print('='*70)
            
            # Get row count
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
            count = cursor.fetchone()[0]
            print(f"   Records: {count}")
            
            # Get column info
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            
            columns = cursor.fetchall()
            print(f"   Columns: {len(columns)}")
            for col_name, col_type in columns:
                print(f"      • {col_name} ({col_type})")
            
            # Show sample data
            if count > 0:
                print(f"\n   Sample Data (first 5 rows):")
                print("   " + "-"*65)
                
                cursor.execute(sql.SQL("SELECT * FROM {} LIMIT 5").format(sql.Identifier(table)))
                rows = cursor.fetchall()
                
                for i, row in enumerate(rows, 1):
                    print(f"   Row {i}:")
                    for (col_name, _), value in zip(columns, row):
                        # Truncate long values
                        val_str = str(value)
                        if len(val_str) > 50:
                            val_str = val_str[:47] + "..."
                        print(f"      {col_name}: {val_str}")
                    print()
        
        print("="*70)
        print("✅ Data inspection complete!\n")
        
        conn.close()
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed")
        print("\nInstalling psycopg2...")
        os.system(f"{sys.executable} -m pip install psycopg2-binary -q")
        print("\nPlease run the script again.")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = sync_check_database()
    sys.exit(0 if success else 1)
