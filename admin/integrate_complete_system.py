"""
Integration Script for DrumTracKAI Complete System
Integrates the complete system with the existing batch processor
"""

import logging
import sys
import os

# Add admin directory to path
admin_dir = os.path.dirname(os.path.abspath(__file__))
if admin_dir not in sys.path:
    sys.path.insert(0, admin_dir)

logger = logging.getLogger(__name__)

def integrate_complete_system_with_batch_processor():
    """Integrate complete system with existing batch processor"""
    try:
        # Import the integration module
        from services.batch_processor_complete_integration import add_complete_system_integration
        
        # This function will be called by the main window during initialization
        # to add complete system integration to the batch processor widget
        
        logger.info("Complete system integration module loaded successfully")
        return add_complete_system_integration
        
    except ImportError as e:
        logger.error(f"Failed to import complete system integration: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading complete system integration: {e}")
        return None

def initialize_complete_system_services():
    """Initialize all complete system services"""
    try:
        # Initialize the batch complete integration service
        from services.batch_complete_integration import initialize_batch_complete_integration
        
        success = initialize_batch_complete_integration()
        if success:
            logger.info("Batch complete integration service initialized")
        else:
            logger.error("Failed to initialize batch complete integration service")
            
        return success
        
    except ImportError as e:
        logger.warning(f"Complete system services not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Error initializing complete system services: {e}")
        return False

def setup_complete_system_integration(main_window):
    """Setup complete system integration in the main window"""
    try:
        # Initialize services first
        services_initialized = initialize_complete_system_services()
        
        # Get the integration function
        integration_function = integrate_complete_system_with_batch_processor()
        
        if not integration_function:
            logger.warning("Complete system integration not available")
            return False
        
        # Find the batch processor widget
        batch_processor_widget = None
        
        # Method 1: Try to find by object name
        batch_processor_widget = main_window.findChild(object, "batch_processor_widget")
        
        # Method 2: Try to find through tab widget
        if not batch_processor_widget:
            from PySide6.QtWidgets import QTabWidget
            tab_widget = main_window.findChild(QTabWidget)
            if tab_widget:
                for i in range(tab_widget.count()):
                    tab = tab_widget.widget(i)
                    if "batch" in tab_widget.tabText(i).lower() or \
                       "BatchProcessor" in tab.__class__.__name__:
                        batch_processor_widget = tab
                        break
        
        if not batch_processor_widget:
            logger.error("Could not find batch processor widget")
            return False
        
        # Apply the integration
        success = integration_function(batch_processor_widget)
        
        if success:
            logger.info("Successfully integrated complete system with batch processor")
            
            # Store reference in main window for later access
            main_window.complete_system_integration = True
            
            return True
        else:
            logger.error("Failed to integrate complete system with batch processor")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up complete system integration: {e}")
        return False

if __name__ == "__main__":
    # Test the integration
    logging.basicConfig(level=logging.INFO)
    
    print("Testing DrumTracKAI Complete System Integration...")
    
    # Test service initialization
    services_ok = initialize_complete_system_services()
    print(f"Services initialization: {'OK' if services_ok else 'FAILED'}")
    
    # Test integration function loading
    integration_func = integrate_complete_system_with_batch_processor()
    print(f"Integration function loading: {'OK' if integration_func else 'FAILED'}")
    
    print("Integration test complete.")
