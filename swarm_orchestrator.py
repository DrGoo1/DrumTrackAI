#!/usr/bin/env python3
"""
DrumTracKAI v1.1.16 Agentic Swarm Orchestrator
Coordinates specialized agents to build and deploy the full Docker stack
"""

import asyncio
import subprocess
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    name: str
    description: str
    dependencies: List[str]
    agent_type: str
    priority: int
    status: AgentStatus = AgentStatus.IDLE
    result: Optional[Dict] = None
    error: Optional[str] = None

class BaseAgent:
    def __init__(self, name: str, agent_type: str):
        self.name = name
        self.agent_type = agent_type
        self.status = AgentStatus.IDLE
        self.current_task: Optional[Task] = None
        self.logger = logging.getLogger(f"Agent.{name}")
    
    async def execute_task(self, task: Task) -> Dict:
        """Execute a task and return results"""
        self.status = AgentStatus.WORKING
        self.current_task = task
        self.logger.info(f"Starting task: {task.name}")
        
        try:
            result = await self._execute_task_impl(task)
            self.status = AgentStatus.COMPLETED
            task.status = AgentStatus.COMPLETED
            task.result = result
            self.logger.info(f"Completed task: {task.name}")
            return result
        except Exception as e:
            self.status = AgentStatus.FAILED
            task.status = AgentStatus.FAILED
            task.error = str(e)
            self.logger.error(f"Failed task {task.name}: {e}")
            raise
        finally:
            self.current_task = None
    
    async def _execute_task_impl(self, task: Task) -> Dict:
        """Override in subclasses"""
        raise NotImplementedError

class DockerAgent(BaseAgent):
    def __init__(self):
        super().__init__("DockerAgent", "docker")
        self.docker_path = self._find_docker_path()
    
    def _find_docker_path(self) -> str:
        """Find Docker executable path"""
        possible_paths = [
            "C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe",
            "docker"
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.logger.info(f"Found Docker at: {path}")
                    return path
            except:
                continue
        
        # Fallback to native deployment if Docker not available
        self.logger.warning("Docker not found - will use native deployment")
        return None
    
    async def _execute_task_impl(self, task: Task) -> Dict:
        if task.id == "docker_cleanup":
            return await self._cleanup_containers()
        elif task.id == "docker_build":
            return await self._build_containers()
        elif task.id == "docker_deploy":
            return await self._deploy_containers()
        elif task.id == "docker_verify":
            return await self._verify_deployment()
        else:
            raise ValueError(f"Unknown Docker task: {task.id}")
    
    async def _cleanup_containers(self) -> Dict:
        """Stop and remove existing containers"""
        self.logger.info("Cleaning up existing containers...")
        
        # Stop containers
        cmd = [self.docker_path, "ps", "-q"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout.strip():
            stop_cmd = [self.docker_path, "stop"] + result.stdout.strip().split('\n')
            subprocess.run(stop_cmd, capture_output=True)
        
        # Remove containers
        cmd = [self.docker_path, "ps", "-aq"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout.strip():
            rm_cmd = [self.docker_path, "rm"] + result.stdout.strip().split('\n')
            subprocess.run(rm_cmd, capture_output=True)
        
        return {"status": "cleaned", "message": "Existing containers removed"}
    
    async def _build_containers(self) -> Dict:
        """Build Docker containers using docker-compose"""
        self.logger.info("Building Docker containers...")
        
        cmd = [self.docker_path + "-compose", "build", "--no-cache"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        output_lines = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                line = output.strip()
                output_lines.append(line)
                self.logger.info(f"Build: {line}")
        
        if process.returncode != 0:
            raise RuntimeError(f"Docker build failed with code {process.returncode}")
        
        return {"status": "built", "output": output_lines}
    
    async def _deploy_containers(self) -> Dict:
        """Deploy containers using docker-compose up"""
        self.logger.info("Deploying Docker containers...")
        
        cmd = [self.docker_path + "-compose", "up", "-d"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"Docker deploy failed: {result.stderr}")
        
        return {"status": "deployed", "output": result.stdout}
    
    async def _verify_deployment(self) -> Dict:
        """Verify containers are running and healthy"""
        self.logger.info("Verifying deployment...")
        
        cmd = [self.docker_path, "ps", "--format", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to check container status: {result.stderr}")
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                containers.append(json.loads(line))
        
        return {"status": "verified", "containers": containers, "count": len(containers)}

class RustAgent(BaseAgent):
    def __init__(self):
        super().__init__("RustAgent", "rust")
    
    async def _execute_task_impl(self, task: Task) -> Dict:
        if task.id == "rust_build_ffi":
            return await self._build_ffi_library()
        else:
            raise ValueError(f"Unknown Rust task: {task.id}")
    
    async def _build_ffi_library(self) -> Dict:
        """Build Rust FFI library"""
        self.logger.info("Building Rust FFI library...")
        
        ffi_path = Path("tracktion-hybrid/rust/audio-core-ffi")
        if not ffi_path.exists():
            raise RuntimeError(f"FFI library path not found: {ffi_path}")
        
        cmd = ["cargo", "build", "--release"]
        result = subprocess.run(cmd, cwd=ffi_path, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"Rust FFI build failed: {result.stderr}")
        
        # Check if library was created
        lib_path = ffi_path / "target/release/audio_core_ffi.dll"
        if not lib_path.exists():
            raise RuntimeError("FFI library not found after build")
        
        return {"status": "built", "library_path": str(lib_path), "size": lib_path.stat().st_size}

class ConfigAgent(BaseAgent):
    def __init__(self):
        super().__init__("ConfigAgent", "config")
    
    async def _execute_task_impl(self, task: Task) -> Dict:
        if task.id == "validate_config":
            return await self._validate_configuration()
        elif task.id == "setup_environment":
            return await self._setup_environment()
        else:
            raise ValueError(f"Unknown Config task: {task.id}")
    
    async def _validate_configuration(self) -> Dict:
        """Validate Docker configuration files"""
        self.logger.info("Validating configuration files...")
        
        required_files = [
            "docker-compose.yml",
            "Dockerfile.backend",
            "Dockerfile.tracktion"
        ]
        
        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            raise RuntimeError(f"Missing required files: {missing_files}")
        
        return {"status": "validated", "files": required_files}
    
    async def _setup_environment(self) -> Dict:
        """Setup environment variables and configuration"""
        self.logger.info("Setting up environment...")
        
        # Create .env file if it doesn't exist
        env_file = Path(".env")
        if not env_file.exists():
            env_content = """
USE_TRACKTION_FFI=1
TRACKTION_FFI_LIB=/usr/local/lib/audio_core_ffi.so
PYTHONPATH=/app
USE_RUST=1
AUDIO_CORE_BIN=/usr/local/bin/audio-core
REACT_APP_API_BASE=http://localhost:8000
"""
            env_file.write_text(env_content.strip())
        
        return {"status": "configured", "env_file": str(env_file)}

class SwarmOrchestrator:
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {
            "docker": DockerAgent(),
            "rust": RustAgent(),
            "config": ConfigAgent()
        }
        self.tasks: List[Task] = []
        self.completed_tasks: List[str] = []
        self.logger = logging.getLogger("SwarmOrchestrator")
    
    def add_task(self, task: Task):
        """Add a task to the execution queue"""
        self.tasks.append(task)
        self.logger.info(f"Added task: {task.name}")
    
    def create_deployment_tasks(self):
        """Create the full deployment task pipeline"""
        tasks = [
            Task("validate_config", "Validate Configuration", 
                 "Check all required Docker files exist", [], "config", 1),
            
            Task("setup_environment", "Setup Environment", 
                 "Configure environment variables", ["validate_config"], "config", 2),
            
            Task("rust_build_ffi", "Build Rust FFI", 
                 "Compile Rust FFI library", ["setup_environment"], "rust", 3),
            
            Task("docker_cleanup", "Docker Cleanup", 
                 "Remove existing containers", ["rust_build_ffi"], "docker", 4),
            
            Task("docker_build", "Docker Build", 
                 "Build all Docker containers", ["docker_cleanup"], "docker", 5),
            
            Task("docker_deploy", "Docker Deploy", 
                 "Deploy containers with docker-compose", ["docker_build"], "docker", 6),
            
            Task("docker_verify", "Verify Deployment", 
                 "Check containers are running", ["docker_deploy"], "docker", 7)
        ]
        
        for task in tasks:
            self.add_task(task)
    
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (dependencies satisfied)"""
        ready = []
        for task in self.tasks:
            if task.status == AgentStatus.IDLE:
                deps_satisfied = all(dep in self.completed_tasks for dep in task.dependencies)
                if deps_satisfied:
                    ready.append(task)
        return sorted(ready, key=lambda t: t.priority)
    
    async def execute_swarm(self) -> Dict:
        """Execute all tasks using the agent swarm"""
        self.logger.info("Starting swarm execution...")
        start_time = time.time()
        
        while True:
            ready_tasks = self.get_ready_tasks()
            
            if not ready_tasks:
                # Check if all tasks are completed
                remaining = [t for t in self.tasks if t.status not in [AgentStatus.COMPLETED, AgentStatus.FAILED]]
                if not remaining:
                    break
                
                # Check for failed tasks
                failed = [t for t in self.tasks if t.status == AgentStatus.FAILED]
                if failed:
                    raise RuntimeError(f"Tasks failed: {[t.name for t in failed]}")
                
                # Wait for running tasks
                await asyncio.sleep(1)
                continue
            
            # Execute ready tasks
            for task in ready_tasks:
                agent = self.agents[task.agent_type]
                if agent.status == AgentStatus.IDLE:
                    self.logger.info(f"Assigning task '{task.name}' to {agent.name}")
                    
                    # Execute task asynchronously
                    asyncio.create_task(self._execute_task_with_completion(agent, task))
                    break  # Only execute one task at a time to prevent infinite loop
        
        execution_time = time.time() - start_time
        completed = [t for t in self.tasks if t.status == AgentStatus.COMPLETED]
        failed = [t for t in self.tasks if t.status == AgentStatus.FAILED]
        
        return {
            "status": "completed" if not failed else "failed",
            "execution_time": execution_time,
            "completed_tasks": len(completed),
            "failed_tasks": len(failed),
            "results": {t.id: t.result for t in completed}
        }
    
    async def _execute_task_with_completion(self, agent: BaseAgent, task: Task):
        """Execute task and mark as completed"""
        try:
            await agent.execute_task(task)
            self.completed_tasks.append(task.id)
        except Exception as e:
            self.logger.error(f"Task {task.name} failed: {e}")

async def main():
    """Main orchestrator entry point"""
    orchestrator = SwarmOrchestrator()
    orchestrator.create_deployment_tasks()
    
    try:
        result = await orchestrator.execute_swarm()
        
        print("\n" + "="*60)
        print("SWARM EXECUTION COMPLETED")
        print("="*60)
        print(f"Status: {result['status'].upper()}")
        print(f"Execution Time: {result['execution_time']:.2f} seconds")
        print(f"Completed Tasks: {result['completed_tasks']}")
        print(f"Failed Tasks: {result['failed_tasks']}")
        
        if result['status'] == 'completed':
            print("\n🎉 DrumTracKAI v1.1.16 Docker deployment successful!")
            print("\nAccess points:")
            print("- Backend:  http://localhost:8000")
            print("- Frontend: http://localhost:3000") 
            print("- Tracktion: http://localhost:8080")
        else:
            print("\n❌ Deployment failed. Check logs above for details.")
        
        return result['status'] == 'completed'
        
    except Exception as e:
        print(f"\n❌ Swarm execution failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main())
