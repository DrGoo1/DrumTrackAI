#!/usr/bin/env python3
"""Check database tables"""
import sqlite3
from pathlib import Path

db_path = Path("admin/data/drum_training.db")
print(f"Checking database: {db_path}")
print(f"Exists: {db_path.exists()}")

if db_path.exists():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    print(f"\nTables found: {tables}")
    
    # Check each table
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  - {table}: {count} rows")
    
    # Check if humanization_features exists
    if 'humanization_features' in tables:
        print("\n✅ humanization_features table EXISTS")
        cur.execute("SELECT * FROM humanization_features LIMIT 1")
        cols = [desc[0] for desc in cur.description]
        print(f"   Columns: {cols}")
    else:
        print("\n❌ humanization_features table MISSING")
        print("\nCreating humanization_features table...")
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS humanization_features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                drummer_name TEXT,
                style TEXT,
                tempo REAL,
                features_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        print("✅ Table created!")
    
    conn.close()
else:
    print("\n❌ Database file does not exist!")
    print("Creating database and table...")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS humanization_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            drummer_name TEXT,
            style TEXT,
            tempo REAL,
            features_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sd_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            instrument TEXT,
            velocity INT,
            articulation TEXT,
            features_json TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database and tables created!")
