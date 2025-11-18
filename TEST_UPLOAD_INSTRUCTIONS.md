# DrumTracKAI v1.1.16 - Upload Testing Instructions

## Issue: "Failed to Fetch" Error

If you're getting a "failed to fetch" error when uploading files:

### **Step 1: Clear Browser Cache**
The browser may be caching old JavaScript that tries to access `localhost:8000` directly.

**Option A: Hard Refresh**
- **Chrome/Edge:** Ctrl + Shift + R (Windows) or Cmd + Shift + R (Mac)
- **Firefox:** Ctrl + F5 (Windows) or Cmd + Shift + R (Mac)

**Option B: Open DevTools and Disable Cache**
1. Press F12 to open Developer Tools
2. Go to Network tab  
3. Check "Disable cache"
4. Refresh the page (Ctrl+R or Cmd+R)

### **Step 2: Check Which Endpoint is Being Called**

Open DevTools (F12) → Network tab:
1. Try uploading a file
2. Look for the failed request
3. Check the URL:
   - ✅ **CORRECT:** `http://localhost:3000/files/upload` (relative URL through nginx)
   - ❌ **WRONG:** `http://localhost:8000/files/upload` (direct access - won't work in Docker)

### **Step 3: If URL is Wrong**

The frontend JavaScript still has the old API_BASE. You need to rebuild:

```bash
docker-compose up -d --build frontend
```

Then **clear browser cache again** (Ctrl+Shift+R).

### **Step 4: Test Direct Access**

Open these URLs in your browser to verify services:

- ✅ Frontend: http://localhost:3000
- ✅ Health check (through nginx): http://localhost:3000/healthz
- ❌ Backend direct (should fail): http://localhost:8000/healthz

If the direct backend URL works in your browser, Docker port mapping is misconfigured.

### **Step 5: Check Docker Services**

```powershell
# Check both containers are running
docker-compose ps

# Check backend logs for requests
docker logs drumtrackai-v1116-backend --tail 20

# Check frontend nginx logs  
docker logs drumtrackai-v1116-frontend --tail 20
```

### **Expected Behavior**

When you upload a file:
1. Browser sends: `POST http://localhost:3000/files/upload`
2. Nginx proxies to: `http://backend:8000/files/upload`
3. Backend saves file and returns JSON
4. You should see in backend logs: `INFO: ... "POST /files/upload HTTP/1.0" 200`

### **Troubleshooting**

**Error: "Failed to fetch"**
- Browser can't reach the endpoint
- Check DevTools Console for the actual error
- Verify API_BASE is empty string (not `http://localhost:8000`)

**Error: "CORS policy"**
- Shouldn't happen with same-origin requests
- If you see this, check nginx CORS headers

**Error: "Network error"**
- Docker containers may not be running
- Run: `docker-compose ps` to verify

**No error in console, just fails silently**
- Check if file size is too large
- Check backend logs for actual error
- Try a small test file (< 1MB)

## Quick Test

1. **Hard refresh:** Ctrl+Shift+R
2. **Open DevTools:** F12 → Network tab
3. **Upload:** Click "Load Audio" and select a small WAV/MP3 file
4. **Watch Network tab:** Should see POST to `/files/upload` with 200 response

If you see a request to `localhost:8000`, the browser has cached old code!
