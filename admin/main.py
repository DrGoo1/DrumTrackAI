#!/usr/bin/env python3
"""
DrumTracKAI Admin Application Entry Point
=========================================
Main entry point for the DrumTracKAI Admin application.
Handles initialization, GPU setup, and launches the main window.
"""
import os
import sys
import logging
import traceback
from pathlib import Path

# Add the parent directory to Python path for imports
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))  # Add the parent directory so 'admin' is importable

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('drumtrackai_admin.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup environment variables for GPU support and application configuration"""
    logger.info("Setting up environment variables...")
    
    # CUDA environment variables for GPU support
    cuda_env = {
        "CUDA_PATH": r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8",
        "CUDA_HOME": r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8",
        "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
        "CUDA_VISIBLE_DEVICES": "0",
        "TORCH_CUDNN_V8_API_ENABLED": "1",
        "TF_FORCE_GPU_ALLOW_GROWTH": "true"
    }
    
    # LLVM environment variables for arrangement analysis (prevents LLVM runtime errors)
    llvm_env = {
        "NUMBA_DISABLE_INTEL_SVML": "1",  # Disable Intel Short Vector Math Library
        "OMP_NUM_THREADS": "1",           # Limit OpenMP threading
        "NUMBA_DISABLE_JIT": "0",         # Keep JIT enabled but safe
        "NUMBA_THREADING_LAYER": "safe"   # Use safe threading layer
    }
    
    # DrumTracKAI specific variables
    app_env = {
        "DRUMTRACKAI_FORCE_GPU": "1",
        "MVSEP_DEBUG": "1",
        "DRUMTRACKAI_LOG_LEVEL": "INFO"
    }
    
    # Apply environment variables
    for key, value in {**cuda_env, **llvm_env, **app_env}.items():
        if key not in os.environ:
            os.environ[key] = value
            logger.debug(f"Set {key}={value}")
    
    # Log LLVM configuration for arrangement analysis
    logger.info("LLVM environment configured for arrangement analysis:")
    logger.info(f"  NUMBA_DISABLE_INTEL_SVML: {os.environ.get('NUMBA_DISABLE_INTEL_SVML', 'not set')}")
    logger.info(f"  OMP_NUM_THREADS: {os.environ.get('OMP_NUM_THREADS', 'not set')}")
    
    # Load .env file if it exists
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        logger.info(f"Loading environment from {env_file}")
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
                        if "API_KEY" in key:
                            logger.info(f"Loaded {key}: {value[:5]}...")
                        else:
                            logger.debug(f"Loaded {key}={value}")
        except Exception as e:
            logger.warning(f"Error loading .env file: {e}")
    
    logger.info("Environment setup complete")

def check_gpu_availability():
    """Check if GPU and CUDA are available"""
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU available: {device_name}")
            return True
        else:
            logger.warning("CUDA is not available. Some features may be limited.")
            return False
    except ImportError:
        logger.warning("PyTorch not available. GPU features will be disabled.")
        return False

def check_dependencies():
    """Check if required dependencies are available"""
    required_modules = [
        ('PySide6', 'PySide6.QtWidgets'),
        ('pathlib', 'pathlib'),
        ('json', 'json'),
        ('logging', 'logging')
    ]
    
    missing_modules = []
    
    for module_name, import_path in required_modules:
        try:
            __import__(import_path)
            logger.debug(f" {module_name} available")
        except ImportError:
            missing_modules.append(module_name)
            logger.error(f" {module_name} not available")
    
    if missing_modules:
        logger.error(f"Missing required modules: {', '.join(missing_modules)}")
        return False
    
    logger.info("All required dependencies are available")
    return True

def create_application():
    """Create and configure the QApplication"""
    try:
        logger.debug("Importing PySide6 components for QApplication creation")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QIcon
        
        # Create application
        logger.debug("Creating QApplication instance")
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            logger.debug("New QApplication instance created")
        else:
            logger.debug("Using existing QApplication instance")
        
        # Set application properties
        logger.debug("Setting application properties")
        try:
            app.setApplicationName("DrumTracKAI Admin")
            app.setApplicationVersion("1.1.6")
            app.setOrganizationName("DrumTracKAI")
            app.setOrganizationDomain("drumtrackai.com")
            logger.debug("Application properties set successfully")
        except Exception as prop_error:
            logger.warning(f"Error setting application properties: {prop_error}")
            # Continue despite property errors
        
        # Set application icon if available
        try:
            icon_path = Path(__file__).parent / "resources" / "icon.png"
            if icon_path.exists():
                app.setWindowIcon(QIcon(str(icon_path)))
                logger.debug(f"Set application icon from {icon_path}")
            else:
                logger.debug(f"Icon not found at {icon_path}")
        except Exception as icon_error:
            logger.warning(f"Error setting application icon: {icon_error}")
            # Continue despite icon errors
        
        # Enable high DPI scaling
        try:
            logger.debug("Setting up High DPI scaling")
            # These attributes are deprecated but still functional
            app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
            logger.debug("High DPI scaling enabled")
        except Exception as dpi_error:
            logger.warning(f"Error enabling High DPI scaling: {dpi_error}")
            # Continue despite DPI errors
        
        logger.info("QApplication created successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create QApplication: {e}")
        logger.error(traceback.format_exc())
        return None

def create_main_window():
    """Create and configure the main window"""
    try:
        logger.info("Attempting to import MainWindow and ApplicationStateManager...")
        # Import after environment setup
        try:
            from admin.ui.main_window import MainWindow
            logger.info("MainWindow import successful")
        except ImportError as e:
            logger.error(f"Failed to import MainWindow: {e}")
            logger.error(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"Unexpected error importing MainWindow: {e}")
            logger.error(traceback.format_exc())
            raise
            
        try:
            from admin.core.application_state import ApplicationStateManager
            logger.info("ApplicationStateManager import successful")
        except ImportError as e:
            logger.critical(f"Failed to import ApplicationStateManager: {e}")
            logger.critical(traceback.format_exc())
            return None
            
        # Create state manager
        logger.info("Creating ApplicationStateManager...")
        try:
            state_manager = ApplicationStateManager()
            logger.info("ApplicationStateManager created successfully")
        except Exception as e:
            logger.critical(f"Failed to create ApplicationStateManager: {e}")
            logger.critical(traceback.format_exc())
            return None
        
        # Create main window
        logger.info("Creating MainWindow instance...")
        try:
            main_window = MainWindow(state_manager=state_manager)
            logger.info("MainWindow instance created successfully")
        except Exception as e:
            logger.critical(f"Failed to create MainWindow instance: {e}")
            logger.critical(traceback.format_exc())
            return None
        
        # Verify main window was created properly
        if main_window is None:
            logger.critical("MainWindow constructor returned None")
            return None
            
        logger.info("MainWindow creation complete")
        return main_window
        
    except ImportError as e:
        logger.error(f"Import error creating main window: {e}")
        logger.error(traceback.format_exc())
        return None
        logger.error("This usually indicates missing or broken widget files")
        
        # Try to create a minimal fallback window
        try:
            from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
            
            class FallbackWindow(QMainWindow):
                def __init__(self):
                    super().__init__()
                    self.setWindowTitle("DrumTracKAI Admin - Error")
                    self.resize(800, 600)
                    
                    central_widget = QWidget()
                    layout = QVBoxLayout(central_widget)
                    
                    error_label = QLabel(
                        "WARNING Application Error\n\n"
                        "The main application components could not be loaded.\n"
                        "Please check the logs for more details.\n\n"
                        f"Error: {str(e)}"
                    )
                    error_label.setWordWrap(True)
                    error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
                    
                    layout.addWidget(error_label)
                    self.setCentralWidget(central_widget)
            
            logger.warning("Creating fallback window due to import errors")
            return FallbackWindow()
            
        except Exception as fallback_error:
            logger.error(f"Even fallback window creation failed: {fallback_error}")
            return None
    
    except Exception as e:
        logger.error(f"Unexpected error creating main window: {e}")
        logger.error(traceback.format_exc())
        return None

def main():
    """Main application entry point"""
    logger.info("=" * 60)
    logger.info("DrumTracKAI Admin Application Starting")
    logger.info("=" * 60)
    
    try:
        # Step 1: Setup environment
        logger.info("STEP 1: Setting up environment variables")
        setup_environment()
        
        # Step 2: Check dependencies
        logger.info("STEP 2: Checking dependencies")
        if not check_dependencies():
            logger.error("Dependency check failed. Cannot continue.")
            return 1
        
        # Step 3: Check GPU availability (optional)
        logger.info("STEP 3: Checking GPU availability")
        gpu_available = check_gpu_availability()
        if gpu_available:
            logger.info("GPU acceleration will be available for supported features")
        else:
            logger.warning("GPU acceleration not available. Some features may be slower.")
        
        # Step 4: Create QApplication
        logger.info("STEP 4: Creating QApplication")
        app = create_application()
        if app is None:
            logger.error("Failed to create QApplication. Cannot continue.")
            return 1
        
        # Step 5: Create main window
        logger.info("STEP 5: Creating main window")
        main_window = create_main_window()
        if main_window is None:
            logger.error("Failed to create main window. Cannot continue.")
            return 1
        
        # Step 6: Show main window
        logger.info("STEP 6: Showing main window")
        try:
            main_window.show()
            logger.info("Main window displayed successfully")
        except Exception as e:
            logger.error(f"Failed to show main window: {e}")
            logger.error(traceback.format_exc())
            return 1
        
        # Step 7: Setup signal handlers for graceful shutdown
        import signal
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            if hasattr(main_window, 'state_manager'):
                main_window.state_manager.initiate_shutdown()
            app.quit()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Step 8: Run the application
        logger.info("Starting application event loop...")
        exit_code = app.exec()
        
        logger.info(f"Application finished with exit code: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        logger.error(traceback.format_exc())
        return 1
    finally:
        logger.info("DrumTracKAI Admin Application Shutdown Complete")

if __name__ == "__main__":
    sys.exit(main())
