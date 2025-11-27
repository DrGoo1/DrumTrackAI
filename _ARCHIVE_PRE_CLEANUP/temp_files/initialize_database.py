"""
Initialize Unified DrumTracKAI Database
Creates complete database structure and prepares for indexing
"""

import sqlite3
from pathlib import Path
import os

def initialize_database():
    """Initialize the unified database"""
    
    # Use existing admin database location
    db_path = "f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db"
    
    print("🗄️  DrumTracKAI Database Initialization")
    print("="*60)
    print(f"Database: {db_path}")
    
    # Backup existing if present
    if os.path.exists(db_path):
        backup_path = db_path.replace('.db', '_backup_pre_upgrade.db')
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created: {backup_path}")
    
    # Connect
    conn = sqlite3.connect(db_path)
    
    # Read and execute schema
    schema_path = "unified_database_schema.sql"
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    print("\n📊 Creating tables...")
    conn.executescript(schema_sql)
    conn.commit()
    
    # Verify tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n✓ Created {len(tables)} tables:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  - {table:30s} {count:6d} rows")
    
    # Create indexes for performance
    print("\n🔍 Creating indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_patterns_tempo ON drum_patterns(tempo_bpm)",
        "CREATE INDEX IF NOT EXISTS idx_patterns_style ON drum_patterns(style)",
        "CREATE INDEX IF NOT EXISTS idx_patterns_section ON drum_patterns(section_type)",
        "CREATE INDEX IF NOT EXISTS idx_patterns_complexity ON drum_patterns(complexity)",
        "CREATE INDEX IF NOT EXISTS idx_patterns_density ON drum_patterns(density)",
        "CREATE INDEX IF NOT EXISTS idx_samples_type ON drum_samples(drum_type)",
        "CREATE INDEX IF NOT EXISTS idx_samples_category ON drum_samples(category)",
    ]
    
    for idx_sql in indexes:
        cursor.execute(idx_sql)
    
    conn.commit()
    print("✓ Indexes created")
    
    # Get database size
    db_size = os.path.getsize(db_path) / 1024  # KB
    print(f"\n📦 Database size: {db_size:.1f} KB")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ DATABASE READY")
    print("="*60)
    print("\n🎯 Next Step:")
    print("   Run: python ultimate_scanner.py --midi-only")
    print("   This will index all 91,074 MIDI patterns")

if __name__ == "__main__":
    initialize_database()
