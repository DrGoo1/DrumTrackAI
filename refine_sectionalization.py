"""
Refine and Merge Sections
Takes over-segmented results and intelligently merges them to match expected structure
"""
import json
import numpy as np

def load_results():
    """Load results from previous test"""
    with open('sectionalization_test_results.json', 'r') as f:
        return json.load(f)

def merge_short_sections(sections, min_duration=8.0):
    """Merge sections shorter than min_duration with neighbors"""
    print(f"\n🔧 Merging sections shorter than {min_duration}s...")
    
    merged = []
    i = 0
    while i < len(sections):
        current = sections[i].copy()
        
        # If this section is too short, try to merge with next
        while i + 1 < len(sections) and (current['end'] - current['start']) < min_duration:
            next_sec = sections[i + 1]
            current['end'] = next_sec['end']
            current['duration'] = current['end'] - current['start']
            current['bars'] = int(current['duration'] / (60.0 / 157.0 * 4))  # Using detected tempo
            i += 1
        
        merged.append(current)
        i += 1
    
    print(f"   Reduced from {len(sections)} to {len(merged)} sections")
    return merged

def merge_by_similarity(sections, max_sections=7, tempo=157.0):
    """Iteratively merge most similar adjacent sections"""
    print(f"\n🎯 Target: {max_sections} sections")
    print(f"   Starting with: {len(sections)} sections")
    
    current = sections.copy()
    
    while len(current) > max_sections:
        # Find most similar adjacent pair
        best_idx = 0
        min_diff = float('inf')
        
        for i in range(len(current) - 1):
            # Similarity based on duration
            dur1 = current[i]['end'] - current[i]['start']
            dur2 = current[i+1]['end'] - current[i+1]['start']
            diff = abs(dur1 - dur2)
            
            if diff < min_diff:
                min_diff = diff
                best_idx = i
        
        # Merge the pair
        merged_section = {
            'start': current[best_idx]['start'],
            'end': current[best_idx + 1]['end'],
            'method': current[best_idx].get('method', 'merged')
        }
        merged_section['duration'] = merged_section['end'] - merged_section['start']
        merged_section['bars'] = int(merged_section['duration'] / (60.0 / tempo * 4))
        
        # Replace the two sections with merged one
        current = current[:best_idx] + [merged_section] + current[best_idx+2:]
        
        print(f"   Merged sections {best_idx+1} and {best_idx+2}: {len(current)} remaining")
    
    return current

def label_sections(sections, expected_labels):
    """Assign labels to sections based on position and duration"""
    labeled = []
    for i, sec in enumerate(sections):
        sec_copy = sec.copy()
        if i < len(expected_labels):
            sec_copy['label'] = expected_labels[i]['name']
        else:
            sec_copy['label'] = f"Section {i+1}"
        labeled.append(sec_copy)
    return labeled

def print_sections(sections, title="Sections"):
    """Pretty print sections"""
    print(f"\n{title}:")
    print("   ┌────┬──────────┬──────────┬──────────┬──────┬─────────────┐")
    print("   │ #  │ Start    │ End      │ Duration │ Bars │ Label       │")
    print("   ├────┼──────────┼──────────┼──────────┼──────┼─────────────┤")
    for i, sec in enumerate(sections, 1):
        start = sec['start']
        end = sec['end']
        dur = sec.get('duration', end - start)
        bars = sec.get('bars', '?')
        label = sec.get('label', '')
        print(f"   │ {i:2d} │ {start:6.1f}s  │ {end:6.1f}s │ {dur:6.1f}s  │ {bars:4d} │ {label:11s} │")
    print("   └────┴──────────┴──────────┴──────────┴──────┴─────────────┘")

def main():
    print("="*70)
    print("  SECTION REFINEMENT - Intelligent Merging")
    print("="*70)
    
    # Load results
    results = load_results()
    
    # Use repetition method (best performer)
    sections = results['repetition']
    print(f"\n📊 Starting with REPETITION method: {len(sections)} sections")
    
    # Expected structure
    expected = [
        {"name": "Intro"},
        {"name": "Verse 1"},
        {"name": "Verse 2"},
        {"name": "Refrain"},
        {"name": "Instrumental"},
        {"name": "Verse 3"},
        {"name": "Outro"}
    ]
    
    # Strategy 1: Merge short sections first
    print("\n" + "="*70)
    print("  STRATEGY 1: Merge Short Sections")
    print("="*70)
    
    merged_short = merge_short_sections(sections, min_duration=10.0)
    print_sections(merged_short, "After merging short sections")
    
    # Strategy 2: Merge to target count
    print("\n" + "="*70)
    print("  STRATEGY 2: Merge to Target Count (7 sections)")
    print("="*70)
    
    merged_target = merge_by_similarity(merged_short, max_sections=7, tempo=157.0)
    print_sections(merged_target, "After merging to target")
    
    # Add labels
    labeled = label_sections(merged_target, expected)
    print_sections(labeled, "Final Labeled Sections")
    
    # Evaluate
    print("\n" + "="*70)
    print("  EVALUATION")
    print("="*70)
    
    expected_durations = [10, 15, 15, 10, 15, 15, -1]
    print("\n   Comparison to Sheet Music:")
    for i, sec in enumerate(labeled):
        if i < len(expected_durations) and expected_durations[i] > 0:
            expected = expected_durations[i]
            actual = sec['duration']
            diff = abs(expected - actual)
            match = "✅" if diff < 5 else "⚠️ "
            print(f"   {match} {sec['label']:15s}: Expected ~{expected:2d}s, Got {actual:5.1f}s (Δ{diff:4.1f}s)")
    
    # Save refined results
    output = {
        "method": "repetition_refined",
        "sections": labeled,
        "summary": {
            "total_sections": len(labeled),
            "method": "repetition + intelligent merging",
            "parameters": {
                "min_duration": 10.0,
                "target_sections": 7
            }
        }
    }
    
    with open('sectionalization_refined.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n💾 Refined results saved to: sectionalization_refined.json")
    
    print("\n" + "="*70)
    print("  RECOMMENDATION FOR MAIN APP")
    print("="*70)
    print("""
1. Use REPETITION-based method (MFCC + recurrence matrix)
2. Apply minimum duration filter (10 seconds)
3. Merge similar adjacent sections
4. Target 6-8 sections for typical songs
5. Use detected tempo for bar calculations

Implementation:
- Update DCSM sectionization to use these parameters
- Add post-processing merging step
- Test with multiple files to validate
""")

if __name__ == "__main__":
    main()
