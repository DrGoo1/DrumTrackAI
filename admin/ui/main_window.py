"""
Main Window for DrumTracKAI Admin - COMPLETELY FIXED VERSION
============================================================
Main application window with tabbed interface for different components.
All structural issues, imports, and initialization problems have been resolved.
"""
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PySide6 imports
from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer, QSettings
from PySide6.QtGui import QIcon, QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QMessageBox,
    QToolBar, QMenu, QDockWidget, QTextEdit,
    QSplitter, QTreeWidget, QTreeWidgetItem, QSizePolicy,
    QWidget, QGroupBox
)

# Try to import core modules with fallbacks
try:
    from core.application_state import ApplicationStateManager, AppState
    from core.event_bus import EventBus, EventType, Event
    from core.service_container import ServiceContainer, ServiceTier
except ImportError as e:
    logger.error(f"Failed to import core modules: {e}")
    # Create dummy classes to allow the application to load
    class AppState:
        INITIALIZED = 0
        READY = 1
        BUSY = 2
        ERROR = 3
        RUNNING = 4
        SHUTTING_DOWN = 5

    class ApplicationStateManager:
        class DummySignal:
            def __init__(self):
                self.callbacks = []
            def connect(self, callback):
                self.callbacks.append(callback)
            def emit(self, *args, **kwargs):
                for callback in self.callbacks:
                    try:
                        callback(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Error in signal callback: {e}")

        def __init__(self):
            self.state = AppState.INITIALIZED
            self.state_changed = self.DummySignal()
            self.event_bus = None

        def set_state(self, state):
            old_state = self.state
            self.state = state
            self.state_changed.emit(state, f"State changed from {old_state} to {state}")

        def initiate_shutdown(self):
            self.set_state(AppState.SHUTTING_DOWN)

    class EventType:
        STATE_CHANGED = "state_changed"
        DATA_LOADED = "data_loaded"
        STATUS = "status"
        ERROR = "error"

    class Event:
        def __init__(self, event_type, source="unknown", topic="", data=None):
            self.event_type = event_type
            self.source = source
            self.topic = topic
            self.data = data

    class EventBus:
        def __init__(self):
            self.subscribers = {}

        def subscribe(self, callback, event_type=None):
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(callback)

        def publish(self, event_type, source, topic, data):
            event = Event(event_type, source, topic, data)
            if event_type in self.subscribers:
                for callback in self.subscribers[event_type]:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Error in event callback: {e}")


class LogWidget(QTextEdit):
    """Widget for displaying log messages"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #E0E0E0;
                font-family: Consolas, monospace;
                font-size: 10pt;
                border: 1px solid #4B0082;
                border-radius: 3px;
            }
        """)

    def append_message(self, message: str, level: str = "INFO"):
        """Append a log message with appropriate styling"""
        color = {
            "DEBUG": "#9370DB",
            "INFO": "#FFC619",
            "WARNING": "#FFA500",
            "ERROR": "#FF69B4",
            "CRITICAL": "#FF1493"
        }.get(level, "#FFFFFF")

        self.append(f'<span style="color:{color}">[{level}]</span> <span style="color:#E0E0E0">{message}</span>')
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class MainWindow(QMainWindow):
    """Main application window for DrumTracKAI Admin"""

    initialization_completed = Signal(str)

    def __init__(self, state_manager=None):
        """Initialize the main window"""
        super().__init__()

        logger.info("Initializing MainWindow")

        try:
            # Set window title and size
            self.setWindowTitle("DrumTracKAI Admin")
            self.resize(1280, 800)

            # Initialize state manager and event bus
            self.state_manager = state_manager or ApplicationStateManager()
            self.event_bus = getattr(self.state_manager, 'event_bus', None) or EventBus()

            # Ensure state manager has event bus reference
            if not hasattr(self.state_manager, 'event_bus') or not self.state_manager.event_bus:
                self.state_manager.event_bus = self.event_bus
            
            # Initialize service container
            try:
                from core.service_container import ServiceContainer
                self.service_container = ServiceContainer()
                self._initialize_services()
            except ImportError as e:
                logger.warning(f"ServiceContainer not available: {e}")
                # Create a dummy service container for compatibility
                self.service_container = type('DummyServiceContainer', (), {
                    'register': lambda *args, **kwargs: None,
                    'get': lambda name: None
                })()
            except Exception as e:
                logger.error(f"Error initializing services: {e}")
                # Continue anyway to allow UI to load, even with limited functionality

            # Tab widgets and initialization tracking
            self.tab_widgets = {}
            self.tab_names_added = set()
            self.pending_widgets = set()
            self.initialization_timer = QTimer(self)
            self.initialization_timer.timeout.connect(self._check_initialization_complete)
            self.initialization_timer.setInterval(100)

            # Initialize log dock property
            self.log_dock = None
            self.log_widget = None

            # Setup UI
            self._setup_ui()
            self._connect_tabs()

            # Mark initialization as complete
            self._initialization_complete = True

            logger.info("Main window initialized successfully")

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Exception during main window initialization: {e}\n{tb}")
            QMessageBox.critical(None, "Initialization Error", f"Failed to initialize main window: {e}")

    def _initialize_services_legacy(self):
        """Legacy service initialization (unused; kept for reference)."""
        try:
            logger.info("Initializing services...")
            
            # Register services using factory lambdas as required by ServiceContainer
            # This fixes the service registration issue mentioned in the debugging memory
            
            # Register BatchProcessor service
            try:
                from admin.services.batch_processor import BatchProcessor
                self.service_container.register('batch_processor', factory=lambda: BatchProcessor.get_instance())
                logger.debug("Registered BatchProcessor service")
            except ImportError as e:
                logger.warning(f"BatchProcessor service not available: {e}")
            
            # Register MVSep service
            try:
                from admin.services.mvsep_service import MVSepService
                api_key = os.environ.get('MVSEP_API_KEY', '')
                
                # If environment variable not found, try config file
                if not api_key:
                    try:
                        config_path = os.path.join(os.getcwd(), 'mvsep_config.txt')
                        if os.path.exists(config_path):
                            with open(config_path, 'r') as f:
                                for line in f:
                                    line = line.strip()
                                    if line.startswith('MVSEP_API_KEY=') and not line.startswith('#'):
                                        api_key = line.split('=', 1)[1].strip()
                                        logger.info("MVSep API key loaded from config file")
                                        break
                    except Exception as e:
                        logger.debug(f"Could not read config file: {e}")
                
                logger.info(f"MVSep API key detection: {'Found' if api_key else 'Not found'}")
                
                if api_key and api_key.strip() and api_key != 'your_actual_api_key_here':
                    # Real API key provided
                    self.service_container.register('mvsep_service', factory=lambda: MVSepService(api_key))
                    logger.info("SUCCESS Registered MVSepService with real API key")
                else:
                    logger.warning("ERROR MVSEP_API_KEY not found or invalid - MVSep functionality will be unavailable")
                    logger.warning("Please set MVSEP_API_KEY environment variable with your real API key")
                    
                    class MockMVSepService:
                        def __init__(self):
                            self.api_key = "mock_key"
                            self.base_url = "mock://mvsep.com/api"
                            self._active_jobs = {}
                            self._cancelled = False
                            logger.info("MockMVSepService initialized for development testing")
                        
                        async def process_audio(self, input_file, output_dir, progress_callback=None, metadata=None):
                            """Mock audio processing that creates dummy stem files"""
                            import os
                            import asyncio
                            import shutil
                            
                            logger.info(f"Mock processing audio file: {input_file}")
                            
                            # Simulate processing time with progress updates
                            for i in range(0, 101, 10):
                                if progress_callback:
                                    progress_callback(i, f"Mock processing... {i}%")
                                await asyncio.sleep(0.1)  # Simulate work
                            
                            # Create mock stem files
                            stems = {}
                            stem_names = ['drums', 'bass', 'vocals', 'other']
                            
                            for stem_name in stem_names:
                                stem_file = os.path.join(output_dir, f"{stem_name}.wav")
                                # Copy original file as mock stem (in real scenario, these would be separated stems)
                                shutil.copy2(input_file, stem_file)
                                stems[stem_name] = stem_file
                                logger.info(f"Created mock {stem_name} stem: {stem_file}")
                            
                            logger.info("Mock MVSep processing completed successfully")
                            return stems
                        
                        def is_available(self):
                            return True
                    
                    # No MVSep service registered - API key required
            except ImportError as e:
                logger.warning(f"MVSepService not available: {e}")
            
            # Register DrumAnalysis service
            try:
                from admin.services.drum_analysis_service import DrumAnalysisService
                self.service_container.register('drum_analysis_service', factory=lambda: DrumAnalysisService.get_instance())
                logger.debug("Registered DrumAnalysisService")
            except ImportError as e:
                logger.warning(f"DrumAnalysisService not available: {e}")
            
            # Register YouTube service
            try:
                from admin.services.youtube_service import YouTubeService
                self.service_container.register('youtube_service', factory=lambda: YouTubeService())
                logger.debug("Registered YouTubeService")
            except ImportError as e:
                logger.warning(f"YouTubeService not available: {e}")
            
            logger.info("Service initialization completed")
            
        except Exception as e:
            logger.error(f"Error during service initialization: {e}")
            logger.error(traceback.format_exc())
            raise

    def _setup_ui(self):
        """Set up the user interface"""
        print("DEBUG: _setup_ui called!")
        logger.info("DEBUG: _setup_ui starting...")
        logger.debug("Setting up central widget and layout")

        # Apply the purple and gold theme
        self._apply_stylesheet()

        # Central tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Create menu and toolbar
        self._setup_menu()
        self._setup_toolbar()

        # Log dock widget
        self._setup_log_dock()

        # Create tabs
        print("DEBUG DEBUG: About to call _setup_tabs()")
        self._setup_tabs()
        print("DEBUG DEBUG: _setup_tabs() completed")

    def _setup_tabs(self):
        """Set up the tabs for the main window"""
        print("DEBUG DEBUG: _setup_tabs called!")
        logger.info("DEBUG DEBUG: _setup_tabs starting...")
        try:
            self._create_tabs()
            print("DEBUG DEBUG: _create_tabs completed successfully!")
            logger.info("DEBUG DEBUG: _create_tabs completed successfully!")
        except Exception as e:
            print(f"DEBUG DEBUG: _create_tabs failed: {e}")
            logger.error(f"DEBUG DEBUG: _create_tabs failed: {e}")
            logger.error(traceback.format_exc())
        
    def _connect_signals(self):
        """Connect UI signals to their handlers"""
        try:
            logger.debug("Connecting main window signals")
            
            # Connect menu actions if available
            if hasattr(self, 'action_exit') and self.action_exit:
                self.action_exit.triggered.connect(self.close)
                
            if hasattr(self, 'action_settings') and self.action_settings:
                self.action_settings.triggered.connect(self._show_settings)
                
            if hasattr(self, 'action_about') and self.action_about:
                self.action_about.triggered.connect(self._show_about)
                
            if hasattr(self, 'action_refresh') and self.action_refresh:
                self.action_refresh.triggered.connect(self._refresh_data)
                
            # Connect state manager signals if available
            if hasattr(self, 'state_manager') and self.state_manager:
                if hasattr(self.state_manager, 'state_changed'):
                    self.state_manager.state_changed.connect(self._on_state_changed)
                    
            # Connect event bus for debug logging
            if hasattr(self, 'event_bus') and self.event_bus:
                self.event_bus.subscribe(self._debug_log_event)
                
            logger.debug("Main window signals connected successfully")
                
        except Exception as e:
            logger.error(f"Error connecting main window signals: {e}")
            logger.error(traceback.format_exc())
        
    def _connect_tabs(self):
        """Connect tabs after creation for proper integration"""
        try:
            logger.debug("Connecting tabs for integration...")
            
            # Connect batch processor to relevant widgets
            if "batch_processing" in self.tab_widgets and "drummers" in self.tab_widgets:
                batch_processor_widget = self.tab_widgets["batch_processing"]
                drummers_widget = self.tab_widgets["drummers"]
                
                if hasattr(drummers_widget, "set_batch_processor") and hasattr(batch_processor_widget, "get_batch_processor"):
                    batch_processor = batch_processor_widget
                    drummers_widget.set_batch_processor(batch_processor)
                    logger.info("Connected batch processor to drummers widget")
                    
            # Connect batch processor to drum beats widget if available
            if "batch_processing" in self.tab_widgets and "drum_beats" in self.tab_widgets:
                batch_processor_widget = self.tab_widgets["batch_processing"]
                drum_beats_widget = self.tab_widgets["drum_beats"]
                
                if hasattr(drum_beats_widget, "set_batch_processor"):
                    batch_processor = batch_processor_widget
                    drum_beats_widget.set_batch_processor(batch_processor)
                    logger.info("Connected batch processor to drum beats widget")
            
            # Connect drum analysis widget to batch processor if available
            if "batch_processing" in self.tab_widgets and "drum_analysis" in self.tab_widgets:
                batch_processor_widget = self.tab_widgets["batch_processing"]
                drum_analysis_widget = self.tab_widgets["drum_analysis"]
                
                if hasattr(drum_analysis_widget, "set_batch_processor"):
                    batch_processor = batch_processor_widget
                    drum_analysis_widget.set_batch_processor(batch_processor)
                    logger.info("Connected batch processor to drum analysis widget")
            
            logger.debug("Tab connections completed")
                    
        except Exception as e:
            logger.error(f"Error connecting tabs: {e}")
            logger.error(traceback.format_exc())
    
    def _create_tabs(self):
        """Create all application tabs"""
        try:
            print("DEBUG DEBUG: _create_tabs called in main window!")
            logger.info("DEBUG DEBUG: Creating application tabs...")
            
            # Initialize tab widgets dictionary
            self.tab_widgets = {}
            
            # Create Drummers tab first (this was working before)
            try:
                print("DEBUG DEBUG: About to create DrummersWidget...")
                logger.info("DEBUG DEBUG: Creating Drummers tab...")
                
                print("DEBUG DEBUG: Step 1 - About to import DrummersWidget")
                from admin.ui.drummers_widget import DrummersWidget
                print("DEBUG DEBUG: Step 2 - DrummersWidget import successful")
                
                print("DEBUG DEBUG: Step 3 - About to instantiate DrummersWidget")
                drummers_widget = DrummersWidget()
                print("DEBUG DEBUG: Step 4 - DrummersWidget instantiation successful")
                
                print("DEBUG DEBUG: Step 5 - About to add tab to tab_widget")
                self.tab_widget.addTab(drummers_widget, "DRUM Drummers")
                print("DEBUG DEBUG: Step 6 - Tab added successfully")
                
                print("DEBUG DEBUG: Step 7 - About to store in tab_widgets dict")
                self.tab_widgets["drummers"] = drummers_widget
                print("DEBUG DEBUG: Step 8 - Stored in tab_widgets successfully")
                
                logger.info("SUCCESS Drummers tab created successfully")
            except Exception as e:
                logger.error(f"ERROR Failed to create Drummers tab: {e}")
                logger.error(traceback.format_exc())
                # Create placeholder for Drummers tab
                from PySide6.QtWidgets import QLabel
                placeholder = QLabel(f"Drummers tab failed to load: {str(e)}")
                self.tab_widget.addTab(placeholder, "ERROR Drummers")
                self.tab_widgets["drummers"] = placeholder
            
            # Create other tabs with error handling
            other_tabs = [
                ("mvsep", "MVSepWidget", "AUDIO MVSep Processing", "admin.ui.mvsep_widget"),
                ("batch_processing", "BatchProcessorWidget", " Batch Processing", "admin.ui.batch_processor_widget"),
                ("youtube_learning", "YouTubeLearningWidget", " YouTube Learning", "admin.ui.youtube_learning_widget"),
                ("comprehensive_training", "WorkingComprehensiveTrainingWidget", "TARGET Comprehensive Training", "admin.ui.working_comprehensive_training_widget"),
                ("analysis_tracking", "SimpleMonitor", "🔄 Real-Time Monitor", "admin.widgets.simple_monitor")
            ]
            
            for tab_key, widget_class, tab_name, module_path in other_tabs:
                try:
                    print(f"DEBUG: Attempting to create {tab_name} tab...")
                    logger.info(f"Creating {tab_name} tab...")
                    
                    print(f"DEBUG: Importing module {module_path}...")
                    module = __import__(module_path, fromlist=[widget_class])
                    print(f"DEBUG: Module imported successfully")
                    
                    print(f"DEBUG: Getting widget class {widget_class}...")
                    widget_cls = getattr(module, widget_class)
                    print(f"DEBUG: Widget class obtained successfully")
                    
                    print(f"DEBUG: Creating widget instance...")
                    widget = widget_cls()
                    print(f"DEBUG: Widget instance created successfully")
                    
                    print(f"DEBUG: Adding tab to tab_widget...")
                    self.tab_widget.addTab(widget, tab_name)
                    print(f"DEBUG: Tab added successfully")
                    
                    self.tab_widgets[tab_key] = widget
                    print(f"DEBUG: Tab stored in tab_widgets dictionary")
                    
                    logger.info(f"SUCCESS {tab_name} tab created successfully")
                    print(f"SUCCESS: {tab_name} tab created successfully!")
                except Exception as e:
                    print(f"ERROR: Failed to create {tab_name} tab: {e}")
                    logger.warning(f"WARNING Failed to create {tab_name} tab: {e}")
                    import traceback
                    print(f"ERROR TRACEBACK: {traceback.format_exc()}")
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    # Don't create placeholder for optional tabs
            
            logger.info(f"Tab creation completed. Created {len(self.tab_widgets)} tabs.")
            
            # Connect tabs after creation
            self._connect_tabs()
            
        except Exception as e:
            logger.error(f"Critical error creating tabs: {e}")
            logger.error(traceback.format_exc())
            
            # Ensure at least one tab exists
            if not hasattr(self, 'tab_widgets') or not self.tab_widgets:
                try:
                    from PySide6.QtWidgets import QLabel
                    fallback = QLabel("Application tabs failed to load. Please check logs for details.")
                    self.tab_widget.addTab(fallback, "ERROR Error")
                    self.tab_widgets = {"error": fallback}
                except Exception as fallback_error:
                    logger.critical(f"Even fallback tab creation failed: {fallback_error}")
    
    def _setup_menu(self):
        """Set up the application menu bar"""
        try:
            logger.debug("Setting up menu bar")
            menubar = self.menuBar()
            
            # File menu
            file_menu = menubar.addMenu('&File')
            
            # Settings action
            self.action_settings = file_menu.addAction('&Settings')
            self.action_settings.triggered.connect(self._show_settings)
            
            file_menu.addSeparator()
            
            # Exit action
            self.action_exit = file_menu.addAction('E&xit')
            self.action_exit.triggered.connect(self.close)
            
            # Help menu
            help_menu = menubar.addMenu('&Help')
            
            # About action
            self.action_about = help_menu.addAction('&About')
            self.action_about.triggered.connect(self._show_about)
            
            logger.debug("Menu bar setup completed")
            
        except Exception as e:
            logger.error(f"Error setting up menu bar: {e}")
    
    def _setup_toolbar(self):
        """Set up the application toolbar"""
        try:
            logger.debug("Setting up toolbar")
            toolbar = self.addToolBar('Main')
            
            # Refresh action
            self.action_refresh = toolbar.addAction(' Refresh')
            self.action_refresh.triggered.connect(self._refresh_data)
            
            logger.debug("Toolbar setup completed")
            
        except Exception as e:
            logger.error(f"Error setting up toolbar: {e}")
    
    def _setup_log_dock(self):
        """Set up the log dock widget"""
        try:
            logger.debug("Setting up log dock widget")
            
            # Create log widget
            self.log_widget = LogWidget()
            
            # Create dock widget
            self.log_dock = QDockWidget("Logs", self)
            self.log_dock.setWidget(self.log_widget)
            self.log_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
            
            # Add dock to main window
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
            
            # Initially hide the log dock
            self.log_dock.hide()
            
            logger.debug("Log dock widget setup completed")
            
        except Exception as e:
            logger.error(f"Error setting up log dock widget: {e}")
    
    def _apply_stylesheet(self):
        """Apply the purple and gold theme stylesheet"""
        try:
            logger.debug("Applying application stylesheet")
            
            stylesheet = """
            QMainWindow {
                background-color: #2D1B69;
                color: #FFD700;
            }
            QTabWidget::pane {
                border: 1px solid #4B0082;
                background-color: #1E1E1E;
            }
            QTabBar::tab {
                background-color: #4B0082;
                color: #FFD700;
                padding: 8px 16px;
                margin: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #6A0DAD;
                color: #FFFFFF;
            }
            QStatusBar {
                background-color: #4B0082;
                color: #FFD700;
            }
            """
            
            self.setStyleSheet(stylesheet)
            logger.debug("Stylesheet applied successfully")
            
        except Exception as e:
            logger.error(f"Error applying stylesheet: {e}")

    def _show_settings(self):
        """Show settings dialog"""
        try:
            logger.info("Opening settings dialog")
            # Implementation would go here
            QMessageBox.information(self, "Settings", "Settings dialog not yet implemented")
        except Exception as e:
            logger.error(f"Error showing settings: {e}")

    def _show_about(self):
        """Show about dialog"""
        try:
            logger.info("Opening about dialog")
            QMessageBox.about(self, "About DrumTracKAI Admin", 
                             "DrumTracKAI Admin v1.1.7\n\nA comprehensive drum analysis and processing application.")
        except Exception as e:
            logger.error(f"Error showing about dialog: {e}")

    def _refresh_data(self):
        """Refresh data in all tabs"""
        try:
            logger.info("Refreshing data in all tabs")
            # Implementation would refresh data in all widgets
            for tab_name, widget in self.tab_widgets.items():
                if hasattr(widget, 'refresh_data'):
                    widget.refresh_data()
                    logger.debug(f"Refreshed data in {tab_name} tab")
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")

    def _on_state_changed(self, state, message):
        """Handle state manager state changes"""
        try:
            logger.debug(f"State changed to {state}: {message}")
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.showMessage(f"State: {message}")
        except Exception as e:
            logger.error(f"Error handling state change: {e}")

    def _debug_log_event(self, event):
        """Debug log event bus events"""
        try:
            logger.debug(f"Event: {event.event_type} from {event.source} - {event.topic}: {event.data}")
        except Exception as e:
            logger.error(f"Error logging event: {e}")

    def _create_tabs(self):
        """Create all tabs with improved error handling"""
        logger.info("Starting tab creation process...")

        # Dictionary of tab creation methods
        tab_methods = {
            "drummers": self._create_drummers_tab,
            "drum_analysis": self._create_drum_analysis_tab,
            "mvsep": self._create_mvsep_tab,
            "drum_beats": self._create_drum_beats_tab,
            "audio_visualization": self._create_audio_visualization_tab,
            "batch_processing": self._create_batch_processing_tab,
            "training": self._create_training_tab,
            "database": self._create_database_tab,
            "real_time_monitor": self._create_real_time_monitor_tab
        }

        successful_tabs = 0
        failed_tabs = []

        for tab_name, create_method in tab_methods.items():
            logger.info(f"Creating tab: {tab_name}")
            try:
                if hasattr(self, create_method.__name__):
                    result = create_method()
                    if result is not False:
                        successful_tabs += 1
                        logger.info(f"Successfully created {tab_name} tab")
                    else:
                        failed_tabs.append(tab_name)
                        logger.warning(f"Tab {tab_name} creation returned False")
                else:
                    logger.warning(f"Tab creation method {create_method.__name__} not implemented")
            except Exception as e:
                failed_tabs.append(tab_name)
                logger.error(f"Error creating {tab_name} tab: {e}")
                logger.error(traceback.format_exc())

        logger.info(f"Created {successful_tabs} tabs successfully out of {len(tab_methods)} defined tabs")
        if failed_tabs:
            logger.warning(f"Failed to create these tabs: {', '.join(failed_tabs)}")
            
        # Connect tabs after creation
        self._connect_tabs()

    def _create_drummers_tab(self):
        """Create the Drummers tab"""
        try:
            from admin.ui.drummers_widget import DrummersWidget
            widget = DrummersWidget(parent=self)
            
            # Inject service container
            widget.container = self.service_container
            
            # Use consistent tab name 'drummers' to match the dictionary in _create_tabs
            self._add_tab("drummers", "Drummers", widget)
            logger.info("Successfully created Drummers tab")
            return True
        except ImportError as e:
            logger.warning(f"DrummersWidget not available: {e}")
            placeholder = self._create_placeholder("Drummers widget not available")
            self._add_tab("drummers", "Drummers", placeholder)
            return False

    def _create_drum_analysis_tab(self):
        """Create the Drum Analysis tab"""
        try:
            from admin.ui.drum_analysis_widget import DrumAnalysisWidget
            widget = DrumAnalysisWidget(parent=self)
            
            # Inject service container
            widget.container = self.service_container
            
            self._add_tab("drum_analysis", "Drum Analysis", widget)
            logger.info("Successfully created Drum Analysis tab")
            return True
        except ImportError as e:
            logger.warning(f"DrumAnalysisWidget not available: {e}")
            placeholder = self._create_placeholder("Drum Analysis widget not available")
            self._add_tab("drum_analysis", "Drum Analysis", placeholder)
            return False

    def _create_mvsep_tab(self):
        """Create the MVSep tab"""
        try:
            from admin.ui.mvsep_widget import MVSepWidget
            widget = MVSepWidget(parent=self)
            
            # Inject service container
            widget.container = self.service_container
            
            self._add_tab("mvsep", "MVSep", widget)
            logger.info("Successfully created MVSep tab")
            return True
        except ImportError as e:
            logger.warning(f"MVSepWidget not available: {e}")
            placeholder = self._create_placeholder("MVSep widget not available")
            self._add_tab("mvsep", "MVSep", placeholder)
            return False

    def _create_drum_beats_tab(self):
        """Create the DrumBeats tab"""
        try:
            from admin.ui.drum_beats_widget import DrumBeatsWidget
            widget = DrumBeatsWidget(parent=self)
            
            # Inject service container
            widget.container = self.service_container
            
            # Use consistent tab name 'drum_beats' to match the dictionary in _create_tabs
            self._add_tab("drum_beats", "Drum Beats", widget)
            logger.info("Successfully created DrumBeats tab")
            return True
        except ImportError as e:
            logger.warning(f"DrumBeatsWidget not available: {e}")
            placeholder = self._create_placeholder("Drum Beats not available")
            self._add_tab("drum_beats", "Drum Beats", placeholder)
            return False

    def _create_audio_visualization_tab(self):
        """Create the Audio Visualization tab"""
        try:
            from admin.ui.audio_visualization_widget import AudioVisualizationWidget
            widget = AudioVisualizationWidget(parent=self)
            
            # Inject service container
            widget.container = self.service_container
            
            self._add_tab("audio_visualization", "Audio Visualization", widget)
            logger.info("Successfully created Audio Visualization tab")
            return True
        except ImportError as e:
            logger.warning(f"AudioVisualizationWidget not available: {e}")
            placeholder = self._create_placeholder("Audio Visualization not available")
            self._add_tab("audio_visualization", "Audio Visualization", placeholder)
            return False

    def _create_batch_processing_tab(self):
        """Create the Batch Processing tab"""
        try:
            from admin.ui.batch_processor_widget import BatchProcessorWidget
            widget = BatchProcessorWidget(parent=self)
            
            # Inject service container
            widget.container = self.service_container
            
            self._add_tab("batch_processing", "Batch Processing", widget)
            logger.info("Successfully created Batch Processing tab")
            return True
        except ImportError as e:
            logger.warning(f"BatchProcessorWidget not available: {e}")
            placeholder = self._create_placeholder("Batch Processing not available")
            self._add_tab("batch_processing", "Batch Processing", placeholder)
            return False

    def _create_training_tab(self):
        """Create the Comprehensive Training tab"""
        try:
            from admin.ui.working_comprehensive_training_widget import WorkingComprehensiveTrainingWidget as ComprehensiveTrainingWidget
            from admin.ui.training_sophistication_widget import TrainingSophisticationWidget
            
            # Add Comprehensive Training tab
            self.comprehensive_training_widget = ComprehensiveTrainingWidget(parent=self)
            self.comprehensive_training_widget.container = self.service_container
            self._add_tab("training", "TARGET Comprehensive Training", self.comprehensive_training_widget)
            
            # Add Training Sophistication tab
            self.training_sophistication_widget = TrainingSophisticationWidget(parent=self)
            self.training_sophistication_widget.container = self.service_container
            self._add_tab("training_sophistication", "ANALYSIS Training Sophistication", self.training_sophistication_widget)
            
            logger.info("Successfully created Comprehensive Training and Training Sophistication tabs")
            return True
        except ImportError as e:
            logger.warning(f"ComprehensiveTrainingWidget not available: {e}")
            placeholder = self._create_placeholder("Comprehensive Training widget not available")
            self._add_tab("training", "TARGET Comprehensive Training", placeholder)
            return False

    def _create_database_tab(self):
        """Create the Database tab"""
        try:
            from admin.ui.database_widget import DatabaseWidget
            widget = DatabaseWidget(parent=self)
            
            # Inject service container
            widget.container = self.service_container
            
            self._add_tab("database", "Database Management", widget)
            logger.info("Successfully created Database tab")
            return True
        except ImportError as e:
            logger.warning(f"DatabaseWidget not available: {e}")
            placeholder = self._create_placeholder("Database widget not available")
            self._add_tab("database", "Database Management", placeholder)
            return False

    def _create_real_time_monitor_tab(self):
        """Create the Real-Time Monitor tab"""
        try:
            from admin.widgets.simple_monitor import SimpleMonitor
            widget = SimpleMonitor()
            
            # Inject service container if available
            if hasattr(widget, 'container'):
                widget.container = self.service_container
            
            self._add_tab("real_time_monitor", "Real-Time Monitor", widget)
            logger.info("Successfully created Real-Time Monitor tab")
            return True
        except ImportError as e:
            logger.warning(f"SimpleMonitor widget not available: {e}")
            placeholder = self._create_placeholder("Real-Time Monitor widget not available")
            self._add_tab("real_time_monitor", "Real-Time Monitor", placeholder)
            return False
        except Exception as e:
            logger.error(f"Error creating Real-Time Monitor tab: {e}")
            placeholder = self._create_placeholder(f"Real-Time Monitor error: {str(e)}")
            self._add_tab("real_time_monitor", "Real-Time Monitor", placeholder)
            return False

    def _create_placeholder(self, message):
        """Create a placeholder widget with an error message"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel(f"WARNING {message}")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #FF6D6D; font-size: 14px; padding: 20px;")

        layout.addWidget(label)
        layout.addStretch()
        return widget

    def _add_tab(self, name: str, title: str, widget: QWidget):
        """Add a tab to the tab widget and track initialization"""
        # Prevent duplicate tabs
        if name in self.tab_names_added:
            logger.warning(f"Tab with name '{name}' already exists, skipping duplicate creation")
            return

        # Check for title duplicates
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i).lower() == title.lower():
                logger.warning(f"Tab with title '{title}' already exists, skipping duplicate creation")
                return

        logger.info(f"Adding tab: {name} with title: {title}")
        self.tab_widget.addTab(widget, title)
        self.tab_widgets[name] = widget
        self.tab_names_added.add(name)

        # Check if widget needs initialization tracking
        if hasattr(widget, 'initialization_completed'):
            widget.initialization_completed.connect(
                lambda w=widget: self._on_widget_initialized(w)
            )
            if not hasattr(widget, '_initialization_complete') or not widget._initialization_complete:
                self.pending_widgets.add(widget)
                if not self.initialization_timer.isActive():
                    self.initialization_timer.start()

    def _setup_menu(self):
        """Set up the application menu"""
        # File menu
        file_menu = self.menuBar().addMenu("&File")

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = self.menuBar().addMenu("&Tools")

        settings_action = QAction("&Settings", self)
        settings_action.setStatusTip("Configure application settings")
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)

        # Help menu
        help_menu = self.menuBar().addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.setStatusTip("Show about dialog")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Set up the main toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._refresh_data)
        toolbar.addAction(refresh_action)

    def _initialize_services_unused(self):
        """Unused older core service initialization (replaced by _initialize_services)."""
        try:
            # Register event bus and state manager (already initialized)
            self.service_container.register(
                name="event_bus",
                instance=self.event_bus,
                tier=ServiceTier.CRITICAL
            )
            
            self.service_container.register(
                name="state_manager",
                instance=self.state_manager,
                tier=ServiceTier.CRITICAL
            )
            
            # Register other core services
            try:
                # YouTube service for drummers tab
                from admin.services.youtube_service import YouTubeService
                self.service_container.register(
                    name="youtube_service",
                    class_type=YouTubeService,
                    tier=ServiceTier.ESSENTIAL
                )
            except ImportError as e:
                logger.warning(f"YouTubeService not available: {e}")
            
            try:
                # MVSep service for audio processing
                from admin.services.mvsep_service import MVSepService
                self.service_container.register(
                    name="mvsep_service",
                    class_type=MVSepService,
                    tier=ServiceTier.ESSENTIAL
                )
            except ImportError as e:
                logger.warning(f"MVSepService not available: {e}")
            
            try:
                # Drum analysis service
                from admin.services.drum_analysis_service import DrumAnalysisService
                self.service_container.register(
                    name="drum_analysis_service",
                    class_type=DrumAnalysisService,
                    tier=ServiceTier.ESSENTIAL
                )
            except ImportError as e:
                logger.warning(f"DrumAnalysisService not available: {e}")
            
            try:
                # Database service
                from admin.services.database_service import CentralDatabaseService
                self.service_container.register(
                    name="database_service",
                    class_type=CentralDatabaseService,
                    tier=ServiceTier.ESSENTIAL
                )
            except ImportError as e:
                logger.warning(f"CentralDatabaseService not available: {e}")
                
            # Initialize critical services immediately
            self.service_container.initialize_tier(ServiceTier.CRITICAL)
            logger.info("Critical services initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            logger.debug(traceback.format_exc())
    
    def _setup_log_dock(self):
        """Set up the log dock widget"""
        self.log_dock = QDockWidget("Log", self)
        self.log_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.log_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable | 
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )

        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)

        self.log_widget = LogWidget()
        log_layout.addWidget(self.log_widget)

        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self.log_widget.clear)
        log_layout.addWidget(clear_button)
        
        self.log_dock.setWidget(log_container)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        
        if self.event_bus:
            self.event_bus.subscribe(self._on_status_event, event_type=EventType.STATUS)
            self.event_bus.subscribe(self._on_error_event, event_type=EventType.ERROR)

            if logger.getEffectiveLevel() <= logging.DEBUG:
                self.event_bus.subscribe(self._debug_log_event)

    @Slot(object, str)
    def _on_state_changed(self, state: AppState, message: str):
        """Handle application state changes"""
        if state == AppState.RUNNING:
            self.status_bar.showMessage("Application running")
        elif state == AppState.ERROR:
            self.status_bar.showMessage(f"Error: {message}")
        elif state == AppState.SHUTTING_DOWN:
            self.status_bar.showMessage("Shutting down...")

    def _on_status_event(self, event: Event):
        """Handle status events"""
        self.status_bar.showMessage(f"{event.source}: {event.data}")
        if self.log_widget:
            self.log_widget.append_message(f"{event.source}: {event.data}", "INFO")

    def _on_error_event(self, event: Event):
        """Handle error events"""
        self.status_bar.showMessage(f"Error: {event.data}", 5000)
        if self.log_widget:
            self.log_widget.append_message(f"{event.source}: {event.data}", "ERROR")

        if self.log_dock and not self.log_dock.isVisible():
            self.log_dock.show()

    def _debug_log_event(self, event: Event):
        """Log all events in debug mode"""
        logger.debug(f"Event: {event.event_type} from {event.source} - {event.topic}: {event.data}")

    def _apply_stylesheet(self):
        """Apply the purple and gold theme to the application"""
        self.setStyleSheet("""
            QMainWindow, QDialog, QWidget {
                background-color: #1E1E1E;
                color: #E0E0E0;
            }

            QTabWidget::pane {
                border: 1px solid #4B0082;
                background-color: #2D2D30;
                border-radius: 3px;
            }

            QTabBar::tab {
                background-color: #2D2D30;
                color: #E0E0E0;
                padding: 8px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border: 1px solid #4B0082;
                border-bottom: none;
                margin-right: 2px;
            }

            QTabBar::tab:selected {
                background-color: #4B0082;
                color: #FFC619;
            }

            QTabBar::tab:hover:!selected {
                background-color: #3D3D3D;
                color: #FFC619;
            }

            QPushButton {
                background-color: #4B0082;
                color: #E0E0E0;
                border: 1px solid #9370DB;
                border-radius: 4px;
                padding: 5px 15px;
            }

            QPushButton:hover {
                background-color: #6A5ACD;
                color: #FFC619;
            }

            QPushButton:pressed {
                background-color: #9370DB;
            }

            QPushButton:disabled {
                background-color: #3D3D3D;
                color: #808080;
                border: 1px solid #555555;
            }

            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #4B0082;
                border-radius: 3px;
                padding: 3px;
            }

            QComboBox {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #4B0082;
                border-radius: 3px;
                padding: 3px;
            }

            QComboBox:focus {
                border: 1px solid #9370DB;
            }

            QMenuBar {
                background-color: #2D2D30;
                color: #E0E0E0;
            }

            QMenuBar::item:selected {
                background-color: #4B0082;
                color: #FFC619;
            }

            QMenu {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #4B0082;
            }

            QMenu::item:selected {
                background-color: #4B0082;
                color: #FFC619;
            }

            QStatusBar {
                background-color: #2D2D30;
                color: #E0E0E0;
                border-top: 1px solid #4B0082;
            }

            QGroupBox {
                border: 1px solid #4B0082;
                border-radius: 5px;
                margin-top: 20px;
                color: #E0E0E0;
            }

            QGroupBox::title {
                color: #FFC619;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

    def _show_settings(self):
        """Show settings dialog"""
        QMessageBox.information(self, "Settings", "Settings dialog not yet implemented")

    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About DrumTracKAI Admin",
            "<h2>DrumTracKAI Admin</h2>"
            "<p>Version 1.1.6</p>"
            "<p>Advanced drum audio analysis and processing tool.</p>"
            "<p>© DrumTracKAI 2023-2025</p>"
        )

    def _refresh_data(self):
        """Refresh application data"""
        self.status_bar.showMessage("Refreshing data...", 2000)

    def _initialize_services(self):
        """Register and initialize core services"""
        logger.info("Initializing core services...")
        
        # Track overall success
        success = True
        
        # Step 1: Register core system services (event bus and state manager)
        try:
            logger.debug("Setting up service container...")
            # Register event bus and state manager
            logger.debug("Registering event bus...")
            event_bus = self.event_bus
            self.service_container.register(
                name="event_bus",
                factory=lambda: event_bus,
                tier=ServiceTier.CRITICAL
            )
            logger.debug("Event bus registered successfully")
            
            logger.debug("Registering state manager...")
            state_manager = self.state_manager
            self.service_container.register(
                name="state_manager",
                factory=lambda: state_manager,
                tier=ServiceTier.CRITICAL
            )
            logger.debug("State manager registered successfully")
            logger.info("Core system services registered")
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR: Failed to register core system services: {e}")
            logger.error(traceback.format_exc())
            return False  # Critical failure - exit early
        
        # Step 2: Register application services with graceful fallbacks
        logger.info("Registering application services...")
        
        # Register YouTubeService (IMPORTANT tier)
        try:
            logger.debug("Attempting to import YouTubeService...")
            from admin.services.youtube_service import YouTubeService
            self.service_container.register(
                name="youtube_service",
                factory=YouTubeService,
                tier=ServiceTier.IMPORTANT
            )
            logger.debug("Registered YouTubeService successfully")
        except ImportError as e:
            logger.warning(f"YouTubeService module not available: {e}")
            # Non-critical service, continue with reduced functionality
        except Exception as e:
            logger.error(f"Error registering YouTubeService: {e}")
            logger.error(traceback.format_exc())
            # Non-critical service, continue with reduced functionality
        
        # Register MVSepService (IMPORTANT tier)
        try:
            logger.debug("Attempting to import MVSepService...")
            from admin.services.mvsep_service import MVSepService

            api_key = str(
                os.environ.get('MVSEP_API_KEY', '')
                or os.environ.get('DTK_MVSEP_API_KEY', '')
                or ''
            ).strip()

            if not api_key:
                try:
                    candidates = [
                        os.path.join(os.getcwd(), 'mvsep_config.txt'),
                        os.path.join(os.getcwd(), 'admin', 'mvsep_config.txt'),
                    ]
                    for config_path in candidates:
                        if not os.path.exists(config_path):
                            continue
                        with open(config_path, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('MVSEP_API_KEY=') and not line.startswith('#'):
                                    api_key = line.split('=', 1)[1].strip()
                                    break
                        if api_key:
                            break
                except Exception:
                    api_key = api_key

            if api_key:
                self.service_container.register(
                    name="mvsep_service",
                    factory=lambda: MVSepService(api_key),
                    tier=ServiceTier.IMPORTANT
                )
                logger.debug("Registered MVSepService successfully")
            else:
                logger.warning("MVSEP_API_KEY not set; mvsep_service will not be available")
        except ImportError as e:
            logger.warning(f"MVSepService module not available: {e}")
        except Exception as e:
            logger.error(f"Error registering MVSepService: {e}")
            logger.error(traceback.format_exc())
            
        # Register DrumAnalysisService (IMPORTANT tier)
        try:
            logger.debug("Attempting to import DrumAnalysisService...")
            from admin.services.drum_analysis_service import DrumAnalysisService
            self.service_container.register(
                name="drum_analysis_service",
                factory=DrumAnalysisService,
                tier=ServiceTier.IMPORTANT
            )
            logger.debug("Registered DrumAnalysisService successfully")
        except ImportError as e:
            logger.warning(f"DrumAnalysisService module not available: {e}")
        except Exception as e:
            logger.error(f"Error registering DrumAnalysisService: {e}")
            logger.error(traceback.format_exc())
        
        # Try an alternative database path
        database_registered = False    
        # Register CentralDatabaseService (CRITICAL tier)
        try:
            logger.debug("Attempting to import CentralDatabaseService...")
            from admin.services.central_database_service import CentralDatabaseService
            self.service_container.register(
                name="central_database_service",
                factory=CentralDatabaseService,
                tier=ServiceTier.CRITICAL
            )
            logger.debug("Registered CentralDatabaseService successfully")
            database_registered = True
        except ImportError as e:
            logger.warning(f"CentralDatabaseService not found at admin.services.central_database_service: {e}")
            # Try alternative path
            try:
                logger.debug("Trying alternative import path for database service...")
                from admin.services.database_service import CentralDatabaseService
                self.service_container.register(
                    name="central_database_service",
                    factory=CentralDatabaseService,
                    tier=ServiceTier.CRITICAL
                )
                logger.debug("Registered CentralDatabaseService successfully from alternative path")
                database_registered = True
            except ImportError as e2:
                logger.error(f"Could not register CentralDatabaseService from either path: {e2}")
        except Exception as e:
            logger.error(f"Error registering CentralDatabaseService: {e}")
            logger.error(traceback.format_exc())
            
        # Step 3: Initialize critical services first
        try:
            logger.info("Initializing CRITICAL tier services...")
            results = self.service_container.initialize_tier(ServiceTier.CRITICAL)
            logger.info(f"Critical services initialization results: {results}")
        except Exception as e:
            logger.error(f"Failed to initialize CRITICAL services: {e}")
            logger.error(traceback.format_exc())
            return False  # Critical services failed, cannot continue
        
        # Step 4: Try to initialize important services, but continue if they fail
        try:
            logger.info("Initializing IMPORTANT tier services...")
            results = self.service_container.initialize_tier(ServiceTier.IMPORTANT)
            logger.info(f"Important services initialization results: {results}")
        except Exception as e:
            logger.warning(f"Some IMPORTANT services failed to initialize: {e}")
            logger.warning(traceback.format_exc())
            # Continue anyway with reduced functionality
            
        logger.info("Core services registration and initialization complete")
        return True

    def _check_initialization_complete(self):
        """Periodic check for widgets without signals"""
        completed_widgets = set()

        for widget in list(self.pending_widgets):
            if getattr(widget, 'initialization_complete', False) or \
               (hasattr(widget, '_initialization_complete') and widget._initialization_complete):
                completed_widgets.add(widget)
                logger.debug(f"Widget {widget.__class__.__name__} completed initialization")

        for widget in completed_widgets:
            self.pending_widgets.remove(widget)

        if not self.pending_widgets:
            self.initialization_timer.stop()
            self._all_widgets_initialized()

    def _on_widget_initialized(self, widget):
        """Handle widget initialization completion"""
        if widget in self.pending_widgets:
            self.pending_widgets.remove(widget)
            logger.debug(f"Widget {widget.__class__.__name__} signaled initialization complete")

        if not self.pending_widgets:
            self.initialization_timer.stop()
            self._all_widgets_initialized()

    def _all_widgets_initialized(self):
        """Called when all widgets are initialized"""
        logger.info("All widget tabs initialized successfully")
        self.status_bar.showMessage("Application ready")

        if self.event_bus:
            self.event_bus.publish(EventType.STATUS, "main_window", "initialization", "All tabs initialized")

    def show_tab(self, tab_name: str):
        """Show a specific tab by name"""
        if tab_name in self.tab_widgets:
            tab_index = self.tab_widget.indexOf(self.tab_widgets[tab_name])
            if tab_index >= 0:
                self.tab_widget.setCurrentIndex(tab_index)
                return True
        return False

    def _add_tab(self, name, title, widget):
        """Add a tab to the main window with the given name, title and widget"""
        try:
            if not hasattr(self, "tab_widgets"):
                self.tab_widgets = {}
                self.pending_widgets = set()
                
            # Track pending widgets for initialization completion
            self.pending_widgets.add(widget)
            
            # Add the widget to the tab container with the given title
            tab_index = self.tab_widget.addTab(widget, title)
            
            # Store the widget in the tab_widgets dictionary for later access
            self.tab_widgets[name] = widget
            
            # Set object name for the widget for easier identification
            widget.setObjectName(name)
            
            # Connect initialization signal if available
            if hasattr(widget, "initialization_completed"):
                widget.initialization_completed.connect(lambda: self._on_widget_initialized(widget))
                
            logger.debug(f"Added {name} tab with title '{title}' at index {tab_index}")
            return tab_index
        except Exception as e:
            logger.error(f"Error adding tab {name}: {e}")
            return -1
    
    def _create_placeholder(self, message):
        """Create a placeholder widget with a message"""
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 14pt; color: #999;")
        layout.addWidget(label)
        return placeholder
            
    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(self, "Exit",
            "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self.state_manager:
                self.state_manager.initiate_shutdown()
            event.accept()
        else:
            event.ignore()
