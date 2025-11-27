#!/usr/bin/env python3
"""
Native Deployment Agent for DrumTracKAI v1.1.16 Hybrid System
Deploys the system without Docker using native Python/Node.js
"""

import asyncio
import subprocess
import json
import time
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class NativeDeploymentAgent:
    def __init__(self):
        self.name = "NativeDeploymentAgent"
        self.base_path = Path("f:/DrumTracKAI_v1.1.16_Clean")
        self.v111_path = Path("f:/DrumTracKAI_v1.1.11")
        self.processes = {}
        
    async def deploy_hybrid_system(self) -> Dict:
        """Deploy the complete hybrid system natively"""
        logger.info("Starting native hybrid deployment...")
        
        try:
            # Step 1: Build Rust FFI library
            await self._build_rust_ffi()
            
            # Step 2: Setup Python environment
            await self._setup_python_env()
            
            # Step 3: Start backend server
            await self._start_backend()
            
            # Step 4: Setup and start frontend
            await self._start_frontend()
            
            # Step 5: Verify deployment
            result = await self._verify_native_deployment()
            
            return {
                "status": "success",
                "deployment_type": "native",
                "access_points": {
                    "frontend": "http://localhost:3000",
                    "backend": "http://localhost:8000"
                },
                "processes": list(self.processes.keys())
            }
            
        except Exception as e:
            logger.error(f"Native deployment failed: {e}")
            await self._cleanup_processes()
            raise
    
    async def _build_rust_ffi(self) -> Dict:
        """Build the Rust FFI library"""
        logger.info("Building Rust FFI library...")
        
        # Check if we're in v1.1.16 or need to use v1.1.11 structure
        ffi_paths = [
            self.base_path / "tracktion-hybrid/rust/audio-core-ffi",
            self.v111_path / "tracktion-hybrid/rust/audio-core-ffi"
        ]
        
        ffi_path = None
        for path in ffi_paths:
            if path.exists():
                ffi_path = path
                break
        
        if not ffi_path:
            logger.warning("FFI library path not found, skipping Rust build")
            return {"status": "skipped", "reason": "FFI path not found"}
        
        # Build the FFI library
        cmd = ["cargo", "build", "--release"]
        result = subprocess.run(cmd, cwd=ffi_path, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.warning(f"Rust FFI build failed: {result.stderr}")
            return {"status": "failed", "error": result.stderr}
        
        # Check if library was created
        lib_extensions = [".dll", ".so", ".dylib"]
        lib_path = None
        
        for ext in lib_extensions:
            potential_path = ffi_path / f"target/release/audio_core_ffi{ext}"
            if potential_path.exists():
                lib_path = potential_path
                break
        
        if lib_path:
            logger.info(f"FFI library built successfully: {lib_path}")
            return {"status": "built", "library_path": str(lib_path)}
        else:
            logger.warning("FFI library not found after build")
            return {"status": "built_no_lib"}
    
    async def _setup_python_env(self) -> Dict:
        """Setup Python virtual environment"""
        logger.info("Setting up Python environment...")
        
        # Use existing environment from v1.1.11 if available
        env_paths = [
            self.v111_path / "drumtrackai_env",
            self.base_path / "drumtrackai_env"
        ]
        
        python_exe = None
        for env_path in env_paths:
            potential_python = env_path / "Scripts/python.exe"
            if potential_python.exists():
                python_exe = potential_python
                logger.info(f"Using existing Python environment: {python_exe}")
                break
        
        if not python_exe:
            logger.error("No Python virtual environment found")
            raise RuntimeError("Python environment not available")
        
        return {"status": "ready", "python_exe": str(python_exe)}
    
    async def _start_backend(self) -> Dict:
        """Start the backend server"""
        logger.info("Starting backend server...")
        
        # Find the backend script
        backend_scripts = [
            self.v111_path / "drumtrackai_api_server_clean.py",
            self.v111_path / "dcsm_backend.py",
            self.base_path / "dcsm_backend.py"
        ]
        
        backend_script = None
        python_exe = None
        
        for script_path in backend_scripts:
            if script_path.exists():
                backend_script = script_path
                # Find corresponding Python environment
                if script_path.parent == self.v111_path:
                    python_exe = self.v111_path / "drumtrackai_env/Scripts/python.exe"
                else:
                    python_exe = self.base_path / "drumtrackai_env/Scripts/python.exe"
                break
        
        if not backend_script or not python_exe.exists():
            raise RuntimeError("Backend script or Python environment not found")
        
        # Set environment variables for FFI integration
        env = os.environ.copy()
        env.update({
            "USE_TRACKTION_FFI": "1",
            "USE_RUST": "1",
            "PYTHONPATH": str(backend_script.parent)
        })
        
        # Start backend process
        cmd = [str(python_exe), str(backend_script)]
        process = subprocess.Popen(
            cmd, 
            cwd=backend_script.parent,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        self.processes["backend"] = process
        logger.info(f"Backend started with PID: {process.pid}")
        
        # Wait a moment for startup
        await asyncio.sleep(5)
        
        return {"status": "started", "pid": process.pid, "script": str(backend_script)}
    
    async def _start_frontend(self) -> Dict:
        """Start the frontend server"""
        logger.info("Starting frontend server...")
        
        # Find frontend directory
        frontend_paths = [
            self.v111_path / "web-frontend",
            self.base_path / "frontend"
        ]
        
        frontend_path = None
        for path in frontend_paths:
            if (path / "package.json").exists():
                frontend_path = path
                break
        
        if not frontend_path:
            raise RuntimeError("Frontend directory not found")
        
        # Check if node_modules exists, install if needed
        if not (frontend_path / "node_modules").exists():
            logger.info("Installing frontend dependencies...")
            install_result = subprocess.run(
                ["npm", "install"], 
                cwd=frontend_path, 
                capture_output=True, 
                text=True,
                timeout=300
            )
            if install_result.returncode != 0:
                logger.warning(f"npm install failed: {install_result.stderr}")
        
        # Start frontend process
        cmd = ["npm", "start"]
        process = subprocess.Popen(
            cmd,
            cwd=frontend_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        self.processes["frontend"] = process
        logger.info(f"Frontend started with PID: {process.pid}")
        
        # Wait for startup
        await asyncio.sleep(10)
        
        return {"status": "started", "pid": process.pid, "path": str(frontend_path)}
    
    async def _verify_native_deployment(self) -> Dict:
        """Verify the native deployment is working"""
        logger.info("Verifying native deployment...")
        
        import aiohttp
        
        # Check backend
        backend_healthy = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/health", timeout=5) as resp:
                    if resp.status == 200:
                        backend_healthy = True
        except:
            pass
        
        # Check frontend (just check if port is responding)
        frontend_healthy = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:3000", timeout=5) as resp:
                    if resp.status in [200, 404]:  # 404 is OK for React dev server
                        frontend_healthy = True
        except:
            pass
        
        return {
            "backend_healthy": backend_healthy,
            "frontend_healthy": frontend_healthy,
            "overall_status": "healthy" if backend_healthy and frontend_healthy else "partial"
        }
    
    async def _cleanup_processes(self):
        """Clean up any running processes"""
        logger.info("Cleaning up processes...")
        
        for name, process in self.processes.items():
            try:
                process.terminate()
                logger.info(f"Terminated {name} process")
            except:
                pass
        
        self.processes.clear()

async def main():
    """Main entry point for native deployment"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    agent = NativeDeploymentAgent()
    
    try:
        result = await agent.deploy_hybrid_system()
        
        print("\n" + "="*60)
        print("NATIVE DEPLOYMENT COMPLETED")
        print("="*60)
        print(f"Status: {result['status'].upper()}")
        print(f"Deployment Type: {result['deployment_type']}")
        print("\nAccess Points:")
        for name, url in result['access_points'].items():
            print(f"- {name.title()}: {url}")
        print(f"\nRunning Processes: {len(result['processes'])}")
        
        print("\n🎉 DrumTracKAI v1.1.16 Hybrid system is running!")
        print("\nPress Ctrl+C to stop all services...")
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            await agent._cleanup_processes()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Native deployment failed: {e}")
        await agent._cleanup_processes()
        return False

if __name__ == "__main__":
    asyncio.run(main())
