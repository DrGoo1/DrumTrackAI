# 🥁 **DrumTracKAI - Complete Drum Track Creation Options**

**All available options for creating custom drum tracks**

---

## 👤 **DRUMMER TYPES** (12 Total)

These are the fictional DrumTracKAI drummers based on real analyzed drummers:

### **1. Studio Groove Master** 🎩
- **Style:** Jazz Fusion, Pop, Rock, Session Work
- **Difficulty:** Advanced
- **Best For:** Steely Dan style, Toto grooves, Sophisticated pop
- **Signature:** Half-time shuffle, Ghost note mastery, Ride cymbal work

### **2. Metal Atomic Clock** ⚡
- **Style:** Death Metal, Thrash, Technical Metal
- **Difficulty:** Expert
- **Best For:** Extreme metal, Technical death metal, Fast tempos
- **Signature:** Blast beats, Double bass precision, Complex fills

### **3. Progressive Polymath** 🎼
- **Style:** Progressive Rock, Progressive Metal, Math Rock
- **Difficulty:** Expert
- **Best For:** Dream Theater style, Tool rhythms, Prog metal
- **Signature:** Odd time signatures, Polyrhythms, Orchestral approach

### **4. Funk Machine** 🕺
- **Style:** Funk, R&B, Soul, Gospel
- **Difficulty:** Advanced
- **Best For:** P-Funk style, Gospel, Neo-soul
- **Signature:** Funk grooves, Gospel chops, Linear fills

### **5. Jazz Innovator** 🎷
- **Style:** Jazz, Bebop, Fusion, Avant-garde
- **Difficulty:** Expert
- **Best For:** Jazz standards, Bebop, Free jazz
- **Signature:** Polyrhythmic playing, Rolling triplets, Dynamic swells

### **6. Rock Powerhouse** 🔨
- **Style:** Rock, Hard Rock, Blues Rock
- **Difficulty:** Intermediate
- **Best For:** Led Zeppelin style, Classic rock, Blues rock
- **Signature:** Triplet patterns, Heavy foot, Groove-oriented

### **7. Alternative Innovator** 🤘
- **Style:** Grunge, Alternative Rock, Punk
- **Difficulty:** Intermediate
- **Best For:** Grunge, Alternative rock, Punk
- **Signature:** Power playing, Simple effectiveness, Primal energy

### **8. World Fusion Master** 🌍
- **Style:** World Music, Reggae, New Wave, Fusion
- **Difficulty:** Advanced
- **Best For:** Police style, Reggae rock, World fusion
- **Signature:** Reggae influences, Hi-hat mastery, Splash cymbals

### **9. Hip-Hop Architect** 🎤
- **Style:** Hip-Hop, Neo-Soul, R&B
- **Difficulty:** Advanced
- **Best For:** Roots style, Neo-soul, Boom-bap
- **Signature:** Sample-based playing, Pocket mastery, Minimalist approach

### **10. Metal Chaos Master** 💀
- **Style:** Nu Metal, Industrial, Alternative Metal
- **Difficulty:** Advanced
- **Best For:** Slipknot style, Industrial metal, Nu metal
- **Signature:** Fast double bass, Tribal rhythms, Percussive elements

### **11. Latin Percussionist** 🌶️
- **Style:** Latin, Salsa, Afro-Cuban, Samba
- **Difficulty:** Advanced
- **Best For:** Latin grooves, Salsa, Brazilian styles
- **Signature:** Clave patterns, Timbale work, Latin percussion

### **12. Electronic Beat Smith** 🎹
- **Style:** Electronic, EDM, House, Techno
- **Difficulty:** Intermediate
- **Best For:** Electronic music, Four-on-the-floor, Club beats
- **Signature:** Electronic precision, Quantized feels, Build-ups

---

## 🎵 **MUSIC STYLE**

Choose the genre/style for your drum track:

- **rock** - Classic rock grooves
- **funk** - Funk and R&B grooves
- **edm** - Electronic dance music patterns
- **hiphop** - Hip-hop and boom-bap
- **jazz** - Jazz and swing patterns
- **pop** - Pop and contemporary

---

## 🎚️ **SWING PRESETS**

Controls the swing feel of the drum pattern:

- **off** - Straight timing, no swing
- **light** - Subtle swing feel (~55% timing)
- **heavy** - Strong swing feel (~66% timing)

---

## 🎯 **VELOCITY PROFILES**

Controls the dynamic emphasis pattern:

- **flat** - Even velocity across all hits
- **accent24** - Accents on beats 2 and 4 (backbeat)
- **funk16** - 16th note funk accents pattern

---

## 🥁 **FILL PRESETS**

Drum fills at section transitions:

- **none** - No fills, just groove
- **random** - Random fill patterns
- **tomrun** - Tom-tom runs
- **snarebuzz** - Snare buzz rolls
- **edmriser** - EDM-style riser fills

---

## 🎼 **SECTION LABELS**

Identify the song section for appropriate patterns:

- **verse** - Verse sections (simpler patterns)
- **chorus** - Chorus sections (fuller patterns)
- **bridge** - Bridge sections (transitional)
- **outro** - Outro sections (wind-down)
- **intro** - Intro sections (building)
- **breakdown** - Breakdown sections (sparse)

---

## ⚙️ **ADVANCED PARAMETERS**

### **Density** (0.0 - 1.0)
- Controls how busy the drum pattern is
- **0.0** = Minimal, sparse pattern
- **0.5** = Moderate groove
- **1.0** = Very busy, complex pattern
- **Default:** 0.7

### **Swing** (0.0 - 1.0)
- Fine-tune swing amount (in addition to preset)
- **0.0** = No additional swing
- **0.5** = Moderate swing
- **1.0** = Maximum swing
- **Default:** 0.1

### **Humanize** (0.0 - 1.0)
- Add human timing variations
- **0.0** = Perfect machine timing
- **0.5** = Natural human variations
- **1.0** = Loose, very human feel
- **Default:** 0.15

### **BPM** (40 - 240)
- Tempo in beats per minute
- **Default:** 120

### **Bars** (1 - 64)
- Length of pattern in bars (measures)
- **Default:** 8

---

## 🎛️ **COMPLETE OPTIONS OBJECT**

Example of all options together:

```javascript
{
  // Drummer Selection
  "drummer_type": "studio_groove_master",
  
  // Style & Genre
  "style": "funk",
  
  // Groove Settings
  "swing_preset": "light",
  "vel_preset": "funk16",
  "fill_preset": "tomrun",
  
  // Section Info
  "label": "chorus",
  
  // Advanced Parameters
  "density": 0.8,
  "swing": 0.15,
  "humanize": 0.2,
  "bpm": 105,
  "bars": 8,
  
  // Audio Source (if uploaded)
  "audio_file": "uploads/user_track.mp3",
  
  // Time Range
  "start": 0.0,
  "end": 16.0  // seconds
}
```

---

## 📊 **RECOMMENDED COMBINATIONS**

### **Classic Rock**
```javascript
{
  "drummer_type": "rock_powerhouse",
  "style": "rock",
  "swing_preset": "off",
  "vel_preset": "accent24",
  "fill_preset": "tomrun",
  "density": 0.6,
  "humanize": 0.2
}
```

### **Funk Groove**
```javascript
{
  "drummer_type": "funk_machine",
  "style": "funk",
  "swing_preset": "light",
  "vel_preset": "funk16",
  "fill_preset": "snarebuzz",
  "density": 0.8,
  "humanize": 0.15
}
```

### **Progressive Metal**
```javascript
{
  "drummer_type": "progressive_polymath",
  "style": "rock",
  "swing_preset": "off",
  "vel_preset": "flat",
  "fill_preset": "random",
  "density": 0.9,
  "humanize": 0.05
}
```

### **Hip-Hop Beat**
```javascript
{
  "drummer_type": "hip_hop_architect",
  "style": "hiphop",
  "swing_preset": "light",
  "vel_preset": "accent24",
  "fill_preset": "none",
  "density": 0.5,
  "humanize": 0.25
}
```

### **EDM Drop**
```javascript
{
  "drummer_type": "electronic_beat_smith",
  "style": "edm",
  "swing_preset": "off",
  "vel_preset": "flat",
  "fill_preset": "edmriser",
  "density": 1.0,
  "humanize": 0.0
}
```

---

## 🔄 **WORKFLOW WITH OPTIONS**

### **User Flow:**

1. **Upload Audio** (Professional Tier page)
   ↓
2. **Select Drummer Type** (or auto-set from YouTube search)
   ↓
3. **Choose Style** (rock, funk, jazz, etc.)
   ↓
4. **Set Groove Options** (swing, velocity, fills)
   ↓
5. **Adjust Advanced Parameters** (density, humanize)
   ↓
6. **Create Drum Track** → Opens DCSM
   ↓
7. **DCSM Analyzes & Generates**
   ↓
8. **Download MIDI**

---

## 🎯 **DEFAULT VALUES**

When user clicks "Create Drum Track" without customizing:

```javascript
{
  "drummer_type": "studio_groove_master",  // or from YouTube search
  "style": "rock",  // auto-detected from audio
  "swing_preset": "light",
  "vel_preset": "accent24",
  "fill_preset": "tomrun",
  "density": 0.7,
  "swing": 0.1,
  "humanize": 0.15,
  "bpm": 120,  // auto-detected
  "bars": 8,
  "label": "verse"
}
```

---

## ✅ **SUMMARY**

**Total Options:**
- 12 Drummer Types
- 6 Music Styles
- 3 Swing Presets
- 3 Velocity Profiles
- 5 Fill Presets
- 6 Section Labels
- 5 Advanced Parameters

**= Millions of possible combinations!**

---

**All these options should be available on the DCSM page after audio upload.**
