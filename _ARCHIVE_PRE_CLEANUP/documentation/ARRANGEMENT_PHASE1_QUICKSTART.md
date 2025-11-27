# Phase 1: Intelligent Section Labeling - Quick Start Guide

**Goal:** Add intelligent intro/verse/chorus/bridge/outro labeling to sections  
**Timeline:** Days 1-7  
**Difficulty:** Medium

---

## 🎯 **DAY 1-2: Backend Foundation**

### Step 1: Create Enhanced Section Analysis Module

**File:** `section_analyzer.py`

```python
"""
Intelligent musical section analysis
Detects intro, verse, chorus, bridge, outro with confidence scores
"""
import numpy as np
from pathlib import Path
import soundfile as sf
from typing import List, Dict, Tuple

class SectionAnalyzer:
    """Analyzes sections and assigns intelligent labels"""
    
    def __init__(self, audio_path: str, bpm: float):
        self.audio_path = Path(audio_path)
        self.bpm = bpm
        self.audio, self.sr = sf.read(str(audio_path))
        if len(self.audio.shape) > 1:
            self.audio = np.mean(self.audio, axis=1)  # Convert to mono
    
    def calculate_section_energy(self, start_sec: float, end_sec: float) -> float:
        """Calculate RMS energy for a section"""
        start_sample = int(start_sec * self.sr)
        end_sample = int(end_sec * self.sr)
        section_audio = self.audio[start_sample:end_sample]
        
        if len(section_audio) == 0:
            return 0.0
        
        rms = np.sqrt(np.mean(section_audio ** 2))
        return float(rms)
    
    def calculate_spectral_centroid(self, start_sec: float, end_sec: float) -> float:
        """Calculate spectral centroid (brightness) for a section"""
        start_sample = int(start_sec * self.sr)
        end_sample = int(end_sec * self.sr)
        section_audio = self.audio[start_sample:end_sample]
        
        if len(section_audio) < 2048:
            return 0.0
        
        # Simple FFT-based centroid
        spectrum = np.abs(np.fft.rfft(section_audio))
        freqs = np.fft.rfftfreq(len(section_audio), 1/self.sr)
        centroid = np.sum(freqs * spectrum) / (np.sum(spectrum) + 1e-6)
        
        # Normalize to 0-1
        return float(centroid / (self.sr / 2))
    
    def analyze_sections(self, raw_sections: List[Dict]) -> List[Dict]:
        """Analyze sections and add energy/centroid data"""
        analyzed = []
        for section in raw_sections:
            analyzed.append({
                **section,
                'energy': self.calculate_section_energy(section['start'], section['end']),
                'spectral_centroid': self.calculate_spectral_centroid(section['start'], section['end'])
            })
        return analyzed
    
    def group_similar_sections(self, sections: List[Dict], threshold: float = 0.15) -> List[int]:
        """Group sections by similarity (energy + spectral features)"""
        n = len(sections)
        groups = [-1] * n
        next_group = 0
        
        for i in range(n):
            if groups[i] != -1:
                continue
            
            # Start new group
            groups[i] = next_group
            
            # Find similar sections
            for j in range(i+1, n):
                if groups[j] != -1:
                    continue
                
                energy_diff = abs(sections[i]['energy'] - sections[j]['energy'])
                centroid_diff = abs(sections[i]['spectral_centroid'] - sections[j]['spectral_centroid'])
                
                distance = (energy_diff + centroid_diff) / 2
                
                if distance < threshold:
                    groups[j] = next_group
            
            next_group += 1
        
        return groups
    
    def label_sections(self, sections: List[Dict]) -> List[Dict]:
        """Apply intelligent labels to sections"""
        if len(sections) == 0:
            return sections
        
        # Get similarity groups
        groups = self.group_similar_sections(sections)
        
        # Calculate group statistics
        group_counts = {}
        group_energies = {}
        for i, group in enumerate(groups):
            group_counts[group] = group_counts.get(group, 0) + 1
            if group not in group_energies:
                group_energies[group] = []
            group_energies[group].append(sections[i]['energy'])
        
        # Find most repeated group (likely verse or chorus)
        most_repeated_group = max(group_counts.items(), key=lambda x: x[1])[0]
        avg_energy_repeated = np.mean(group_energies[most_repeated_group])
        
        # Overall average energy
        all_energies = [s['energy'] for s in sections]
        avg_energy = np.mean(all_energies)
        max_energy = max(all_energies)
        
        # Label each section
        labeled = []
        for i, section in enumerate(sections):
            label = "unknown"
            confidence = 0.5
            
            # Position-based rules
            if i == 0:
                # First section is likely intro
                label = "intro"
                confidence = 0.75
                
            elif i == len(sections) - 1:
                # Last section is likely outro
                label = "outro"
                confidence = 0.75
                
            elif groups[i] == most_repeated_group:
                # Most repeated group: check energy to distinguish verse/chorus
                if section['energy'] > avg_energy * 1.15:
                    label = "chorus"
                    confidence = 0.8
                else:
                    label = "verse"
                    confidence = 0.75
                    
            elif group_counts[groups[i]] == 1:
                # Unique section in middle: likely bridge
                if 0.3 < (i / len(sections)) < 0.7:
                    label = "bridge"
                    confidence = 0.65
                else:
                    label = "break"
                    confidence = 0.6
                    
            else:
                # Multiple occurrences but not most repeated
                # Could be pre-chorus or second verse
                label = "verse"
                confidence = 0.5
            
            labeled.append({
                **section,
                'label': label,
                'confidence': confidence,
                'repetition_group': groups[i]
            })
        
        return labeled

# Helper function for backend integration
def analyze_and_label_sections(audio_path: str, bpm: float, raw_sections: List[Dict]) -> List[Dict]:
    """Main entry point for section analysis"""
    analyzer = SectionAnalyzer(audio_path, bpm)
    
    # Add energy and spectral features
    analyzed_sections = analyzer.analyze_sections(raw_sections)
    
    # Apply intelligent labels
    labeled_sections = analyzer.label_sections(analyzed_sections)
    
    return labeled_sections
```

### Step 2: Integrate with Backend

**File:** `dcsm_backend.py` (add new endpoint)

```python
# Add this import at the top
from section_analyzer import analyze_and_label_sections

# Add this new endpoint (around line 1073)
async def dcsm_sectionize_enhanced(request):
    """Enhanced sectionization with intelligent labeling"""
    key = request.query.get("key")
    bpm_str = request.query.get("bpm", "0")
    mode = request.query.get("mode", "smart")
    min_bars = int(request.query.get("min_bars", "4"))
    max_bars = int(request.query.get("max_bars", "16"))
    
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    # Auto-detect tempo if not provided
    bpm = float(bpm_str)
    if bpm == 0:
        try:
            tempo_result = run_audio_core(["analyze", str(path), "--min-bpm", "60", "--max-bpm", "200"])
            bpm = tempo_result.get("tempo", 120.0)
            LOG.info(f"Auto-detected tempo: {bpm} BPM")
        except Exception as e:
            LOG.warning(f"Tempo detection failed: {e}, using default 120 BPM")
            bpm = 120.0
    
    # Get raw sections from Rust
    try:
        result = run_audio_core([
            "sectionize-smart", str(path),
            "--bpm", str(bpm),
            "--min-bars", str(min_bars),
            "--max-bars", str(max_bars)
        ])
        raw_sections = result.get("sections", [])
    except Exception as e:
        LOG.error(f"Rust sectionize failed: {e}")
        return web.json_response({"error": str(e)}, status=500)
    
    # Enhance with intelligent labeling
    try:
        enhanced_sections = analyze_and_label_sections(
            str(path),
            bpm,
            raw_sections
        )
        
        # Calculate song structure
        structure = "-".join([s['label'][0].upper() for s in enhanced_sections])
        avg_confidence = np.mean([s['confidence'] for s in enhanced_sections])
        
        return web.json_response({
            "sections": enhanced_sections,
            "metadata": {
                "detected_bpm": bpm,
                "song_structure": structure,
                "avg_confidence": float(avg_confidence),
                "total_sections": len(enhanced_sections)
            }
        })
    except Exception as e:
        LOG.error(f"Section enhancement failed: {e}")
        # Return raw sections as fallback
        return web.json_response({
            "sections": raw_sections,
            "metadata": {
                "detected_bpm": bpm,
                "enhancement_failed": True
            }
        })

# Add route (around line 668)
web.get("/dcsm/sectionize_enhanced", dcsm_sectionize_enhanced),
```

---

## 🎨 **DAY 3-4: Frontend Integration**

### Step 3: Update Types

**File:** `frontend/src/components/WebDAWApp.tsx`

```typescript
// Update Section type (around line 20)
export type Section = {
  id: string;
  start: number;
  end: number;
  density: number;
  fillIn: boolean;
  fillOut: boolean;
  label?: "intro" | "verse" | "chorus" | "bridge" | "outro" | "break" | "solo" | "unknown";
  confidence?: number;
  tempoLocked?: boolean;
  energy?: number;
  repetition_group?: number;
};
```

### Step 4: Update Auto-Sectionize Function

**File:** `frontend/src/components/WebDAWApp.tsx` (around line 360)

```typescript
async function handleAutoSectionize(trackKey: string) {
  setBusy(true);
  try {
    // Use enhanced endpoint with auto-tempo detection
    const response = await fetch(
      `/dcsm/sectionize_enhanced?key=${encodeURIComponent(trackKey)}&bpm=0&mode=smart&min_bars=4&max_bars=16`
    );
    
    if (!response.ok) {
      throw new Error(`Sectionization failed: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    // Display detected structure
    if (result.metadata) {
      console.log(`✨ Detected song structure: ${result.metadata.song_structure}`);
      console.log(`📊 Average confidence: ${(result.metadata.avg_confidence * 100).toFixed(1)}%`);
      console.log(`🎵 Detected tempo: ${result.metadata.detected_bpm} BPM`);
      
      // Update BPM if auto-detected
      if (result.metadata.detected_bpm) {
        setBpm(Math.round(result.metadata.detected_bpm));
      }
    }
    
    // Convert to UI sections
    const detectedSections: Section[] = result.sections.map((s: any, i: number) => ({
      id: `auto-section-${Date.now()}-${i}`,
      start: s.start,
      end: s.end,
      label: s.label || "unknown",
      confidence: s.confidence || 0.5,
      energy: s.energy || 0.5,
      repetition_group: s.repetition_group,
      density: 0.5 + (s.energy || 0.5) * 0.5,  // Map energy to drum density
      fillIn: false,
      fillOut: false,
      tempoLocked: false,
    }));
    
    setSections(detectedSections);
    setErr(null);
    
    // Show success message
    const avgConf = result.metadata?.avg_confidence || 0.5;
    if (avgConf > 0.7) {
      console.log("✅ High confidence detection!");
    } else if (avgConf > 0.5) {
      console.log("⚠️ Medium confidence - review recommended");
    } else {
      console.log("⚠️ Low confidence - manual adjustment may be needed");
    }
    
  } catch (e: any) {
    console.error("Section detection error:", e);
    setErr(`Section detection failed: ${e.message}`);
  } finally {
    setBusy(false);
  }
}
```

### Step 5: Add Visual Styling

**File:** `frontend/src/components/SectionControls.tsx` or create new component

```typescript
// Section color mapping
const SECTION_COLORS: Record<string, string> = {
  intro: "#3b82f6",    // Blue
  verse: "#10b981",    // Green
  chorus: "#f59e0b",   // Orange/Gold
  bridge: "#8b5cf6",   // Purple
  outro: "#6366f1",    // Indigo
  break: "#64748b",    // Gray
  solo: "#ef4444",     // Red
  unknown: "#94a3b8",  // Light gray
};

const SECTION_LABELS: Record<string, string> = {
  intro: "🎬 Intro",
  verse: "📝 Verse",
  chorus: "🎵 Chorus",
  bridge: "🌉 Bridge",
  outro: "🎬 Outro",
  break: "⏸️ Break",
  solo: "🎸 Solo",
  unknown: "❓ Unknown",
};

// Add this to section rendering
function SectionCard({ section }: { section: Section }) {
  const backgroundColor = SECTION_COLORS[section.label || "unknown"];
  const labelText = SECTION_LABELS[section.label || "unknown"];
  const confidence = section.confidence || 0.5;
  const confidenceColor = 
    confidence > 0.7 ? "bg-green-500" : 
    confidence > 0.5 ? "bg-yellow-500" : 
    "bg-red-500";
  
  return (
    <div 
      className="p-3 rounded-lg mb-2"
      style={{ backgroundColor, color: "white" }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-semibold">{labelText}</span>
          {section.repetition_group !== undefined && (
            <span className="text-xs opacity-75">
              #{section.repetition_group + 1}
            </span>
          )}
        </div>
        <div 
          className={`w-3 h-3 rounded-full ${confidenceColor}`}
          title={`Confidence: ${(confidence * 100).toFixed(0)}%`}
        />
      </div>
      <div className="text-xs opacity-90 mt-1">
        {section.start.toFixed(1)}s - {section.end.toFixed(1)}s
        {section.energy && (
          <span className="ml-2">
            Energy: {(section.energy * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  );
}
```

---

## ✅ **DAY 5-7: Testing & Refinement**

### Test Cases

**Create:** `test_enhanced_sectionization.py`

```python
import requests
import json

BASE_URL = "http://localhost:8000"

def test_enhanced_sectionization():
    """Test enhanced sectionization with various songs"""
    
    # Test files (you'll need to upload these first)
    test_files = [
        "test_pop_song.mp3",      # Standard verse-chorus structure
        "test_rock_song.mp3",     # Intro-verse-chorus-bridge-chorus-outro
        "test_edm_song.mp3",      # Buildup-drop-breakdown-drop
        "test_jazz_song.mp3",     # Non-standard structure
    ]
    
    for file_key in test_files:
        print(f"\n{'='*60}")
        print(f"Testing: {file_key}")
        print('='*60)
        
        response = requests.get(
            f"{BASE_URL}/dcsm/sectionize_enhanced",
            params={"key": file_key, "bpm": 0}  # Auto-detect tempo
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ Success!")
            print(f"📊 Structure: {result['metadata']['song_structure']}")
            print(f"🎵 BPM: {result['metadata']['detected_bpm']}")
            print(f"📈 Confidence: {result['metadata']['avg_confidence']:.2%}")
            print(f"\nSections:")
            
            for i, section in enumerate(result['sections'], 1):
                label = section['label'].upper()
                start = section['start']
                end = section['end']
                conf = section['confidence']
                energy = section.get('energy', 0)
                
                print(f"  {i}. {label:10s} {start:6.1f}s - {end:6.1f}s  "
                      f"Conf: {conf:.2%}  Energy: {energy:.2f}")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    test_enhanced_sectionization()
```

### Manual Verification Checklist

- [ ] **Upload test songs with known structures**
- [ ] **Verify labels match expected structure**
- [ ] **Check confidence scores are reasonable**
- [ ] **Test with different genres (pop, rock, jazz, EDM)**
- [ ] **Test with non-standard songs (no clear structure)**
- [ ] **Verify fallback behavior when analysis fails**
- [ ] **Check UI displays colors correctly**
- [ ] **Verify timeline shows sections properly**

---

## 🚀 **DEPLOYMENT**

### Production Checklist

- [ ] All tests passing
- [ ] Error handling robust
- [ ] Logging comprehensive
- [ ] Performance acceptable (< 3 sec for 3-min song)
- [ ] UI polished and intuitive
- [ ] Documentation updated
- [ ] User feedback collected

### Rollout Strategy

1. **Internal Testing** (Day 1-2)
2. **Beta Users** (Day 3-4)
3. **Production Release** (Day 5)
4. **Monitor & Iterate** (Ongoing)

---

## 📊 **SUCCESS CRITERIA**

**Must Have:**
- ✅ Sections automatically labeled with > 70% accuracy
- ✅ Confidence scores displayed
- ✅ Works with common song structures
- ✅ Graceful fallback on failure

**Nice to Have:**
- ⭐ Auto-detect tempo
- ⭐ Repetition group indicators
- ⭐ Energy visualization
- ⭐ One-click structure correction

---

**Ready to start? Begin with Step 1: Create `section_analyzer.py`!**
