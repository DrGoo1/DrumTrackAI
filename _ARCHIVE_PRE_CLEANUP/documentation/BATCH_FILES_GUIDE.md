# 🚀 **DrumTracKAI v1.1.16 - Batch Files Guide**

**All batch files are now in the root directory for easy access!**

---

## 📁 **STARTUP SCRIPTS**

### **START_ALL.bat** ⭐ (Recommended)
**What it does:**
- Starts Backend (port 8000)
- Starts DCSM Studio (port 3000)
- Starts Landing Page (port 3004)
- Opens landing page in browser

**Usage:**
```
Double-click START_ALL.bat
```

**Result:**
- 3 windows open (Backend, DCSM, Landing Page)
- Browser opens to http://localhost:3004
- All services ready in ~60 seconds

---

### **1_START_BACKEND.bat**
**What it does:**
- Starts Python backend on port 8000
- AI system, API endpoints, database

**Usage:**
```
Double-click 1_START_BACKEND.bat
```

**When to use:**
- Testing backend only
- Development work on backend

---

### **2_START_DCSM.bat**
**What it does:**
- Starts DCSM Studio on port 3000
- Drum Composer interface

**Usage:**
```
Double-click 2_START_DCSM.bat
```

**When to use:**
- Testing DCSM only
- Working on frontend

---

### **3_START_LANDING_PAGE.bat**
**What it does:**
- Starts Landing Page on port 3004
- Marketing site with tier pages

**Usage:**
```
Double-click 3_START_LANDING_PAGE.bat
```

**When to use:**
- Testing landing page
- Showing to clients
- Working on commercial features

---

## 🛑 **SHUTDOWN SCRIPTS**

### **STOP_ALL.bat**
**What it does:**
- Stops all Node processes (frontends)
- Stops all Python processes (backend)
- Cleans up all services

**Usage:**
```
Double-click STOP_ALL.bat
```

**When to use:**
- When done working
- Before restarting
- To free up ports

---

## 🌐 **QUICK ACCESS SCRIPTS**

### **OPEN_LANDING_PAGE.bat**
Opens: http://localhost:3004

### **OPEN_PROFESSIONAL_TIER.bat**
Opens: http://localhost:3004/?page=professional

### **OPEN_BASIC_TIER.bat**
Opens: http://localhost:3004/?page=basic

### **OPEN_DCSM.bat**
Opens: http://localhost:3000

---

## 🧪 **TESTING SCRIPTS**

### **TEST_BACKEND.bat**
**What it does:**
- Tests backend API
- Checks if AI system is running
- Displays status

**Usage:**
```
Double-click TEST_BACKEND.bat
```

**When to use:**
- Verify backend is working
- Check AI system status
- Troubleshooting

---

## 📋 **TYPICAL WORKFLOWS**

### **Daily Development:**
```
1. Double-click START_ALL.bat
2. Wait 60 seconds
3. Work on your code
4. When done: STOP_ALL.bat
```

### **Testing Landing Page:**
```
1. 1_START_BACKEND.bat
2. 3_START_LANDING_PAGE.bat
3. OPEN_LANDING_PAGE.bat
```

### **Testing Professional Tier:**
```
1. START_ALL.bat
2. OPEN_PROFESSIONAL_TIER.bat
3. Test upload features
```

### **Backend Development:**
```
1. 1_START_BACKEND.bat
2. TEST_BACKEND.bat
3. Make changes
4. Restart: STOP_ALL.bat then 1_START_BACKEND.bat
```

---

## 🎯 **QUICK REFERENCE**

| What You Want | Batch File to Run |
|---------------|-------------------|
| Start everything | `START_ALL.bat` |
| Stop everything | `STOP_ALL.bat` |
| See landing page | `OPEN_LANDING_PAGE.bat` |
| See pro tier | `OPEN_PROFESSIONAL_TIER.bat` |
| Test backend | `TEST_BACKEND.bat` |
| Just backend | `1_START_BACKEND.bat` |
| Just DCSM | `2_START_DCSM.bat` |
| Just landing | `3_START_LANDING_PAGE.bat` |

---

## ⚡ **ADVANTAGES OF BATCH FILES**

**Why we use them:**
- ✅ No PowerShell syntax issues
- ✅ Reliable and consistent
- ✅ Easy to run (double-click)
- ✅ Easy to edit
- ✅ Works every time
- ✅ Simple debugging

**vs PowerShell commands:**
- ❌ Complex escaping
- ❌ Syntax errors
- ❌ Different behavior in different contexts
- ❌ Hard to troubleshoot

---

## 🔧 **CUSTOMIZATION**

### **Want to change ports?**

Edit the batch file:
```batch
REM In 3_START_LANDING_PAGE.bat
set PORT=3004  ← Change this number
```

### **Want to add logging?**

Add to any batch file:
```batch
echo [%date% %time%] Service started >> log.txt
```

### **Want to run in background?**

Change from:
```batch
npm start
```

To:
```batch
start /B npm start
```

---

## 🐛 **TROUBLESHOOTING**

### **"Port already in use"**
```
Run: STOP_ALL.bat
Then: START_ALL.bat
```

### **Backend won't start**
```
Check: Is Python installed?
Check: Is virtual environment active?
Run: 1_START_BACKEND.bat and read error
```

### **Frontend won't start**
```
Check: Are node_modules installed?
Run: cd frontend && npm install
Then: 2_START_DCSM.bat
```

### **Page won't open in browser**
```
Wait 60 seconds for services to start
Manually open: http://localhost:3004
Check: Is service running?
```

---

## 📊 **STATUS CHECK**

### **Is Backend Running?**
```
Open: http://localhost:8000/api/ai/status
Should see: JSON response with "success": true
```

### **Is DCSM Running?**
```
Open: http://localhost:3000
Should see: DCSM interface
```

### **Is Landing Page Running?**
```
Open: http://localhost:3004
Should see: DrumTracKAI landing page
```

---

## 🎓 **BEST PRACTICES**

1. **Always use START_ALL.bat** for daily work
2. **Always use STOP_ALL.bat** when done
3. **Use TEST_BACKEND.bat** to verify backend
4. **Edit batch files** instead of typing commands
5. **Keep batch files** in root directory
6. **Don't delete** batch files (they're small)

---

## 📝 **CREATING YOUR OWN**

Want to create a custom batch file?

**Template:**
```batch
@echo off
echo ========================================
echo Your Task Name
echo ========================================
echo.

REM Your commands here
cd /d f:\DrumTracKAI_v1.1.16_Clean
python my_script.py

echo.
echo Done!
pause
```

**Save as:** `MY_TASK.bat`
**Run:** Double-click

---

## ✅ **SUMMARY**

**You now have:**
- ✅ 10 reliable batch files
- ✅ No PowerShell syntax issues
- ✅ One-click operations
- ✅ Easy startup/shutdown
- ✅ Quick access to all pages
- ✅ Simple testing tools

**To get started:**
```
1. Double-click START_ALL.bat
2. Wait 60 seconds
3. Start working!
```

**To stop:**
```
1. Double-click STOP_ALL.bat
2. All services stopped!
```

---

**All PowerShell syntax issues are now eliminated! Just double-click batch files.** 🎉
