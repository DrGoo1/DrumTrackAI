#!/usr/bin/env python3
"""
DrumTracKAI v1.1.16 Clean Build Creator
Creates a minimal installation with only DCSM module, landing page, and admin connection.
"""

import os
import shutil
import json
from pathlib import Path

def create_clean_v1116():
    """Create clean v1.1.16 build with only essential components"""
    
    source_dir = Path("f:\\DrumTracKAI_v1.1.11")
    target_dir = Path("f:\\DrumTracKAI_v1.1.16_Clean")
    
    print("🎯 Creating DrumTracKAI v1.1.16 Clean Build")
    print("=" * 50)
    
    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Essential files and directories to copy
    essential_components = {
        # Core DCSM Backend
        "drumtrackai_api_server_clean.py": "dcsm_backend.py",
        
        # Rust Audio-Core (complete)
        "audio-core/": "audio-core/",
        
        # Clean Frontend (DCSM only)
        "web-frontend/src/components/": "frontend/src/components/",
        "web-frontend/src/services/": "frontend/src/services/",
        "web-frontend/src/audio/": "frontend/src/audio/",
        "web-frontend/src/pages/BenchPage.tsx": "frontend/src/pages/BenchPage.tsx",
        "web-frontend/src/App.tsx": "frontend/src/App.tsx",
        "web-frontend/src/index.tsx": "frontend/src/index.tsx",
        "web-frontend/src/index.css": "frontend/src/index.css",
        "web-frontend/src/App.css": "frontend/src/App.css",
        "web-frontend/public/": "frontend/public/",
        "web-frontend/package.json": "frontend/package.json",
        "web-frontend/tailwind.config.js": "frontend/tailwind.config.js",
        "web-frontend/tsconfig.json": "frontend/tsconfig.json",
        "web-frontend/.gitignore": "frontend/.gitignore",
        "web-frontend/netlify.toml": "frontend/netlify.toml",
        
        # Admin Module (essential only)
        "admin/main.py": "admin/main.py",
        "admin/core/": "admin/core/",
        "admin/ui/": "admin/ui/",
        
        # Environment and Configuration
        "drumtrackai_env/": "drumtrackai_env/",
        ".env.template": ".env.template",
        "Cargo.toml": "Cargo.toml",
        
        # Documentation
        "README_V1116_COMPLETE.md": "README.md",
        
        # Build Scripts
        "build_rust_python.bat": "build_rust_python.bat",
        "deploy_dcsm_local.bat": "deploy.bat",
        "test_v1116_workflow.py": "test_workflow.py",
    }
    
    # Copy essential components
    copied_items = []
    for source_item, target_item in essential_components.items():
        source_path = source_dir / source_item
        target_path = target_dir / target_item
        
        if source_path.exists():
            try:
                if source_path.is_dir():
                    print(f"📁 Copying directory: {source_item} → {target_item}")
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    shutil.copytree(source_path, target_path, ignore=shutil.ignore_patterns(
                        '*.pyc', '__pycache__', 'node_modules', 'target/debug', '.git', '*.log'
                    ))
                else:
                    print(f"📄 Copying file: {source_item} → {target_item}")
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
                
                copied_items.append(target_item)
            except Exception as e:
                print(f"⚠️  Failed to copy {source_item}: {e}")
        else:
            print(f"⚠️  Source not found: {source_item}")
    
    # Create clean package.json for frontend
    clean_package_json = {
        "name": "drumtrackai-dcsm",
        "version": "1.1.16",
        "description": "DrumTracKAI DCSM - Clean Build",
        "main": "index.js",
        "scripts": {
            "start": "react-scripts start",
            "build": "react-scripts build",
            "test": "react-scripts test",
            "eject": "react-scripts eject"
        },
        "dependencies": {
            "@tonejs/midi": "^2.0.28",
            "axios": "^1.6.0",
            "lucide-react": "^0.294.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "react-router-dom": "^6.8.0",
            "react-scripts": "^5.0.1",
            "tone": "^15.1.22"
        },
        "devDependencies": {
            "@types/react": "^19.1.9",
            "@types/react-dom": "^19.1.7",
            "autoprefixer": "^10.4.16",
            "postcss": "^8.4.31",
            "tailwindcss": "^3.3.0",
            "typescript": "^5.4.5"
        },
        "browserslist": {
            "production": [">0.2%", "last 1 versions", "not dead", "not op_mini all"],
            "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
        }
    }
    
    # Write clean package.json
    with open(target_dir / "frontend/package.json", 'w') as f:
        json.dump(clean_package_json, f, indent=2)
    
    # Create clean requirements.txt
    clean_requirements = """# DrumTracKAI v1.1.16 Clean Build - Essential Dependencies
aiohttp==3.9.1
aiohttp-cors==0.7.0
numpy==1.24.3
librosa==0.10.1
scipy==1.10.1
soundfile==0.12.1
fastapi==0.104.1
uvicorn==0.24.0
PySide6==6.6.1
"""
    
    with open(target_dir / "requirements.txt", 'w') as f:
        f.write(clean_requirements)
    
    # Create clean startup script
    startup_script = """@echo off
echo 🎯 DrumTracKAI v1.1.16 Clean Build Startup
echo ==========================================

:: Set environment variables
set USE_RUST=1
set AUDIO_CORE_MODE=auto
set AUDIO_CORE_BIN=%CD%\\audio-core\\target\\release\\audio-core.exe

:: Build Rust audio-core if needed
if not exist "audio-core\\target\\release\\audio-core.exe" (
    echo Building Rust audio-core...
    cd audio-core
    cargo build --release
    cd ..
)

:: Start backend
echo Starting DCSM Backend...
start "DCSM Backend" cmd /k "drumtrackai_env\\Scripts\\python.exe dcsm_backend.py"

:: Wait for backend
timeout /t 3 /nobreak >nul

:: Start frontend
echo Starting DCSM Frontend...
cd frontend
start "DCSM Frontend" cmd /k "npm start"

echo.
echo ✅ DrumTracKAI v1.1.16 Clean Build Started
echo 🌐 DCSM Studio: http://localhost:3000
echo 🔧 Backend API: http://localhost:8000
echo 📊 Benchmarks: http://localhost:3000/bench
"""
    
    with open(target_dir / "start_dcsm.bat", 'w') as f:
        f.write(startup_script)
    
    # Create project structure documentation
    structure_doc = f"""# DrumTracKAI v1.1.16 Clean Build Structure

## 🎯 Minimal DCSM-Only Installation

This is a clean, minimal installation containing only:
- **DCSM Backend** - Core drum composition and analysis
- **DCSM Frontend** - Professional web interface
- **Admin Connection** - Integration with admin module
- **Rust Audio-Core** - High-performance processing

## 📁 Directory Structure

```
DrumTracKAI_v1.1.16_Clean/
├── dcsm_backend.py              # DCSM API server
├── audio-core/                  # Rust audio processing
├── frontend/                    # React DCSM interface
├── admin/                       # Admin module connection
├── drumtrackai_env/            # Python environment
├── start_dcsm.bat              # One-click startup
├── requirements.txt            # Python dependencies
└── README.md                   # Documentation
```

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install
   ```

2. **Start System**:
   ```bash
   start_dcsm.bat
   ```

3. **Access DCSM**:
   - DCSM Studio: http://localhost:3000
   - Backend API: http://localhost:8000
   - Benchmarks: http://localhost:3000/bench

## ✨ Features Included

- Advanced Groove Engine with swing presets
- Multi-bar Fill Library with style awareness
- Smart Sectionization with musical arrangement detection
- Type-1 Multi-track MIDI export
- Performance Benchmarking Suite
- Professional mixer and piano roll
- Admin module integration

## 🧹 What's Removed

- Legacy code and unused components
- Development artifacts and test files
- Redundant documentation and scripts
- Unused dependencies and packages

Built: {Path.cwd()}
Items Copied: {len(copied_items)}
"""
    
    with open(target_dir / "PROJECT_STRUCTURE.md", 'w') as f:
        f.write(structure_doc)
    
    print("\n" + "=" * 50)
    print("✅ DrumTracKAI v1.1.16 Clean Build Complete!")
    print("=" * 50)
    print(f"📁 Location: {target_dir}")
    print(f"📦 Components: {len(copied_items)} items")
    print(f"🎯 Features: DCSM + Landing + Admin")
    print(f"🧹 Cleaned: Removed all legacy code")
    
    print("\n🚀 Next Steps:")
    print("1. cd f:/DrumTracKAI_v1.1.16_Clean")
    print("2. pip install -r requirements.txt")
    print("3. cd frontend && npm install")
    print("4. start_dcsm.bat")
    
    return True

if __name__ == "__main__":
    create_clean_v1116()
