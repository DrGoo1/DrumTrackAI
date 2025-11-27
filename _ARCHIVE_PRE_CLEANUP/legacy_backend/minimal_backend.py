"""
Minimal backend - ONLY upload endpoint for testing
"""
import os, asyncio, time
from pathlib import Path
from aiohttp import web
import aiohttp_cors

HOST = "0.0.0.0"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = (BASE_DIR / "uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)

async def healthz(_):
    return web.json_response({"ok": True, "ts": time.time()})

async def upload(request: web.Request):
    try:
        reader = await request.multipart()
        part = await reader.next()
        if part is None or part.name != "file":
            return web.json_response({"error": "missing file field"}, status=400)

        filename = safe_name(part.filename or f"file-{int(time.time()*1000)}.wav")
        key = f"{int(time.time()*1000)}-{filename}"
        dest = (UPLOAD_DIR / key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with dest.open("wb") as f:
            while True:
                chunk = await part.read_chunk()
                if not chunk:
                    break
                f.write(chunk)

        print(f"✅ File uploaded: {key}")

        return web.json_response({
            "success": True,
            "key": key,
            "file_id": key,
            "waveform": {
                "sr": 44100,
                "peaks": [0.5] * 100,
                "key": key,
                "duration": 30.0
            },
            "message": "File uploaded successfully"
        })
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def waveform(request: web.Request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "missing key"}, status=400)
    
    return web.json_response({
        "sr": 44100,
        "peaks": [0.5] * 100,
        "key": key,
        "duration": 30.0
    })

def make_app():
    app = web.Application()
    app.add_routes([
        web.get("/healthz", healthz),
        web.post("/api/upload", upload),
        web.get("/waveform", waveform),
    ])

    # CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_headers="*",
            allow_methods="*",
            expose_headers="*",
            allow_credentials=False,
        )
    })
    for route in list(app.router.routes()):
        try:
            cors.add(route)
        except Exception:
            pass
    
    return app

async def main():
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    print(f"✅ Minimal backend running on http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bye!")
