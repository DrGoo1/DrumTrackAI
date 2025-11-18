"""
Check Database Statistics
Verify what was indexed and show comprehensive stats
"""

import sqlite3
import json

def check_database():
    db_path = "f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("📊 DATABASE STATISTICS")
    print("="*70)
    
    # Total patterns
    cursor.execute("SELECT COUNT(*) FROM drum_patterns")
    total = cursor.fetchone()[0]
    print(f"\n✅ Total Patterns Indexed: {total:,}")
    
    # By tempo
    print("\n⏱️  Tempo Distribution:")
    cursor.execute("""
        SELECT 
            CASE 
                WHEN tempo_bpm < 80 THEN 'Slow (< 80 BPM)'
                WHEN tempo_bpm < 100 THEN 'Medium (80-100 BPM)'
                WHEN tempo_bpm < 120 THEN 'Moderate (100-120 BPM)'
                WHEN tempo_bpm < 140 THEN 'Fast (120-140 BPM)'
                ELSE 'Very Fast (> 140 BPM)'
            END as tempo_range,
            COUNT(*) as count
        FROM drum_patterns
        GROUP BY tempo_range
        ORDER BY MIN(tempo_bpm)
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]:25s}: {row[1]:6,} patterns")
    
    # Tempo stats
    cursor.execute("SELECT MIN(tempo_bpm), MAX(tempo_bpm), AVG(tempo_bpm) FROM drum_patterns")
    min_t, max_t, avg_t = cursor.fetchone()
    print(f"\n  Range: {min_t:.0f} - {max_t:.0f} BPM (avg: {avg_t:.0f})")
    
    # By style
    print("\n🎵 Style Distribution:")
    cursor.execute("""
        SELECT style, COUNT(*) as count
        FROM drum_patterns
        WHERE style IS NOT NULL AND style != 'unknown'
        GROUP BY style
        ORDER BY count DESC
        LIMIT 10
    """)
    for style, count in cursor.fetchall():
        print(f"  {style:15s}: {count:6,} patterns")
    
    # Complexity
    print("\n📊 Complexity Distribution:")
    cursor.execute("""
        SELECT 
            CASE 
                WHEN complexity < 0.2 THEN 'Very Simple'
                WHEN complexity < 0.4 THEN 'Simple'
                WHEN complexity < 0.6 THEN 'Moderate'
                WHEN complexity < 0.8 THEN 'Complex'
                ELSE 'Very Complex'
            END as complexity_level,
            COUNT(*) as count
        FROM drum_patterns
        WHERE complexity IS NOT NULL
        GROUP BY complexity_level
        ORDER BY MIN(complexity)
    """)
    for level, count in cursor.fetchall():
        print(f"  {level:15s}: {count:6,} patterns")
    
    # Drum hit statistics
    print("\n🥁 Average Drum Hits per Pattern:")
    cursor.execute("""
        SELECT 
            AVG(kick_count) as avg_kick,
            AVG(snare_count) as avg_snare,
            AVG(hihat_count) as avg_hihat,
            AVG(ride_count) as avg_ride,
            AVG(tom_count) as avg_tom,
            AVG(crash_count) as avg_crash
        FROM drum_patterns
    """)
    avg_kick, avg_snare, avg_hihat, avg_ride, avg_tom, avg_crash = cursor.fetchone()
    print(f"  Kick:   {avg_kick:.1f}")
    print(f"  Snare:  {avg_snare:.1f}")
    print(f"  Hi-hat: {avg_hihat:.1f}")
    print(f"  Ride:   {avg_ride:.1f}")
    print(f"  Tom:    {avg_tom:.1f}")
    print(f"  Crash:  {avg_crash:.1f}")
    
    # Time signatures
    print("\n🎼 Time Signatures:")
    cursor.execute("""
        SELECT time_signature, COUNT(*) as count
        FROM drum_patterns
        GROUP BY time_signature
        ORDER BY count DESC
        LIMIT 5
    """)
    for sig, count in cursor.fetchall():
        print(f"  {sig:6s}: {count:6,} patterns")
    
    # Database size
    import os
    db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
    print(f"\n💾 Database Size: {db_size:.1f} MB")
    
    # Sample query - find patterns for 156 BPM rock
    print("\n🔍 Example Query: Rock patterns around 156 BPM")
    cursor.execute("""
        SELECT file_path, tempo_bpm, complexity, 
               kick_count, snare_count, hihat_count
        FROM drum_patterns
        WHERE tempo_bpm BETWEEN 150 AND 160
          AND (style LIKE '%rock%' OR style = 'unknown')
        ORDER BY RANDOM()
        LIMIT 5
    """)
    print("  Sample results:")
    for row in cursor.fetchall():
        path, tempo, complexity, kick, snare, hihat = row
        filename = path.split('\\')[-1] if '\\' in path else path.split('/')[-1]
        print(f"    {filename[:40]:40s} {tempo:6.1f} BPM  K:{kick:3d} S:{snare:3d} H:{hihat:3d}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("✅ DATABASE READY FOR AI TRAINING!")
    print("="*70)

if __name__ == "__main__":
    check_database()
