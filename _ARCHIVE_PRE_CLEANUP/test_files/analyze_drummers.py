"""
Analyze Drummer Data in Database
Shows what drummers we have and suggests additions
"""

import sqlite3
from collections import Counter

def analyze_drummers():
    conn = sqlite3.connect('f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db')
    cursor = conn.cursor()
    
    print("="*70)
    print("🥁 CURRENT DRUMMER ANALYSIS")
    print("="*70)
    
    # Check if we have an artist column
    cursor.execute("PRAGMA table_info(drum_patterns)")
    columns = [row[1] for row in cursor.fetchall()]
    
    print(f"\nDatabase columns: {', '.join(columns)}")
    
    # Check for style distribution
    print("\n📊 PATTERN DISTRIBUTION BY STYLE:")
    print("-"*70)
    cursor.execute("""
        SELECT style, COUNT(*) as count
        FROM drum_patterns
        WHERE style IS NOT NULL AND style != ''
        GROUP BY style
        ORDER BY count DESC
        LIMIT 20
    """)
    
    for row in cursor.fetchall():
        style, count = row
        pct = (count / 91074) * 100
        bar = '█' * int(pct / 2)
        print(f"  {style:15s} {count:6,d} ({pct:5.2f}%) {bar}")
    
    # Check file paths for drummer hints
    print("\n📂 CHECKING FILE PATHS FOR DRUMMER NAMES:")
    print("-"*70)
    cursor.execute("""
        SELECT file_path
        FROM drum_patterns
        LIMIT 100
    """)
    
    # Extract potential drummer names from file paths
    drummer_hints = []
    for row in cursor.fetchall():
        path = row[0].lower()
        # Common drummer name patterns
        if 'porcaro' in path:
            drummer_hints.append('Jeff Porcaro')
        elif 'gadd' in path:
            drummer_hints.append('Steve Gadd')
        elif 'purdie' in path:
            drummer_hints.append('Bernard Purdie')
        elif 'copeland' in path:
            drummer_hints.append('Stewart Copeland')
        elif 'bonham' in path:
            drummer_hints.append('John Bonham')
        elif 'collins' in path:
            drummer_hints.append('Phil Collins')
        elif 'peart' in path:
            drummer_hints.append('Neil Peart')
    
    if drummer_hints:
        counter = Counter(drummer_hints)
        print("  Found in file paths:")
        for name, count in counter.most_common():
            print(f"    • {name}: {count} files")
    else:
        print("  No specific drummer names found in file paths")
    
    conn.close()
    
    print("\n" + "="*70)
    print("🎯 CURRENT HARDCODED PROFILES")
    print("="*70)
    
    current_profiles = [
        {'name': 'Jeff Porcaro', 'style': 'Jazz, Rock, Funk', 'era': '1970s-1990s'},
        {'name': 'Steve Gadd', 'style': 'Jazz, Fusion', 'era': '1970s-present'},
        {'name': 'Bernard Purdie', 'style': 'Funk, R&B', 'era': '1960s-present'}
    ]
    
    for profile in current_profiles:
        print(f"\n  ✓ {profile['name']}")
        print(f"     Style: {profile['style']}")
        print(f"     Era: {profile['era']}")
    
    print("\n" + "="*70)
    print("🎯 SUGGESTED ADDITIONS FOR COMPREHENSIVE COVERAGE")
    print("="*70)
    
    suggested = [
        {
            'name': 'John Bonham',
            'style': 'Hard Rock, Heavy Metal',
            'era': '1960s-1980',
            'signature': ['When the Levee Breaks', 'Kashmir', 'Moby Dick'],
            'characteristics': ['Power', 'Triplets', 'Foot technique', 'Heavy grooves'],
            'priority': 'HIGH'
        },
        {
            'name': 'Stewart Copeland',
            'style': 'Rock, Reggae, New Wave',
            'era': '1970s-present',
            'signature': ['Roxanne', 'Message in a Bottle', 'Every Breath You Take'],
            'characteristics': ['Hi-hat mastery', 'Reggae influence', 'Linear patterns'],
            'priority': 'HIGH'
        },
        {
            'name': 'Vinnie Colaiuta',
            'style': 'Fusion, Jazz, Rock',
            'era': '1970s-present',
            'signature': ['Pick Up the Pieces', 'Sting songs', 'Frank Zappa'],
            'characteristics': ['Technical mastery', 'Odd time', 'Fusion chops'],
            'priority': 'HIGH'
        },
        {
            'name': 'Tony Williams',
            'style': 'Jazz, Fusion',
            'era': '1960s-1997',
            'signature': ['Miles Davis Quintet', 'Emergency!', 'Lifetime'],
            'characteristics': ['Ride cymbal', 'Polyrhythms', 'Free time'],
            'priority': 'MEDIUM'
        },
        {
            'name': 'Dennis Chambers',
            'style': 'Funk, Fusion',
            'era': '1970s-present',
            'signature': ['Parliament/Funkadelic', 'Santana', 'John Scofield'],
            'characteristics': ['Funk grooves', 'Speed', 'Precision'],
            'priority': 'MEDIUM'
        },
        {
            'name': 'Neil Peart',
            'style': 'Progressive Rock',
            'era': '1974-2020',
            'signature': ['Tom Sawyer', 'YYZ', '2112'],
            'characteristics': ['Complex patterns', 'Large kit', 'Odd meters'],
            'priority': 'MEDIUM'
        },
        {
            'name': 'Phil Collins',
            'style': 'Pop, Rock',
            'era': '1970s-present',
            'signature': ['In the Air Tonight', 'Genesis', 'Solo work'],
            'characteristics': ['Gated reverb', 'Fill mastery', 'Pop grooves'],
            'priority': 'HIGH'
        },
        {
            'name': 'Clyde Stubblefield',
            'style': 'Funk, Soul',
            'era': '1960s-2017',
            'signature': ['Funky Drummer', 'James Brown', 'Cold Sweat'],
            'characteristics': ['Funky Drummer break', 'Syncopation', 'Hip-hop foundation'],
            'priority': 'HIGH'
        },
        {
            'name': 'Jabo Starks',
            'style': 'Funk, Soul',
            'era': '1960s-2018',
            'signature': ['James Brown', 'Sex Machine', 'Get Up Offa That Thing'],
            'characteristics': ['Tight grooves', 'Pocket', 'Minimal'],
            'priority': 'MEDIUM'
        },
        {
            'name': 'Elvin Jones',
            'style': 'Jazz',
            'era': '1950s-2004',
            'signature': ['John Coltrane Quartet', 'A Love Supreme'],
            'characteristics': ['Polyrhythmic', 'Independence', 'Intensity'],
            'priority': 'MEDIUM'
        }
    ]
    
    for drummer in suggested:
        priority_symbol = '🔥' if drummer['priority'] == 'HIGH' else '⭐'
        print(f"\n{priority_symbol} {drummer['name']} ({drummer['priority']} PRIORITY)")
        print(f"   Style: {drummer['style']}")
        print(f"   Era: {drummer['era']}")
        print(f"   Signature Songs:")
        for song in drummer['signature']:
            print(f"     • {song}")
        print(f"   Characteristics: {', '.join(drummer['characteristics'])}")
    
    print("\n" + "="*70)
    print("📋 RECOMMENDED YOUTUBE DOWNLOAD STRATEGY")
    print("="*70)
    
    print("""
PHASE 1: HIGH PRIORITY (Expand Core Styles)
  🔥 John Bonham - Rock power
  🔥 Stewart Copeland - Reggae/Rock fusion  
  🔥 Phil Collins - Pop/Gated reverb
  🔥 Clyde Stubblefield - Funk foundation
  🔥 Vinnie Colaiuta - Fusion mastery

PHASE 2: MEDIUM PRIORITY (Genre Specialists)
  ⭐ Neil Peart - Progressive/Odd time
  ⭐ Dennis Chambers - Funk/Speed
  ⭐ Tony Williams - Jazz innovation
  ⭐ Jabo Starks - Minimal funk
  ⭐ Elvin Jones - Jazz poly-rhythms

DOWNLOAD PROCESS (per drummer):
  1. Open Admin Module → Drummers Tab
  2. Add New Drummer (name, style, bio)
  3. Add 3-5 Signature Songs:
     - Click "Add Song"
     - Paste YouTube URL
     - Set Quality (best/high)
     - Download & Process
  4. Extract Drums with MVSep:
     - Process each song
     - Isolate drum stems
     - Auto-analyze patterns
  5. Train AI on New Patterns:
     - Patterns auto-added to database
     - Re-run training with new data
     - Model learns drummer characteristics
""")
    
    print("\n" + "="*70)
    print("🎯 IMMEDIATE ACTION ITEMS")
    print("="*70)
    
    print("""
1. OPEN ADMIN MODULE:
   cd f:\\DrumTracKAI_v1.1.11\\admin
   python admin_window.py

2. ADD HIGH PRIORITY DRUMMERS:
   - John Bonham → When the Levee Breaks, Kashmir
   - Stewart Copeland → Roxanne, Message in a Bottle
   - Phil Collins → In the Air Tonight, Sussudio
   - Clyde Stubblefield → Funky Drummer
   - Vinnie Colaiuta → Pick Up the Pieces

3. DOWNLOAD & PROCESS:
   - Use YouTube downloader (built-in)
   - MVSep for drum isolation
   - Auto-scan for patterns

4. UPDATE AI PROFILES:
   - Add new profiles to backend_ai_endpoints.py
   - Update _apply_drummer_profile() method
   - Re-test generation

5. OPTIONAL: RETRAIN MODEL
   - If significant new patterns added (>10K)
   - Run prepare_training_data.py again
   - Re-train GrooVAE on expanded dataset
""")

if __name__ == "__main__":
    analyze_drummers()
