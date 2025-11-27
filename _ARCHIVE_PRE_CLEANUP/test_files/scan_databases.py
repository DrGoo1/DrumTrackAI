"""
Database Scanner - Recursively finds all training data
Scans all subfolders for E-GMD, Loops, and other training content
"""

from pathlib import Path
import sys

print("=" * 80)
print("🔍 DrumTracKAI Database Scanner")
print("=" * 80)
print("\nScanning all drives and subfolders for training data...\n")

# Define potential paths to check
SEARCH_PATHS = {
    'E-GMD': [
        Path("E:/"),
        Path("F:/"),
        Path("C:/"),
        Path("D:/"),
    ],
    'Loops': [
        Path("E:/"),
        Path("F:/"),
        Path("C:/"),
        Path("D:/"),
    ]
}

def scan_for_midi(root_path, max_depth=5):
    """Recursively scan for MIDI files"""
    found_dirs = {}
    
    try:
        # Search recursively for .mid and .midi files
        for midi_file in root_path.rglob('*.mid'):
            parent_dir = midi_file.parent
            if parent_dir not in found_dirs:
                found_dirs[parent_dir] = []
            found_dirs[parent_dir].append(midi_file)
        
        for midi_file in root_path.rglob('*.midi'):
            parent_dir = midi_file.parent
            if parent_dir not in found_dirs:
                found_dirs[parent_dir] = []
            found_dirs[parent_dir].append(midi_file)
    except PermissionError:
        pass
    except Exception as e:
        pass
    
    return found_dirs

def scan_for_loops(root_path):
    """Recursively scan for audio loop files"""
    found_dirs = {}
    
    try:
        # Search recursively for audio files
        for ext in ['*.wav', '*.aif', '*.aiff', '*.mp3', '*.flac']:
            for audio_file in root_path.rglob(ext):
                parent_dir = audio_file.parent
                if parent_dir not in found_dirs:
                    found_dirs[parent_dir] = []
                found_dirs[parent_dir].append(audio_file)
    except PermissionError:
        pass
    except Exception as e:
        pass
    
    return found_dirs

# Scan for E-GMD
print("1️⃣ Scanning for E-GMD MIDI files...")
print("-" * 80)

all_midi_dirs = {}
for search_path in SEARCH_PATHS['E-GMD']:
    if search_path.exists():
        print(f"   Scanning: {search_path}")
        found = scan_for_midi(search_path)
        all_midi_dirs.update(found)

if all_midi_dirs:
    print(f"\n✅ Found MIDI files in {len(all_midi_dirs)} directories:\n")
    
    # Sort by file count
    sorted_dirs = sorted(all_midi_dirs.items(), key=lambda x: len(x[1]), reverse=True)
    
    for dir_path, files in sorted_dirs[:10]:  # Show top 10
        print(f"   📁 {dir_path}")
        print(f"      Files: {len(files)}")
        
        # Check if this looks like E-GMD
        dir_name_lower = str(dir_path).lower()
        if 'gmd' in dir_name_lower or 'groove' in dir_name_lower or 'midi' in dir_name_lower:
            print(f"      ⭐ LIKELY E-GMD DATASET")
        print()
    
    if len(sorted_dirs) > 10:
        print(f"   ... and {len(sorted_dirs) - 10} more directories")
else:
    print("   ❌ No MIDI files found")

# Scan for Loops
print("\n\n2️⃣ Scanning for Audio Loop files...")
print("-" * 80)

all_loop_dirs = {}
for search_path in SEARCH_PATHS['Loops']:
    if search_path.exists():
        print(f"   Scanning: {search_path}")
        found = scan_for_loops(search_path)
        all_loop_dirs.update(found)

if all_loop_dirs:
    print(f"\n✅ Found audio files in {len(all_loop_dirs)} directories:\n")
    
    # Sort by file count
    sorted_dirs = sorted(all_loop_dirs.items(), key=lambda x: len(x[1]), reverse=True)
    
    for dir_path, files in sorted_dirs[:10]:  # Show top 10
        print(f"   📁 {dir_path}")
        print(f"      Files: {len(files)}")
        
        # Check if this looks like loops/drums
        dir_name_lower = str(dir_path).lower()
        if any(keyword in dir_name_lower for keyword in ['loop', 'drum', 'percussion', 'sample']):
            print(f"      ⭐ LIKELY DRUM LOOP LIBRARY")
        print()
    
    if len(sorted_dirs) > 10:
        print(f"   ... and {len(sorted_dirs) - 10} more directories")
else:
    print("   ❌ No audio files found")

# Summary and recommendations
print("\n\n" + "=" * 80)
print("📊 SCAN SUMMARY")
print("=" * 80)

total_midi = sum(len(files) for files in all_midi_dirs.values())
total_audio = sum(len(files) for files in all_loop_dirs.values())

print(f"\n🎵 MIDI Files: {total_midi}")
print(f"🔊 Audio Files: {total_audio}")

print("\n💡 RECOMMENDED PATHS FOR TRAINING:")
print("-" * 80)

if all_midi_dirs:
    # Find best E-GMD candidate
    midi_sorted = sorted(all_midi_dirs.items(), key=lambda x: len(x[1]), reverse=True)
    best_midi_dir = midi_sorted[0][0]
    print(f"\nE-GMD path:")
    print(f"   {best_midi_dir}")
    print(f"   ({len(midi_sorted[0][1])} MIDI files)")

if all_loop_dirs:
    # Find best loop library candidate
    loop_sorted = sorted(all_loop_dirs.items(), key=lambda x: len(x[1]), reverse=True)
    best_loop_dir = loop_sorted[0][0]
    print(f"\nLoops path:")
    print(f"   {best_loop_dir}")
    print(f"   ({len(loop_sorted[0][1])} audio files)")

print("\n✅ Rudiments: Built-in (always available)")

# Save results to file
output_file = Path("database_scan_results.txt")
with open(output_file, 'w') as f:
    f.write("Database Scan Results\n")
    f.write("=" * 80 + "\n\n")
    
    f.write("E-GMD MIDI Files:\n")
    for dir_path, files in sorted(all_midi_dirs.items(), key=lambda x: len(x[1]), reverse=True):
        f.write(f"{dir_path}: {len(files)} files\n")
    
    f.write("\n\nAudio Loop Files:\n")
    for dir_path, files in sorted(all_loop_dirs.items(), key=lambda x: len(x[1]), reverse=True):
        f.write(f"{dir_path}: {len(files)} files\n")
    
    if all_midi_dirs:
        f.write(f"\n\nRecommended E-GMD path:\n{best_midi_dir}\n")
    if all_loop_dirs:
        f.write(f"\nRecommended Loops path:\n{best_loop_dir}\n")

print(f"\n💾 Results saved to: {output_file}")

print("\n" + "=" * 80)
print("🚀 Next Steps:")
print("=" * 80)
print("\n1. Review the recommended paths above")
print("2. Run bootstrap_training.py")
print("3. Enter the recommended paths when prompted")
print("\nOR:")
print("4. Run: python auto_train.py (will use paths automatically)")

print("\n" + "=" * 80)
