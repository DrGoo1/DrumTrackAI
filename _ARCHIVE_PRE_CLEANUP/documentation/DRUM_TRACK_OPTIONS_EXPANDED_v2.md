# 🥁 **DrumTracKAI - EXPANDED Drum Track Creation Options v2.0**

**Complete list of ALL drum track parameters - Current + Planned**

---

## ✅ **CURRENT OPTIONS (Already Built)**

### **Basic Parameters:**
- **BPM** (40-240): Tempo in beats per minute
- **Density** (0.0-1.0): Overall pattern complexity/busyness
- **Swing** (0.0-1.0): Timing offset for off-beats
- **Humanize** (0.0-1.0): Random timing variations for human feel
- **Seed** (integer): Random seed for pattern consistency

### **Style Options:**
- rock, funk, edm, hiphop, jazz, pop

### **Section Labels:**
- intro, verse, chorus, bridge, outro

### **Groove Presets:**
- **Swing Preset:** off, light (10%), heavy (25%)
- **Velocity Profile:** flat, accent24, funk16
- **Fill Preset:** none, random, tomrun, snarebuzz, edmriser

### **Section Flags:**
- **fill_in**: Add fill at start of section
- **fill_out**: Add fill at end of section

---

## 🆕 **NEW OPTIONS TO ADD (From User Request)**

### **1. CYMBAL VS DRUM VELOCITY** ⭐

**Purpose:** Independent volume control for cymbals vs drums

```javascript
{
  "drum_velocity": 0.85,      // 0.0-1.0 - Overall drum volume (kick, snare, toms)
  "cymbal_velocity": 0.65,    // 0.0-1.0 - Overall cymbal volume (hihat, crash, ride)
  
  // OR more granular:
  "kick_velocity": 0.95,
  "snare_velocity": 0.90,
  "tom_velocity": 0.85,
  "hihat_velocity": 0.65,
  "crash_velocity": 0.80,
  "ride_velocity": 0.70
}
```

**Implementation:**
- Multiply base velocity by these factors
- Allow per-instrument mixing
- Save as user presets

---

### **2. CYMBAL PLAYING DENSITY** ⭐

**Purpose:** Control how busy the cymbal patterns are (separate from drums)

```javascript
{
  "drum_density": 0.7,        // 0.0-1.0 - How busy drums are (kick, snare, toms)
  "cymbal_density": 0.9,      // 0.0-1.0 - How busy cymbals are (hihat, ride)
  
  // OR more specific:
  "hihat_density": 0.95,      // Very busy hi-hats
  "ride_density": 0.6,        // Moderate ride cymbal
  "crash_density": 0.3        // Sparse crash hits
}
```

**Use Cases:**
- Sparse drums + busy hi-hats (funk/jazz)
- Busy drums + minimal cymbals (metal)
- Full density everywhere (prog rock)

---

### **3. DRUM FILL DENSITY** ⭐

**Purpose:** Control how complex/busy the fills are

```javascript
{
  "fill_density": 0.7,        // 0.0-1.0 - How many notes in fills
  
  // Presets:
  "fill_density_preset": "sparse",  // Options: sparse, moderate, busy, insane
  
  // Breakdown:
  // 0.0-0.3 = Sparse (1-2 hits)
  // 0.3-0.6 = Moderate (3-5 hits)
  // 0.6-0.8 = Busy (6-10 hits)
  // 0.8-1.0 = Insane (11+ hits, technical fills)
}
```

**Examples:**
- **Sparse:** Single snare hit
- **Moderate:** Tom-tom-snare
- **Busy:** Full tom run with crashes
- **Insane:** 32nd note rolls and flams

---

### **4. FILL LOCATION** ⭐

**Purpose:** Where in the measure the fills occur

```javascript
{
  "fill_location": "end",     // Options: "front", "middle", "end", "auto"
  
  // Timing within measure:
  "fill_timing": {
    "front": [0.0, 0.25],     // First 25% of measure
    "middle": [0.25, 0.75],   // Middle 50% of measure
    "end": [0.75, 1.0],       // Last 25% of measure (most common)
    "auto": null              // AI decides based on song
  },
  
  // Frequency:
  "fill_frequency": 4,        // Every N bars (1=every bar, 4=every 4 bars)
  
  "fill_positions": [
    "bar_end",                // Classic: end of bar
    "bar_start",              // Aggressive: start of bar
    "beat_2_3",               // Middle of bar (beat 2-3)
    "syncopated"              // Off-beat fill placement
  ]
}
```

**Use Cases:**
- **End fills:** Traditional rock/pop
- **Front fills:** Aggressive metal/punk
- **Middle fills:** Jazz/fusion complexity
- **Auto:** AI analyzes song structure

---

### **5. HIHAT COMPLEXITY** ⭐ (To Be Built)

**Purpose:** Advanced hi-hat patterns and techniques

```javascript
{
  "hihat_complexity": 0.7,    // 0.0-1.0 - Overall complexity
  
  "hihat_pattern": "standard", // Options: standard, disco, funk, latin, techno
  
  "hihat_techniques": {
    "open_hits": 0.3,         // 0.0-1.0 - Frequency of open hi-hat
    "chick_hits": 0.2,        // 0.0-1.0 - Foot splash/chick
    "half_open": 0.1,         // 0.0-1.0 - Half-open articulation
    "ghost_notes": 0.4,       // 0.0-1.0 - Quiet ghost notes between
    "flams": 0.1              // 0.0-1.0 - Flammed hi-hat hits
  },
  
  "hihat_variation": {
    "subdivision": "16th",    // Options: 8th, 16th, 32nd, triplet
    "swing_amount": 0.15,     // Independent swing for hi-hat
    "dynamics": 0.6           // 0.0-1.0 - Volume variation within pattern
  },
  
  // Presets:
  "hihat_preset": "disco",    // Options: basic, disco, funk, techno, jazz, latin
  
  // Disco: Constant 16ths with open on off-beats
  // Funk: Syncopated with ghost notes
  // Techno: Steady 16ths, minimal variation
  // Jazz: Ride pattern on hihat
  // Latin: Clave-based patterns
}
```

**Implementation Priority:** HIGH - Critical for realistic grooves

---

### **6. RIDE CYMBAL COMPLEXITY** ⭐ (To Be Built)

**Purpose:** Ride cymbal patterns and techniques

```javascript
{
  "ride_complexity": 0.6,     // 0.0-1.0 - Overall complexity
  
  "ride_pattern": "jazz",     // Options: rock, jazz, fusion, latin
  
  "ride_techniques": {
    "bell_hits": 0.2,         // 0.0-1.0 - Ride bell accents
    "crash_ride": 0.1,        // 0.0-1.0 - Crash the ride cymbal
    "cross_stick": 0.0,       // 0.0-1.0 - Cross-stick on ride
    "bow_center_ratio": 0.7   // 0.0=all bow, 1.0=all center
  },
  
  "ride_patterns": {
    "rock": "ding-ding-da-ding",     // Standard rock ride pattern
    "jazz": "ding-da-ding-da",       // Jazz ride (triplet feel)
    "fusion": "complex",             // Complex polyrhythmic
    "latin": "clave_based"           // Following clave pattern
  },
  
  "ride_vs_hihat_ratio": 0.5,       // 0.0=all hihat, 1.0=all ride
  "ride_transition_points": [       // When to switch hihat <-> ride
    "chorus",
    "bridge"
  ]
}
```

**Implementation Priority:** MEDIUM - Important for style authenticity

---

### **7. BASS LINE REFERENCE** ⭐ (To Be Built)

**Purpose:** Align drums with bass line for tight groove

```javascript
{
  "bass_line_mode": "follow",       // Options: ignore, follow, complement, lock
  
  "bass_line_source": {
    "type": "analyzed",             // Options: analyzed, uploaded, generated
    "file": "bassline.mid",         // MIDI file or audio
    "track": "bass"                 // Which track to follow
  },
  
  "bass_kick_alignment": {
    "sync_level": 0.9,              // 0.0-1.0 - How closely kick follows bass
    "lock_downbeats": true,         // Always kick with bass on 1
    "lock_fills": false,            // Free kick during fills
    "ghost_kick_on_bass": 0.3       // Add ghost kick notes on bass hits
  },
  
  "bass_snare_interaction": {
    "avoid_bass_notes": 0.5,        // 0.0-1.0 - Don't snare when bass plays
    "accent_bass_offbeats": 0.7,    // Snare when bass is silent
    "complement_rhythm": true       // Fill in gaps in bass line
  },
  
  "bass_groove_lock": {
    "enabled": true,
    "strictness": 0.8,              // 0.0=loose, 1.0=locked tight
    "analyze_bass_pattern": true,   // Auto-detect bass groove
    "match_bass_swing": true        // Match swing feel of bass
  },
  
  // Presets:
  "bass_drum_preset": "locked",     // Options: independent, loose, locked, symbiotic
  
  // locked: Kick always with bass
  // loose: Kick mostly with bass
  // independent: Drums ignore bass
  // symbiotic: Drums and bass weave together
}
```

**Implementation Priority:** HIGH - Essential for pro-level groove

---

## 🎛️ **ADDITIONAL ADVANCED OPTIONS**

### **8. TOM CONFIGURATION**

```javascript
{
  "tom_usage": 0.4,                 // 0.0-1.0 - How often toms are used
  "tom_pattern": "descending",      // Options: random, ascending, descending, alternating
  "tom_in_groove": 0.2,             // Use toms in main groove (vs only fills)
  "floor_tom_emphasis": 0.7         // 0.0-1.0 - Favor floor tom over rack toms
}
```

### **9. CRASH CYMBAL CONTROL**

```javascript
{
  "crash_frequency": 0.3,           // 0.0-1.0 - How often crashes hit
  "crash_on_downbeats": true,       // Crash on section starts
  "crash_on_fills": 0.8,            // Probability of crash after fills
  "crash_type": "single",           // Options: single, double, stack
  "crash_sustain": 0.6              // Let ring vs choke
}
```

### **10. GHOST NOTES**

```javascript
{
  "ghost_note_density": 0.4,        // 0.0-1.0 - How many ghost notes
  "ghost_note_lanes": ["snare", "kick", "hihat"],
  "ghost_note_velocity": 0.25,      // Volume of ghost notes
  "ghost_note_pattern": "funk"      // Options: subtle, funk, technical
}
```

### **11. DYNAMICS & ARTICULATION**

```javascript
{
  "dynamic_range": 0.7,             // 0.0-1.0 - Difference between soft/loud
  "accent_pattern": "downbeats",    // Options: downbeats, syncopated, random, none
  "crescendo_fills": true,          // Fills get louder
  "flams": 0.1,                     // 0.0-1.0 - Frequency of flammed notes
  "drags": 0.05,                    // 0.0-1.0 - Frequency of drag rudiments
  "ruffs": 0.05                     // 0.0-1.0 - Frequency of ruff ornaments
}
```

### **12. POLYRHYTHMIC OPTIONS**

```javascript
{
  "polyrhythm_complexity": 0.0,     // 0.0-1.0 - Add polyrhythmic elements
  "cross_rhythm_ratio": "3:2",      // Options: "3:2", "4:3", "5:4", etc.
  "polyrhythm_lanes": ["ride"],     // Which instruments play cross-rhythm
  "polyrhythm_duration": "bridge"   // When to apply (section label)
}
```

### **13. TIME SIGNATURE HANDLING**

```javascript
{
  "time_signature": [4, 4],         // [numerator, denominator]
  "odd_time_subdivision": "3+3+2",  // For 7/8, etc.
  "time_sig_changes": [             // Progressive time changes
    { "bar": 8, "signature": [7, 8] },
    { "bar": 16, "signature": [4, 4] }
  ]
}
```

### **14. SECTION-SPECIFIC OVERRIDES**

```javascript
{
  "section_overrides": {
    "verse": {
      "density": 0.5,
      "hihat_density": 0.9,
      "drum_velocity": 0.7,
      "fill_frequency": 8
    },
    "chorus": {
      "density": 0.9,
      "crash_frequency": 0.8,
      "drum_velocity": 0.95,
      "ride_vs_hihat_ratio": 0.7
    },
    "bridge": {
      "polyrhythm_complexity": 0.6,
      "fill_location": "middle",
      "hihat_complexity": 0.8
    }
  }
}
```

---

## 📊 **COMPLETE OPTIONS OBJECT (v2.0)**

```javascript
{
  // === EXISTING OPTIONS ===
  "drummer_type": "studio_groove_master",
  "style": "funk",
  "bpm": 105,
  "bars": 8,
  "density": 0.7,
  "swing": 0.15,
  "humanize": 0.2,
  "seed": 12345,
  "swing_preset": "light",
  "vel_preset": "funk16",
  "fill_preset": "tomrun",
  "label": "chorus",
  "fill_in": true,
  "fill_out": true,
  
  // === NEW: VELOCITY CONTROLS ===
  "drum_velocity": 0.85,
  "cymbal_velocity": 0.65,
  "kick_velocity": 0.95,
  "snare_velocity": 0.90,
  "tom_velocity": 0.85,
  "hihat_velocity": 0.65,
  "crash_velocity": 0.80,
  "ride_velocity": 0.70,
  
  // === NEW: DENSITY CONTROLS ===
  "drum_density": 0.7,
  "cymbal_density": 0.9,
  "hihat_density": 0.95,
  "ride_density": 0.6,
  "crash_density": 0.3,
  
  // === NEW: FILL CONTROLS ===
  "fill_density": 0.7,
  "fill_density_preset": "moderate",
  "fill_location": "end",
  "fill_frequency": 4,
  "fill_positions": ["bar_end"],
  
  // === NEW: HIHAT COMPLEXITY ===
  "hihat_complexity": 0.7,
  "hihat_pattern": "funk",
  "hihat_techniques": {
    "open_hits": 0.3,
    "chick_hits": 0.2,
    "half_open": 0.1,
    "ghost_notes": 0.4,
    "flams": 0.1
  },
  "hihat_subdivision": "16th",
  "hihat_swing": 0.15,
  
  // === NEW: RIDE COMPLEXITY ===
  "ride_complexity": 0.6,
  "ride_pattern": "jazz",
  "ride_techniques": {
    "bell_hits": 0.2,
    "crash_ride": 0.1,
    "bow_center_ratio": 0.7
  },
  "ride_vs_hihat_ratio": 0.5,
  
  // === NEW: BASS LINE REFERENCE ===
  "bass_line_mode": "follow",
  "bass_line_source": {
    "type": "analyzed",
    "file": "bassline.mid"
  },
  "bass_kick_alignment": {
    "sync_level": 0.9,
    "lock_downbeats": true,
    "ghost_kick_on_bass": 0.3
  },
  "bass_drum_preset": "locked",
  
  // === ADDITIONAL ADVANCED ===
  "tom_usage": 0.4,
  "tom_pattern": "descending",
  "crash_frequency": 0.3,
  "crash_on_downbeats": true,
  "ghost_note_density": 0.4,
  "dynamic_range": 0.7,
  "accent_pattern": "downbeats",
  "flams": 0.1,
  "polyrhythm_complexity": 0.0,
  "time_signature": [4, 4],
  
  // === SECTION OVERRIDES ===
  "section_overrides": {
    "verse": { "density": 0.5 },
    "chorus": { "density": 0.9, "crash_frequency": 0.8 }
  }
}
```

---

## 🎯 **IMPLEMENTATION PRIORITY**

### **Phase 1: Critical (Do First)**
1. ✅ **Cymbal vs Drum Velocity** - Easy to add
2. ✅ **Cymbal/Drum Density Split** - Easy to add
3. ✅ **Fill Density Control** - Easy to add
4. ✅ **Fill Location** - Moderate complexity

### **Phase 2: High Priority**
5. 🔨 **Hi-Hat Complexity** - Requires pattern generation updates
6. 🔨 **Bass Line Reference** - Requires bass analysis integration
7. ✅ **Ghost Notes** - Moderate complexity
8. ✅ **Crash Cymbal Control** - Easy to add

### **Phase 3: Medium Priority**
9. 🔨 **Ride Cymbal Complexity** - Requires new pattern logic
10. ✅ **Tom Configuration** - Easy to add
11. ✅ **Dynamics & Articulation** - Moderate complexity
12. ✅ **Section Overrides** - Easy to add

### **Phase 4: Advanced Features**
13. 🔨 **Polyrhythmic Options** - Complex
14. 🔨 **Time Signature Handling** - Complex
15. 🔨 **Advanced Rudiments** (flams, drags, ruffs) - Moderate

---

## 📝 **USAGE EXAMPLES**

### **Example 1: Funk Groove with Busy Hi-Hats**
```javascript
{
  "style": "funk",
  "drum_density": 0.5,        // Sparse drums
  "cymbal_density": 0.95,     // Very busy hi-hats
  "hihat_pattern": "funk",
  "hihat_techniques": {
    "open_hits": 0.4,
    "ghost_notes": 0.6
  },
  "bass_line_mode": "locked"  // Lock with bass
}
```

### **Example 2: Progressive Metal with Complex Fills**
```javascript
{
  "style": "rock",
  "drummer_type": "progressive_polymath",
  "fill_density": 0.95,       // Insane fills
  "fill_location": "middle",
  "tom_pattern": "alternating",
  "polyrhythm_complexity": 0.7,
  "time_signature": [7, 8]
}
```

### **Example 3: Jazz with Ride Cymbal Focus**
```javascript
{
  "style": "jazz",
  "ride_vs_hihat_ratio": 0.9, // Mostly ride
  "ride_pattern": "jazz",
  "ride_techniques": {
    "bell_hits": 0.3
  },
  "ghost_note_density": 0.6,
  "bass_drum_preset": "independent"
}
```

---

## ✅ **SUMMARY**

**Current Parameters:** 16  
**New Parameters:** 40+  
**Total Parameters:** 56+

**Easy to Implement:** 20  
**Moderate Complexity:** 15  
**High Complexity:** 10  
**Not Started:** 11

---

**Next Steps:**
1. Review this list with user
2. Prioritize which options to implement first
3. Update Rust generator.rs with new parameters
4. Update DCSM UI with new controls
5. Test and refine

**This gives you professional-level control over every aspect of drum track creation!** 🎸🥁
