# 🔧 **File Upload Error - "Failed to fetch"**

## 🔴 **THE ERROR:**
```
Failed to upload file: Failed to fetch
```

This error means the browser **cannot connect to the backend server**.

---

## ✅ **SOLUTION - Check Backend is Running**

### **Step 1: Check if Backend is Running**

Open a new command prompt and run:
```batch
netstat -ano | findstr ":8000"
```

**If you see output:** Backend is running ✅  
**If you see nothing:** Backend is NOT running ❌

---

### **Step 2: Start Backend if Not Running**

**Run this:**
```batch
cd f:\DrumTracKAI_v1.1.16_Clean
python dcsm_backend.py
```

**Or use the restart script:**
```batch
RESTART_ALL_SERVERS.bat
```

---

### **Step 3: Test Backend**

Open browser and go to:
```
http://localhost:8000/healthz
```

**Should show:**
```json
{"ok": true, "ts": 1234567890.123}
```

---

## 🧪 **QUICK TEST:**

Run this batch file:
```batch
CHECK_BACKEND_STATUS.bat
```

It will:
1. Check if backend is running
2. Start it if not
3. Test the connection

---

## 🎯 **COMPLETE STARTUP SEQUENCE:**

### **Option 1: Use Restart Script** (Easiest)
```batch
RESTART_ALL_SERVERS.bat
```

Starts all three servers:
- Backend (port 8000)
- DCSM (port 3000)
- Landing Page (port 3004)

### **Option 2: Manual Startup**

**Terminal 1 - Backend:**
```batch
cd f:\DrumTracKAI_v1.1.16_Clean
python dcsm_backend.py
```

**Terminal 2 - DCSM:**
```batch
cd f:\DrumTracKAI_v1.1.16_Clean\frontend
npm start
```

**Terminal 3 - Landing Page:**
```batch
cd f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
set PORT=3004
npm start
```

---

## 🐛 **OTHER POSSIBLE ISSUES:**

### **Issue 1: Python Not Found**
```
Error: 'python' is not recognized
```

**Fix:** Use full path or activate virtual environment:
```batch
f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py
```

### **Issue 2: Port Already in Use**
```
Error: Address already in use
```

**Fix:** Kill existing process:
```batch
netstat -ano | findstr ":8000"
taskkill /F /PID <PID_NUMBER>
```

### **Issue 3: Missing Dependencies**
```
ModuleNotFoundError: No module named 'aiohttp'
```

**Fix:** Install dependencies:
```batch
pip install aiohttp aiohttp-cors numpy librosa soundfile
```

---

## ✅ **VERIFICATION CHECKLIST:**

Before uploading, make sure:

- [ ] Backend running (check port 8000)
- [ ] `http://localhost:8000/healthz` shows `{"ok": true}`
- [ ] Landing page on port 3004
- [ ] No firewall blocking localhost
- [ ] Browser console shows no CORS errors

---

## 🎯 **EXPECTED FLOW:**

**1. Start All Servers**
```batch
RESTART_ALL_SERVERS.bat
```

**2. Go to Professional Tier**
```
http://localhost:3004/?page=professional
```

**3. Upload File**
- Select file
- See "Uploading to server..."
- See "✓ Ready for drum track creation"

**4. Create Drum Track**
- Click button
- DCSM opens with file loaded

---

## 🔍 **DEBUGGING:**

### **Check Backend Logs**
Look in the terminal where backend is running for:
```
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
```

### **Check Browser Console (F12)**
Look for:
- Network tab → /upload request
- Red errors
- CORS messages

### **Test Upload Manually**
```batch
curl -X POST -F "file=@test.mp3" http://localhost:8000/upload
```

Should return:
```json
{
  "success": true,
  "key": "1234567890-test.mp3",
  ...
}
```

---

## 📁 **FILES CREATED:**

1. ✅ `CHECK_BACKEND_STATUS.bat` - Check/start backend
2. ✅ `RESTART_ALL_SERVERS.bat` - Restart everything
3. ✅ `FILE_UPLOAD_FIX.md` - This guide

---

## 🚀 **QUICK FIX NOW:**

**Run this:**
```batch
cd f:\DrumTracKAI_v1.1.16_Clean
CHECK_BACKEND_STATUS.bat
```

Then try uploading again!

---

**Created:** Nov 18, 2025  
**Issue:** Failed to fetch - Backend not accessible  
**Solution:** Ensure backend running on port 8000
