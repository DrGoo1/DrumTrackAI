# Phase 2 Implementation Plan: Bar Layer & Intelligent Labeling

**Target:** Bring system from 40% → 70% complete  
**Timeline:** 2-3 weeks  
**Focus:** Bar structure, meter detection, intelligent section labels

---

## 🎯 **Goals**

1. **Bar-level representation** - Group beats into measures with metadata
2. **Meter detection** - Detect 4/4, 3/4, 6/8 time signatures
3. **Tempo per bar** - Calculate BPM per measure
4. **Intelligent labels** - Actually use energy/spectral for intro/verse/chorus
5. **Improved confidence** - Real confidence scoring, not heuristics

---

## 📋 **Task Breakdown**

### **Week 1: Bar Structure Foundation**

#### **Task 1.1: Add Bar struct to Rust** (2 hours)
**File:** `audio-core/src/lib.rs` or `audio-core/src/bar.rs`

```rust
use serde::Serialize;

#[derive(Serialize, Clone, Debug)]
pub struct Bar {
    /// Bar index (0-based)
    pub index: u32,
    
    /// Start time in seconds
    pub start_time: f32,
    
    /// End time in seconds
    pub end_time: f32,
    
    /// Time signature (numerator, denominator)
    pub meter: (u32, u32),  // e.g., (4, 4) or (3, 4)
    
    /// Tempo for this bar in BPM
    pub tempo_bpm: f32,
    
    /// Beat times within this bar
    pub beat_times: Vec<f32>,
    
    /// Combined confidence (0.0-1.0)
    pub confidence: f32,
}

impl Bar {
    pub fn new(index: u32, beats: &[f32], meter: (u32, u32)) -> Self {
        let start_time = beats[0];
        let end_time = beats[beats.len() - 1];
        let duration = end_time - start_time;
        let beats_per_bar = meter.0 as f32;
        let tempo_bpm = 60.0 * beats_per_bar / duration;
        
        Self {
            index,
            start_time,
            end_time,
            meter,
            tempo_bpm,
            beat_times: beats.to_vec(),
            confidence: 0.85,  // TODO: calculate real confidence
        }
    }
}
```

#### **Task 1.2: Implement meter detection** (4 hours)
**File:** `audio-core/src/meter.rs`

```rust
/// Detect time signature by analyzing accent patterns
pub fn detect_meter(
    beat_times: &[f32],
    beat_energy: &[f32],
    pcm: &[f32],
    sr: u32
) -> Vec<MeterSegment> {
    // For MVP: just detect 4/4 vs 3/4
    
    // 1. Calculate accent strength for each beat
    let accents = beat_energy.iter()
        .map(|&e| e)
        .collect::<Vec<f32>>();
    
    // 2. Test hypothesis: is this 3/4 or 4/4?
    let score_3_4 = test_meter_hypothesis(&accents, 3);
    let score_4_4 = test_meter_hypothesis(&accents, 4);
    
    // 3. Choose best meter
    let meter = if score_3_4 > score_4_4 * 1.1 {
        (3, 4)
    } else {
        (4, 4)  // Default to 4/4
    };
    
    vec![MeterSegment {
        start_beat: 0,
        end_beat: beat_times.len(),
        meter,
        confidence: (score_4_4.max(score_3_4) / (score_4_4 + score_3_4 + 1e-6)),
    }]
}

fn test_meter_hypothesis(accents: &[f32], beats_per_bar: usize) -> f32 {
    // Expected pattern: strong on downbeat
    let mut score = 0.0;
    let n_bars = accents.len() / beats_per_bar;
    
    for bar_idx in 0..n_bars {
        let bar_start = bar_idx * beats_per_bar;
        if bar_start + beats_per_bar > accents.len() {
            break;
        }
        
        let bar_accents = &accents[bar_start..bar_start + beats_per_bar];
        
        // Downbeat should be strongest
        let downbeat_energy = bar_accents[0];
        let avg_other = bar_accents[1..].iter().sum::<f32>() / (beats_per_bar - 1) as f32;
        
        if downbeat_energy > avg_other {
            score += (downbeat_energy - avg_other);
        }
    }
    
    score / n_bars as f32
}

#[derive(Debug, Clone)]
pub struct MeterSegment {
    pub start_beat: usize,
    pub end_beat: usize,
    pub meter: (u32, u32),
    pub confidence: f32,
}
```

#### **Task 1.3: Group beats into bars** (2 hours)
**File:** `audio-core/src/bar.rs`

```rust
pub fn group_beats_into_bars(
    beat_times: &[f32],
    meter_segments: &[MeterSegment]
) -> Vec<Bar> {
    let mut bars = Vec::new();
    
    for meter_seg in meter_segments {
        let beats_per_bar = meter_seg.meter.0 as usize;
        let start_beat = meter_seg.start_beat;
        let end_beat = meter_seg.end_beat;
        
        // Group beats into chunks
        for (bar_idx, chunk) in beat_times[start_beat..end_beat]
            .chunks(beats_per_bar)
            .enumerate()
        {
            if chunk.len() < beats_per_bar {
                // Partial bar at end, skip or handle specially
                continue;
            }
            
            let bar = Bar::new(
                (bars.len()) as u32,
                chunk,
                meter_seg.meter
            );
            bars.push(bar);
        }
    }
    
    bars
}
```

#### **Task 1.4: Update analyze output** (1 hour)
**File:** `audio-core/src/lib.rs`

```rust
#[derive(Serialize)]
pub struct AnalysisResult {
    pub tempo: f32,
    pub beats: Vec<f32>,
    pub onsets: Vec<f32>,
    pub bars: Vec<Bar>,  // ← NEW
    pub meter: (u32, u32),  // ← NEW
}
```

---

### **Week 2: Intelligent Section Labeling**

#### **Task 2.1: Enhance section labeling logic** (3 hours)
**File:** `dcsm_backend.py` - Improve `dcsm_sectionize_enhanced()`

```python
def intelligent_label_sections(sections: List[Dict], metadata: Dict) -> List[Dict]:
    """Apply sophisticated heuristics for section labeling"""
    
    if not sections:
        return sections
    
    # Calculate statistics
    energies = [s['energy'] for s in sections]
    avg_energy = sum(energies) / len(energies)
    max_energy = max(energies)
    
    # Group by similarity (repetition detection)
    groups = group_similar_sections(sections)
    
    # Find the most repeated high-energy group → Chorus
    chorus_group = find_chorus_group(groups, sections, avg_energy)
    
    # Label sections
    for i, section in enumerate(sections):
        position = 'first' if i == 0 else 'last' if i == len(sections)-1 else 'middle'
        energy = section['energy']
        group_id = section.get('repetition_group', -1)
        
        # Rule-based labeling
        if position == 'first' and energy < avg_energy * 0.7:
            section['label'] = 'intro'
            section['confidence'] = 0.80
            
        elif position == 'last' and energy < avg_energy * 0.7:
            section['label'] = 'outro'
            section['confidence'] = 0.75
            
        elif group_id == chorus_group and energy > avg_energy * 1.1:
            section['label'] = 'chorus'
            section['confidence'] = 0.85
            
        elif is_repeated_section(section, sections) and energy <= avg_energy * 1.1:
            section['label'] = 'verse'
            section['confidence'] = 0.75
            
        elif not is_repeated_section(section, sections) and position == 'middle':
            # Unique section in middle → likely bridge
            section['label'] = 'bridge'
            section['confidence'] = 0.70
            
        else:
            # Fallback
            section['label'] = 'section'
            section['confidence'] = 0.50
    
    return sections

def group_similar_sections(sections: List[Dict]) -> Dict[int, List[int]]:
    """Group sections by energy/spectral similarity"""
    groups = {}
    threshold = 0.15
    
    for i, s1 in enumerate(sections):
        group_found = False
        for group_id, indices in groups.items():
            # Compare with first section in group
            s2 = sections[indices[0]]
            dist = abs(s1['energy'] - s2['energy']) + \
                   abs(s1['spectral_centroid'] - s2['spectral_centroid'])
            dist /= 2.0
            
            if dist < threshold:
                indices.append(i)
                group_found = True
                break
        
        if not group_found:
            groups[len(groups)] = [i]
    
    return groups

def find_chorus_group(groups: Dict, sections: List[Dict], avg_energy: float) -> int:
    """Find the group most likely to be chorus"""
    best_group = -1
    best_score = 0.0
    
    for group_id, indices in groups.items():
        if len(indices) < 2:
            continue  # Chorus should repeat
        
        # Average energy of this group
        group_energy = sum(sections[i]['energy'] for i in indices) / len(indices)
        
        # Score: repetition count × energy relative to average
        score = len(indices) * (group_energy / avg_energy)
        
        if score > best_score:
            best_score = score
            best_group = group_id
    
    return best_group

def is_repeated_section(section: Dict, all_sections: List[Dict]) -> bool:
    """Check if this section repeats elsewhere"""
    threshold = 0.15
    similar_count = 0
    
    for other in all_sections:
        if other is section:
            continue
        
        dist = abs(section['energy'] - other['energy']) + \
               abs(section['spectral_centroid'] - other['spectral_centroid'])
        dist /= 2.0
        
        if dist < threshold:
            similar_count += 1
    
    return similar_count >= 1  # Appears at least twice
```

#### **Task 2.2: Add confidence calculation** (2 hours)
**File:** `section_analyzer.py`

```python
def calculate_label_confidence(
    section: Dict,
    all_sections: List[Dict],
    label: str,
    avg_energy: float
) -> float:
    """Calculate confidence score for a section label"""
    
    base_confidence = 0.60
    position_bonus = 0.0
    energy_bonus = 0.0
    repetition_bonus = 0.0
    
    # Position-based confidence
    if label == 'intro' and section['index'] == 0:
        position_bonus = 0.15
    elif label == 'outro' and section['index'] == len(all_sections) - 1:
        position_bonus = 0.15
    
    # Energy-based confidence
    energy_ratio = section['energy'] / avg_energy
    if label == 'chorus' and energy_ratio > 1.2:
        energy_bonus = 0.15
    elif label == 'intro' and energy_ratio < 0.8:
        energy_bonus = 0.10
    
    # Repetition-based confidence
    if label in ['verse', 'chorus']:
        similar_count = count_similar_sections(section, all_sections)
        if similar_count >= 2:
            repetition_bonus = 0.10
    
    return min(0.95, base_confidence + position_bonus + energy_bonus + repetition_bonus)
```

---

### **Week 3: Integration & Testing**

#### **Task 3.1: Wire up bar data in backend** (2 hours)
**File:** `dcsm_backend.py`

```python
async def dcsm_analyze_with_bars(request):
    """Enhanced analysis with bar-level detail"""
    key = request.query.get("key")
    
    # ... path validation ...
    
    # Call Rust with bar analysis
    result = run_audio_core([
        "analyze-full",  # New command
        str(path),
        "--min-bpm", "60",
        "--max-bpm", "200"
    ])
    
    # Result now includes bars
    return web.json_response({
        "tempo": result['tempo'],
        "beats": result['beats'],
        "bars": result['bars'],  # NEW
        "meter": result['meter'],  # NEW
        "sections": enhance_sections_with_bars(
            result.get('sections', []),
            result['bars']
        )
    })

def enhance_sections_with_bars(sections: List[Dict], bars: List[Dict]) -> List[Dict]:
    """Add bar indices to sections"""
    for section in sections:
        start_bar = find_bar_at_time(section['start'], bars)
        end_bar = find_bar_at_time(section['end'], bars)
        section['start_bar_index'] = start_bar
        section['end_bar_index'] = end_bar
        section['bar_count'] = end_bar - start_bar
    return sections
```

#### **Task 3.2: Update frontend types** (1 hour)
**File:** `frontend/src/components/WebDAWApp.tsx`

```typescript
export type Bar = {
  index: number;
  startTime: number;
  endTime: number;
  meter: [number, number];
  tempoBpm: number;
  beatTimes: number[];
  confidence: number;
};

export type Section = {
  // ... existing fields ...
  startBarIndex?: number;  // NEW
  endBarIndex?: number;    // NEW
  barCount?: number;       // NEW
};

export type SongMap = {
  duration: number;
  globalBpmEstimate: number;
  meter: [number, number];
  bars: Bar[];
  sections: Section[];
  beatTimes: number[];
};
```

#### **Task 3.3: Create test suite** (3 hours)
**File:** `test_enhanced_analysis.py`

```python
import subprocess
import json

def test_bar_detection():
    """Test that bars are properly detected"""
    result = subprocess.run(
        ['target/release/audio-core.exe', 'analyze-full', 'test.mp3'],
        capture_output=True,
        text=True
    )
    data = json.loads(result.stdout)
    
    assert 'bars' in data
    assert len(data['bars']) > 0
    assert data['bars'][0]['meter'] in [(4, 4), (3, 4), (6, 8)]
    print(f"✅ Detected {len(data['bars'])} bars")

def test_intelligent_labeling():
    """Test that sections get meaningful labels"""
    # Upload a known song structure
    response = requests.get(
        'http://localhost:8000/dcsm/sectionize_enhanced',
        params={'key': 'test_song.mp3', 'bpm': 0}
    )
    data = response.json()
    
    labels = set(s['label'] for s in data['sections'])
    
    # Should have at least intro and outro
    assert 'intro' in labels or 'verse' in labels
    print(f"✅ Detected labels: {labels}")
    
    # Chorus should have higher energy than verse
    chorus_sections = [s for s in data['sections'] if s['label'] == 'chorus']
    verse_sections = [s for s in data['sections'] if s['label'] == 'verse']
    
    if chorus_sections and verse_sections:
        avg_chorus_energy = sum(s['energy'] for s in chorus_sections) / len(chorus_sections)
        avg_verse_energy = sum(s['energy'] for s in verse_sections) / len(verse_sections)
        assert avg_chorus_energy > avg_verse_energy
        print(f"✅ Chorus energy ({avg_chorus_energy:.2f}) > Verse energy ({avg_verse_energy:.2f})")

if __name__ == '__main__':
    test_bar_detection()
    test_intelligent_labeling()
    print("\n🎉 All tests passed!")
```

---

## 📊 **Success Criteria**

After Phase 2, the system should:

✅ **Bar Detection**
- Detect meter (4/4, 3/4) with >80% accuracy
- Group beats into bars correctly
- Calculate tempo per bar

✅ **Intelligent Labeling**
- Intro detection: 85% accuracy
- Chorus detection: 80% accuracy
- Verse detection: 75% accuracy
- Outro detection: 85% accuracy

✅ **Confidence Scores**
- Meaningful confidence values (not just heuristics)
- High confidence (>0.7) correlates with correct labels

✅ **Integration**
- Backend returns full SongMap
- Frontend displays bar-level detail
- Drum generation uses per-bar tempo

---

## 🎯 **Definition of Done**

- [ ] Rust `Bar` struct implemented and tested
- [ ] Meter detection works for 4/4 and 3/4
- [ ] Beats grouped into bars correctly
- [ ] Tempo calculated per bar
- [ ] Section labeling uses energy/spectral intelligently
- [ ] Confidence scores are meaningful
- [ ] Backend returns bars in JSON
- [ ] Frontend types updated
- [ ] Test suite passes
- [ ] Documentation updated

---

## 🚀 **Getting Started**

```bash
# 1. Create new branch
git checkout -b phase2-bar-layer

# 2. Start with Task 1.1 (Bar struct)
code audio-core/src/bar.rs

# 3. Build and test incrementally
cargo test --release

# 4. Test with real audio
./target/release/audio-core.exe analyze-full test.mp3
```

---

## 📚 **Resources**

**Papers:**
- Ellis, "Beat Tracking by Dynamic Programming" (2007)
- Paulus et al., "State of the Art in Music Structure Analysis" (2010)
- McFee & Ellis, "Better Beat Tracking Through Robust Onset Aggregation" (2014)

**Datasets for Testing:**
- SALAMI annotations (song structure labels)
- Ballroom dataset (known meters/tempos)
- Your own test collection

**Libraries:**
- `realfft` for FFT (already using)
- `ndarray` for matrix operations (if adding SSM)

---

**Timeline:** 2-3 weeks  
**Effort:** ~40-50 hours total  
**Impact:** System goes from 40% → 70% complete  
**Result:** Production-ready bar-level analysis with intelligent labeling! 🎉
