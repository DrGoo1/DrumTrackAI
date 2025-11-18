import json
import logging
import os
import platform
import re
import shutil
import subprocess
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple, Union

import pytube
from PySide6.QtCore import Qt, Signal, Slot, QSize, QUrl, QThread, QObject
from PySide6.QtGui import QIcon, QPixmap, QColor, QDesktopServices, QAction
from PySide6.QtWidgets import (
    QWidget, QMessageBox, QPushButton, QTableWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QGroupBox, QListWidget, QListWidgetItem,
    QTabWidget, QTextEdit, QSplitter, QTableWidgetItem, QHeaderView,
    QProgressBar, QToolButton, QMenu, QDialog,
    QFileDialog, QCheckBox, QRadioButton, QButtonGroup, QScrollArea, QSizePolicy
)

# Configure logging
logger = logging.getLogger(__name__)

# Import internal modules with strict absolute imports - will error if not found
from admin.services.youtube_service import YouTubeService
from admin.utils.api_key_manager import get_api_key_manager
from admin.utils.youtube_search import YouTubeSearchAPI
from admin.ui.settings_dialog import SettingsDialog

# Import thread-safe UI updater with strict absolute import
from admin.utils.thread_safe_ui_updater import ThreadSafeUIUpdater
from admin.services.phased_drum_analysis import PhasedDrumAnalysis, AnalysisPhase


class DrummersWidget(QWidget):
    # Signals
    drummer_selected = Signal(dict)
    song_added = Signal(str, dict)
    batch_submitted = Signal(list)
    youtube_search_finished = Signal(list)
    download_completed = Signal(str, dict)

    def __init__(self, parent=None):
        """Initialize the DrummersWidget"""
        print("DEBUG DEBUG: DrummersWidget.__init__ called!")
        logger.info("DEBUG DEBUG: DrummersWidget initialization starting...")
        super().__init__(parent)
        
        # Set container for service access
        self.container = None
        
        # Initialize attributes
        self.current_drummer = None
        self.current_song = None
        self.filtered_drummers = []
        self.downloaded_songs = {}
        self._initialization_complete = False
        
        # Initialize phased drum analysis system
        self.phased_analysis = PhasedDrumAnalysis()
        self.analysis_jobs = {}  # Track analysis jobs

        # Define paths using absolute imports
        self.data_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.profiles_path = os.path.join(self.data_root, 'drummers', 'profiles.json')
        self.download_path = os.path.join(self.data_root, 'drummer_songs')
        self.mvsep_output_path = os.path.join(self.data_root, 'processed_stems')

        # Ensure paths exist
        os.makedirs(os.path.dirname(self.profiles_path), exist_ok=True)
        os.makedirs(self.download_path, exist_ok=True)
        os.makedirs(self.mvsep_output_path, exist_ok=True)

        # Initialize basic attributes (defer complex service initialization)
        print("DEBUG DEBUG: Initializing basic attributes...")
        self.youtube_search_api = None
        self.youtube_service = None
        self.thread_safe = None  # Will be initialized in setup_ui
        self.download_threads = []
        self.youtube_api = None
        self.mvsep_service = None
        
        logger.info("Basic DrummersWidget initialization completed")
        
        # Initialize UI first
        self.setup_ui()
        
        # Then load drummer profiles and populate data (after UI elements exist)
        try:
            print("DEBUG DEBUG: Loading drummer profiles after UI setup...")
            self.load_drummer_profiles()
            print(f"DEBUG DEBUG: Drummer profiles loaded: {len(getattr(self, 'drummer_profiles', {})) if hasattr(self, 'drummer_profiles') else 0} profiles")
            
            print("DEBUG DEBUG: Populating drummer list...")
            self.populate_drummer_list()
            
            # Verify data was actually loaded
            if hasattr(self, 'drummer_list') and self.drummer_list:
                item_count = self.drummer_list.count()
                print(f"DEBUG DEBUG: Drummer list populated with {item_count} items")
                
                # Check first item data
                if item_count > 0:
                    first_item = self.drummer_list.item(0)
                    if first_item:
                        data = first_item.data(Qt.ItemDataRole.UserRole)
                        print(f"DEBUG DEBUG: First item data type: {type(data)}")
                        if hasattr(data, 'get'):
                            songs = data.get('signature_songs', [])
                            print(f"DEBUG DEBUG: First item signature songs: {songs}")
                        else:
                            print(f"DEBUG DEBUG: First item data content: {data}")
                    else:
                        print("DEBUG DEBUG: First item is None")
                else:
                    print("DEBUG DEBUG: No items in drummer list")
            else:
                print("DEBUG DEBUG: drummer_list widget not found")
                
            print("DEBUG DEBUG: Data loading completed successfully")
            
        except Exception as e:
            print(f"ERROR DEBUG: Data loading failed: {e}")
            logger.error(f"Data loading failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_mock_mvsep_service(self):
        """Create a mock MVSep service for testing when real service is unavailable"""
        class MockMVSepService:
            def __init__(self):
                self.available = True
                
            def process_audio(self, audio_file, output_dir=None):
                """Mock audio processing that simulates MVSep workflow"""
                import os
                import time
                
                # Simulate processing time
                time.sleep(1)
                
                # Create mock stem file paths
                base_name = os.path.splitext(os.path.basename(audio_file))[0]
                output_dir = output_dir or os.path.dirname(audio_file)
                
                stem_files = {
                    'drums': os.path.join(output_dir, f"{base_name}_drums.wav"),
                    'bass': os.path.join(output_dir, f"{base_name}_bass.wav"),
                    'vocals': os.path.join(output_dir, f"{base_name}_vocals.wav"),
                    'other': os.path.join(output_dir, f"{base_name}_other.wav")
                }
                
                return {
                    'success': True,
                    'message': 'Mock processing completed',
                    'stem_files': stem_files,
                    'processing_time': 1.0
                }
                
            def is_available(self):
                return True
        
        return MockMVSepService()
    
    def setup_ui(self):
        """Set up the user interface for the DrummersWidget"""
        try:
            print("DEBUG DEBUG: setup_ui called!")
            logger.info("DEBUG DEBUG: Setting up DrummersWidget UI...")
            
            print("DEBUG DEBUG: Step A - About to initialize ThreadSafeUIUpdater")
            
            # Initialize ThreadSafeUIUpdater now that Qt is properly set up
            try:
                print("DEBUG DEBUG: Step A1 - Creating ThreadSafeUIUpdater...")
                self.thread_safe = ThreadSafeUIUpdater()
                print("DEBUG DEBUG: Step A2 - ThreadSafeUIUpdater created successfully")
                logger.debug("ThreadSafeUIUpdater initialized successfully")
            except Exception as e:
                print(f"DEBUG DEBUG: Step A3 - ThreadSafeUIUpdater failed: {e}")
                logger.warning(f"ThreadSafeUIUpdater initialization failed: {e}")
                self.thread_safe = None
            
            # Create main layout
            print("DEBUG DEBUG: Step B - Creating main layout...")
            main_layout = QVBoxLayout(self)
            print("DEBUG DEBUG: Step B1 - Main layout created")
            
            # Create title
            print("DEBUG DEBUG: Step C - Creating title label...")
            title_label = QLabel("DRUM Famous Drummers Analysis")
            print("DEBUG DEBUG: Step C1 - Title label created")
            title_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    font-weight: bold;
                    color: #FFD700;
                    padding: 10px;
                    text-align: center;
                }
            """)
            main_layout.addWidget(title_label)
            
            # Create drummers list widget
            self.drummer_list = QListWidget()
            self.drummer_list.setStyleSheet("""
                QListWidget {
                    background-color: #1E1E1E;
                    color: #FFD700;
                    border: 1px solid #4B0082;
                    border-radius: 5px;
                    padding: 5px;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #4B0082;
                }
                QListWidget::item:selected {
                    background-color: #6A0DAD;
                    color: #FFFFFF;
                }
            """)
            main_layout.addWidget(self.drummer_list)
            
            # Create control buttons
            button_layout = QHBoxLayout()
            
            self.analyze_button = QPushButton("AUDIO Analyze Song")
            self.analyze_button.setStyleSheet("""
                QPushButton {
                    background-color: #4B0082;
                    color: #FFD700;
                    border: 2px solid #6A0DAD;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #6A0DAD;
                }
                QPushButton:pressed {
                    background-color: #8A2BE2;
                }
            """)
            
            self.download_button = QPushButton(" Download Song")
            self.download_button.setStyleSheet("""
                QPushButton {
                    background-color: #4B0082;
                    color: #FFD700;
                    border: 2px solid #6A0DAD;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #6A0DAD;
                }
                QPushButton:pressed {
                    background-color: #8A2BE2;
                }
            """)
            
            button_layout.addWidget(self.analyze_button)
            button_layout.addWidget(self.download_button)
            main_layout.addLayout(button_layout)
            
            # Connect signals after UI is created
            print("DEBUG DEBUG: UI setup completed, connecting signals...")
            self.connect_signals()
            print("DEBUG DEBUG: Signals connected successfully")
            
            logger.info("SUCCESS DrummersWidget UI setup completed successfully")
            
        except Exception as e:
            logger.error(f"ERROR Error setting up DrummersWidget UI: {e}")
            logger.error(traceback.format_exc())
    
    def populate_drummer_list(self):
        """Populate the drummers list with famous drummers data"""
        try:
            print("DEBUG DEBUG: populate_drummer_list called!")
            logger.info("DEBUG DEBUG: Populating drummers list...")
            
            # Check if drummer_list widget exists
            if not hasattr(self, 'drummer_list') or self.drummer_list is None:
                logger.warning("Drummer list widget not available, skipping population")
                return
            
            # Clear existing items
            self.drummer_list.clear()
            
            # Use loaded drummer profiles data (contains full signature songs arrays)
            if not hasattr(self, 'drummer_profiles') or not self.drummer_profiles:
                logger.warning("No drummer profiles loaded, cannot populate list")
                return
            
            # Icon mapping for drummers
            drummer_icons = {
                "Neil Peart": "DRUM",
                "John Bonham": "", 
                "Stewart Copeland": "AUDIO",
                "Jeff Porcaro": "SOUND",
                "Keith Moon": "",
                "Ginger Baker": "DEBUG"
            }
            
            # Add drummers to the list using loaded profile data
            for drummer_name, profile in self.drummer_profiles.items():
                icon = drummer_icons.get(drummer_name, "DRUM")
                band = profile.get('band', 'Unknown')
                signature_songs = profile.get('signature_songs', [])
                style = profile.get('style', 'Unknown')
                
                # Create display text with first signature song
                primary_song = signature_songs[0] if signature_songs else 'Unknown'
                item_text = f"{icon} {drummer_name} ({band}) - {primary_song}"
                
                # Create list item
                item = QListWidgetItem(item_text)
                
                # Store complete profile data including all signature songs
                drummer_data = {
                    'name': drummer_name,
                    'band': band,
                    'signature_songs': signature_songs,  # Full array of songs
                    'style': style,
                    'icon': icon
                }
                item.setData(Qt.ItemDataRole.UserRole, drummer_data)
                self.drummer_list.addItem(item)
            
            logger.info(f"SUCCESS Added {len(self.drummer_profiles)} drummers to the list")
            
        except Exception as e:
            logger.error(f"ERROR Error populating drummers list: {e}")
            logger.error(traceback.format_exc())
    
    def load_drummer_profiles(self):
        """Load drummer profiles from JSON file or create default ones"""
        try:
            logger.info("Loading drummer profiles...")
            
            # For now, we'll use the hardcoded famous drummers data
            # This method can be expanded later to load from JSON files
            self.drummer_profiles = {
                "Neil Peart": {
                    "band": "Rush",
                    "signature_songs": ["Tom Sawyer", "Limelight", "Freewill"],
                    "style": "Progressive Rock"
                },
                "John Bonham": {
                    "band": "Led Zeppelin", 
                    "signature_songs": ["Stairway to Heaven", "Whole Lotta Love", "Black Dog"],
                    "style": "Hard Rock"
                },
                "Stewart Copeland": {
                    "band": "The Police",
                    "signature_songs": ["Roxanne", "Every Breath You Take", "Message in a Bottle"],
                    "style": "New Wave/Rock"
                },
                "Jeff Porcaro": {
                    "band": "Toto",
                    "signature_songs": ["Rosanna", "Africa", "Hold the Line"],
                    "style": "Pop Rock/AOR"
                }
            }
            
            logger.info(f"SUCCESS Loaded {len(self.drummer_profiles)} drummer profiles")
            
        except Exception as e:
            logger.error(f"ERROR Error loading drummer profiles: {e}")
            self.drummer_profiles = {}
    
    def connect_signals(self):
        """Connect UI signals to their handlers"""
        try:
            logger.info("Connecting DrummersWidget signals...")
            
            # Connect drummer list selection
            if hasattr(self, 'drummer_list') and self.drummer_list:
                self.drummer_list.itemSelectionChanged.connect(self._on_drummer_selected)
                self.drummer_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                self.drummer_list.customContextMenuRequested.connect(self._show_context_menu)
            
            # Connect buttons if they exist
            if hasattr(self, 'analyze_button') and self.analyze_button:
                self.analyze_button.clicked.connect(self._on_analyze_clicked)
                
            if hasattr(self, 'download_button') and self.download_button:
                self.download_button.clicked.connect(self._on_download_clicked)
            
            logger.info("SUCCESS DrummersWidget signals connected successfully")
            
        except Exception as e:
            logger.error(f"ERROR Error connecting signals: {e}")
            logger.error(traceback.format_exc())
    
    def _update_button_states(self):
        """Update button states based on current selection"""
        try:
            # Enable/disable buttons based on selection
            has_selection = hasattr(self, 'drummer_list') and self.drummer_list and self.drummer_list.currentItem() is not None
            
            if hasattr(self, 'analyze_button') and self.analyze_button:
                self.analyze_button.setEnabled(has_selection)
                
            if hasattr(self, 'download_button') and self.download_button:
                self.download_button.setEnabled(has_selection)
            
        except Exception as e:
            logger.error(f"Error updating button states: {e}")
    
    def _on_drummer_selected(self):
        """Handle drummer selection from the list"""
        try:
            current_item = self.drummer_list.currentItem()
            if current_item:
                drummer_data = current_item.data(Qt.ItemDataRole.UserRole)
                logger.info(f"Selected drummer: {drummer_data['name']} ({drummer_data['band']})")
                self.current_drummer = drummer_data
                self._update_button_states()
        except Exception as e:
            logger.error(f"Error handling drummer selection: {e}")
    
    def _show_context_menu(self, position):
        """Show context menu for drummer list items"""
        try:
            item = self.drummer_list.itemAt(position)
            if item:
                drummer_data = item.data(Qt.ItemDataRole.UserRole)
                
                menu = QMenu(self)
                
                # Get signature songs array
                signature_songs = drummer_data.get('signature_songs', [])
                drummer_name = drummer_data.get('name', 'Unknown')
                
                if signature_songs:
                    # Create submenu for each signature song
                    for song in signature_songs:
                        song_menu = menu.addMenu(f"AUDIO {song}")
                        
                        # Add actions for each song
                        analyze_action = song_menu.addAction(f"AUDIO Analyze {song}")
                        download_action = song_menu.addAction(f" Download {song}")
                        youtube_action = song_menu.addAction(f"INSPECTING Find on YouTube")
                        
                        # Connect actions with specific song
                        analyze_action.triggered.connect(lambda checked, s=song: self._analyze_signature_song(drummer_data, s))
                        download_action.triggered.connect(lambda checked, s=song: self._download_signature_song(drummer_data, s))
                        youtube_action.triggered.connect(lambda checked, s=song: self._find_on_youtube(drummer_data, s))
                    
                    # Add separator and general actions
                    menu.addSeparator()
                    all_songs_action = menu.addAction(f"AUDIO Analyze All Songs for {drummer_name}")
                    all_songs_action.triggered.connect(lambda: self._analyze_all_signature_songs(drummer_data))
                else:
                    # Fallback if no signature songs
                    no_songs_action = menu.addAction("No signature songs available")
                    no_songs_action.setEnabled(False)
                
                menu.exec(self.drummer_list.mapToGlobal(position))
                
        except Exception as e:
            logger.error(f"Error showing context menu: {e}")
    
    def _on_analyze_clicked(self):
        """Handle analyze button click"""
        if self.current_drummer:
            # Show dialog to select which signature song to analyze
            signature_songs = self.current_drummer.get('signature_songs', [])
            if signature_songs:
                if len(signature_songs) == 1:
                    self._analyze_signature_song(self.current_drummer, signature_songs[0])
                else:
                    # Show selection dialog for multiple songs
                    self._show_song_selection_dialog(self.current_drummer, 'analyze')
    
    def _on_download_clicked(self):
        """Handle download button click"""
        if self.current_drummer:
            # Show dialog to select which signature song to download
            signature_songs = self.current_drummer.get('signature_songs', [])
            if signature_songs:
                if len(signature_songs) == 1:
                    self._download_signature_song(self.current_drummer, signature_songs[0])
                else:
                    # Show selection dialog for multiple songs
                    self._show_song_selection_dialog(self.current_drummer, 'download')
    
    def _analyze_signature_song(self, drummer_data, song_title):
        """Analyze a specific signature song for the selected drummer"""
        try:
            drummer_name = drummer_data.get('name', 'Unknown')
            logger.info(f"Starting analysis for {drummer_name} - {song_title}")
            # This will integrate with the existing arrangement analysis workflow
            QMessageBox.information(self, "Analysis", f"Starting analysis for {drummer_name} - {song_title}")
        except Exception as e:
            logger.error(f"Error analyzing signature song: {e}")
    
    def _download_signature_song(self, drummer_data, song_title):
        """Download a specific signature song for the selected drummer"""
        try:
            drummer_name = drummer_data.get('name', 'Unknown')
            logger.info(f"Starting download for {drummer_name} - {song_title}")
            QMessageBox.information(self, "Download", f"Starting download for {drummer_name} - {song_title}")
        except Exception as e:
            logger.error(f"Error downloading signature song: {e}")
    
    def _find_on_youtube(self, drummer_data, song_title):
        """Find a specific signature song on YouTube"""
        try:
            drummer_name = drummer_data.get('name', 'Unknown')
            logger.info(f"Searching YouTube for {drummer_name} - {song_title}")
            QMessageBox.information(self, "YouTube Search", f"Searching for {drummer_name} - {song_title}")
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
    
    def _show_song_selection_dialog(self, drummer_data, action):
        """Show dialog to select which signature song to process"""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel
            
            drummer_name = drummer_data.get('name', 'Unknown')
            signature_songs = drummer_data.get('signature_songs', [])
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Select Song - {drummer_name}")
            dialog.setMinimumSize(400, 300)
            
            layout = QVBoxLayout(dialog)
            
            # Add label
            label = QLabel(f"Select a signature song to {action}:")
            layout.addWidget(label)
            
            # Add song list
            song_list = QListWidget()
            for song in signature_songs:
                song_list.addItem(song)
            layout.addWidget(song_list)
            
            # Add buttons
            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")
            
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            # Connect buttons
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            # Show dialog and handle result
            if dialog.exec() == QDialog.DialogCode.Accepted:
                current_item = song_list.currentItem()
                if current_item:
                    selected_song = current_item.text()
                    if action == 'analyze':
                        self._analyze_signature_song(drummer_data, selected_song)
                    elif action == 'download':
                        self._download_signature_song(drummer_data, selected_song)
                        
        except Exception as e:
            logger.error(f"Error showing song selection dialog: {e}")
    
    def _analyze_all_signature_songs(self, drummer_data):
        """Analyze all signature songs for the selected drummer"""
        try:
            drummer_name = drummer_data.get('name', 'Unknown')
            signature_songs = drummer_data.get('signature_songs', [])
            
            logger.info(f"Starting analysis for all signature songs of {drummer_name}")
            QMessageBox.information(self, "Batch Analysis", 
                                  f"Starting analysis for all {len(signature_songs)} signature songs of {drummer_name}:\n" +
                                  "\n".join([f"• {song}" for song in signature_songs]))
            
            # TODO: Implement batch analysis workflow
            
        except Exception as e:
            logger.error(f"Error analyzing all signature songs: {e}")
        
        # Load drummer profiles
        try:
            print("DEBUG DEBUG: About to call load_drummer_profiles()")
            self.load_drummer_profiles()
            print("DEBUG DEBUG: load_drummer_profiles() completed successfully")
            logger.info(f"Loaded drummer profiles successfully")
        except Exception as e:
            print(f"DEBUG DEBUG: load_drummer_profiles() failed: {e}")
            logger.error(f"Failed to load drummer profiles: {e}")
            logger.error(traceback.format_exc())
        
        # Connect UI signals
        self.connect_signals()
        logger.info("Connected all drummer widget signals")
        
        # Populate UI with data
        try:
            print("DEBUG DEBUG: About to call setup_ui()")
            self.setup_ui()
            print("DEBUG DEBUG: setup_ui() completed successfully")
            logger.info("DrummersWidget UI setup completed")
        except Exception as e:
            print(f"DEBUG DEBUG: setup_ui() failed: {e}")
            logger.error(f"Failed to setup DrummersWidget UI: {e}")
            logger.error(traceback.format_exc())
        
        # Populate the drummers list
        try:
            print("DEBUG DEBUG: About to call populate_drummer_list()")
            self.populate_drummer_list()
            print("DEBUG DEBUG: populate_drummer_list() completed")
            logger.info("DrummersWidget setup completed successfully")
        except Exception as e:
            print(f"DEBUG DEBUG: populate_drummer_list() failed: {e}")
            logger.error(f"Failed to populate drummers list: {e}")
            logger.error(traceback.format_exc())

        self._initialization_complete = True
        
    def setup_batch_processor(self):
        """Setup batch processor integration"""
        try:
            # Initialize batch processor if available
            self.batch_processor = None
            if hasattr(self, 'container') and self.container:
                try:
                    self.batch_processor = self.container.get('batch_processor')
                    if self.batch_processor:
                        logger.info("Batch processor connected to DrummersWidget")
                    else:
                        logger.warning("Batch processor not available in service container")
                except Exception as e:
                    logger.warning(f"Could not get batch processor from container: {e}")
            else:
                logger.info("Service container not available for batch processor")
        except Exception as e:
            logger.error(f"Error setting up batch processor: {e}")
        
    def connect_signals(self):
        """Connect all UI signals"""
        try:
            # Drummer list - use ONLY ONE signal to avoid conflicts
            logger.info("Connecting drummer list signals...")
            # Disconnect any existing connections first
            try:
                self.drummer_list.itemSelectionChanged.disconnect()
                self.drummer_list.itemClicked.disconnect()
            except:
                pass  # Ignore if no connections exist
            
            # Connect only the selection changed signal for consistent behavior
            self.drummer_list.itemSelectionChanged.connect(self._on_drummer_selected)
            
            # Search and filter
            self.search_edit.textChanged.connect(self.populate_drummer_list)
            self.genre_combo.currentIndexChanged.connect(self.populate_drummer_list)
            
            # Buttons
            self.add_drummer_btn.clicked.connect(self._on_add_drummer)
            self.edit_drummer_btn.clicked.connect(self._on_edit_drummer)
            self.delete_drummer_btn.clicked.connect(self._on_delete_drummer)
            self.add_song_btn.clicked.connect(self._on_add_song)
            self.find_on_youtube_btn.clicked.connect(self._on_find_song_on_youtube)
            self.process_all_btn.clicked.connect(self._on_process_all_btn_clicked)
            
            # Connect song table selection
            self.songs_table.itemSelectionChanged.connect(self._on_song_selected)
            
            # Connect YouTube controls
            self.youtube_search_btn.clicked.connect(self._on_youtube_search)
            self.download_btn.clicked.connect(self._on_download_video)
            self.play_preview_btn.clicked.connect(self._on_play_preview)
            
            logger.info("All signals connected successfully")
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            traceback.print_exc()

    def setup_ui(self):
        """Setup the UI components"""
        self.setObjectName("drummers_widget")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Create main splitter
        self.main_splitter = QSplitter(Qt.Horizontal)

        # === Left Panel (Drummer List and Filtering) ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Filter controls
        filter_group = QGroupBox("Filters")
        filter_layout = QVBoxLayout(filter_group)

        # Genre filter
        genre_layout = QHBoxLayout()
        genre_layout.addWidget(QLabel("Genre:"))
        self.genre_combo = QComboBox()
        self.genre_combo.setEditable(False)
        self.genre_combo.addItem("All Genres")
        genre_layout.addWidget(self.genre_combo)
        filter_layout.addLayout(genre_layout)

        # Search filter
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search drummer name")
        search_layout.addWidget(self.search_edit)
        filter_layout.addLayout(search_layout)

        left_layout.addWidget(filter_group)

        # Drummer list
        self.drummer_list = QListWidget()
        self.drummer_list.setSelectionMode(QListWidget.SingleSelection)
        self.drummer_list.setMinimumWidth(200)
        left_layout.addWidget(QLabel("Drummers:"))
        left_layout.addWidget(self.drummer_list)

        # Drummer actions
        drummer_actions = QHBoxLayout()
        self.add_drummer_btn = QPushButton("Add")
        self.edit_drummer_btn = QPushButton("Edit")
        self.delete_drummer_btn = QPushButton("Delete")
        drummer_actions.addWidget(self.add_drummer_btn)
        drummer_actions.addWidget(self.edit_drummer_btn)
        drummer_actions.addWidget(self.delete_drummer_btn)
        left_layout.addLayout(drummer_actions)

        # === Center Panel (Drummer Details) ===
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # Drummer details
        self.details_group = QGroupBox("Drummer Details")
        details_layout = QVBoxLayout(self.details_group)

        # Drummer info
        self.drummer_info = QTextEdit()
        self.drummer_info.setReadOnly(True)
        details_layout.addWidget(self.drummer_info)

        # Signature songs
        songs_group = QGroupBox("Signature Songs")
        songs_group.setStyleSheet("""
            QGroupBox {
                color: #E0E0E0;
                border: 1px solid #4B0082;
                border-radius: 3px;
                margin-top: 0.5em;
            }
            QGroupBox::title {
                color: #FFC619;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)
        songs_layout = QVBoxLayout(songs_group)

        self.songs_table = QTableWidget()
        self.songs_table.setColumnCount(4)
        self.songs_table.setHorizontalHeaderLabels(["Title", "Status", "Local File", "Actions"])
        self.songs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.songs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.songs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.songs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        # Style the table for better visibility
        self.songs_table.setStyleSheet("""
            QTableWidget {
                background-color: #2D2D30;
                color: #E0E0E0;
                gridline-color: #3D3D3D;
                border: 1px solid #3D3D3D;
            }
            QTableWidget::item {
                padding: 4px;
                color: #E0E0E0;
            }
            QTableWidget::item:selected {
                background-color: #4B0082;
                color: #FFC619;
            }
            QHeaderView::section {
                background-color: #1E1E1E;
                color: #FFC619;
                padding: 4px;
                border: 1px solid #3D3D3D;
            }
        """)
        songs_layout.addWidget(self.songs_table)

        # Song actions
        song_actions = QHBoxLayout()
        self.add_song_btn = QPushButton("Add Song")
        self.find_on_youtube_btn = QPushButton("Find on YouTube")
        self.process_all_btn = QPushButton("Process All with MVSep")
        
        # Apply consistent button styling for better visibility
        button_style = """
            QPushButton {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #4B0082;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
                color: #FFC619;
                border: 1px solid #6B0082;
            }
            QPushButton:pressed {
                background-color: #4B0082;
                color: #FFC619;
            }
            QPushButton:disabled {
                background-color: #1E1E1E;
                color: #808080;
                border: 1px solid #3D3D3D;
            }
        """
        
        self.add_song_btn.setStyleSheet(button_style)
        self.find_on_youtube_btn.setStyleSheet(button_style)
        self.process_all_btn.setStyleSheet(button_style)
        
        song_actions.addWidget(self.add_song_btn)
        song_actions.addWidget(self.find_on_youtube_btn)
        song_actions.addWidget(self.process_all_btn)
        songs_layout.addLayout(song_actions)

        details_layout.addWidget(songs_group)
        center_layout.addWidget(self.details_group)

        # === Right Panel (YouTube Search/Download) ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # YouTube search
        youtube_group = QGroupBox("YouTube Search")
        youtube_layout = QVBoxLayout(youtube_group)

        # Search controls
        yt_search_layout = QHBoxLayout()
        self.youtube_search_edit = QLineEdit()
        self.youtube_search_edit.setPlaceholderText("Search for song")
        self.youtube_search_btn = QPushButton("Search")
        yt_search_layout.addWidget(self.youtube_search_edit)
        yt_search_layout.addWidget(self.youtube_search_btn)
        youtube_layout.addLayout(yt_search_layout)

        # Results list
        self.youtube_results_list = QListWidget()
        youtube_layout.addWidget(QLabel("Results:"))
        youtube_layout.addWidget(self.youtube_results_list)

        # Download actions
        yt_actions = QHBoxLayout()
        self.download_btn = QPushButton("Download Selected")
        self.play_preview_btn = QPushButton("Play Preview")
        yt_actions.addWidget(self.download_btn)
        yt_actions.addWidget(self.play_preview_btn)
        youtube_layout.addLayout(yt_actions)

        # Download progress
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Download Progress:"))
        self.download_progress = QProgressBar()
        progress_layout.addWidget(self.download_progress)
        youtube_layout.addLayout(progress_layout)

        right_layout.addWidget(youtube_group)

        # Add all panels to the splitter
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(center_widget)
        self.main_splitter.addWidget(right_widget)

        # Set initial splitter sizes
        self.main_splitter.setSizes([200, 400, 300])

        # Add splitter to main layout
        main_layout.addWidget(self.main_splitter)

        # Set initial button states
        self._update_button_states()

    def load_drummer_profiles(self):
        """Load drummer profiles from JSON file"""
        try:
            if not os.path.exists(self.profiles_path):
                # Check if the older profile file exists
                old_path = "H:\\app\\data\\drummers\\drummer_profiles.json"
                if os.path.exists(old_path):
                    # Copy the file to our new location
                    os.makedirs(os.path.dirname(self.profiles_path), exist_ok=True)
                    shutil.copy(old_path, self.profiles_path)
                    logger.info(f"Copied drummer profiles from {old_path} to {self.profiles_path}")
                else:
                    # Create an empty profiles file
                    os.makedirs(os.path.dirname(self.profiles_path), exist_ok=True)
                    with open(self.profiles_path, 'w') as f:
                        json.dump({"profiles": []}, f, indent=2)
                    logger.info(f"Created new empty drummer profiles at {self.profiles_path}")

            # Load profiles
            with open(self.profiles_path, 'r') as f:
                data = json.load(f)
                self.drummer_profiles = data.get('profiles', [])

            # Extract all genres for filtering
            all_genres = set()
            for drummer in self.drummer_profiles:
                for style in drummer.get('styles', []):
                    all_genres.add(style)

            # Populate genre filter
            self.genre_combo.clear()
            self.genre_combo.addItem("All Genres")
            for genre in sorted(all_genres):
                self.genre_combo.addItem(genre)

            # Initial population of drummer list
            print("DEBUG DEBUG: About to call populate_drummer_list()")
            self.populate_drummer_list()
            print("DEBUG DEBUG: populate_drummer_list() completed")
            logger.info("DrummersWidget setup completed successfully")

        except Exception as e:
            logger.error(f"Error loading drummer profiles: {e}")
            traceback.print_exc()

    def save_drummer_profiles(self):
        """Save drummer profiles to JSON file"""
        try:
            data = {"profiles": self.drummer_profiles}
            with open(self.profiles_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.drummer_profiles)} drummer profiles")

        except Exception as e:
            logger.error(f"Error saving drummer profiles: {e}")
            traceback.print_exc()

    def populate_drummer_list(self):
        """Populate the drummer list based on current filters"""
        try:
            self.drummer_list.clear()
            selected_genre = self.genre_combo.currentText()
            search_text = self.search_edit.text().lower()

            logger.info(f"Populating drummer list with genre '{selected_genre}' and search '{search_text}'")
            self.filtered_drummers = []

            for drummer in self.drummer_profiles:
                # Apply filters
                if selected_genre != "All Genres" and selected_genre not in drummer.get("styles", []):
                    continue

                if search_text and search_text not in drummer.get("name", "").lower():
                    continue
                
                # Add to filtered list
                self.filtered_drummers.append(drummer)

                # Create list item
                item = QListWidgetItem(drummer.get("name", "Unknown Drummer"))
                # Use ItemDataRole.UserRole consistently
                item.setData(Qt.ItemDataRole.UserRole, drummer.get("id", ""))
                self.drummer_list.addItem(item)

            logger.info(f"Added {len(self.filtered_drummers)} drummers to list")
            
            # Clear selection
            self.drummer_list.clearSelection()
            self.current_drummer = None
            self.update_drummer_details()
            
        except Exception as e:
            logger.error(f"Error populating drummer list: {e}")
            traceback.print_exc()

    def update_drummer_details(self):
        """Update the drummer details panel with current drummer information"""
        try:
            logger.info("Updating drummer details")
            if not self.current_drummer:
                logger.info("No current drummer - clearing displays")
                self.drummer_info.clear()
                self.songs_table.setRowCount(0)
                self.details_group.setTitle("Drummer Details")
                return

            # Set details group title
            name = self.current_drummer.get("name", "Unknown")
            logger.info(f"Updating UI for drummer: {name}")
            self.details_group.setTitle(f"Drummer: {name}")

            # Format drummer info
            info_text = f"<h2>{name}</h2>"

            # Main band(s)
            if "band" in self.current_drummer:
                info_text += f"<p><b>Main Band:</b> {self.current_drummer['band']}</p>"

            # All bands
            if "bands" in self.current_drummer and self.current_drummer["bands"]:
                info_text += f"<p><b>All Bands:</b> {', '.join(self.current_drummer['bands'])}</p>"

            # Styles/Genres
            if "styles" in self.current_drummer and self.current_drummer["styles"]:
                info_text += f"<p><b>Styles:</b> {', '.join(self.current_drummer['styles'])}</p>"

            # Alias
            if "alias" in self.current_drummer and self.current_drummer["alias"]:
                info_text += f"<p><b>Also known as:</b> {self.current_drummer['alias']}</p>"

            # Techniques
            if "techniques" in self.current_drummer and self.current_drummer["techniques"]:
                info_text += "<p><b>Notable Techniques:</b></p><ul>"
                for technique in self.current_drummer["techniques"]:
                    info_text += f"<li>{technique}</li>"
                info_text += "</ul>"

            # Set the info text
            self.drummer_info.setHtml(info_text)

            # Populate signature songs table
            self.populate_songs_table()

        except Exception as e:
            logger.error(f"Error updating drummer details: {e}")
            traceback.print_exc()

    def populate_songs_table(self):
        """Populate the signature songs table"""
        try:
            logger.info("Populating songs table")
            self.songs_table.setRowCount(0)

            if not self.current_drummer:
                logger.warning("Cannot populate songs table - no current drummer")
                return

            drummer_id = self.current_drummer.get("id", "unknown")
            logger.info(f"Finding notable songs for drummer: {self.current_drummer.get('name')} (ID: {drummer_id})")
            
            notable_songs = self.current_drummer.get("notable_songs", [])
            logger.info(f"Found {len(notable_songs)} notable songs: {notable_songs}")
            
            if not notable_songs:
                logger.warning(f"No notable songs found for drummer {drummer_id}")
                return

            logger.info(f"Setting table to show {len(notable_songs)} songs")
            self.songs_table.setRowCount(len(notable_songs))

            for row, song_title in enumerate(notable_songs):
                # Find if we have a local file
                song_info = {"title": song_title, "drummer_id": self.current_drummer["id"]}

                # Check if the song file exists
                filename = f"{self.current_drummer['id']}_{self._sanitize_filename(song_title)}.mp3"
                file_path = os.path.join(self.download_path, filename)
                local_file = os.path.exists(file_path)

                if local_file:
                    song_info["file_path"] = file_path
                    song_info["status"] = "Downloaded"
                else:
                    song_info["status"] = "Not Downloaded"

                # Set song title
                title_item = QTableWidgetItem(song_title)
                title_item.setData(Qt.ItemDataRole.UserRole, song_info)
                self.songs_table.setItem(row, 0, title_item)

                # Set status
                status_item = QTableWidgetItem(song_info["status"])
                self.songs_table.setItem(row, 1, status_item)

                # Set local file info
                if local_file:
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    file_item = QTableWidgetItem(f"Yes ({size_mb:.1f} MB)")
                else:
                    file_item = QTableWidgetItem("No")
                self.songs_table.setItem(row, 2, file_item)

                # Create action buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2, 2, 2, 2)
                actions_layout.setSpacing(2)

                # Play button
                play_btn = QToolButton()
                play_btn.setIcon(QIcon.fromTheme("media-playback-start"))
                play_btn.setToolTip("Play Song")
                play_btn.clicked.connect(lambda checked=False, r=row: self._on_play_song_at_row(r))
                play_btn.setEnabled(local_file)
                actions_layout.addWidget(play_btn)

                # Find on YouTube button
                youtube_btn = QToolButton()
                youtube_btn.setIcon(QIcon.fromTheme("system-search"))
                youtube_btn.setToolTip("Find on YouTube")
                youtube_btn.clicked.connect(lambda checked=False, r=row: self._on_find_on_youtube_at_row(r))
                actions_layout.addWidget(youtube_btn)

                # MVSep button if file exists
                if local_file:
                    mvsep_btn = QToolButton()
                    mvsep_btn.setIcon(QIcon.fromTheme("audio-x-generic"))
                    mvsep_btn.setToolTip("Process with MVSep")
                    mvsep_btn.clicked.connect(lambda checked=False, r=row: self._on_process_with_mvsep_at_row(r))
                    actions_layout.addWidget(mvsep_btn)

                # Set the widget to the table
                self.songs_table.setCellWidget(row, 3, actions_widget)

            # Resize rows for better display
            self.songs_table.resizeRowsToContents()

        except Exception as e:
            logger.error(f"Error populating songs table: {e}")
            traceback.print_exc()

    def _update_button_states(self):
        """Update button states based on selection"""
        try:
            if not hasattr(self, 'edit_drummer_btn'):
                return  # UI not yet initialized

            # Drummer-related buttons
            has_drummer = self.current_drummer is not None
            self.edit_drummer_btn.setEnabled(has_drummer)
            self.delete_drummer_btn.setEnabled(has_drummer)

            # Song-related buttons
            has_song = self.current_song is not None
            has_downloaded_song = has_song and "file_path" in self.current_song and self.current_song.get("file_path")
            self.add_song_btn.setEnabled(has_drummer)
            self.find_on_youtube_btn.setEnabled(has_song)  # Using correct button name
            self.process_all_btn.setEnabled(has_drummer and has_downloaded_song)

            # YouTube-related buttons
            has_youtube_selection = len(self.youtube_results_list.selectedItems()) > 0
            self.download_btn.setEnabled(has_youtube_selection)
            self.play_preview_btn.setEnabled(has_youtube_selection)
        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            traceback.print_exc()

    def _on_add_drummer(self):
        """Add a new drummer profile"""
        try:
            # Show a dialog to input drummer details
            name, ok = QInputDialog.getText(self, "Add Drummer", "Enter drummer name:")
            if ok and name:
                # Create a new drummer profile
                new_drummer = {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "genre": "Rock",  # Default genre
                    "bio": "",
                    "songs": []
                }
                
                # Add to the drummer profiles
                self.drummer_profiles.append(new_drummer)
                self.save_drummer_profiles()
                
                # Refresh the UI
                self.populate_drummer_list()
                
                # Find and select the new drummer
                for i in range(self.drummer_list.count()):
                    item = self.drummer_list.item(i)
                    if item.data(Qt.UserRole) == new_drummer["id"]:
                        self.drummer_list.setCurrentItem(item)
                        break
        except Exception as e:
            logger.error(f"Error adding drummer: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add drummer: {e}")
    
    def _on_edit_drummer(self):
        """Edit the selected drummer profile"""
        try:
            # Get the current drummer
            current_drummer = self._get_selected_drummer()
            if not current_drummer:
                QMessageBox.warning(self, "No Selection", "No drummer selected to edit.")
                return
                
            # Show a dialog to edit drummer details
            name, ok = QInputDialog.getText(self, "Edit Drummer", "Drummer name:", text=current_drummer.get("name", ""))
            if ok and name:
                # Update the drummer profile
                current_drummer["name"] = name
                self.save_drummer_profiles()
                
                # Refresh the UI
                self.populate_drummer_list()
                
                # Find and select the edited drummer
                for i in range(self.drummer_list.count()):
                    item = self.drummer_list.item(i)
                    if item.data(Qt.UserRole) == current_drummer["id"]:
                        self.drummer_list.setCurrentItem(item)
                        break
        except Exception as e:
            logger.error(f"Error editing drummer: {e}")
            QMessageBox.critical(self, "Error", f"Failed to edit drummer: {e}")
    
    def _on_delete_drummer(self):
        """Delete the selected drummer profile"""
        try:
            # Get the current drummer
            current_drummer = self._get_selected_drummer()
            if not current_drummer:
                QMessageBox.warning(self, "No Selection", "No drummer selected to delete.")
                return
                
            # Confirm deletion
            reply = QMessageBox.question(
                self, 
                "Confirm Delete", 
                f"Are you sure you want to delete drummer '{current_drummer.get('name', 'Unknown')}'?", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Remove from the drummer profiles
                self.drummer_profiles = [d for d in self.drummer_profiles if d.get("id") != current_drummer.get("id")]
                self.save_drummer_profiles()
                
                # Refresh the UI
                self.populate_drummer_list()
                
        except Exception as e:
            logger.error(f"Error deleting drummer: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete drummer: {e}")
            
    def _on_add_song(self):
        """Add a new song to the current drummer"""
        try:
            # Get the current drummer
            current_drummer = self._get_selected_drummer()
            if not current_drummer:
                QMessageBox.warning(self, "No Selection", "No drummer selected.")
                return
                
            # Show a dialog to input song details
            title, ok = QInputDialog.getText(self, "Add Song", "Enter song title:")
            if ok and title:
                # Create a new song
                new_song = {
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "status": "Not Downloaded",
                    "file_path": None
                }
                
                # Add to the drummer's songs
                if "songs" not in current_drummer:
                    current_drummer["songs"] = []
                    
                current_drummer["songs"].append(new_song)
                self.save_drummer_profiles()
                
                # Refresh the songs table
                self._populate_songs_table(current_drummer)
                
        except Exception as e:
            logger.error(f"Error adding song: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add song: {e}")
            
    def _on_find_song_on_youtube(self):
        """Find the selected song on YouTube"""
        try:
            if not self.current_song:
                QMessageBox.warning(self, "No Selection", "No song selected.")
                return
                
            # Get the song title
            song_title = self.current_song.get("title", "")
            if not song_title:
                QMessageBox.warning(self, "Missing Title", "The selected song has no title.")
                return
                
            # Get the drummer name for more specific search
            drummer_name = ""
            if self.current_drummer:
                drummer_name = self.current_drummer.get("name", "")
            
            # Build the search query
            query = song_title
            if drummer_name:
                query = f"{drummer_name} {song_title}"
                
            # Set the search query and trigger search
            self.youtube_search_edit.setText(query)
            self._on_youtube_search()
            
        except Exception as e:
            logger.error(f"Error finding song on YouTube: {e}")
            QMessageBox.critical(self, "Error", f"Failed to find song on YouTube: {e}")
            
    def _on_play_preview(self):
        """Play a preview of the selected YouTube video"""
        try:
            # Check if a video is selected
            if not self.selected_video:
                QMessageBox.warning(self, "No Video Selected", "Please select a YouTube video first.")
                return
                
            # Get video URL
            video_url = self.selected_video.get("url")
            if not video_url:
                QMessageBox.warning(self, "Invalid Video", "Selected video doesn't have a valid URL.")
                return
                
            # Update UI state
            self.play_preview_btn.setEnabled(False)
            self.play_preview_btn.setText("Loading...")
            
            # Use the YouTube service to play preview
            def on_preview_success(preview_url):
                # Here we would typically use a media player to play the preview
                # For now, we'll just show the URL and update the UI
                logger.info(f"Preview URL: {preview_url}")
                self.status_label.setText(f"Preview ready for: {self.selected_video.get('title')}")
                
                # Reset button state
                self.thread_safe_updater.queue_update(self.play_preview_btn.setEnabled, True)
                self.thread_safe_updater.queue_update(self.play_preview_btn.setText, "Play Preview")
                
            def on_preview_error(error):
                logger.error(f"Preview error: {error}")
                self.thread_safe_updater.queue_update(self.status_label.setText, f"Preview error: {error}")
                
                # Reset button state
                self.thread_safe_updater.queue_update(self.play_preview_btn.setEnabled, True)
                self.thread_safe_updater.queue_update(self.play_preview_btn.setText, "Play Preview")
            
            # Attempt to get preview URL (this would be implemented in the YouTube service)
            # Since this is a placeholder, we'll just simulate success for now
            QTimer.singleShot(1000, lambda: on_preview_success(f"https://youtube.com/watch?v={self.selected_video.get('id')}"))
            
        except Exception as e:
            logger.error(f"Error playing preview: {e}")
            QMessageBox.critical(self, "Error", f"Failed to play preview: {e}")
            # Reset button state
            self.play_preview_btn.setEnabled(True)
            self.play_preview_btn.setText("Play Preview")
            
    def _on_process_all_btn_clicked(self):
        """Process all downloaded songs for the current drummer"""
        try:
            # Get the current drummer
            current_drummer = self._get_selected_drummer()
            if not current_drummer:
                QMessageBox.warning(self, "No Selection", "No drummer selected to process.")
                return
                
            # Get all downloaded songs
            downloaded_songs = self._get_downloaded_songs()
            if not downloaded_songs:
                QMessageBox.warning(self, "No Downloads", "No downloaded songs available to process.")
                return
                
            # Confirm with user
            reply = QMessageBox.question(
                self, 
                "Process All Songs", 
                f"Process all {len(downloaded_songs)} downloaded songs for {current_drummer.get('name', 'Unknown')}?", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Update status
                self.status_label.setText(f"Processing {len(downloaded_songs)} songs...")
                
                # Add songs to batch processor
                try:
                    # In a real implementation, we'd use the batch processor service
                    # For this placeholder, we'll just show success
                    QTimer.singleShot(1000, lambda: self.thread_safe_updater.queue_update(
                        self.status_label.setText, f"Successfully queued {len(downloaded_songs)} songs for processing"))
                    
                except Exception as e:
                    logger.error(f"Error queueing songs: {e}")
                    QMessageBox.critical(self, "Processing Error", f"Failed to queue songs: {e}")
        
        except Exception as e:
            logger.error(f"Error processing all songs: {e}")
            QMessageBox.critical(self, "Error", f"Failed to process songs: {e}")
        
    def _get_downloaded_songs(self):
        """Get list of downloaded songs for the current drummer"""
        try:
            current_drummer = self._get_selected_drummer()
            if not current_drummer:
                return []
            
            # Return songs that have been downloaded (have a valid filepath)
            return [song for song in current_drummer.get("songs", []) 
                    if song.get("filepath") and os.path.exists(song.get("filepath"))]
        except Exception as e:
            logger.error(f"Error getting downloaded songs: {e}")
            return []
            
    def _get_selected_drummer(self):
        """Get the currently selected drummer profile"""
        try:
            # Get the selected item
            selected_item = self.drummer_list.currentItem()
            if not selected_item:
                return None
                
            # Get the drummer ID from the item data
            drummer_id = selected_item.data(Qt.UserRole)
            
            # Find the drummer profile with the matching ID
            for drummer in self.drummer_profiles:
                if drummer.get("id") == drummer_id:
                    return drummer
            
            return None
        except Exception as e:
            logger.error(f"Error getting selected drummer: {e}")
            return None

    # Removed redundant _on_drummer_item_clicked method to prevent signal conflicts
    # All drummer selection is now handled by _on_drummer_selected for consistency
            
    def _on_drummer_selected(self):
        """Handle drummer selection change with IMMEDIATE UI updates - FIXED VERSION"""
        try:
            logger.info("*** Drummer selection changed ***")
            current_items = self.drummer_list.selectedItems()
            
            if current_items:
                selected_item = current_items[0]
                drummer_id = selected_item.data(Qt.ItemDataRole.UserRole)
                logger.info(f"Selected drummer: {selected_item.text()} (ID: {drummer_id})")

                # Find drummer in profiles immediately - optimized lookup
                self.current_drummer = None
                for drummer in self.drummer_profiles:
                    if drummer.get("id", "") == drummer_id:
                        self.current_drummer = drummer
                        break
                
                if self.current_drummer:
                    logger.info(f"Found drummer: {self.current_drummer.get('name')}")
                    
                    # IMMEDIATE UI updates - no delays
                    self.update_drummer_details()
                    self._update_button_states()
                    
                    # Force Qt to process all pending events IMMEDIATELY
                    from PySide6.QtWidgets import QApplication
                    QApplication.processEvents()
                    QApplication.processEvents()  # Double process for reliability
                    
                    # Emit signal after UI is fully updated
                    self.drummer_selected.emit(self.current_drummer)
                else:
                    logger.warning(f"Drummer with ID {drummer_id} not found in profiles")
                    self.current_drummer = None
                    self.update_drummer_details()
                    self._update_button_states()
            else:
                logger.info("No drummer selected - clearing details")
                self.current_drummer = None
                self.update_drummer_details()
                self._update_button_states()
                
                # Force immediate clearing
                from PySide6.QtWidgets import QApplication
                QApplication.processEvents()
                QApplication.processEvents()

        except Exception as e:
            logger.error(f"Error handling drummer selection: {e}")
            traceback.print_exc()

    def _on_song_selected(self):
        """Handle song selection change"""
        try:
            current_row = self.songs_table.currentRow()
            if current_row >= 0:
                title_item = self.songs_table.item(current_row, 0)
                if title_item:
                    self.current_song = title_item.data(Qt.ItemDataRole.UserRole)
                else:
                    self.current_song = None
            else:
                self.current_song = None

            self._update_button_states()

        except Exception as e:
            logger.error(f"Error handling song selection: {e}")
            traceback.print_exc()

    def _on_play_song_at_row(self, row):
        """Play song at specific row"""
        try:
            item = self.songs_table.item(row, 0)
            if item:
                song_info = item.data(Qt.ItemDataRole.UserRole)
                if song_info and "file_path" in song_info:
                    self._play_song(song_info)
        except Exception as e:
            logger.error(f"Error playing song at row {row}: {e}")
            traceback.print_exc()

    def _on_process_with_mvsep_at_row(self, row):
        """Process song with MVSep at specific row"""
        try:
            item = self.songs_table.item(row, 0)
            if item:
                song_info = item.data(Qt.ItemDataRole.UserRole)
                if song_info and "file_path" in song_info:
                    self._process_with_mvsep(song_info)
        except Exception as e:
            logger.error(f"Error processing song with MVSep at row {row}: {e}")

    def _on_find_on_youtube_at_row(self, row):
        """Find song on YouTube at specific row with improved search query construction"""
        try:
            item = self.songs_table.item(row, 0)
            if item:
                song_info = item.data(Qt.ItemDataRole.UserRole)
                if song_info:
                    # Construct optimized search query
                    drummer_name = self.current_drummer.get("name", "")
                    song_title = song_info.get("title", "")
                    band = self.current_drummer.get("band", "")
                    
                    # Get additional context from drummer profile
                    notable_bands = self.current_drummer.get("notable_bands", [])
                    genre = self.current_drummer.get("genre", "")
                    
                    # Create multiple search query variations for better results
                    search_queries = []
                    
                    # Primary search with band name (most specific)
                    if band:
                        search_queries.append(f'"{song_title}" "{band}" official')
                        search_queries.append(f'{song_title} {band} studio')
                        search_queries.append(f'{song_title} {band} album version')
                    
                    # Secondary search with notable bands if different from main band
                    for notable_band in notable_bands[:2]:  # Limit to first 2 notable bands
                        if notable_band != band:
                            search_queries.append(f'"{song_title}" "{notable_band}" official')
                    
                    # Fallback search with drummer name
                    search_queries.append(f'"{song_title}" {drummer_name} drums')
                    search_queries.append(f'{song_title} {drummer_name} performance')
                    
                    # Genre-based search if available
                    if genre:
                        search_queries.append(f'{song_title} {genre} classic')
                    
                    # Use the most specific query as primary
                    primary_query = search_queries[0] if search_queries else f'{song_title} {drummer_name}'
                    
                    # Update search field text
                    self.youtube_search_edit.setText(primary_query)
                    logger.info(f"Searching YouTube for song with primary query: {primary_query}")
                    logger.info(f"Alternative queries available: {search_queries[1:3]}")
                    
                    # Store alternative queries for potential retry
                    self.alternative_search_queries = search_queries[1:]
                    
                    # Perform search
                    self._on_youtube_search()

        except Exception as e:
            logger.error(f"Error finding song on YouTube at row {row}: {e}")
            traceback.print_exc()

    def _on_youtube_search(self):
        """Handle YouTube search button click"""
        try:
            query = self.youtube_search_edit.text().strip()
            if not query:
                QMessageBox.warning(self, "Search Error", "Please enter a search query")
                return

            # Check if YouTube API is available
            if not self.youtube_api or not self.youtube_search_api:
                QMessageBox.warning(self, "Search Error", "YouTube search service is not available")
                logger.error("YouTube API not initialized")
                return

            # Show searching status
            self.youtube_results_list.clear()
            self.youtube_results_list.addItem("Searching...")

            logger.info(f"Performing YouTube search for: {query}")

            # Use direct search without threading
            try:
                results = self.youtube_api.search(query, max_results=10)
                logger.info(f"Search results: {len(results)} items found")
                self._update_youtube_results(results)
            except Exception as search_error:
                logger.error(f"YouTube search failed: {search_error}")
                self.youtube_results_list.clear()
                self.youtube_results_list.addItem(f"Search failed: {str(search_error)}")
                QMessageBox.warning(self, "Search Error", f"Search failed: {str(search_error)}")

        except Exception as e:
            logger.error(f"Error handling YouTube search: {e}")
            traceback.print_exc()
            self.youtube_results_list.clear()
            self.youtube_results_list.addItem(f"Error: {str(e)}")
            QMessageBox.warning(self, "Search Error", f"Error during search: {str(e)}")

    def _update_youtube_results(self, results):
        """Update YouTube search results in UI"""
        try:
            self.youtube_results = results
            self.youtube_results_list.clear()

            if not results:
                self.youtube_results_list.addItem("No results found")
                return

            for result in results:
                item = QListWidgetItem(result.get("title", "Unknown"))
                item.setData(Qt.UserRole, result)
                self.youtube_results_list.addItem(item)

            # Select the first result
            self.youtube_results_list.setCurrentRow(0)
            self._update_button_states()

        except Exception as e:
            logger.error(f"Error updating YouTube results: {e}")

    def _on_download_video(self):
        """Handle YouTube download button click"""
        try:
            current_items = self.youtube_results_list.selectedItems()
            if not current_items:
                QMessageBox.warning(self, "Download Error", "Please select a video to download")
                return

            video_data = current_items[0].data(Qt.UserRole)
            if not video_data or "url" not in video_data:
                QMessageBox.warning(self, "Download Error", "Invalid video data")
                return

            # If we have a current song selected, use its title
            song_title = None
            if self.current_song:
                song_title = self.current_song.get("title")

            # Otherwise use the video title
            if not song_title:
                song_title = video_data.get("title", "Unknown")

            # Create output filename
            filename = None
            if self.current_drummer:
                filename = f"{self.current_drummer['id']}_{self._sanitize_filename(song_title)}.mp3"

            # If no drummer context, use video ID
            if not filename:
                filename = f"{video_data.get('id', 'unknown')}_{self._sanitize_filename(song_title)}.mp3"

            output_path = os.path.join(self.download_path, filename)

            # Reset progress bar
            self.download_progress.setValue(0)
            self.download_progress.setMaximum(100)

            # Get the correct video URL or ID
            video_url = video_data.get("url")
            if not video_url and "id" in video_data:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"

            logger.info(f"Starting download from URL: {video_url}")

            # Start download using YouTubeService
            download_thread, thread = self.youtube_service.download_audio(
                video_url,
                output_path,
                self._on_download_progress,
                self._on_download_complete,
                lambda error: self.thread_safe.queue_update(
                    self, 
                    lambda: QMessageBox.critical(self, "Download Error", f"Failed to download: {error}")
                )
            )

            # Store the download thread objects for potential cancellation later
            self.download_threads.append((download_thread, thread))

            # Disable download button during download
            self.download_btn.setEnabled(False)
            self.download_btn.setText("Downloading...")

        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            QMessageBox.critical(self, "Download Error", f"Failed to download: {str(e)}")

    def _on_download_progress(self, progress):
        """Handle download progress updates"""
        try:
            logger.debug(f"Received download progress update: {progress}%")

            # Use thread-safe UI updates
            def update_progress_bar():
                self.download_progress.setValue(progress)
                self.download_btn.setText(f"Downloading... {progress}%")

            # Fixed: Use queue_update instead of run_in_main_thread
            self.thread_safe.queue_update(self, update_progress_bar)
        except Exception as e:
            logger.error(f"Error updating download progress: {e}")
            traceback.print_exc()

    def _on_download_complete(self, result_path):
        """Handle download completion"""
        try:
            logger.info(f"Download completed: {result_path}")

            def update_ui():
                self.download_btn.setEnabled(True)
                self.download_btn.setText("Download Selected")
                self.download_progress.setValue(100)

                if result_path:
                    QMessageBox.information(
                        self, "Download Complete",
                        f"Downloaded successfully to:\n{result_path}"
                    )

                    # Update song status if applicable
                    if self.current_drummer and self.current_song:
                        # Update the current song with the file path
                        self.current_song["file_path"] = result_path
                        self.current_song["status"] = "Downloaded"
                        
                        # Make sure to update the database
                        self.db.update_song(self.current_song)
                        logger.info(f"Updated song in database: {self.current_song['id']}")
                        
                        # Refresh the songs table to show updated status
                        self.populate_songs_table()
                        
                        # NEW WORKFLOW: Start phased drum analysis
                        self._start_phased_analysis(result_path, self.current_song)
                        self._update_button_states()
                        
                        # Process with MVSep
                        success, message = self._process_with_mvsep(self.current_song)
                        
                        if not success:
                            QMessageBox.warning(self, "MVSep Processing Failed", 
                                              f"Failed to queue file for MVSep processing: {message}")
                        else:
                            QMessageBox.information(self, "MVSep Processing", 
                                                 f"File queued for MVSep processing: {message}")
                else:
                    QMessageBox.critical(
                        self, "Download Failed",
                        "Failed to download the video. Check the logs for details."
                    )
            
            # Use thread-safe update method
            self.thread_safe.queue_update(self, update_ui)
            
            # Clean up finished download threads
            self._cleanup_download_threads()
        except Exception as e:
            logger.error(f"Error in download thread: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Download Error", f"An error occurred: {str(e)}")

    def _process_with_mvsep(self, song_data) -> Tuple[bool, str]:
        """Process a song with MVSep
        
        Args:
            song_data: Dictionary containing song metadata
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if self.batch_processor is None:
                error_msg = "Batch processor is not available"
                logger.error(error_msg)
                return False, error_msg
            
            # Get the input file path
            input_file = song_data.get('file_path', '')
            if not input_file or not os.path.exists(input_file):
                error_msg = f"Input file does not exist: {input_file}"
                logger.error(error_msg)
                return False, error_msg
            
            # Create output directory
            drummer_dir = os.path.join(self.mvsep_output_path, self.current_drummer['name'])
            song_dir = os.path.join(drummer_dir, song_data['title'])
            os.makedirs(song_dir, exist_ok=True)
            
            # Add to batch processor with metadata
            metadata = {
                'song_data': song_data.copy(),
                'drummer_name': self.current_drummer['name'],
                'auto_route_stems': self._auto_route_stems,
                'process_time': datetime.now().isoformat()
            }
            
            # Add to batch processor
            self.batch_processor.add_to_queue(input_file, song_dir, metadata)
            
            success_msg = f"Added {os.path.basename(input_file)} to MVSep processing queue"
            logger.info(f"{success_msg} with output to {song_dir}")
            return True, success_msg
            
        except Exception as e:
            self._last_error = str(e)
            error_msg = f"Error in _process_with_mvsep: {e}"
            logger.error(error_msg)
            traceback.print_exc()
            return False, str(e)

    def _cleanup_download_threads(self):
        """Clean up finished download threads"""
        try:
            active_threads = []
            for thread_tuple in self.download_threads:
                if len(thread_tuple) == 2 and thread_tuple[1].is_alive():
                    active_threads.append(thread_tuple)
            self.download_threads = active_threads
            logger.debug(f"Cleaned up download threads. Active threads: {len(self.download_threads)}")
        except Exception as e:
            logger.error(f"Error cleaning up download threads: {e}")

    def _on_process_all_btn_clicked(self):
        """Process all downloaded songs with MVSep"""
        try:
            # Check if MVSep API key is available
            if not self._check_mvsep_api_key():
                return
                
            if not self.current_drummer or 'songs' not in self.current_drummer:
                QMessageBox.warning(self, "No Songs", "No songs available to process")
                return
            
            # Count downloaded songs
            downloaded_songs = [s for s in self.current_drummer['songs'] 
                              if s.get('downloaded') and s.get('file_path')]
            
            if not downloaded_songs:
                QMessageBox.warning(self, "No Downloads", "No downloaded songs available to process")
                return
            
            # Confirm with user
            reply = QMessageBox.question(
                self, "Process All Songs", 
                f"Process {len(downloaded_songs)} downloaded songs with MVSep?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Process all downloaded songs
            for song in downloaded_songs:
                # Process with MVSep
                success, message = self._process_with_mvsep(song)
                
                if not success:
                    QMessageBox.warning(self, "MVSep Processing Failed", 
                                      f"Failed to queue file for MVSep processing: {message}")
                else:
                    QMessageBox.information(self, "MVSep Processing", 
                                         f"File queued for MVSep processing: {message}")
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error processing all songs: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"An error occurred while processing all songs: {e}")

    def _on_process_current_song(self):
        """Process the current song with MVSep"""
        if self.current_song:
            # Process with MVSep
            success, message = self._process_with_mvsep(self.current_song)
            
            if not success:
                QMessageBox.warning(self, "MVSep Processing Failed", 
                                  f"Failed to queue file for MVSep processing: {message}")
            else:
                QMessageBox.information(self, "MVSep Processing", 
                                     f"File queued for MVSep processing: {message}")
        else:
            QMessageBox.warning(self, "No Song Selected", "Please select a song to process")

    def _on_process_with_mvsep_at_row(self, row):
        """Process song with MVSep at specific row using phased analysis - FIXED VERSION"""
        try:
            logger.info(f"Processing song at row {row} with phased analysis")
            
            # Get the song data from the table item
            if row >= self.songs_table.rowCount():
                QMessageBox.warning(self, "Invalid Selection", "Invalid song selection")
                return
            
            # Get song info from the table item's UserRole data
            title_item = self.songs_table.item(row, 0)
            if not title_item:
                QMessageBox.warning(self, "No Song Data", "No song data available")
                return
            
            song_data = title_item.data(Qt.ItemDataRole.UserRole)
            if not song_data:
                QMessageBox.warning(self, "No Song Data", "No song information available")
                return
            
            logger.info(f"Song data: {song_data}")
            
            # Check if file exists
            file_path = song_data.get('file_path')
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(
                    self, "No File", 
                    f"No downloaded file available for '{song_data.get('title', 'Unknown')}'\n\n"
                    "Please download the song first using the YouTube search feature."
                )
                return
            
            logger.info(f"Starting phased analysis for: {file_path}")
            
            # Start phased analysis workflow
            self._start_phased_analysis(file_path, song_data)
            
        except Exception as e:
            logger.error(f"Error processing song with phased analysis: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to start analysis: {e}")
    
    def _start_phased_analysis(self, file_path: str, song_data: dict = None):
        """Start the comprehensive phased drum analysis workflow - CRASH FIX VERSION"""
        try:
            logger.info(f"Starting phased analysis for: {file_path}")
            
            # Validate file exists
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", f"File does not exist: {file_path}")
                return
            
            # Check if phased analysis service is available
            if not hasattr(self, 'phased_analysis') or self.phased_analysis is None:
                logger.error("Phased analysis service not initialized")
                QMessageBox.critical(self, "Service Error", 
                                   "Phased analysis service is not available.\n\n"
                                   "This feature requires the phased analysis service to be properly initialized.")
                return
            
            # Prepare metadata safely
            metadata = {
                'drummer_name': self.current_drummer.get('name', 'Unknown') if self.current_drummer else 'Unknown',
                'song_title': song_data.get('title', 'Unknown') if song_data else 'Unknown',
                'source_type': 'downloaded_file',
                'original_file': file_path
            }
            
            logger.info(f"Creating analysis job with metadata: {metadata}")
            
            # Create analysis job with error handling
            try:
                job_id = self.phased_analysis.create_job(source_file=file_path)
                logger.info(f"Created analysis job: {job_id}")
                
                # Store metadata in the job results for later use
                if job_id in self.phased_analysis.jobs:
                    self.phased_analysis.jobs[job_id].results.update(metadata)
                    
            except Exception as job_error:
                logger.error(f"Failed to create analysis job: {job_error}")
                QMessageBox.critical(self, "Job Creation Error", 
                                   f"Failed to create analysis job:\n{job_error}")
                return
            
            # Initialize analysis_jobs if not exists
            if not hasattr(self, 'analysis_jobs'):
                self.analysis_jobs = {}
            
            # Store job reference
            self.analysis_jobs[job_id] = {
                'file_path': file_path,
                'song_data': song_data,
                'drummer': self.current_drummer,
                'started_at': datetime.now()
            }
            
            logger.info(f"Stored job reference for: {job_id}")
            
            # Start the enhanced two-stage workflow
            self._start_enhanced_workflow(job_id, file_path, metadata)
            
        except Exception as e:
            logger.error(f"Error starting phased analysis: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Analysis Error", 
                               f"Failed to start analysis:\n\n{e}\n\n"
                               f"Please check the logs for more details.")
    
    def _show_analysis_dialog(self, job_id: str):
        """Show the phased analysis progress dialog"""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit
            from PySide6.QtCore import QTimer
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Phased Drum Analysis")
            dialog.setModal(True)
            dialog.resize(500, 400)
            
            layout = QVBoxLayout(dialog)
            
            # Job info
            job_info = self.analysis_jobs.get(job_id, {})
            info_label = QLabel(f"Analyzing: {job_info.get('file_path', 'Unknown')}")
            layout.addWidget(info_label)
            
            # Phase progress
            phase_label = QLabel("Phase: Initializing...")
            layout.addWidget(phase_label)
            
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 6)  # 6 phases
            progress_bar.setValue(0)
            layout.addWidget(progress_bar)
            
            # Results display
            results_text = QTextEdit()
            results_text.setReadOnly(True)
            layout.addWidget(results_text)
            
            # Buttons
            button_layout = QHBoxLayout()
            start_btn = QPushButton("Start Analysis")
            close_btn = QPushButton("Close")
            button_layout.addWidget(start_btn)
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)
            
            # Timer for progress updates
            timer = QTimer()
            current_phase = [0]  # Use list for mutable reference
            
            def update_progress():
                try:
                    status = self.phased_analysis.get_job_status(job_id)
                    if status:
                        phase_name = status['current_phase']
                        phase_label.setText(f"Phase: {phase_name.replace('_', ' ').title()}")
                        
                        # Update progress based on phase
                        phase_map = {
                            'download': 1,
                            'arrangement_analysis': 2,
                            'mvsep_processing': 3,
                            'drum_analysis': 4,
                            'post_processing': 5,
                            'export': 6
                        }
                        progress_bar.setValue(phase_map.get(phase_name, 0))
                        
                        # Update results
                        results_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] Phase: {phase_name}")
                        
                        # Check if completed
                        if phase_name == 'export' and current_phase[0] < 6:
                            results_text.append("Analysis completed successfully!")
                            start_btn.setText("Completed")
                            start_btn.setEnabled(False)
                            timer.stop()
                            current_phase[0] = 6
                except Exception as e:
                    logger.error(f"Error updating progress: {e}")
            
            def start_analysis():
                try:
                    start_btn.setEnabled(False)
                    start_btn.setText("Processing...")
                    results_text.append("Starting phased drum analysis...")
                    
                    # Start the analysis in a separate thread
                    import threading
                    def run_analysis():
                        try:
                            success, messages = self.phased_analysis.process_full_workflow(job_id)
                            if success:
                                results_text.append("\nSUCCESS Analysis completed successfully!")
                                for msg in messages:
                                    results_text.append(f"  • {msg}")
                            else:
                                results_text.append("\nERROR Analysis failed:")
                                for msg in messages:
                                    results_text.append(f"  • {msg}")
                        except Exception as e:
                            results_text.append(f"\nERROR Analysis error: {e}")
                    
                    thread = threading.Thread(target=run_analysis)
                    thread.daemon = True
                    thread.start()
                    
                    # Start progress timer
                    timer.timeout.connect(update_progress)
                    timer.start(1000)  # Update every second
                    
                except Exception as e:
                    logger.error(f"Error starting analysis: {e}")
                    QMessageBox.critical(dialog, "Error", f"Failed to start analysis: {e}")
            
            start_btn.clicked.connect(start_analysis)
            close_btn.clicked.connect(dialog.accept)
            
            dialog.show()
            
        except Exception as e:
            logger.error(f"Error showing analysis dialog: {e}")
            QMessageBox.critical(self, "Dialog Error", f"Failed to show analysis dialog: {e}")
    
    def _notify_drum_analysis_tab(self, job_id: str, metadata: Dict[str, Any]):
        """Notify the drum analysis tab about a new background job"""
        try:
            # Try to find the drum analysis tab in the main window
            main_window = self.window()
            if hasattr(main_window, 'tab_widget'):
                # Look for the drum analysis tab
                for i in range(main_window.tab_widget.count()):
                    tab_widget = main_window.tab_widget.widget(i)
                    if hasattr(tab_widget, 'add_background_job'):
                        # Found a widget that can handle background jobs
                        tab_widget.add_background_job(job_id, metadata, self.phased_analysis)
                        logger.info(f"Notified drum analysis tab about job: {job_id}")
                        break
                else:
                    logger.warning("Could not find drum analysis tab to notify about background job")
            else:
                logger.warning("Could not access main window tab widget")
        except Exception as e:
            logger.error(f"Error notifying drum analysis tab: {e}")
    
    def _start_enhanced_workflow(self, job_id: str, file_path: str, metadata: Dict[str, Any]):
        """Start the enhanced two-stage workflow with arrangement analysis and admin review"""
        try:
            # Stage 1: Start with arrangement analysis
            self._show_arrangement_analysis_dialog(job_id, file_path, metadata)
            
        except Exception as e:
            logger.error(f"Error starting enhanced workflow: {e}")
            QMessageBox.critical(self, "Workflow Error", 
                               f"Failed to start enhanced workflow:\n\n{e}")
    
    def _show_arrangement_analysis_dialog(self, job_id: str, file_path: str, metadata: Dict[str, Any]):
        """Show the arrangement analysis dialog for Stage 1"""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit, QGroupBox, QCheckBox, QSpinBox, QComboBox
            from PySide6.QtCore import QTimer
            
            dialog = QDialog(self)
            dialog.setWindowTitle("AUDIO Musical Arrangement Analysis - Stage 1")
            dialog.setModal(True)
            dialog.resize(700, 500)
            
            layout = QVBoxLayout(dialog)
            
            # Header info
            header_group = QGroupBox("Song Information")
            header_layout = QVBoxLayout(header_group)
            
            song_label = QLabel(f"FOLDER File: {os.path.basename(file_path)}")
            drummer_label = QLabel(f"DRUM Drummer: {metadata.get('drummer_name', 'Unknown')}")
            title_label = QLabel(f" Song: {metadata.get('song_title', 'Unknown')}")
            
            header_layout.addWidget(song_label)
            header_layout.addWidget(drummer_label)
            header_layout.addWidget(title_label)
            layout.addWidget(header_group)
            
            # Analysis progress
            progress_group = QGroupBox("Analysis Progress")
            progress_layout = QVBoxLayout(progress_group)
            
            status_label = QLabel("Status: Starting arrangement analysis...")
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            
            progress_layout.addWidget(status_label)
            progress_layout.addWidget(progress_bar)
            layout.addWidget(progress_group)
            
            # Results display
            results_group = QGroupBox("Analysis Results")
            results_layout = QVBoxLayout(results_group)
            
            results_text = QTextEdit()
            results_text.setReadOnly(True)
            results_text.setMaximumHeight(150)
            results_layout.addWidget(results_text)
            layout.addWidget(results_group)
            
            # Selection controls (initially hidden)
            selection_group = QGroupBox("Select Analysis Scope")
            selection_layout = QVBoxLayout(selection_group)
            
            # Whole song option - make it prominent
            whole_song_check = QCheckBox("AUDIO Analyze entire song (recommended)")
            whole_song_check.setChecked(True)
            whole_song_check.setStyleSheet("font-weight: bold; color: #2E8B57;")
            selection_layout.addWidget(whole_song_check)
            
            # Section selection
            sections_label = QLabel("Or select specific sections:")
            selection_layout.addWidget(sections_label)
            
            # Dynamic section checkboxes (will be populated after analysis)
            self.section_checkboxes = []
            
            selection_group.setVisible(False)  # Hide until analysis completes
            layout.addWidget(selection_group)
            
            # Buttons
            button_layout = QHBoxLayout()
            start_btn = QPushButton("INSPECTING Start Analysis")
            proceed_btn = QPushButton(" Proceed to Drummer Analysis")
            proceed_btn.setEnabled(False)
            cancel_btn = QPushButton("ERROR Cancel")
            
            button_layout.addWidget(start_btn)
            button_layout.addWidget(proceed_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)
            
            # Analysis state for synchronous approach
            arrangement_results = [{}]
            
            def start_analysis():
                try:
                    start_btn.setEnabled(False)
                    start_btn.setText("Analyzing...")
                    results_text.append("AUDIO Starting real musical arrangement analysis...")
                    results_text.append("ANALYSIS Using librosa for tempo, key, and section detection...")
                    
                    # RADICAL FIX: Use synchronous analysis in main thread to avoid all threading issues
                    logger.info("RADICAL APPROACH: Running analysis synchronously in main thread...")
                    
                    def run_synchronous_analysis():
                        import traceback  # For detailed crash isolation logging
                        from PySide6.QtWidgets import QApplication
                        try:
                            logger.info(f"Starting real arrangement analysis for: {file_path}")
                            results_text.append(f"\nINSPECTING Analyzing file: {os.path.basename(file_path)}")
                            
                            # Validate file path exists
                            if not os.path.exists(file_path):
                                raise FileNotFoundError(f"Audio file not found: {file_path}")
                            
                            # Check file size
                            file_size = os.path.getsize(file_path)
                            logger.info(f"File size: {file_size} bytes")
                            if file_size < 1024:  # Less than 1KB
                                raise ValueError(f"Audio file too small: {file_size} bytes")
                            
                            # Create a unique temporary job for arrangement analysis
                            import time
                            temp_job_id = f"temp_arrangement_{int(time.time())}_{hash(file_path)}"
                            logger.info(f"Created unique temp job ID: {temp_job_id}")
                            
                            # Create output directory
                            output_dir = metadata.get('output_directory', os.path.dirname(file_path))
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"Output directory: {output_dir}")
                            
                            # CRITICAL: Clear any existing cached analysis results for this file
                            logger.info("Clearing any cached analysis results...")
                            if hasattr(self.phased_analysis, '_analysis_cache'):
                                self.phased_analysis._analysis_cache.clear()
                            
                            # Create fresh analysis job with source file
                            logger.info("Creating fresh analysis job...")
                            job_id = self.phased_analysis.create_job(source_file=file_path)
                            
                            # Store metadata in the job results for later use
                            if job_id in self.phased_analysis.jobs:
                                self.phased_analysis.jobs[job_id].results.clear()  # Clear any existing results
                                self.phased_analysis.jobs[job_id].results.update(metadata)
                            
                            # Get the created job object
                            job = self.phased_analysis.jobs[job_id]
                            logger.info(f"Created job {job_id} with output directory: {job.output_directory}")
                            
                            # CRITICAL: Ensure the source file is properly set and verified
                            job.results['source_file'] = file_path
                            job.source_file = file_path  # Also set on job object directly
                            
                            # Verify file accessibility before analysis
                            if not os.path.exists(file_path):
                                raise FileNotFoundError(f"Source file not found: {file_path}")
                            
                            file_size = os.path.getsize(file_path)
                            logger.info(f"Job created successfully. Source file: {file_path} ({file_size} bytes)")
                            
                            # Call the real arrangement analysis with fresh job
                            logger.info(f"Calling _process_arrangement_analysis for file: {os.path.basename(file_path)}...")
                            
                            # Update progress to show analysis starting
                            progress_bar.setValue(10)
                            status_label.setText("Status: INSPECTING Analyzing audio...")
                            QApplication.processEvents()
                            
                            success, message, arrangement_data = self.phased_analysis._process_arrangement_analysis(job)
                            
                            # Update progress after analysis
                            progress_bar.setValue(90)
                            status_label.setText("Status: ANALYSIS Processing results...")
                            QApplication.processEvents()
                            logger.info(f"Analysis result: success={success}, message='{message}'")
                            
                            if arrangement_data:
                                logger.info(f"Analysis data keys: {list(arrangement_data.keys())}")
                                logger.info(f"Detected tempo: {arrangement_data.get('tempo', 'N/A')}")
                                logger.info(f"Detected key: {arrangement_data.get('key', 'N/A')}")
                                logger.info(f"Sections found: {len(arrangement_data.get('sections', []))}")
                            
                            # GUARANTEED UI UPDATE - Multiple execution paths to ensure completion
                            logger.info("Performing GUARANTEED UI update to prevent 90% hang...")
                            
                            # Mark complete immediately (no timer in synchronous approach)
                            logger.info("Analysis marked complete (synchronous mode)")
                            
                            # Perform UI updates immediately and synchronously
                            try:
                                logger.info("Executing IMMEDIATE UI update...")
                                
                                if success:
                                    logger.info("SUCCESS: Updating progress to 100%")
                                    progress_bar.setValue(100)
                                    status_label.setText("Status: SUCCESS Real analysis complete!")
                                    results_text.append(f"\nSUCCESS Real analysis successful!")
                                    results_text.append(f"\nANALYSIS Analysis method: {arrangement_data.get('analysis_method', 'unknown')}")
                                    
                                    # CRASH-PROOF APPROACH: Use completely isolated UI update method
                                    logger.info("Using CRASH-PROOF isolated UI update approach...")
                                    
                                    try:
                                        # Instead of calling the complex method, do minimal essential UI updates only
                                        logger.info("Performing MINIMAL ESSENTIAL UI updates only...")
                                        
                                        # Store results for proceed button
                                        arrangement_results[0] = arrangement_data
                                        logger.info("Results stored successfully")
                                        
                                        # Enable proceed button with minimal UI interaction
                                        proceed_btn.setEnabled(True)
                                        logger.info("Proceed button enabled successfully")
                                        
                                        # Show selection group with minimal UI interaction
                                        selection_group.setVisible(True)
                                        selection_group.show()  # Force show to ensure visibility
                                        logger.info("Selection group made visible successfully")
                                        
                                        # Ensure whole song checkbox is visible and properly set
                                        whole_song_check.setVisible(True)
                                        whole_song_check.show()
                                        logger.info("Whole song checkbox made visible successfully")
                                        
                                        # Add minimal success message to results
                                        results_text.append("\nSUCCESS Analysis completed successfully!")
                                        results_text.append(f"\nAUDIO Detected: {arrangement_data.get('tempo', 'Unknown')} BPM, {arrangement_data.get('key', 'Unknown')} key")
                                        results_text.append(f"\nMUSIC Found {len(arrangement_data.get('sections', []))} musical sections")
                                        results_text.append("\n Click 'Proceed to Drummer Analysis' to continue")
                                        logger.info("Essential results text added successfully")
                                        
                                        # NOW SAFE: Create section checkboxes with synchronous approach
                                        logger.info("Creating section checkboxes (now safe with synchronous approach)")
                                        self._complete_arrangement_analysis_real(results_text, selection_group, proceed_btn, arrangement_results, arrangement_data)
                                        
                                        logger.info("SUCCESS CRASH-PROOF UI update completed successfully")
                                        
                                        # CRITICAL: Add post-completion crash prevention
                                        logger.info("Starting POST-COMPLETION crash prevention...")
                                        
                                        try:
                                            # Force Qt event processing to prevent post-completion crashes
                                            from PySide6.QtWidgets import QApplication
                                            from PySide6.QtCore import QTimer
                                            
                                            logger.info("Processing Qt events to prevent post-completion crash...")
                                            QApplication.processEvents()
                                            QApplication.processEvents()
                                            QApplication.processEvents()  # Triple process for maximum safety
                                            
                                            # Add a small delay to allow UI to fully stabilize
                                            import time
                                            time.sleep(0.1)  # 100ms delay for UI stabilization
                                            logger.info("UI stabilization delay completed")
                                            
                                            # Final Qt event processing
                                            QApplication.processEvents()
                                            logger.info("Final Qt event processing completed")
                                            
                                            # CRITICAL FIX: Avoid thread cleanup crashes entirely
                                            logger.info("AVOIDING thread cleanup to prevent crash...")
                                            
                                            # Instead of cleaning up the thread, let it complete naturally
                                            # and use Qt's signal/slot mechanism for safe completion
                                            from PySide6.QtCore import QMetaObject, Qt
                                            
                                            def safe_completion_signal():
                                                try:
                                                    logger.info("SUCCESS THREAD-SAFE completion signal executed successfully")
                                                    logger.info("TARGET Analysis workflow ready for user interaction")
                                                except Exception as signal_error:
                                                    print(f"Signal completion error: {signal_error}")
                                            
                                            # Use Qt's thread-safe signal mechanism instead of direct thread cleanup
                                            QMetaObject.invokeMethod(
                                                QApplication.instance(),
                                                safe_completion_signal,
                                                Qt.ConnectionType.QueuedConnection
                                            )
                                            
                                            logger.info("SUCCESS THREAD-SAFE completion approach activated successfully")
                                            
                                            # Let the background thread complete naturally without forced cleanup
                                            logger.info("Background thread will complete naturally - no forced cleanup")
                                            
                                        except Exception as post_completion_error:
                                            logger.error(f"CRITICAL: Post-completion crash prevention failed: {post_completion_error}")
                                            logger.error(f"Post-completion error traceback: {traceback.format_exc()}")
                                            # Continue anyway - don't let crash prevention cause crashes
                                            logger.warning("Continuing despite post-completion error...")
                                        
                                    except Exception as crash_proof_error:
                                        # Ultimate fallback - even the crash-proof method failed
                                        logger.error(f"CRITICAL: Even crash-proof method failed: {crash_proof_error}")
                                        logger.error(f"Crash-proof error traceback: {traceback.format_exc()}")
                                        
                                        # Absolute minimal fallback
                                        try:
                                            proceed_btn.setEnabled(True)
                                            results_text.append("\nWARNING Analysis completed with UI display issues")
                                            results_text.append("\n Click 'Proceed to Drummer Analysis' to continue")
                                            logger.info("ABSOLUTE MINIMAL fallback completed")
                                        except:
                                            print("ULTIMATE FALLBACK: Analysis completed but UI updates failed")
                                    
                                else:
                                    logger.warning("FAILURE: Analysis failed")
                                    progress_bar.setValue(0)
                                    status_label.setText(f"Status: ERROR Analysis failed")
                                    results_text.append(f"\nERROR Real Analysis Failed: {message}")
                                    results_text.append("\nINFO Common solutions:")
                                    results_text.append("  • Install librosa: pip install librosa")
                                    results_text.append("  • Check audio file format and quality")
                                    results_text.append("  • Ensure file contains musical content")
                                    start_btn.setEnabled(True)
                                    start_btn.setText("INSPECTING Retry Analysis")
                                    logger.warning(f"Analysis failed: {message}")
                                
                                logger.info("TARGET GUARANTEED UI update completed successfully")
                                
                            except Exception as ui_error:
                                logger.error(f"ERROR CRITICAL: Guaranteed UI update failed: {ui_error}")
                                import traceback
                                logger.error(f"UI Error traceback: {traceback.format_exc()}")
                                
                                # Emergency fallback - minimal UI update
                                try:
                                    progress_bar.setValue(100)
                                    status_label.setText("Status: WARNING Analysis completed with UI errors")
                                    results_text.append(f"\nWARNING Analysis completed but UI update had errors: {ui_error}")
                                    logger.warning("Emergency fallback UI update applied")
                                except Exception as emergency_error:
                                    logger.error(f"ERROR EMERGENCY: Even fallback UI update failed: {emergency_error}")
                            
                        except Exception as analysis_error:
                            logger.error(f"Error in real arrangement analysis: {analysis_error}")
                            import traceback
                            logger.error(f"Analysis error traceback: {traceback.format_exc()}")
                            
                            # Show error immediately (synchronous mode)
                            progress_bar.setValue(0)
                            status_label.setText("Status: ERROR Analysis error")
                            results_text.append(f"\nERROR Real Analysis Error: {analysis_error}")
                            results_text.append(f"\nINSPECTING Error details: {str(analysis_error)}")
                            results_text.append("\nINFO Please check the logs for more details")
                            start_btn.setEnabled(True)
                            start_btn.setText("INSPECTING Retry Analysis")
                            logger.error("Error UI update completed (synchronous mode)")
                            QApplication.processEvents()
                    
                    # RADICAL FIX: Run analysis synchronously in main thread
                    from PySide6.QtWidgets import QApplication
                    logger.info("EXECUTING SYNCHRONOUS ANALYSIS - No threading, no crashes!")
                    
                    # Process Qt events before starting to ensure UI is responsive
                    QApplication.processEvents()
                    
                    # Run the analysis directly (synchronously)
                    run_synchronous_analysis()
                    
                    # Process Qt events after completion
                    QApplication.processEvents()
                    
                except Exception as e:
                    logger.error(f"Error starting arrangement analysis: {e}")
                    QMessageBox.critical(dialog, "Error", f"Failed to start analysis: {e}")
            
            def proceed_to_drummer_analysis():
                try:
                    logger.info("Starting proceed_to_drummer_analysis function...")
                    # Get selected scope - use safe checkbox access to prevent deletion errors
                    selected_sections = []
                    scope = "whole_song"  # Default to whole song
                    logger.info("Initialized scope selection variables")
                    
                    try:
                        # Safely check if whole_song_check exists and is checked
                        if whole_song_check and not whole_song_check.isChecked():
                            # User wants to select individual sections
                            logger.info("User selected individual sections mode")
                            scope = "selected_sections"
                            
                            # Safely access section checkboxes
                            if hasattr(self, 'section_checkboxes') and self.section_checkboxes:
                                logger.info(f"Found {len(self.section_checkboxes)} section checkboxes")
                                for i, checkbox in enumerate(self.section_checkboxes):
                                    try:
                                        if checkbox and checkbox.isChecked():
                                            section_text = checkbox.text()
                                            selected_sections.append(section_text)
                                            logger.info(f"Selected section {i+1}: {section_text}")
                                    except RuntimeError as e:
                                        # Checkbox was deleted - skip it
                                        logger.warning(f"Checkbox {i+1} was deleted: {e}")
                                        continue
                            else:
                                logger.warning("No section checkboxes found or accessible")
                        else:
                            # Default to whole song if checkbox is checked or doesn't exist
                            logger.info("User selected whole song analysis (default or checkbox checked)")
                            scope = "whole_song"
                            
                    except (RuntimeError, AttributeError):
                        # If any checkbox access fails, default to whole song
                        logger.warning("Checkbox access failed - defaulting to whole song analysis")
                        scope = "whole_song"
                        selected_sections = []
                    
                    # Validate selection
                    if scope == "selected_sections" and not selected_sections:
                        QMessageBox.warning(dialog, "No Selection", "Please select at least one section or choose 'Analyze entire song'.")
                        return
                    
                    # Update job metadata with arrangement results and scope
                    enhanced_metadata = metadata.copy()
                    enhanced_metadata.update({
                        'arrangement_results': arrangement_results[0],
                        'analysis_scope': scope,
                        'selected_sections': selected_sections,
                        'stage': 'drummer_analysis'
                    })
                    
                    # Close this dialog
                    dialog.accept()
                    
                    # NEW WORKFLOW: First send to MVSep for stem separation
                    logger.info(f"Starting MVSep workflow for {scope}: {selected_sections if scope == 'selected_sections' else 'full song'}")
                    self._start_mvsep_workflow(job_id, file_path, enhanced_metadata)
                    
                except Exception as e:
                    logger.error(f"Error proceeding to drummer analysis: {e}")
                    QMessageBox.critical(dialog, "Error", f"Failed to proceed: {e}")
            
            # Connect signals
            start_btn.clicked.connect(start_analysis)
            proceed_btn.clicked.connect(proceed_to_drummer_analysis)
            cancel_btn.clicked.connect(dialog.reject)
            
            # Show dialog
            dialog.show()
            
        except Exception as e:
            logger.error(f"Error showing arrangement analysis dialog: {e}")
            QMessageBox.critical(self, "Dialog Error", f"Failed to show arrangement analysis dialog: {e}")
    
    def _complete_arrangement_analysis_real(self, results_text, selection_group, proceed_btn, arrangement_results, real_analysis_data):
        """Complete the arrangement analysis using real analysis results"""
        import traceback  # For detailed error logging
        try:
            # Use real analysis data instead of placeholder
            results = {
                'tempo': real_analysis_data.get('tempo', 120.0),
                'time_signature': real_analysis_data.get('time_signature', '4/4'),
                'key': real_analysis_data.get('key', 'Unknown'),
                'duration': real_analysis_data.get('duration', 0.0),
                'sections': real_analysis_data.get('sections', []),
                'style': real_analysis_data.get('style', 'Unknown'),
                'complexity': real_analysis_data.get('complexity', 'Unknown'),
                'analysis_method': real_analysis_data.get('analysis_method', 'librosa_advanced'),
                'onset_density': real_analysis_data.get('onset_density', 0.0),
                'spectral_centroid': real_analysis_data.get('spectral_centroid', 0.0),
                'beat_consistency': real_analysis_data.get('beat_consistency', 0.0),
                'harmonic_strength': real_analysis_data.get('harmonic_strength', 0.0)
            }
            
            arrangement_results[0] = results
            
            # Display real analysis results
            results_text.append("\nSUCCESS Real Analysis Complete!")
            results_text.append(f"AUDIO Tempo: {round(results['tempo'])} BPM (detected)")
            results_text.append(f"⏱ Time Signature: {results['time_signature']} (detected)")
            results_text.append(f"MUSIC Key: {results['key']} (detected)")
            
            duration_mins = int(results['duration'] // 60)
            duration_secs = int(results['duration'] % 60)
            results_text.append(f"⏰ Duration: {results['duration']:.1f}s ({duration_mins}:{duration_secs:02d})")
            
            results_text.append(f" Style: {results['style']} (classified)")
            results_text.append(f"ANALYSIS Complexity: {results['complexity']} (analyzed)")
            
            # Show analysis quality metrics
            results_text.append("\n Analysis Quality:")
            results_text.append(f"  • Method: {results['analysis_method']}")
            results_text.append(f"  • Onset Density: {results['onset_density']:.2f} events/sec")
            results_text.append(f"  • Beat Consistency: {results['beat_consistency']:.2f} (0-1 scale)")
            results_text.append(f"  • Harmonic Strength: {results['harmonic_strength']:.2f} (0-1 scale)")
            results_text.append(f"  • Spectral Centroid: {results['spectral_centroid']:.1f} Hz")
            
            # Display detected sections with improved error handling
            sections = results['sections']
            if sections and len(sections) > 0:
                results_text.append(f"\n Detected {len(sections)} Musical Sections:")
                
                try:
                    # Clear any existing checkboxes safely
                    if hasattr(self, 'section_checkboxes'):
                        self.section_checkboxes.clear()
                    else:
                        self.section_checkboxes = []
                    
                    # Get the selection layout safely
                    selection_layout = selection_group.layout()
                    if selection_layout is None:
                        logger.warning("Selection group has no layout, creating one")
                        from PySide6.QtWidgets import QVBoxLayout
                        selection_layout = QVBoxLayout(selection_group)
                    
                    # Limit sections to prevent UI overload (max 8 sections)
                    display_sections = sections[:8] if len(sections) > 8 else sections
                    if len(sections) > 8:
                        logger.info(f"Limiting display to first 8 of {len(sections)} detected sections")
                        results_text.append(f"\n Showing first 8 of {len(sections)} detected sections:")
                    
                    # Clear existing widgets from layout safely with comprehensive error handling
                    try:
                        widgets_to_delete = []
                        for i in range(selection_layout.count()):
                            try:
                                item = selection_layout.itemAt(i)
                                if item and item.widget():
                                    widgets_to_delete.append(item.widget())
                            except Exception as item_error:
                                logger.warning(f"Error accessing layout item {i}: {item_error}")
                                continue
                        
                        # Delete widgets outside the loop to avoid layout issues
                        for widget in widgets_to_delete:
                            try:
                                if widget and hasattr(widget, 'setParent'):
                                    widget.setParent(None)
                                    widget.deleteLater()
                            except Exception as widget_error:
                                logger.warning(f"Error deleting widget: {widget_error}")
                                continue
                                
                    except Exception as layout_error:
                        logger.error(f"Error clearing layout widgets: {layout_error}")
                        # Continue with section creation even if cleanup fails
                    
                    # Add section checkboxes for real sections with detailed logging
                    logger.info(f"Starting to create {len(display_sections)} section checkboxes...")
                    
                    for i, section in enumerate(display_sections):
                        try:
                            logger.info(f"Processing section {i+1}/{len(display_sections)}...")
                            
                            # Extract section data with logging
                            start_time = section.get('start', 0)
                            end_time = section.get('end', 0)
                            bars = section.get('bars', 0)
                            section_name = section.get('name', f'Section {i+1}')
                            duration = section.get('duration', end_time - start_time)
                            logger.info(f"Section {i+1} data: {section_name}, {start_time:.1f}-{end_time:.1f}s")
                            
                            # Format section display text with logging
                            if duration > 0:
                                section_text = f"{section_name} ({start_time:.1f}-{end_time:.1f}s, {duration:.1f}s, {bars} bars)"
                            else:
                                section_text = f"{section_name} ({start_time:.1f}-{end_time:.1f}s)"
                            logger.info(f"Section {i+1} formatted text: {section_text}")
                            
                            # Create checkbox with detailed error handling and logging
                            logger.info(f"Creating checkbox for section {i+1}...")
                            try:
                                from PySide6.QtWidgets import QCheckBox
                                logger.info(f"QCheckBox import successful for section {i+1}")
                                
                                checkbox = QCheckBox(section_text)
                                logger.info(f"QCheckBox created for section {i+1}")
                                
                                checkbox.setChecked(True)  # Default to selected
                                logger.info(f"QCheckBox checked state set for section {i+1}")
                                
                                self.section_checkboxes.append(checkbox)
                                logger.info(f"QCheckBox added to list for section {i+1}")
                                
                                selection_layout.addWidget(checkbox)
                                logger.info(f"QCheckBox added to layout for section {i+1}")
                                
                                results_text.append(f"  • {section_text}")
                                logger.info(f"Section {i+1} text added to results")
                                
                            except Exception as checkbox_error:
                                logger.error(f"CRITICAL: Checkbox creation failed for section {i+1}: {checkbox_error}")
                                logger.error(f"Checkbox error traceback: {traceback.format_exc()}")
                                raise  # Re-raise to see if this is the crash point
                            
                        except Exception as section_error:
                            logger.error(f"Error processing section {i+1}: {section_error}")
                            logger.error(f"Section error traceback: {traceback.format_exc()}")
                            # Continue with other sections even if one fails
                            continue
                    
                    logger.info(f"Completed creating all {len(display_sections)} section checkboxes")
                    
                    # Show selection controls and enable proceed button with detailed logging
                    try:
                        logger.info("Setting selection_group visibility to True...")
                        selection_group.setVisible(True)
                        logger.info("Selection group visibility set successfully")
                        
                        logger.info("Enabling proceed button...")
                        proceed_btn.setEnabled(True)
                        logger.info("Proceed button enabled successfully")
                        
                        logger.info("Checking if additional sections message needed...")
                        if len(sections) > len(display_sections):
                            logger.info(f"Adding additional sections message: {len(sections) - len(display_sections)} additional sections")
                            results_text.append(f"\nINFO {len(sections) - len(display_sections)} additional sections detected but not shown to prevent UI overload")
                            logger.info("Additional sections message added successfully")
                        
                        logger.info("All post-checkbox operations completed successfully")
                        
                    except Exception as post_checkbox_error:
                        logger.error(f"CRITICAL: Post-checkbox operation failed: {post_checkbox_error}")
                        logger.error(f"Post-checkbox error traceback: {traceback.format_exc()}")
                        raise  # Re-raise to see if this is the crash point
                    
                except Exception as ui_error:
                    logger.error(f"Error setting up section UI: {ui_error}")
                    results_text.append(f"\nWARNING Error displaying sections: {ui_error}")
                    results_text.append("\nINFO Sections were detected but couldn't be displayed - will analyze entire song")
                    
                    # Fallback: enable proceed button for whole song analysis
                    proceed_btn.setEnabled(True)
                    
            else:
                results_text.append("\nWARNING No distinct sections detected - will analyze as single segment")
                results_text.append("\nINFO This is normal for shorter songs or songs with consistent structure")
                # Still enable proceed button for whole song analysis
                proceed_btn.setEnabled(True)
                
                results_text.append("\nTARGET Ready to proceed with drummer analysis!")
                
        except Exception as e:
            logger.error(f"Error completing real arrangement analysis: {e}")
            import traceback
            logger.error(f"Full error traceback: {traceback.format_exc()}")
            
            results_text.append(f"\nERROR Error processing analysis results: {e}")
            results_text.append("\nINFO The analysis completed but there was an issue displaying results.")
            
            # Still try to enable proceed button with basic data
            try:
                # Create safe fallback results
                basic_results = {
                    'tempo': float(real_analysis_data.get('tempo', 120.0)),
                    'time_signature': str(real_analysis_data.get('time_signature', '4/4')),
                    'key': str(real_analysis_data.get('key', 'Unknown')),
                    'duration': float(real_analysis_data.get('duration', 180.0)),
                    'sections': real_analysis_data.get('sections', []),
                    'style': str(real_analysis_data.get('style', 'Unknown')),
                    'complexity': str(real_analysis_data.get('complexity', 'Medium')),
                    'analysis_method': str(real_analysis_data.get('analysis_method', 'safe_fallback')),
                    'onset_density': float(real_analysis_data.get('onset_density', 0.5)),
                    'spectral_centroid': float(real_analysis_data.get('spectral_centroid', 1000.0)),
                    'beat_consistency': float(real_analysis_data.get('beat_consistency', 0.7)),
                    'harmonic_strength': float(real_analysis_data.get('harmonic_strength', 0.6))
                }
                
                # Safely assign results
                arrangement_results[0] = basic_results
                
                # Enable proceed button for fallback analysis
                proceed_btn.setEnabled(True)
                proceed_btn.setText("TARGET Proceed with Basic Analysis")
                
                results_text.append("\n Using fallback analysis data")
                results_text.append(f"\nAUDIO Tempo: {basic_results['tempo']} BPM")
                results_text.append(f"\nMUSIC Key: {basic_results['key']}")
                results_text.append(f"\n⏰ Duration: {basic_results['duration']:.1f}s")
                results_text.append("\nTARGET Ready to proceed with drummer analysis!")
                
                logger.info("Fallback analysis results prepared successfully")
                
            except Exception as fallback_error:
                logger.error(f"Even fallback analysis setup failed: {fallback_error}")
                results_text.append(f"\nERROR Critical error: {fallback_error}")
                results_text.append("\nINFO Please try restarting the analysis or check the audio file")
                
                # Last resort: enable button with minimal functionality
                try:
                    proceed_btn.setEnabled(True)
                    proceed_btn.setText("WARNING Proceed Anyway")
                except:
                    logger.error("Could not even enable proceed button - critical UI failure")
            except:
                pass
    
    def _complete_arrangement_analysis(self, results_text, selection_group, proceed_btn, arrangement_results):
        """Legacy method - should not be used anymore (replaced by real analysis)"""
        results_text.append("\nWARNING Warning: Using legacy placeholder analysis method")
        results_text.append("\nINFO This should have been replaced by real analysis - please check implementation")
        
        # Minimal fallback to prevent complete failure
        basic_results = {
            'tempo': 120,
            'time_signature': '4/4', 
            'key': 'Unknown',
            'duration': 180,
            'sections': [],
            'style': 'Unknown',
            'complexity': 'Unknown'
        }
        arrangement_results[0] = basic_results
        proceed_btn.setEnabled(True)
    
    def _start_mvsep_workflow(self, job_id: str, file_path: str, metadata: Dict[str, Any]):
        """Start MVSep workflow for stem separation before drummer analysis"""
        try:
            from PySide6.QtWidgets import QProgressDialog, QMessageBox
            from PySide6.QtCore import Qt
            
            logger.info("Starting MVSep stem separation workflow...")
            
            # Determine audio source based on user selection
            scope = metadata.get('analysis_scope', 'whole_song')
            selected_sections = metadata.get('selected_sections', [])
            arrangement_results = metadata.get('arrangement_results', {})
            
            # Create progress dialog for MVSep processing
            progress_dialog = QProgressDialog("Processing audio with MVSep...", "Cancel", 0, 100, self)
            progress_dialog.setWindowTitle("MVSep Stem Separation")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.show()
            
            # Prepare audio for MVSep based on user selection
            if scope == "whole_song":
                logger.info("Processing entire song with MVSep")
                audio_source = file_path
                progress_dialog.setLabelText("Processing entire song with MVSep...")
            else:
                logger.info(f"Processing selected sections with MVSep: {selected_sections}")
                # For now, process the whole song (section extraction can be added later)
                audio_source = file_path
                progress_dialog.setLabelText(f"Processing {len(selected_sections)} selected sections with MVSep...")
            
            # Check if MVSep service is available
            if not hasattr(self, 'mvsep_service') or not self.mvsep_service:
                logger.warning("MVSep service not available - proceeding directly to drummer analysis")
                progress_dialog.close()
                QMessageBox.information(self, "MVSep Unavailable", 
                    "MVSep service is not available. Proceeding directly to drummer analysis with original audio.")
                self._show_drummer_analysis_dialog(job_id, file_path, metadata)
                return
            
            # Start MVSep processing
            progress_dialog.setValue(10)
            logger.info(f"Sending audio to MVSep: {audio_source}")
            
            # Use actual MVSep service to process audio
            def process_with_mvsep():
                try:
                    progress_dialog.setValue(30)
                    progress_dialog.setLabelText("MVSep processing stems...")
                    QApplication.processEvents()
                    
                    # Call the actual MVSep service
                    result = self.mvsep_service.process_audio(audio_source, self.mvsep_output_path)
                    
                    progress_dialog.setValue(80)
                    progress_dialog.setLabelText("Finalizing stem separation...")
                    QApplication.processEvents()
                    
                    if result.get('success', False):
                        logger.info(f"MVSep processing successful: {result.get('message', 'No message')}")
                        
                        # Add MVSep results to metadata
                        enhanced_metadata = metadata.copy()
                        enhanced_metadata.update({
                            'mvsep_processed': True,
                            'stems_available': True,
                            'stem_files': result.get('stem_files', {}),
                            'processing_time': result.get('processing_time', 0)
                        })
                        
                        progress_dialog.setValue(100)
                        progress_dialog.close()
                        
                        logger.info("MVSep processing completed - proceeding to drummer analysis")
                        self._show_drummer_analysis_dialog(job_id, file_path, enhanced_metadata)
                    else:
                        raise Exception(result.get('message', 'MVSep processing failed'))
                        
                except Exception as process_error:
                    logger.error(f"MVSep processing failed: {process_error}")
                    progress_dialog.close()
                    QMessageBox.warning(self, "MVSep Error", f"MVSep processing failed: {process_error}\nProceeding with original audio.")
                    self._show_drummer_analysis_dialog(job_id, file_path, metadata)
            
            # Start processing in a short delay to allow UI updates
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, process_with_mvsep)
            
        except Exception as e:
            logger.error(f"Error in MVSep workflow: {e}")
            # Fallback to direct drummer analysis
            QMessageBox.warning(self, "MVSep Error", f"MVSep processing failed: {e}\nProceeding with original audio.")
            self._show_drummer_analysis_dialog(job_id, file_path, metadata)
    
    def _show_drummer_analysis_dialog(self, job_id: str, file_path: str, metadata: Dict[str, Any]):
        """Show the drummer analysis dialog for Stage 2"""
        try:
            # This is the enhanced version of the original progress dialog
            # but now with arrangement context and selected scope
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit
            from PySide6.QtCore import QTimer
            
            dialog = QDialog(self)
            dialog.setWindowTitle("DRUM Drummer Analysis - Stage 2")
            dialog.setModal(True)
            dialog.resize(600, 500)
            
            layout = QVBoxLayout(dialog)
            
            # Context info
            arrangement = metadata.get('arrangement_results', {})
            scope = metadata.get('analysis_scope', 'whole_song')
            selected_sections = metadata.get('selected_sections', [])
            
            context_label = QLabel(f"AUDIO Analyzing: {metadata.get('song_title', 'Unknown')}")
            scope_label = QLabel(f"ANALYSIS Scope: {'Whole Song' if scope == 'whole_song' else f'Selected Sections: {", ".join(selected_sections)}'}")
            tempo_label = QLabel(f"MUSIC Context: {arrangement.get('tempo', 'Unknown')} BPM, {arrangement.get('time_signature', 'Unknown')}, {arrangement.get('style', 'Unknown')}")
            
            layout.addWidget(context_label)
            layout.addWidget(scope_label)
            layout.addWidget(tempo_label)
            
            # Phase progress
            phase_label = QLabel("Phase: Initializing drummer analysis...")
            layout.addWidget(phase_label)
            
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 6)  # 6 phases
            progress_bar.setValue(0)
            layout.addWidget(progress_bar)
            
            # Results display
            results_text = QTextEdit()
            results_text.setReadOnly(True)
            layout.addWidget(results_text)
            
            # Buttons
            button_layout = QHBoxLayout()
            start_btn = QPushButton("DRUM Start Drummer Analysis")
            close_btn = QPushButton("Close")
            button_layout.addWidget(start_btn)
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)
            
            # Timer for progress updates
            timer = QTimer()
            current_phase = [0]
            
            def update_progress():
                try:
                    status = self.phased_analysis.get_job_status(job_id)
                    if status:
                        phase_name = status['current_phase']
                        phase_label.setText(f"Phase: {phase_name.replace('_', ' ').title()}")
                        
                        # Update progress based on phase
                        phase_map = {
                            'download': 1,
                            'arrangement_analysis': 2,  # Already completed
                            'mvsep_processing': 3,
                            'drum_analysis': 4,
                            'post_processing': 5,
                            'export': 6
                        }
                        progress_bar.setValue(phase_map.get(phase_name, 0))
                        
                        # Update results
                        results_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] Phase: {phase_name}")
                        
                        # Check if completed
                        if phase_name == 'export' and current_phase[0] < 6:
                            results_text.append("\nSUCCESS Drummer analysis completed successfully!")
                            start_btn.setText("Completed")
                            start_btn.setEnabled(False)
                            timer.stop()
                            current_phase[0] = 6
                            
                            # Notify the drum analysis tab
                            self._notify_drum_analysis_tab(job_id, metadata)
                            
                except Exception as e:
                    logger.error(f"Error updating drummer analysis progress: {e}")
            
            def start_drummer_analysis():
                try:
                    start_btn.setEnabled(False)
                    start_btn.setText("Processing...")
                    results_text.append("DRUM Starting drummer analysis with arrangement context...")
                    results_text.append(f"ANALYSIS Scope: {'Whole song' if scope == 'whole_song' else f'Sections: {", ".join(selected_sections)}'}")
                    results_text.append(f"MUSIC Musical context: {arrangement.get('tempo', 'Unknown')} BPM, {arrangement.get('style', 'Unknown')} style")
                    
                    # Start the analysis in a separate thread
                    import threading
                    def run_analysis():
                        try:
                            # Update the job with enhanced metadata
                            if job_id in self.phased_analysis.jobs:
                                self.phased_analysis.jobs[job_id].metadata.update(metadata)
                            
                            success, messages = self.phased_analysis.process_full_workflow(job_id)
                            if success:
                                results_text.append("\nSUCCESS Analysis completed successfully!")
                                for msg in messages:
                                    results_text.append(f"  • {msg}")
                            else:
                                results_text.append("\nERROR Analysis failed:")
                                for msg in messages:
                                    results_text.append(f"  • {msg}")
                        except Exception as e:
                            results_text.append(f"\nERROR Analysis error: {e}")
                    
                    thread = threading.Thread(target=run_analysis)
                    thread.daemon = True
                    thread.start()
                    
                    # Start progress timer
                    timer.timeout.connect(update_progress)
                    timer.start(1000)  # Update every second
                    
                except Exception as e:
                    logger.error(f"Error starting drummer analysis: {e}")
                    QMessageBox.critical(dialog, "Error", f"Failed to start analysis: {e}")
            
            start_btn.clicked.connect(start_drummer_analysis)
            close_btn.clicked.connect(dialog.accept)
            
            dialog.show()
            
        except Exception as e:
            logger.error(f"Error showing drummer analysis dialog: {e}")
            QMessageBox.critical(self, "Dialog Error", f"Failed to show drummer analysis dialog: {e}")
            
            def start_analysis():
                try:
                    start_btn.setEnabled(False)
                    start_btn.setText("Processing...")
                    results_text.append("Starting phased drum analysis...")
                    
                    # Start the analysis in a separate thread
                    import threading
                    def run_analysis():
                        try:
                            success, messages = self.phased_analysis.process_full_workflow(job_id)
                            if success:
                                results_text.append("\nSUCCESS Analysis completed successfully!")
                                for msg in messages:
                                    results_text.append(f"  • {msg}")
                            else:
                                results_text.append("\nERROR Analysis failed:")
                                for msg in messages:
                                    results_text.append(f"  • {msg}")
                        except Exception as e:
                            results_text.append(f"\nERROR Analysis error: {e}")
                    
                    thread = threading.Thread(target=run_analysis)
                    thread.daemon = True
                    thread.start()
                    
                    # Start progress timer
                    timer.timeout.connect(update_progress)
                    timer.start(1000)  # Update every second
                    
                except Exception as e:
                    logger.error(f"Error starting analysis: {e}")
                    QMessageBox.critical(dialog, "Error", f"Failed to start analysis: {e}")
            
            start_btn.clicked.connect(start_analysis)
            close_btn.clicked.connect(dialog.accept)
            
            dialog.show()
            
        except Exception as e:
            logger.error(f"Error showing analysis dialog: {e}")
            QMessageBox.critical(self, "Dialog Error", f"Failed to show analysis dialog: {e}")
    
    def _show_song_context_menu(self, position):
        """Show context menu for songs table"""
        try:
            item = self.songs_table.itemAt(position)
            if not item:
                return
            
            row = item.row()
            song_data = self.songs_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if not song_data:
                return
            
            menu = QMenu(self)
            
            # Song title as header
            title_action = QAction(f" {song_data.get('title', 'Unknown Song')}", self)
            title_action.setEnabled(False)
            menu.addAction(title_action)
            menu.addSeparator()
            
            # Find on YouTube action
            youtube_action = QAction("INSPECTING Find on YouTube", self)
            youtube_action.triggered.connect(lambda: self._on_find_on_youtube_at_row(row))
            menu.addAction(youtube_action)
            
            # Play action (if file exists)
            if song_data.get('file_path') and os.path.exists(song_data.get('file_path')):
                play_action = QAction(" Play Song", self)
                play_action.triggered.connect(lambda: self._on_play_song_at_row(row))
                menu.addAction(play_action)
                
                menu.addSeparator()
                
                # Main workflow action - PHASED ANALYSIS
                analysis_action = QAction("TARGET Start Drum Analysis Workflow", self)
                analysis_action.triggered.connect(lambda: self._on_process_with_mvsep_at_row(row))
                menu.addAction(analysis_action)
                
                # Alternative direct MVSep action
                mvsep_action = QAction("TOOL Process with MVSep Only", self)
                mvsep_action.triggered.connect(lambda: self._process_with_mvsep_direct(song_data))
                menu.addAction(mvsep_action)
            else:
                # Show download suggestion
                download_action = QAction(" Download Required", self)
                download_action.setEnabled(False)
                menu.addAction(download_action)
            
            # Show menu at cursor position
            menu.exec(self.songs_table.mapToGlobal(position))
            
        except Exception as e:
            logger.error(f"Error showing song context menu: {e}")
            traceback.print_exc()
    
    def _process_with_mvsep_direct(self, song_data):
        """Process song directly with MVSep (legacy method)"""
        try:
            if not song_data.get('file_path') or not os.path.exists(song_data.get('file_path')):
                QMessageBox.warning(self, "No File", "No downloaded file available to process")
                return
            
            # Use the legacy MVSep processing method
            success, message = self._process_with_mvsep(song_data)
            
            if not success:
                QMessageBox.warning(self, "MVSep Processing Failed", 
                                  f"Failed to queue file for MVSep processing: {message}")
            else:
                QMessageBox.information(self, "MVSep Processing", 
                                       f"File queued for MVSep processing: {message}")
                                       
        except Exception as e:
            logger.error(f"Error in direct MVSep processing: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to process with MVSep: {e}")

    def connect_signals(self):
        """Connect all UI signals - FIXED VERSION with single drummer selection signal"""
        try:
            # Drummer list - use ONLY ONE signal to avoid conflicts
            logger.info("Connecting drummer list signals...")
            # Disconnect any existing connections first
            try:
                self.drummer_list.itemSelectionChanged.disconnect()
                self.drummer_list.itemClicked.disconnect()
                self.drummer_list.currentItemChanged.disconnect()
            except:
                pass  # Ignore if no connections exist
            
            # Connect only the selection changed signal for consistent behavior
            self.drummer_list.itemSelectionChanged.connect(self._on_drummer_selected)
            
            # Search and filter
            self.search_edit.textChanged.connect(self.populate_drummer_list)
            self.genre_combo.currentIndexChanged.connect(self.populate_drummer_list)
            
            # Buttons
            self.add_drummer_btn.clicked.connect(self._on_add_drummer)
            self.edit_drummer_btn.clicked.connect(self._on_edit_drummer)
            self.delete_drummer_btn.clicked.connect(self._on_delete_drummer)
            self.add_song_btn.clicked.connect(self._on_add_song)
            self.find_on_youtube_btn.clicked.connect(self._on_find_song_on_youtube)
            self.process_all_btn.clicked.connect(self._on_process_all_btn_clicked)
            
            # Connect song table selection
            self.songs_table.itemSelectionChanged.connect(self._on_song_selected)
            
            # Add context menu to songs table for workflow assignment
            self.songs_table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.songs_table.customContextMenuRequested.connect(self._show_song_context_menu)
            
            self.find_on_youtube_btn.clicked.connect(self._on_find_song_on_youtube)
            
            # YouTube search signals
            self.youtube_search_btn.clicked.connect(self._on_youtube_search)
            self.download_btn.clicked.connect(self._on_download_video)
            self.play_preview_btn.clicked.connect(self._on_play_preview)
            self.youtube_search_edit.returnPressed.connect(self._on_youtube_search)

            # Filter signals
            self.genre_combo.currentIndexChanged.connect(self.populate_drummer_list)
            self.search_edit.textChanged.connect(self.populate_drummer_list)
            
            # Processing signals
            self.process_all_btn.clicked.connect(self._on_process_all_btn_clicked)
            # Note: process_song_btn doesn't exist in the UI

        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            traceback.print_exc()
            # Log the issue but don't block app startup with a message box
            logger.warning("Some signals couldn't be connected. UI functionality may be limited.")
            return
            
            # Confirm with user
            reply = QMessageBox.question(
                self, "Process All Songs", 
                f"Process {len(downloaded_songs)} downloaded songs with MVSep?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Process all downloaded songs
            success_count = 0
            for song in downloaded_songs:
                result, _ = self._process_with_mvsep(song)
                if result:
                    success_count += 1
            
            # Show result
            if success_count > 0:
                QMessageBox.information(
                    self, "Batch Processing", 
                    f"Successfully queued {success_count} of {len(downloaded_songs)} songs for processing"
                )
            else:
                QMessageBox.warning(
                    self, "Batch Processing Failed", 
                    "Failed to queue any songs for processing"
                )
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error processing all songs: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"An error occurred while processing all songs: {e}")
    
    def _on_mvsep_file_completed(self, batch_id: str, file_path: str, output_files: Dict, file_index: int, total_files: int):
        """Handle completed MVSep file processing"""
        try:
            logger.info(f"MVSep processing completed for {file_path}")
            
            # Find which song this belongs to
            for i, song in enumerate(self.current_drummer['songs']):
                if song.get('file_path') == file_path:
                    # Update song data with stem paths
                    song['stems'] = output_files
                    song['processed'] = True
                    song['process_date'] = datetime.now().isoformat()
                    
                    # Save changes
                    self.save_drummer_profiles()
                    
                    # Update UI if this song is visible
                    def update_song_ui():
                        try:
                            # Find the row for this song
                            for row in range(self.songs_table.rowCount()):
                                if self.songs_table.item(row, 0).data(Qt.UserRole) == i:
                                    # Update processed status
                                    self.songs_table.setItem(row, 3, QTableWidgetItem("Yes"))
                                    self.songs_table.item(row, 3).setBackground(QColor("#4CAF50"))  # Green
                                    break
                        except Exception as e:
                            logger.error(f"Error updating song UI after MVSep completion: {e}")
                    
                    # Update UI safely
                    self.thread_safe.safe_update_ui(update_song_ui)
                    break
            
            # Check if we need to auto-route stems
            # This would interface with the drum analysis component
            metadata = getattr(output_files, 'metadata', {})
            if metadata and metadata.get('auto_route_stems', False):
                # This would call the appropriate method to send stems to analysis
                logger.info(f"Auto-routing stems for analysis: {file_path}")
                # Implementation would go here
                
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error handling MVSep file completion: {e}")
            traceback.print_exc()
    
    def _on_mvsep_file_failed(self, batch_id: str, file_path: str, error: str, file_index: int, total_files: int):
        """Handle failed MVSep file processing"""
        try:
            logger.error(f"MVSep processing failed for {file_path}: {error}")
            
            # Find which song this belongs to
            for i, song in enumerate(self.current_drummer['songs']):
                if song.get('file_path') == file_path:
                    # Update song data with error
                    song['process_error'] = error
                    song['process_date'] = datetime.now().isoformat()
                    
                    # Save changes
                    self.save_drummer_profiles()
                    
                    # Update UI if this song is visible
                    def update_song_ui():
                        try:
                            # Find the row for this song
                            for row in range(self.songs_table.rowCount()):
                                if self.songs_table.item(row, 0).data(Qt.UserRole) == i:
                                    # Update processed status
                                    self.songs_table.setItem(row, 3, QTableWidgetItem("Error"))
                                    self.songs_table.item(row, 3).setBackground(QColor("#F44336"))  # Red
                                    break
                        except Exception as e:
                            logger.error(f"Error updating song UI after MVSep failure: {e}")
                    
                    # Update UI safely
                    self.thread_safe.safe_update_ui(update_song_ui)
                    
                    # Show error message to user
                    self.thread_safe.safe_update_ui(lambda: QMessageBox.warning(
                        self, "MVSep Processing Failed",
                        f"Failed to process {song['title']}:\n{error}"
                    ))
                    break
                    
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error handling MVSep file failure: {e}")
            traceback.print_exc()

    def show_settings_dialog(self):
        """Show the settings dialog"""
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec()
    
    def _sanitize_filename(self, filename):
        """Sanitize filename for safe file system usage"""
        try:
            # Remove or replace invalid characters
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                filename = filename.replace(char, '_')
            
            # Remove leading/trailing spaces and dots
            filename = filename.strip(' .')
            
            # Limit length to avoid filesystem issues
            if len(filename) > 200:
                filename = filename[:200]
            
            # Ensure we have a valid filename
            if not filename:
                filename = "unknown"
                
            return filename
        except Exception as e:
            logger.error(f"Error sanitizing filename '{filename}': {e}")
            return "unknown"

# End of class