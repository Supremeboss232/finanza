#!/usr/bin/env python
"""Check what tables exist in the database"""

import psycopg2
import sys

try:
    conn = psycopg2.connect(
        dbname='Finanza',
        user='postgres',
        password='Supposedbe5',
        host='127.0.0.1',
        port=5432
    )
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    
    tables = cursor.fetchall()
    print('Tables in database:')
    print('-' * 60)
    for table in tables:
        print(f'  {table[0]}')
    
    # Search for treasury/portfolio/asset related tables
    print('\n\nTreasury/Portfolio/Asset Related Tables:')
    print('-' * 60)
    treasury_keywords = ['treasury', 'portfolio', 'asset', 'investment', 'strategy', 'allocation', 'fund']
    found = False
    for table in tables:
        table_name = table[0]
        for keyword in treasury_keywords:
            if keyword in table_name.lower():
                print(f'  ✓ {table_name}')
                found = True
                break
    
    if not found:
        print('  ✗ No treasury/portfolio/asset related tables found')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'Error connecting to database: {e}', file=sys.stderr)
    sys.exit(1)
