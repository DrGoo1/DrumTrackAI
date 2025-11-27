# 🚀 Section Playback System - Quick Start Guide

Get up and running with section-based playback in **5 minutes**!

---

## ⚡ **Quick Steps**

### **1. Start the System (2 minutes)**

```bash
# Terminal 1: Start Backend
cd f:\DrumTracKAI_v1.1.16_Clean
python dcsm_backend.py

# Terminal 2: Start Frontend
cd web-frontend-landing-v117
npm start
```

**Backend:** http://localhost:8000  
**Frontend:** http://localhost:3000

---

### **2. Access Section Player (30 seconds)**

1. Open browser to http://localhost:3000
2. Click **"Section Player"** in navigation
3. You'll see the Section Playback Demo page

---

### **3. Upload & Analyze (2 minutes)**

#### **Option A: Use Your Audio File**
1. Click **"Select Audio File"**
2. Choose a WAV or MP3 file
3. Click **"📤 Upload File"** (wait for ✓)
4. Toggle **"Auto-detect BPM"** (or enter manual BPM)
5. Click **"🔍 Analyze Sections"** (wait ~10-30 seconds)

#### **Option B: Use Demo Data (Instant)**
1. Click **"🎬 Load Demo Sections (Testing)"**
2. Skip to step 4!

---

### **4. Play Sections (30 seconds)**

You'll see a list of sections (intro, verse, chorus, etc.):

1. **Play:** Click the green **▶** button on any section
2. **Pause:** Click the blue **⏸** button on the playing section
3. **Loop:** Click **"🔁 Loop ON"** to repeat current section
4. **Switch:** Click **▶** on a different section to switch
5. **Stop:** Click **"⬛ Stop All"** to stop everything

---

## 🎮 **Controls Overview**

### **Global Controls (Top)**
- **🔁 Loop ON/OFF** - Toggle section looping
- **⬛ Stop All** - Emergency stop button

### **Per-Section Controls**
- **▶ Play** - Start section playback
- **⏸ Pause** - Pause current section
- **Progress Bar** - Shows playback progress
- **Time Display** - Current position in section

### **Visual Indicators**
- **Green Button** = Ready to play
- **Blue Button** = Currently playing (pause available)
- **Pulsing Dot** = Active playback indicator
- **Color Labels** = Section types (blue=intro, green=verse, purple=chorus, etc.)

---

## 📋 **Typical Workflow**

```
┌─────────────┐
│ Upload File │ ← Select WAV/MP3 (Step 1)
└──────┬──────┘
       ↓
┌─────────────┐
│   Analyze   │ ← Detect sections (Step 2)
└──────┬──────┘
       ↓
┌─────────────┐
│ Play Section│ ← Click ▶ on any section (Step 3)
└──────┬──────┘
       ↓
┌─────────────┐
│ Toggle Loop │ ← Enable continuous repeat (Step 4)
└──────┬──────┘
       ↓
┌─────────────┐
│   Practice! │ ← Learn/analyze the section
└─────────────┘
```

---

## 💡 **Pro Tips**

### **For Musicians/Drummers:**
1. **Enable Loop** - Practice difficult sections repeatedly
2. **Check Timing** - See exact start/end times
3. **Energy Levels** - Identify dynamic changes
4. **Bar Counts** - Know section lengths

### **For Producers:**
1. **Section Labels** - Identify song structure
2. **Quick Navigation** - Jump to any section instantly
3. **A/B Testing** - Compare different sections
4. **Arrangement Analysis** - Study professional arrangements

### **For Developers:**
1. **Use Demo Mode** - Test UI without backend
2. **Check Console** - Monitor API calls and errors
3. **Inspect Sections** - See section metadata
4. **Custom Integration** - Import SectionPlayer component

---

## 🔧 **Troubleshooting**

### **"No sound when I click play"**
- **Fix:** Click any button first (browser autoplay policy)
- **Check:** Volume is not muted
- **Verify:** Audio file uploaded successfully

### **"Analyze button doesn't work"**
- **Fix:** Ensure backend is running (python dcsm_backend.py)
- **Check:** File uploaded successfully (green ✓ appears)
- **Wait:** Analysis takes 10-30 seconds

### **"CORS error in console"**
- **Fix:** Backend must run on port 8000
- **Check:** `dcsm_backend.py` has CORS enabled
- **Restart:** Both backend and frontend

### **"No sections appear"**
- **Try:** Click "Load Demo Sections" to test UI
- **Check:** Console for error messages
- **Verify:** Audio file is valid WAV/MP3

---

## 📖 **Example Use Cases**

### **Drum Practice**
```
1. Upload drum track
2. Analyze to get sections
3. Play challenging section
4. Enable Loop ON
5. Practice along with section
```

### **Song Analysis**
```
1. Upload full song
2. Auto-detect sections
3. Play each section
4. Study arrangement structure
5. Note energy changes
```

### **Production Work**
```
1. Upload project audio
2. Identify verse/chorus sections
3. Compare section lengths
4. Check bar counts
5. Refine arrangement
```

---

## 🎯 **What's Next?**

After mastering basic playback, explore:

1. **Keyboard Shortcuts** (coming soon)
2. **Waveform Visualization** (coming soon)
3. **Section Export** (coming soon)
4. **Tempo Adjustment** (coming soon)
5. **Integration with DAW Plugin** (see `GUIDE_TRACK_IMPLEMENTATION.md`)

---

## 📚 **Full Documentation**

For complete details, see:
- **`SECTION_PLAYBACK_SYSTEM.md`** - Complete technical documentation
- **`README.md`** - Main DrumTracKAI documentation
- **`CURRENT_STATE.md`** - System overview

---

## 🆘 **Need Help?**

- **Component Issues:** Check browser console for errors
- **Backend Issues:** Check Python terminal for error logs
- **API Issues:** Verify backend is running on port 8000
- **Feature Requests:** See `SECTION_PLAYBACK_SYSTEM.md` → Future Enhancements

---

## ✅ **Quick Test Checklist**

- [ ] Backend running (http://localhost:8000)
- [ ] Frontend running (http://localhost:3000)
- [ ] Can navigate to Section Player page
- [ ] Can upload audio file
- [ ] Can analyze sections
- [ ] Can play a section
- [ ] Can pause/resume
- [ ] Can toggle loop
- [ ] Can switch sections
- [ ] Progress bars work

**All checked?** 🎉 **You're ready to use the Section Playback System!**

---

**⏱️ Total Setup Time:** ~5 minutes  
**🎯 Difficulty Level:** Easy  
**✨ Feature Status:** Production Ready

🎵 **Start playing sections now!** 🎵
