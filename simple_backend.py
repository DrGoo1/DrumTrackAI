#!/usr/bin/env python3
"""
Simple DCSM Backend Server for v1.1.16
"""

import os
import json
from pathlib import Path
from aiohttp import web
import aiohttp_cors

# Configuration
HOST = "0.0.0.0"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

print(f"Starting DCSM Backend on {HOST}:{PORT}")
print(f"Upload directory: {UPLOAD_DIR}")

async def handle_root(request):
    return web.json_response({"status": "DCSM Backend v1.1.16 Running", "endpoints": [
        "/upload", "/dcsm/sectionize", "/analyze/tempo", "/analyze/onsets"
    ]})

async def handle_upload(request):
    try:
        reader = await request.multipart()
        field = await reader.next()
        
        if field.name == 'file':
            filename = field.filename or 'uploaded_audio'
            filepath = UPLOAD_DIR / filename
            
            with open(filepath, 'wb') as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)
            
            # Generate mock waveform data
            waveform = [0.1 * i % 1.0 for i in range(1000)]
            
            return web.json_response({
                "key": str(filepath.name),
                "filename": filename,
                "waveform": waveform,
                "peaks": waveform,
                "status": "uploaded"
            })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_sectionize(request):
    key = request.query.get("key", "")
    bpm = float(request.query.get("bpm", "120"))
    
    # Mock sectionization data
    sections = [
        {"start": 0.0, "end": 30.0, "label": "intro", "confidence": 0.85},
        {"start": 30.0, "end": 90.0, "label": "verse", "confidence": 0.92},
        {"start": 90.0, "end": 150.0, "label": "chorus", "confidence": 0.88},
        {"start": 150.0, "end": 210.0, "label": "verse", "confidence": 0.90},
        {"start": 210.0, "end": 270.0, "label": "chorus", "confidence": 0.87},
        {"start": 270.0, "end": 300.0, "label": "outro", "confidence": 0.83}
    ]
    
    return web.json_response({
        "sections": sections,
        "bpm": bpm,
        "key": key,
        "status": "analyzed"
    })

async def handle_tempo(request):
    key = request.query.get("key", "")
    return web.json_response({
        "tempo": 120.0,
        "beats": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        "confidence": 0.95,
        "key": key
    })

async def handle_onsets(request):
    key = request.query.get("key", "")
    return web.json_response({
        "onsets": [0.1, 0.6, 1.1, 1.6, 2.1, 2.6],
        "strength": [0.8, 0.9, 0.7, 0.85, 0.75, 0.82],
        "key": key
    })

def create_app():
    app = web.Application()
    
    # Add CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Routes
    app.router.add_get('/', handle_root)
    app.router.add_post('/upload', handle_upload)
    app.router.add_get('/dcsm/sectionize', handle_sectionize)
    app.router.add_get('/analyze/tempo', handle_tempo)
    app.router.add_get('/analyze/onsets', handle_onsets)
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host=HOST, port=PORT)
