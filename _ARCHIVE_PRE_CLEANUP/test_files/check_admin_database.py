"""
Check Admin Database for Training Data
Examines the organized database to find all available samples
"""

import sqlite3
from pathlib import Path

db_paths = [
    Path("admin/drumtrackai.db"),
    Path("admin/admin/drumtrackai.db"),
    Path("admin/sd3_samples_database.db"),
]

print("=" * 80)
print("📊 Admin Database Analysis")
print("=" * 80)

for db_path in db_paths:
    if not db_path.exists():
        continue
    
    print(f"\n🗄️ Database: {db_path}")
    print("-" * 80)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"📋 Tables: {len(tables)}")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count} rows")
        
        # Check for sample paths
        sample_tables = ['samples', 'sd_samples', 'drum_samples', 'audio_files', 'sd3_samples']
        
        for table_name in sample_tables:
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                
                if rows:
                    print(f"\n📁 Sample from {table_name}:")
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in cursor.fetchall()]
                    print(f"   Columns: {columns}")
                    
                    for row in rows[:3]:
                        print(f"   {row}")
                    
                    # Count valid paths
                    cursor.execute(f"SELECT * FROM {table_name}")
                    all_rows = cursor.fetchall()
                    
                    # Try to find path column
                    path_col = None
                    for i, col in enumerate(columns):
                        if 'path' in col.lower() or 'file' in col.lower():
                            path_col = i
                            break
                    
                    if path_col is not None:
                        valid_paths = 0
                        invalid_paths = 0
                        sample_paths = []
                        
                        for row in all_rows:
                            file_path = row[path_col]
                            if file_path:
                                p = Path(file_path)
                                if p.exists():
                                    valid_paths += 1
                                    sample_paths.append(file_path)
                                else:
                                    invalid_paths += 1
                        
                        print(f"\n   ✅ Valid paths: {valid_paths}")
                        print(f"   ❌ Invalid paths: {invalid_paths}")
                        
                        if sample_paths:
                            print(f"\n   Sample valid paths:")
                            for sp in sample_paths[:3]:
                                print(f"      {sp}")
                
            except sqlite3.OperationalError:
                pass
        
        conn.close()
        
    except Exception as e:
        print(f"   Error: {e}")

print("\n" + "=" * 80)
print("💡 RECOMMENDATIONS:")
print("=" * 80)
print("\nTo train using admin database:")
print("1. Export database paths to training format")
print("2. Or create direct database reader for training")
print("3. Or use paths shown above directly")
