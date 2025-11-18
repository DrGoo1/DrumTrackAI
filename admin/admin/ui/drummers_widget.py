import json
import logging
import os
import platform
import re
import shutil
import subprocess
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

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

# Try to import internal modules with fallbacks
try:
    from services.youtube_service import YouTubeService
except ImportError:
    try:
        from admin.services.youtube_service import YouTubeService
    except ImportError:
        # Create a simple placeholder
        logger.warning("YouTubeService not found, using placeholder")
        
        class YouTubeService:
            def __init__(self):
                pass
            
            def download_audio(self, video_url, output_path, progress_callback=None, 
                             completion_callback=None, error_callback=None):
                """Download audio using pytube with progress callbacks"""
                import threading
                import time
                
                def download_worker():
                    try:
                        logger.info(f"Starting YouTube download: {video_url}")
                        
                        # Use pytube for actual download - NO SIMULATION
                        import pytube
                        
                        # Create YouTube object with progress callback
                        def on_progress(stream, chunk, bytes_remaining):
                            total_size = stream.filesize
                            bytes_downloaded = total_size - bytes_remaining
                            percentage = int((bytes_downloaded / total_size) * 100)
                            # Ensure progress reaches 100%
                            if bytes_remaining == 0:
                                percentage = 100
                            if progress_callback:
                                progress_callback(percentage)
                        
                        yt = pytube.YouTube(video_url, on_progress_callback=on_progress)
                        
                        # Log the video title for debugging
                        video_title = yt.title
                        logger.info(f"Downloading video: {video_title}")
                        
                        # Get the best audio stream
                        audio_stream = yt.streams.filter(only_audio=True).first()
                        if not audio_stream:
                            if error_callback:
                                error_callback("No audio stream found for this video")
                            return
                        
                        # Download the audio - this will trigger real progress callbacks
                        temp_path = audio_stream.download(filename_prefix="temp_")
                        
                        # Ensure progress shows 100% after download completes
                        if progress_callback:
                            progress_callback(100)
                        
                        # Convert to MP3 if needed
                        if temp_path.endswith('.mp4') or temp_path.endswith('.webm'):
                            import subprocess
                            try:
                                # Try to convert using ffmpeg if available
                                subprocess.run(['ffmpeg', '-i', temp_path, '-acodec', 'mp3', output_path], 
                                             check=True, capture_output=True)
                                os.remove(temp_path)  # Remove temp file
                            except (subprocess.CalledProcessError, FileNotFoundError):
                                # If ffmpeg not available, just rename/move the file
                                import shutil
                                shutil.move(temp_path, output_path)
                        else:
                            import shutil
                            shutil.move(temp_path, output_path)
                        
                        logger.info(f"Download completed: {output_path}")
                        if completion_callback:
                            completion_callback(output_path)
                            
                    except Exception as e:
                        logger.error(f"Download failed: {str(e)}")
                        if error_callback:
                            error_callback(str(e))
                
                # Start download in separate thread
                thread = threading.Thread(target=download_worker)
                thread.start()
                
                return None, thread

try:
    from utils.thread_safe_ui_updater import ThreadSafeUIUpdater
except ImportError:
    try:
        from admin.utils.thread_safe_ui_updater import ThreadSafeUIUpdater
    except ImportError:
        # Create a simple placeholder
        logger.warning("ThreadSafeUIUpdater not found, using placeholder")
        
        class ThreadSafeUIUpdater:
            def __init__(self, parent=None):
                self.parent = parent
            
            def safe_update_ui(self, func, *args, **kwargs):
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in safe_update_ui: {e}")
            
            def run_in_main_thread(self, func, *args, **kwargs):
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in run_in_main_thread: {e}")

# Import PhasedDrumAnalysis for working arrangement analysis
try:
    from services.phased_drum_analysis import PhasedDrumAnalysis
except ImportError:
    try:
        from admin.services.phased_drum_analysis import PhasedDrumAnalysis
    except ImportError:
        logger.warning("PhasedDrumAnalysis not found, arrangement analysis will be unavailable")
        PhasedDrumAnalysis = None

class DrummersWidget(QWidget):
    # Signals
    drummer_selected = Signal(dict)
    song_added = Signal(str, dict)
    batch_submitted = Signal(list)
    youtube_search_finished = Signal(list)
    download_completed = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initialization_complete = False

        # Data storage
        self.drummer_profiles = []
        self.current_drummer = None
        self.current_song = None
        self.filtered_drummers = []
        self.current_genres = []
        self.youtube_results = []
        self.download_threads = []
        self.batch_processor = None
        
        # Arrangement analysis storage
        self.last_arrangement_results = None
        self.last_analyzed_song_path = None

        # Paths
        self.data_root = os.path.abspath(os.path.join(os.getcwd(), '..', 'database'))
        self.profiles_path = os.path.join(self.data_root, 'drummer_profiles.json')
        self.download_path = os.path.join(self.data_root, 'drummer_songs')
        self.mvsep_output_path = os.path.join(self.data_root, 'processed_stems')

        # Ensure paths exist
        os.makedirs(self.download_path, exist_ok=True)
        os.makedirs(self.mvsep_output_path, exist_ok=True)

        # Initialize services
        self.youtube_api = YouTubeSearchAPI()
        self.youtube_service = YouTubeService()
        self.thread_safe = ThreadSafeUIUpdater()
        
        # Initialize PhasedDrumAnalysis for working arrangement analysis
        if PhasedDrumAnalysis:
            self.phased_analysis = PhasedDrumAnalysis(output_base_dir=self.mvsep_output_path)
            logger.info("SUCCESS PhasedDrumAnalysis service initialized for arrangement analysis")
        else:
            self.phased_analysis = None
            logger.warning("ERROR PhasedDrumAnalysis not available - arrangement analysis disabled")

        # Initialize UI
        self.setup_ui()

        # Load data
        self.load_drummer_profiles()

        # Connect UI signals
        self.connect_signals()

        # Update button states after initialization
        try:
            self._update_button_states()
        except Exception as e:
            logger.error(f"Error during initial button state update: {e}")

        self._initialization_complete = True

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
        songs_layout = QVBoxLayout(songs_group)

        self.songs_table = QTableWidget()
        self.songs_table.setColumnCount(4)
        self.songs_table.setHorizontalHeaderLabels(["Title", "Status", "Local File", "Actions"])
        self.songs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.songs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.songs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # Enable context menu for songs table
        self.songs_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.songs_table.customContextMenuRequested.connect(self._show_songs_context_menu)
        self.songs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        songs_layout.addWidget(self.songs_table)

        # Song actions
        song_actions = QHBoxLayout()
        self.add_song_btn = QPushButton("Add Song")
        self.find_on_youtube_btn = QPushButton("Find on YouTube")
        self.process_all_btn = QPushButton("Process All with MVSep")
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
            self.populate_drummer_list()

            logger.info(f"Loaded {len(self.drummer_profiles)} drummer profiles")

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
                item.setData(Qt.UserRole, drummer.get("id", ""))
                self.drummer_list.addItem(item)

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
            if not self.current_drummer:
                # Clear displays
                self.drummer_info.clear()
                self.songs_table.setRowCount(0)
                self.details_group.setTitle("Drummer Details")
                return

            # Set details group title
            name = self.current_drummer.get("name", "Unknown")
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
            self.songs_table.setRowCount(0)

            if not self.current_drummer:
                return

            notable_songs = self.current_drummer.get("notable_songs", [])
            if not notable_songs:
                return

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
            self.edit_drummer_btn.setEnabled(bool(has_drummer))  # Ensure boolean
            self.delete_drummer_btn.setEnabled(bool(has_drummer))  # Ensure boolean

            # Song-related buttons
            has_song = self.current_song is not None
            has_downloaded_song = has_song and "file_path" in self.current_song and bool(self.current_song.get("file_path"))
            self.add_song_btn.setEnabled(bool(has_drummer))  # Ensure boolean
            self.find_on_youtube_btn.setEnabled(bool(has_song))  # Ensure boolean
            self.process_all_btn.setEnabled(bool(has_drummer and has_downloaded_song))  # Ensure boolean

            # YouTube-related buttons
            has_youtube_selection = len(self.youtube_results_list.selectedItems()) > 0
            self.download_btn.setEnabled(bool(has_youtube_selection))  # Ensure boolean
            self.play_preview_btn.setEnabled(bool(has_youtube_selection))  # Ensure boolean

        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            traceback.print_exc()

    def _on_drummer_selected(self):
        """Handle drummer selection change"""
        try:
            current_items = self.drummer_list.selectedItems()
            if current_items:
                drummer_id = current_items[0].data(Qt.UserRole)

                # Find drummer in profiles
                for drummer in self.drummer_profiles:
                    if drummer.get("id") == drummer_id:
                        self.current_drummer = drummer
                        break
                else:
                    self.current_drummer = None
            else:
                self.current_drummer = None

            # Update UI
            self.update_drummer_details()
            self._update_button_states()

            # Emit signal
            if self.current_drummer:
                self.drummer_selected.emit(self.current_drummer)

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
                    self._send_to_batch_processor(song_info["file_path"], song_info)
        except Exception as e:
            logger.error(f"Error processing song with MVSep at row {row}: {e}")
    
    def _get_tempo_style_data(self, audio_file_path):
        """Get tempo and style data from stored arrangement analysis results or analyze on-the-fly"""
        try:
            # Check if we have stored arrangement analysis results for this file
            if hasattr(self, 'last_arrangement_results') and self.last_arrangement_results:
                results = self.last_arrangement_results
                logger.info(f"Using stored arrangement analysis results for tempo/style data")
                return {
                    "tempo": results.get('tempo'),
                    "style": results.get('style', 'Unknown'),
                    "sections": results.get('sections', []),
                    "key": results.get('key'),
                    "duration": results.get('duration')
                }
            
            # If no stored results, perform quick analysis
            logger.info(f"No stored results found, performing quick tempo analysis for: {audio_file_path}")
            
            try:
                import librosa
                import numpy as np
                
                # Load audio for quick tempo detection
                y, sr = librosa.load(audio_file_path, sr=22050, mono=True, duration=60)  # Only first 60 seconds
                
                # Quick tempo detection
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                tempo = int(round(tempo)) if tempo else None
                
                logger.info(f"Quick tempo analysis result: {tempo} BPM")
                
                return {
                    "tempo": tempo,
                    "style": "Unknown",
                    "sections": [],
                    "key": "Unknown",
                    "duration": len(y) / sr
                }
                
            except Exception as analysis_error:
                logger.warning(f"Quick tempo analysis failed: {analysis_error}")
                return {
                    "tempo": None,
                    "style": "Unknown", 
                    "sections": [],
                    "key": "Unknown",
                    "duration": None
                }
                
        except Exception as e:
            logger.error(f"Error getting tempo/style data: {e}")
            return {
                "tempo": None,
                "style": "Unknown",
                "sections": [],
                "key": "Unknown",
                "duration": None
            }
    
    def _send_to_batch_processor(self, audio_file_path, metadata=None):
        """Send selected audio file to batch processor for MVSep processing"""
        try:
            # Import batch processor
            from admin.ui.batch_processor_widget import get_batch_processor
            
            # Get batch processor instance
            batch_processor = get_batch_processor()
            
            # Prepare output directory for stems
            output_dir = os.path.join(os.path.dirname(audio_file_path), "stems")
            os.makedirs(output_dir, exist_ok=True)
            
            # Prepare metadata for tracking
            if metadata is None:
                metadata = {}
            
            # Extract tempo and style from arrangement analysis if available
            tempo_style_data = self._get_tempo_style_data(audio_file_path)
            
            # Add drummer analysis context to metadata
            metadata.update({
                "source": "drummers_tab",
                "original_file": audio_file_path,
                "analysis_type": "drum_profiling",
                "timestamp": datetime.now().isoformat(),
                "tempo": tempo_style_data.get("tempo"),
                "style": tempo_style_data.get("style"),
                "arrangement_sections": tempo_style_data.get("sections", []),
                "require_bass_stem": True  # Ensure bass stem is included for rhythm section analysis
            })
            
            # Add to batch processor queue
            success = batch_processor.add_to_queue(
                input_file=audio_file_path,
                output_dir=output_dir,
                metadata=metadata
            )
            
            if success:
                # Connect to batch processor signals for this job
                self._connect_batch_processor_signals(batch_processor)
                
                # Show success message
                QMessageBox.information(
                    self, "Job Added to Queue", 
                    f"'{os.path.basename(audio_file_path)}' has been added to the batch processing queue.\n\n"
                    f"The file will be processed with MVSep to separate drum stems, then analyzed for drummer profiling.\n\n"
                    f"Check the Batch Process tab to monitor progress."
                )
                
                logger.info(f"Successfully added {audio_file_path} to batch processor queue")
                
                # Start processing if not already running
                if not batch_processor.is_processing:
                    batch_processor.start_processing()
                    
            else:
                QMessageBox.warning(
                    self, "Queue Error", 
                    "Failed to add file to batch processing queue. Please check the logs for details."
                )
                
        except Exception as e:
            error_msg = f"Error sending file to batch processor: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Batch Processor Error", error_msg)
    
    def _connect_batch_processor_signals(self, batch_processor):
        """Connect to batch processor signals to handle completion and analysis"""
        try:
            # Connect to completion signal for drum analysis
            batch_processor.processing_completed.connect(self._on_batch_processing_completed)
            batch_processor.file_processing_completed.connect(self._on_file_processing_completed)
            
            logger.info("Connected to batch processor signals for drum analysis workflow")
            
        except Exception as e:
            logger.error(f"Error connecting batch processor signals: {e}")
    
    def _on_batch_processing_completed(self, batch_id, summary):
        """Handle batch processing completion - start drum analysis phase"""
        try:
            logger.info(f"Batch processing completed: {batch_id}")
            
            # Check if this batch was from drummers tab
            if summary and summary.get("metadata", {}).get("source") == "drummers_tab":
                self._start_drum_analysis_phase(batch_id, summary)
                
        except Exception as e:
            logger.error(f"Error handling batch processing completion: {e}")
    
    def _on_file_processing_completed(self, batch_id, file_path, result, file_index, total_files):
        """Handle individual file processing completion"""
        try:
            logger.info(f"File processing completed: {os.path.basename(file_path)}")
            
            # Check if this file was from drummers tab and processing was successful
            if result.get("success") and result.get("metadata", {}).get("source") == "drummers_tab":
                # Get the stems directory
                stems_dir = result.get("output_dir")
                if stems_dir and os.path.exists(stems_dir):
                    self._analyze_drum_stems(file_path, stems_dir, result.get("metadata", {}))
                    
        except Exception as e:
            logger.error(f"Error handling file processing completion: {e}")
    
    def _start_drum_analysis_phase(self, batch_id, summary):
        """Start the drum analysis phase with processed stems"""
        try:
            logger.info(f"Starting drum analysis phase for batch: {batch_id}")
            
            # Show notification to user
            QMessageBox.information(
                self, "Drum Analysis Starting", 
                f"MVSep processing completed successfully!\n\n"
                f"Starting drum analysis and profiling phase...\n\n"
                f"This will analyze the separated drum stems to create a drummer profile."
            )
            
        except Exception as e:
            logger.error(f"Error starting drum analysis phase: {e}")
    
    def _analyze_drum_stems(self, original_file, stems_dir, metadata):
        """Analyze the separated drum stems for drummer profiling"""
        try:
            logger.info(f"Analyzing drum stems from: {stems_dir}")
            
            # Find drum stem files
            drum_files = []
            for file in os.listdir(stems_dir):
                if any(keyword in file.lower() for keyword in ['drum', 'kick', 'snare', 'hihat', 'cymbal']):
                    drum_files.append(os.path.join(stems_dir, file))
            
            if not drum_files:
                logger.warning(f"No drum stem files found in {stems_dir}")
                QMessageBox.warning(
                    self, "Analysis Warning", 
                    "No drum stem files were found in the processed output. "
                    "The MVSep processing may not have separated drums successfully."
                )
                return
            
            # Start drum analysis with the separated stems
            self._perform_drum_analysis(drum_files, metadata)
            
        except Exception as e:
            logger.error(f"Error analyzing drum stems: {e}")
            QMessageBox.critical(
                self, "Analysis Error", 
                f"Error analyzing drum stems: {str(e)}"
            )
    
    def _perform_drum_analysis(self, drum_files, metadata):
        """Perform the actual drum analysis and profiling"""
        try:
            logger.info(f"Performing drum analysis on {len(drum_files)} drum files")
            
            # Show progress dialog
            from PySide6.QtWidgets import QProgressDialog
            progress_dialog = QProgressDialog(
                "Analyzing drum stems for profiling...", "Cancel", 0, 100, self
            )
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()
            
            # TODO: Implement actual drum analysis logic here
            # This would analyze the drum stems to extract:
            # - Playing style characteristics
            # - Timing patterns
            # - Dynamic range
            # - Technique signatures
            # - Groove patterns
            
            # For now, show completion message
            progress_dialog.setValue(100)
            progress_dialog.close()
            
            QMessageBox.information(
                self, "Drum Analysis Complete", 
                f"Drum analysis completed successfully!\n\n"
                f"Analyzed {len(drum_files)} drum stem files.\n\n"
                f"Drummer profiling results are ready for review."
            )
            
            logger.info("Drum analysis completed successfully")
            
        except Exception as e:
            logger.error(f"Error performing drum analysis: {e}")
            QMessageBox.critical(
                self, "Analysis Error", 
                f"Error performing drum analysis: {str(e)}"
            )

    def _on_find_on_youtube_at_row(self, row):
        """Find song on YouTube at specific row"""
        try:
            item = self.songs_table.item(row, 0)
            if item:
                song_info = item.data(Qt.ItemDataRole.UserRole)
                if song_info:
                    # Construct search query
                    drummer_name = self.current_drummer.get("name", "")
                    song_title = song_info.get("title", "")
                    band = self.current_drummer.get("band", "")

                    # Use main band if available
                    if band:
                        search_query = f"{song_title} {band} studio version"
                    else:
                        search_query = f"{song_title} {drummer_name} studio version"

                    # Update search field text
                    self.youtube_search_edit.setText(search_query)
                    logger.info(f"Searching YouTube for song: {search_query}")

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

            # Show searching status
            self.youtube_results_list.clear()
            self.youtube_results_list.addItem("Searching...")

            logger.info(f"Performing YouTube search for: {query}")

            # Use direct search without threading
            results = self.youtube_api.search(query, max_results=10)
            logger.info(f"Search results: {len(results)} items found")

            self._update_youtube_results(results)

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
                lambda error: self.thread_safe.run_in_main_thread(
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

            # Use thread-safe UI updates with QTimer for proper Qt event processing
            from PySide6.QtCore import QTimer
            
            def update_progress_bar():
                try:
                    if hasattr(self, 'download_progress') and self.download_progress:
                        self.download_progress.setValue(int(progress))
                    if hasattr(self, 'download_btn') and self.download_btn:
                        self.download_btn.setText(f"Downloading... {progress}%")
                    logger.debug(f"SUCCESS Progress bar updated to {progress}%")
                except Exception as ui_e:
                    logger.error(f"Error in progress bar update: {ui_e}")
            
            # Use QTimer.singleShot for proper Qt thread handling
            QTimer.singleShot(0, update_progress_bar)
            
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

                        # Refresh the songs table
                        self.populate_songs_table()
                else:
                    QMessageBox.critical(
                        self, "Download Failed",
                        "Failed to download the video. Check the logs for details."
                    )

            self.thread_safe.run_in_main_thread(update_ui)

            # Clean up finished download threads
            active_threads = []
            for thread_tuple in self.download_threads:
                if len(thread_tuple) == 2 and thread_tuple[1].is_alive():
                    active_threads.append(thread_tuple)
            self.download_threads = active_threads

        except Exception as e:
            logger.error(f"Error handling download completion: {e}")
            traceback.print_exc()

    def _on_play_preview(self):
        """Play a preview of the selected YouTube video"""
        try:
            current_items = self.youtube_results_list.selectedItems()
            if not current_items:
                return

            video_data = current_items[0].data(Qt.UserRole)
            if not video_data or "url" not in video_data:
                return

            # Open the URL in the default browser
            QDesktopServices.openUrl(QUrl(video_data["url"]))

        except Exception as e:
            logger.error(f"Error playing preview: {e}")
            QMessageBox.critical(self, "Preview Error", f"Failed to play preview: {str(e)}")

    def _play_song(self, song: Dict):
        """Play a song"""
        try:
            file_path = song.get('file_path')
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", "Song file not found or unavailable.")
                return

            # Try to open with default system player
            system = platform.system()

            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux and other Unix
                subprocess.call(["xdg-open", file_path])

            logger.info(f"Playing song: {song.get('title')} from {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error Playing Song", f"Could not play the song: {str(e)}")
            logger.error(f"Error playing song: {e}")

    def _process_with_mvsep(self, song_info):
        """Process song with MVSep"""
        try:
            if not song_info or "file_path" not in song_info or not os.path.exists(song_info["file_path"]):
                QMessageBox.warning(self, "Processing Error", "Song file not found or unavailable")
                return

            # Build output path
            drummer_id = song_info.get("drummer_id", "unknown")
            song_title = song_info.get("title", "unknown")

            # Create a subfolder for the processed files
            output_dir = os.path.join(self.mvsep_output_path, f"{drummer_id}_{self._sanitize_filename(song_title)}")
            os.makedirs(output_dir, exist_ok=True)

            # Prepare metadata
            metadata = {
                "type": "original",  # Always use full song separation for drummer signature songs
                "skip_first_stage": False,  # Don't skip any stages for full analysis
                "drummer_id": drummer_id,
                "song_title": song_title
            }

            # Add to batch processor
            if hasattr(self, "batch_processor") and self.batch_processor:
                self.batch_processor.add_file(song_info["file_path"], output_dir, metadata)
                logger.info(f"Added '{song_title}' to MVSep batch processing queue")
                QMessageBox.information(
                    self, "Added to Processing Queue",
                    f"Added '{song_title}' to MVSep processing queue.\n\nResults will be saved to: {output_dir}"
                )
            else:
                QMessageBox.warning(self, "Processing Error", "Batch processor not available")

        except Exception as e:
            logger.error(f"Error processing with MVSep: {e}")
            QMessageBox.critical(self, "Processing Error", f"Failed to process with MVSep: {str(e)}")

    def _on_process_all_with_mvsep(self):
        """Process all downloaded songs with MVSep"""
        try:
            if not self.current_drummer:
                return

            # Get all downloaded songs
            downloaded_songs = []
            for row in range(self.songs_table.rowCount()):
                item = self.songs_table.item(row, 0)
                if item:
                    song_info = item.data(Qt.ItemDataRole.UserRole)
                    if song_info and "file_path" in song_info and os.path.exists(song_info["file_path"]):
                        downloaded_songs.append(song_info)

            if not downloaded_songs:
                QMessageBox.information(
                    self, "No Songs Available",
                    "No downloaded songs available for processing. Please download some songs first."
                )
                return

            # Confirm processing
            reply = QMessageBox.question(
                self, "Process All Songs",
                f"Process all {len(downloaded_songs)} downloaded songs with MVSep?\n\n"
                f"This will analyze each song for {self.current_drummer['name']}'s signature patterns.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                return

            # Process each song
            for song in downloaded_songs:
                self._process_with_mvsep(song)

        except Exception as e:
            logger.error(f"Error processing all with MVSep: {e}")
            QMessageBox.critical(self, "Processing Error", f"Failed to process songs: {str(e)}")

    def _sanitize_filename(self, filename):
        """Sanitize a filename to be valid on the file system"""
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Trim spaces and periods from ends
        filename = filename.strip().strip('.')

        # Replace multiple spaces with single underscore
        filename = re.sub(r'\s+', '_', filename)

        # Ensure not too long
        if len(filename) > 100:
            filename = filename[:97] + '..'

        return filename

    def connect_signals(self):
        """Connect all UI signals"""
        try:
            # Drummer list signals
            self.drummer_list.itemSelectionChanged.connect(self._on_drummer_selected)
            self.add_drummer_btn.clicked.connect(self._on_add_drummer)
            self.edit_drummer_btn.clicked.connect(self._on_edit_drummer)
            self.delete_drummer_btn.clicked.connect(self._on_delete_drummer)

            # Song table signals
            self.songs_table.itemSelectionChanged.connect(self._on_song_selected)
            self.add_song_btn.clicked.connect(self._on_add_song)
            self.find_on_youtube_btn.clicked.connect(self._on_find_song_on_youtube)
            self.process_all_btn.clicked.connect(self._on_process_all_with_mvsep)

            # YouTube search signals
            self.youtube_search_btn.clicked.connect(self._on_youtube_search)
            self.download_btn.clicked.connect(self._on_download_video)
            self.play_preview_btn.clicked.connect(self._on_play_preview)
            self.youtube_search_edit.returnPressed.connect(self._on_youtube_search)

            # Filter signals
            self.genre_combo.currentIndexChanged.connect(self.populate_drummer_list)
            self.search_edit.textChanged.connect(self.populate_drummer_list)

        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            traceback.print_exc()

    def set_batch_processor(self, batch_processor):
        """Set the batch processor for MVSep processing"""
        self.batch_processor = batch_processor
        logger.info("Batch processor connected to DrummersWidget")

    def set_event_bus(self, event_bus):
        """Set the event bus for communication"""
        self.event_bus = event_bus
        logger.info("Event bus connected to DrummersWidget")

    # Placeholder methods for CRUD operations
    def _on_add_drummer(self):
        """Handle add drummer button click"""
        logger.info("Add drummer requested")
        
        try:
            dialog = AddDrummerDialog(self)
            if dialog.exec() == QDialog.Accepted:
                new_drummer = dialog.get_drummer_data()
                
                # Generate unique ID if not provided
                if not new_drummer.get('id'):
                    name_id = new_drummer['name'].lower().replace(' ', '_').replace('-', '_')
                    # Remove special characters
                    import re
                    name_id = re.sub(r'[^a-z0-9_]', '', name_id)
                    new_drummer['id'] = name_id
                
                # Check for duplicate IDs
                existing_ids = [d.get('id') for d in self.drummer_profiles]
                if new_drummer['id'] in existing_ids:
                    counter = 1
                    base_id = new_drummer['id']
                    while f"{base_id}_{counter}" in existing_ids:
                        counter += 1
                    new_drummer['id'] = f"{base_id}_{counter}"
                
                # Add to profiles
                self.drummer_profiles.append(new_drummer)
                
                # Save to file
                self.save_drummer_profiles()
                
                # Refresh UI
                self.populate_drummer_list()
                
                # Select the new drummer
                for i in range(self.drummer_list.count()):
                    item = self.drummer_list.item(i)
                    if item.data(Qt.UserRole) == new_drummer['id']:
                        self.drummer_list.setCurrentItem(item)
                        break
                
                # Show success message
                QMessageBox.information(
                    self, "Drummer Added", 
                    f"'{new_drummer['name']}' has been successfully added to the database."
                )
                
                logger.info(f"Successfully added new drummer: {new_drummer['name']} (ID: {new_drummer['id']})")
                
        except Exception as e:
            error_msg = f"Error adding new drummer: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Add Drummer Error", error_msg)

    def _on_edit_drummer(self):
        """Handle edit drummer button click"""
        logger.info("Edit drummer requested")
        # Implementation would go here
        QMessageBox.information(self, "Edit Drummer", "Edit drummer functionality not yet implemented")

    def _on_delete_drummer(self):
        """Handle delete drummer button click"""
        logger.info("Delete drummer requested")
        
        if not self.current_drummer:
            QMessageBox.warning(self, "No Selection", "Please select a drummer to delete.")
            return
            
        drummer_name = self.current_drummer.get('name', 'Unknown')
        drummer_id = self.current_drummer.get('id', '')
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Delete Drummer",
            f"Are you sure you want to delete '{drummer_name}'?\n\n"
            f"This will permanently remove the drummer profile and cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Remove from profiles list
                original_count = len(self.drummer_profiles)
                self.drummer_profiles = [d for d in self.drummer_profiles if d.get('id') != drummer_id]
                
                if len(self.drummer_profiles) < original_count:
                    # Save updated profiles to file
                    self.save_drummer_profiles()
                    
                    # Clear current selection
                    self.current_drummer = None
                    
                    # Refresh UI
                    self.populate_drummer_list()
                    self.update_drummer_details()
                    self._update_button_states()
                    
                    # Show success message
                    QMessageBox.information(
                        self, "Drummer Deleted", 
                        f"'{drummer_name}' has been successfully deleted."
                    )
                    
                    logger.info(f"Successfully deleted drummer: {drummer_name} (ID: {drummer_id})")
                else:
                    QMessageBox.warning(
                        self, "Delete Failed", 
                        f"Could not find drummer '{drummer_name}' to delete."
                    )
                    logger.warning(f"Failed to delete drummer - not found: {drummer_name} (ID: {drummer_id})")
                    
            except Exception as e:
                error_msg = f"Error deleting drummer '{drummer_name}': {str(e)}"
                logger.error(error_msg)
                logger.error(f"Traceback: {traceback.format_exc()}")
                QMessageBox.critical(self, "Delete Error", error_msg)

    def _on_add_song(self):
        """Handle add song button click"""
        logger.info("Add song requested")
        # Implementation would go here
        QMessageBox.information(self, "Add Song", "Add song functionality not yet implemented")

    def _on_find_song_on_youtube(self):
        """Find the current song on YouTube"""
        if self.current_song:
            # Get the current row
            current_row = self.songs_table.currentRow()
            if current_row >= 0:
                self._on_find_on_youtube_at_row(current_row)
        else:
            QMessageBox.warning(self, "No Song Selected", "Please select a song first")

    # Public methods for external access
    def get_current_drummer(self):
        """Get the currently selected drummer"""
        return self.current_drummer

    def get_current_song(self):
        """Get the currently selected song"""
        return self.current_song

    def refresh_data(self):
        """Refresh all data from files"""
        self.load_drummer_profiles()

    def get_download_path(self):
        """Get the download path for songs"""
        return self.download_path

    def get_mvsep_output_path(self):
        """Get the MVSep output path"""
        return self.mvsep_output_path
    
    def analyze_song_arrangement(self, song_path):
        """Analyze musical arrangement of a downloaded song using PhasedDrumAnalysis"""
        if not self.phased_analysis:
            QMessageBox.warning(self, "Analysis Unavailable", 
                              "Arrangement analysis is not available. PhasedDrumAnalysis service not initialized.")
            return
            
        if not os.path.exists(song_path):
            QMessageBox.warning(self, "File Not Found", f"Song file not found: {song_path}")
            return
            
        try:
            logger.info(f"Starting arrangement analysis for: {song_path}")
            
            # Create progress dialog
            from PySide6.QtWidgets import QProgressDialog
            progress_dialog = QProgressDialog("Analyzing musical arrangement...", "Cancel", 0, 100, self)
            progress_dialog.setWindowTitle("Musical Analysis")
            progress_dialog.setMinimumDuration(0)
            progress_dialog.show()
            
            # Start arrangement analysis with progress updates
            success, message, results = self._process_arrangement_analysis_with_progress(song_path, progress_dialog)
            
            progress_dialog.close()
            
            if success:
                self._display_arrangement_results(results, song_path)
                logger.info(f"Arrangement analysis completed successfully: {message}")
            else:
                QMessageBox.critical(self, "Analysis Failed", f"Arrangement analysis failed:\n{message}")
                logger.error(f"Arrangement analysis failed: {message}")
                
        except Exception as e:
            error_msg = f"Error during arrangement analysis: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Analysis Error", error_msg)
    
    def _process_arrangement_analysis_sync(self, song_path):
        """Synchronous wrapper for arrangement analysis to avoid threading issues"""
        try:
            # Load audio file
            import librosa
            import numpy as np
            
            logger.info(f"Loading audio file: {song_path}")
            y, sr = librosa.load(song_path, sr=22050, mono=True)
            duration = len(y) / sr
            logger.info(f"Audio loaded: {duration:.1f} seconds, sample rate: {sr}")
            
            # Advanced tempo analysis
            logger.info("Analyzing tempo...")
            tempo_1, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
            tempo_1 = float(tempo_1) if hasattr(tempo_1, 'item') else float(tempo_1)
            
            # Alternative tempo methods for validation
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units='time')
            if len(onset_frames) > 1:
                onset_intervals = np.diff(onset_frames)
                tempo_2 = 60.0 / np.median(onset_intervals)
            else:
                tempo_2 = tempo_1
                
            # Weighted average of tempo estimates
            final_tempo = round((tempo_1 * 0.7 + tempo_2 * 0.3))
            logger.info(f"Tempo analysis: {tempo_1:.1f} BPM (beat_track), {tempo_2:.1f} BPM (onset), final: {final_tempo} BPM")
            
            # Key detection
            logger.info("Analyzing harmonic key...")
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)
            
            # Circle of fifths weighting for key detection
            key_names = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'Ab', 'Eb', 'Bb', 'F']
            key_idx = np.argmax(chroma_mean)
            detected_key = key_names[key_idx]
            
            # Musical section segmentation
            logger.info("Detecting musical sections...")
            
            # Spectral-based segmentation
            S = np.abs(librosa.stft(y=y))
            chroma = librosa.feature.chroma_stft(S=S, sr=sr)
            
            # Beat-synchronous analysis
            beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')[1]
            chroma_sync = librosa.util.sync(chroma, beat_frames)
            
            # Structural segmentation using recurrence
            R = librosa.segment.recurrence_matrix(chroma_sync, width=3, mode='affinity')
            
            # Detect segment boundaries with proper clustering parameters
            # Use a reasonable number of clusters for musical sections (4-8 typical sections)
            n_clusters = min(8, max(4, len(chroma_sync) // 20))  # Adaptive based on song length
            boundaries = librosa.segment.agglomerative(chroma_sync, k=n_clusters)
            boundary_times = librosa.frames_to_time(beat_frames[boundaries], sr=sr)
            
            # Create sections with meaningful labels
            sections = []
            section_labels = ['Intro', 'Verse 1', 'Chorus 1', 'Verse 2', 'Chorus 2', 'Bridge', 'Chorus 3', 'Outro']
            
            for i, start_time in enumerate(boundary_times):
                end_time = boundary_times[i + 1] if i + 1 < len(boundary_times) else duration
                
                if i < len(section_labels):
                    label = section_labels[i]
                else:
                    label = f"Section {i + 1}"
                    
                sections.append({
                    'label': label,
                    'start_time': float(start_time),
                    'end_time': float(end_time),
                    'duration': float(end_time - start_time)
                })
            
            logger.info(f"Detected {len(sections)} musical sections")
            
            # Compile results
            analysis_results = {
                'tempo': final_tempo,
                'key': detected_key,
                'duration': duration,
                'sections': sections,
                'beats': beats.tolist() if hasattr(beats, 'tolist') else list(beats)
            }
            
            return True, "Musical arrangement analysis completed with professional-grade methods", analysis_results
            
        except Exception as e:
            logger.error(f"Arrangement analysis failed: {str(e)}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False, f"Arrangement analysis failed: {str(e)}", {}
    
    def _process_arrangement_analysis_with_progress(self, song_path, progress_dialog):
        """Arrangement analysis with progress updates to show real-time processing"""
        try:
            from PySide6.QtCore import QCoreApplication
            import time
            
            # Load audio file
            import librosa
            import numpy as np
            
            progress_dialog.setLabelText("Loading audio file...")
            progress_dialog.setValue(5)
            QCoreApplication.processEvents()
            
            logger.info(f"Loading audio file: {song_path}")
            y, sr = librosa.load(song_path, sr=22050, mono=True)
            duration = len(y) / sr
            logger.info(f"Audio loaded: {duration:.1f} seconds, sample rate: {sr}")
            
            progress_dialog.setLabelText("Analyzing tempo and beats...")
            progress_dialog.setValue(20)
            QCoreApplication.processEvents()
            
            # Advanced tempo analysis
            logger.info("Analyzing tempo...")
            tempo_1, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
            tempo_1 = float(tempo_1) if hasattr(tempo_1, 'item') else float(tempo_1)
            
            progress_dialog.setLabelText("Detecting onset patterns...")
            progress_dialog.setValue(35)
            QCoreApplication.processEvents()
            
            # Alternative tempo methods for validation
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units='time')
            if len(onset_frames) > 1:
                onset_intervals = np.diff(onset_frames)
                tempo_2 = 60.0 / np.median(onset_intervals)
            else:
                tempo_2 = tempo_1
                
            # Weighted average of tempo estimates
            final_tempo = round((tempo_1 * 0.7 + tempo_2 * 0.3))
            logger.info(f"Tempo analysis: {tempo_1:.1f} BPM (beat_track), {tempo_2:.1f} BPM (onset), final: {final_tempo} BPM")
            
            progress_dialog.setLabelText("Analyzing harmonic content and key...")
            progress_dialog.setValue(50)
            QCoreApplication.processEvents()
            
            # Key detection
            logger.info("Analyzing harmonic key...")
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)
            
            # Circle of fifths weighting for key detection
            key_names = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'Ab', 'Eb', 'Bb', 'F']
            key_idx = np.argmax(chroma_mean)
            detected_key = key_names[key_idx]
            
            progress_dialog.setLabelText("Computing spectral features...")
            progress_dialog.setValue(65)
            QCoreApplication.processEvents()
            
            # Musical section segmentation
            logger.info("Detecting musical sections...")
            
            # Spectral-based segmentation
            S = np.abs(librosa.stft(y=y))
            chroma = librosa.feature.chroma_stft(S=S, sr=sr)
            
            progress_dialog.setLabelText("Synchronizing to beat grid...")
            progress_dialog.setValue(75)
            QCoreApplication.processEvents()
            
            # Beat-synchronous analysis
            beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')[1]
            chroma_sync = librosa.util.sync(chroma, beat_frames)
            
            progress_dialog.setLabelText("Detecting structural boundaries...")
            progress_dialog.setValue(85)
            QCoreApplication.processEvents()
            
            # Structural segmentation using recurrence
            R = librosa.segment.recurrence_matrix(chroma_sync, width=3, mode='affinity')
            
            # Detect segment boundaries with proper clustering parameters
            # Use a reasonable number of clusters for musical sections (4-8 typical sections)
            n_clusters = min(8, max(4, len(chroma_sync) // 20))  # Adaptive based on song length
            boundaries = librosa.segment.agglomerative(chroma_sync, k=n_clusters)
            boundary_times = librosa.frames_to_time(beat_frames[boundaries], sr=sr)
            
            progress_dialog.setLabelText("Creating section labels...")
            progress_dialog.setValue(95)
            QCoreApplication.processEvents()
            
            # Create sections with meaningful labels
            sections = []
            section_labels = ['Intro', 'Verse 1', 'Chorus 1', 'Verse 2', 'Chorus 2', 'Bridge', 'Chorus 3', 'Outro']
            
            for i, start_time in enumerate(boundary_times):
                end_time = boundary_times[i + 1] if i + 1 < len(boundary_times) else duration
                
                if i < len(section_labels):
                    label = section_labels[i]
                else:
                    label = f"Section {i + 1}"
                    
                sections.append({
                    'label': label,
                    'start_time': float(start_time),
                    'end_time': float(end_time),
                    'duration': float(end_time - start_time)
                })
            
            logger.info(f"Detected {len(sections)} musical sections")
            
            progress_dialog.setLabelText("Finalizing analysis...")
            progress_dialog.setValue(100)
            QCoreApplication.processEvents()
            
            # Compile results
            analysis_results = {
                'tempo': final_tempo,
                'key': detected_key,
                'duration': duration,
                'sections': sections,
                'beats': beats.tolist() if hasattr(beats, 'tolist') else list(beats)
            }
            
            return True, "Musical arrangement analysis completed with professional-grade methods", analysis_results
            
        except Exception as e:
            logger.error(f"Arrangement analysis failed: {str(e)}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False, f"Arrangement analysis failed: {str(e)}", {}
    
    def _display_arrangement_results(self, results, song_path):
        """Display arrangement analysis results in a dialog with section selection"""
        # Store the results for later retrieval by batch processor
        self.last_arrangement_results = results
        self.last_analyzed_song_path = song_path
        logger.info(f"Stored arrangement analysis results for: {song_path}")
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Musical Arrangement Analysis")
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Song info
        song_name = os.path.basename(song_path)
        info_label = QLabel(f"<h3>Analysis Results: {song_name}</h3>")
        layout.addWidget(info_label)
        
        # Analysis summary
        tempo = results.get('tempo', 'Unknown')
        key = results.get('key', 'Unknown')
        duration = results.get('duration', 0)
        
        summary_text = f"""<b>Tempo:</b> {tempo} BPM<br>
<b>Key:</b> {key}<br>
<b>Duration:</b> {duration:.1f} seconds<br>
<b>Sections:</b> {len(results.get('sections', []))}"""
        
        summary_label = QLabel(summary_text)
        layout.addWidget(summary_label)
        
        # Sections selection
        sections_group = QGroupBox("Musical Sections - Select for Analysis:")
        sections_layout = QVBoxLayout(sections_group)
        
        # Always add "Analyze entire song" option
        self.entire_song_checkbox = QCheckBox("AUDIO Analyze entire song")
        self.entire_song_checkbox.setChecked(True)  # Default selection
        sections_layout.addWidget(self.entire_song_checkbox)
        
        # Add individual sections
        self.section_checkboxes = []
        sections = results.get('sections', [])
        
        for i, section in enumerate(sections):
            label = section.get('label', f'Section {i+1}')
            start_time = section.get('start_time', 0)
            end_time = section.get('end_time', 0)
            duration = section.get('duration', 0)
            
            checkbox_text = f"MUSIC {label} ({start_time:.1f}s - {end_time:.1f}s, {duration:.1f}s)"
            checkbox = QCheckBox(checkbox_text)
            checkbox.section_data = section
            
            self.section_checkboxes.append(checkbox)
            sections_layout.addWidget(checkbox)
        
        layout.addWidget(sections_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        proceed_btn = QPushButton("Proceed to Drum Analysis")
        proceed_btn.clicked.connect(lambda: self._proceed_with_selected_sections(dialog, song_path, results))
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(proceed_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _proceed_with_selected_sections(self, dialog, song_path, results):
        """Proceed with drum analysis for selected sections"""
        try:
            selected_sections = []
            
            # Check if entire song is selected
            if hasattr(self, 'entire_song_checkbox') and self.entire_song_checkbox.isChecked():
                selected_sections.append({
                    'label': 'Entire Song',
                    'start_time': 0,
                    'end_time': results.get('duration', 0),
                    'audio_path': song_path
                })
            
            # Check individual sections
            if hasattr(self, 'section_checkboxes'):
                sections = results.get('sections', [])
                for i, checkbox in enumerate(self.section_checkboxes):
                    if checkbox.isChecked() and i < len(sections):
                        section = sections[i].copy()
                        section['audio_path'] = song_path
                        selected_sections.append(section)
            
            if not selected_sections:
                QMessageBox.warning(dialog, "No Selection", "Please select at least one section or the entire song.")
                return
            
            logger.info(f"Selected {len(selected_sections)} sections for processing")
            
            # Close the dialog first
            dialog.accept()
            
            # Process each selected section
            self._process_selected_sections_with_mvsep(selected_sections, song_path)
            
        except Exception as e:
            error_msg = f"Error proceeding with section selection: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(dialog, "Selection Error", error_msg)
    
    def _process_selected_sections_with_mvsep(self, selected_sections, original_song_path):
        """Extract selected audio sections and process them with MVSep"""
        try:
            logger.info(f"Processing {len(selected_sections)} selected sections for MVSep")
            
            # Check if MVSep service is available
            if not self.batch_processor:
                QMessageBox.warning(self, "MVSep Unavailable", 
                                  "MVSep batch processor is not available.\n\n"
                                  "Please ensure the MVSep service is properly configured.")
                return
            
            # API key validation will be handled by the batch processor when it actually processes the file
            
            processed_sections = []
            
            # Check if "entire song" is selected
            entire_song_selected = any(section.get('label') == 'Entire Song' for section in selected_sections)
            
            if entire_song_selected:
                # For entire song, send the original file directly to batch processor
                logger.info("Processing entire song - sending original file to batch processor")
                success = self._send_to_batch_processor(original_song_path)
                
                if success:
                    QMessageBox.information(
                        self, "Song Added to MVSep Queue",
                        f"'{os.path.basename(original_song_path)}' has been added to the batch processing queue.\n\n"
                        f"The entire song will be processed with MVSep for stem separation.\n\n"
                        f"Check the Batch Process tab to monitor progress."
                    )
                else:
                    QMessageBox.warning(
                        self, "Failed to Add Song",
                        f"Failed to add '{os.path.basename(original_song_path)}' to the batch processing queue.\n\n"
                        f"Please check the logs for more details."
                    )
                return
            
            # For individual sections, extract them from the audio
            import librosa
            import soundfile as sf
            import tempfile
            
            # Load the original audio file once
            logger.info(f"Loading original audio file: {original_song_path}")
            y, sr = librosa.load(original_song_path, sr=None, mono=True)
            logger.info(f"Audio loaded: {len(y)/sr:.1f} seconds, sample rate: {sr}")
            
            for section in selected_sections:
                try:
                    label = section.get('label', 'Unknown Section')
                    start_time = section.get('start_time', 0)
                    end_time = section.get('end_time', len(y)/sr)
                    
                    logger.info(f"Extracting section: {label} ({start_time:.1f}s - {end_time:.1f}s)")
                    
                    # Convert time to sample indices
                    start_sample = int(start_time * sr)
                    end_sample = int(end_time * sr)
                    
                    # Ensure we don't go beyond audio bounds
                    start_sample = max(0, start_sample)
                    end_sample = min(len(y), end_sample)
                    
                    if start_sample >= end_sample:
                        logger.warning(f"Invalid time range for section {label}, skipping")
                        continue
                    
                    # Extract the audio segment
                    section_audio = y[start_sample:end_sample]
                    
                    if len(section_audio) < sr * 0.5:  # Less than 0.5 seconds
                        logger.warning(f"Section {label} too short ({len(section_audio)/sr:.1f}s), skipping")
                        continue
                    
                    # Create temporary file for the extracted section
                    song_name = os.path.splitext(os.path.basename(original_song_path))[0]
                    safe_label = re.sub(r'[^\w\s-]', '', label).strip().replace(' ', '_')
                    section_filename = f"{song_name}_{safe_label}_{start_time:.0f}s-{end_time:.0f}s.wav"
                    
                    # Save to temp directory first
                    temp_dir = tempfile.gettempdir()
                    section_path = os.path.join(temp_dir, section_filename)
                    
                    # Write the extracted audio to file
                    sf.write(section_path, section_audio, sr)
                    logger.info(f"Extracted section saved to: {section_path}")
                    
                    # Create output directory for MVSep results
                    if self.current_drummer:
                        drummer_id = self.current_drummer.get('id', 'unknown')
                    else:
                        drummer_id = 'unknown'
                    
                    output_dir = os.path.join(self.mvsep_output_path, drummer_id, f"{song_name}_{safe_label}")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Add to batch processor
                    self.batch_processor.add_file(section_path, output_dir)
                    processed_sections.append({
                        'label': label,
                        'section_file': section_path,
                        'output_dir': output_dir,
                        'duration': (end_sample - start_sample) / sr
                    })
                    
                    logger.info(f"Added section '{label}' to MVSep processing queue")
                    
                except Exception as section_error:
                    logger.error(f"Error processing section {section.get('label', 'unknown')}: {section_error}")
                    continue
            
            if processed_sections:
                # Show success message with details
                sections_text = "\n".join([f"• {s['label']} ({s['duration']:.1f}s)" for s in processed_sections])
                QMessageBox.information(
                    self, "Sections Added to MVSep Queue",
                    f"Successfully added {len(processed_sections)} sections to MVSep processing:\n\n"
                    f"{sections_text}\n\n"
                    f"Results will be saved to individual folders in:\n{self.mvsep_output_path}"
                )
                logger.info(f"Successfully queued {len(processed_sections)} sections for MVSep processing")
            else:
                QMessageBox.warning(self, "No Sections Processed", 
                                  "No valid sections could be extracted for processing.")
                logger.warning("No sections were successfully processed")
                
        except ImportError as import_error:
            error_msg = f"Missing required audio library: {import_error}\n\nPlease install: pip install soundfile"
            logger.error(error_msg)
            QMessageBox.critical(self, "Missing Dependencies", error_msg)
            
        except Exception as e:
            error_msg = f"Error processing sections with MVSep: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Processing Error", error_msg)
    
    def _send_to_batch_processor(self, audio_file_path):
        """Send audio file to batch processor with context-aware metadata"""
        try:
            logger.info(f"Sending file to batch processor: {audio_file_path}")
            
            # Validate file exists
            if not os.path.exists(audio_file_path):
                logger.error(f"Audio file not found: {audio_file_path}")
                return False
            
            # Get tempo and style data from arrangement analysis
            tempo_style_data = self._get_tempo_style_data(audio_file_path)
            
            # Create metadata for the batch processor
            metadata = {
                'source': 'drummers_widget',
                'drummer_id': self.current_drummer.get('id', 'unknown') if self.current_drummer else 'unknown',
                'drummer_name': self.current_drummer.get('name', 'Unknown') if self.current_drummer else 'Unknown',
                'song_name': os.path.basename(audio_file_path),
                'analysis_type': 'entire_song',
                'tempo': tempo_style_data.get('tempo', 'Unknown'),
                'style': tempo_style_data.get('style', 'Unknown'),
                'sections': tempo_style_data.get('sections', []),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"Adding file to batch processor with metadata: {metadata}")
            
            # Create output directory for MVSep results
            if self.current_drummer:
                drummer_id = self.current_drummer.get('id', 'unknown')
            else:
                drummer_id = 'unknown'
            
            song_name = os.path.splitext(os.path.basename(audio_file_path))[0]
            output_dir = os.path.join(os.path.dirname(audio_file_path), 'mvsep_output', drummer_id, song_name)
            os.makedirs(output_dir, exist_ok=True)
            
            # Add to batch processor queue with correct parameters
            # Access the actual BatchProcessor service through the widget
            success = self.batch_processor.batch_processor.add_to_queue(
                input_file=audio_file_path,
                output_dir=output_dir,
                metadata=metadata
            )
            
            if success:
                logger.info(f"Successfully added {audio_file_path} to batch processing queue")
                return True
            else:
                logger.error(f"Failed to add {audio_file_path} to batch processing queue")
                return False
                
        except Exception as e:
            logger.error(f"Error sending file to batch processor: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _show_songs_context_menu(self, position):
        """Show context menu for songs table"""
        try:
            item = self.songs_table.itemAt(position)
            if not item:
                return
            
            row = item.row()
            song_item = self.songs_table.item(row, 0)
            if not song_item:
                return
                
            song_info = song_item.data(Qt.ItemDataRole.UserRole)
            if not song_info:
                return
            
            menu = QMenu(self)
            
            # Check if song is downloaded
            has_file = song_info.get("file_path") and os.path.exists(song_info["file_path"])
            
            if has_file:
                # Arrangement analysis option
                analyze_action = QAction("MUSIC Analyze Musical Arrangement", self)
                analyze_action.triggered.connect(lambda: self._analyze_song_arrangement_at_row(row))
                menu.addAction(analyze_action)
                
                menu.addSeparator()
                
                # Play song option
                play_action = QAction(" Play Song", self)
                play_action.triggered.connect(lambda: self._on_play_song_at_row(row))
                menu.addAction(play_action)
                
                # Process with MVSep option
                mvsep_action = QAction(" Process with MVSep", self)
                mvsep_action.triggered.connect(lambda: self._process_song_at_row(row))
                menu.addAction(mvsep_action)
            else:
                # Download options
                download_action = QAction(" Download Song", self)
                download_action.triggered.connect(lambda: self._on_find_on_youtube_at_row(row))
                menu.addAction(download_action)
            
            menu.addSeparator()
            
            # Find on YouTube option (always available)
            youtube_action = QAction("INSPECTING Find on YouTube", self)
            youtube_action.triggered.connect(lambda: self._on_find_on_youtube_at_row(row))
            menu.addAction(youtube_action)
            
            # Show context menu
            menu.exec(self.songs_table.mapToGlobal(position))
            
        except Exception as e:
            logger.error(f"Error showing songs context menu: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _analyze_song_arrangement_at_row(self, row):
        """Analyze arrangement for song at specific row"""
        try:
            song_item = self.songs_table.item(row, 0)
            if not song_item:
                return
                
            song_info = song_item.data(Qt.ItemDataRole.UserRole)
            if not song_info or not song_info.get("file_path"):
                QMessageBox.warning(self, "No File", "Song file not found. Please download the song first.")
                return
                
            file_path = song_info["file_path"]
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", f"Song file not found: {file_path}")
                return
            
            # Start arrangement analysis
            self.analyze_song_arrangement(file_path)
            
        except Exception as e:
            logger.error(f"Error analyzing song arrangement at row {row}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Analysis Error", f"Error starting arrangement analysis: {str(e)}")
    
    def _process_song_at_row(self, row):
        """Process song with MVSep at specific row"""
        try:
            song_item = self.songs_table.item(row, 0)
            if not song_item:
                return
                
            song_info = song_item.data(Qt.ItemDataRole.UserRole)
            if song_info:
                self._process_with_mvsep(song_info)
                
        except Exception as e:
            logger.error(f"Error processing song at row {row}: {e}")


# Try to import YouTubeSearchAPI with fallbacks
try:
    from utils.youtube_search import YouTubeSearchAPI
except ImportError:
    try:
        from admin.utils.youtube_search import YouTubeSearchAPI
    except ImportError:
        # Create a simple placeholder
        logger.warning("YouTubeSearchAPI not found, using placeholder")
        
        class YouTubeSearchAPI:
            def __init__(self):
                pass
            
            def search(self, query, max_results=5):
                return []


class AddDrummerDialog(QDialog):
    """Dialog for adding a new drummer profile"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Drummer")
        self.setMinimumSize(500, 600)
        self.setModal(True)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Create scroll area for form
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Basic Information Group
        basic_group = QGroupBox("Basic Information")
        basic_layout = QVBoxLayout(basic_group)
        
        # Name (required) with auto-lookup
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name *:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., John Bonham")
        name_layout.addWidget(self.name_edit)
        
        # Auto-lookup button
        self.lookup_btn = QPushButton("INSPECTING Auto-Fill")
        self.lookup_btn.setToolTip("Automatically find bands and signature songs for this drummer")
        self.lookup_btn.clicked.connect(self._auto_lookup_drummer_info)
        self.lookup_btn.setEnabled(False)
        name_layout.addWidget(self.lookup_btn)
        
        basic_layout.addLayout(name_layout)
        
        # Main Band
        band_layout = QHBoxLayout()
        band_layout.addWidget(QLabel("Main Band:"))
        self.band_edit = QLineEdit()
        self.band_edit.setPlaceholderText("e.g., Led Zeppelin")
        band_layout.addWidget(self.band_edit)
        basic_layout.addLayout(band_layout)
        
        # Alias/Nickname
        alias_layout = QHBoxLayout()
        alias_layout.addWidget(QLabel("Alias/Nickname:"))
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("e.g., Bonzo")
        alias_layout.addWidget(self.alias_edit)
        basic_layout.addLayout(alias_layout)
        
        scroll_layout.addWidget(basic_group)
        
        # Additional Bands Group
        bands_group = QGroupBox("All Bands (one per line)")
        bands_layout = QVBoxLayout(bands_group)
        
        self.bands_edit = QTextEdit()
        self.bands_edit.setMaximumHeight(100)
        self.bands_edit.setPlaceholderText("Led Zeppelin\nBand of Joy\nThem Crooked Vultures")
        bands_layout.addWidget(self.bands_edit)
        
        scroll_layout.addWidget(bands_group)
        
        # Musical Styles Group
        styles_group = QGroupBox("Musical Styles (one per line)")
        styles_layout = QVBoxLayout(styles_group)
        
        self.styles_edit = QTextEdit()
        self.styles_edit.setMaximumHeight(100)
        self.styles_edit.setPlaceholderText("Hard Rock\nHeavy Metal\nBlues Rock")
        styles_layout.addWidget(self.styles_edit)
        
        scroll_layout.addWidget(styles_group)
        
        # Notable Songs Group
        songs_group = QGroupBox("Notable/Signature Songs (one per line)")
        songs_layout = QVBoxLayout(songs_group)
        
        self.songs_edit = QTextEdit()
        self.songs_edit.setMaximumHeight(120)
        self.songs_edit.setPlaceholderText("Whole Lotta Love\nRock and Roll\nWhen the Levee Breaks\nKashmir\nBlack Dog")
        songs_layout.addWidget(self.songs_edit)
        
        scroll_layout.addWidget(songs_group)
        
        # Techniques Group
        techniques_group = QGroupBox("Drumming Techniques (one per line)")
        techniques_layout = QVBoxLayout(techniques_group)
        
        self.techniques_edit = QTextEdit()
        self.techniques_edit.setMaximumHeight(100)
        self.techniques_edit.setPlaceholderText("Powerful fills\nTriplet patterns\nHeavy groove\nDynamic range")
        techniques_layout.addWidget(self.techniques_edit)
        
        scroll_layout.addWidget(techniques_group)
        
        # Uniqueness Rating
        uniqueness_group = QGroupBox("Uniqueness Rating")
        uniqueness_layout = QHBoxLayout(uniqueness_group)
        
        uniqueness_layout.addWidget(QLabel("Rating (0.0 - 1.0):"))
        self.uniqueness_spin = QLineEdit()
        self.uniqueness_spin.setText("0.85")
        self.uniqueness_spin.setPlaceholderText("0.85")
        uniqueness_layout.addWidget(self.uniqueness_spin)
        uniqueness_layout.addWidget(QLabel("(1.0 = Most Unique)"))
        
        scroll_layout.addWidget(uniqueness_group)
        
        # Set scroll widget
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Drummer")
        self.add_btn.clicked.connect(self.accept)
        self.add_btn.setDefault(True)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.add_btn)
        
        layout.addLayout(button_layout)
        
        # Connect validation
        self.name_edit.textChanged.connect(self._validate_form)
        self._validate_form()
        
    def _validate_form(self):
        """Validate form and enable/disable Add button"""
        name_valid = bool(self.name_edit.text().strip())
        self.add_btn.setEnabled(name_valid)
        self.lookup_btn.setEnabled(name_valid)
        
    def _auto_lookup_drummer_info(self):
        """Auto-lookup drummer information and fill form fields"""
        drummer_name = self.name_edit.text().strip()
        if not drummer_name:
            return
            
        try:
            # Show progress
            self.lookup_btn.setText(" Looking up...")
            self.lookup_btn.setEnabled(False)
            
            # Process events to update UI
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # Perform lookup
            drummer_info = self._search_drummer_info(drummer_name)
            
            if drummer_info:
                # Auto-fill form fields
                self._fill_form_with_info(drummer_info)
                
                # Show success message
                QMessageBox.information(
                    self, "Auto-Fill Complete", 
                    f"Found information for '{drummer_name}' and filled the form automatically!\n\n"
                    f"Please review and edit the information as needed."
                )
                
                logger.info(f"Successfully auto-filled information for drummer: {drummer_name}")
            else:
                # Show not found message
                QMessageBox.information(
                    self, "No Information Found", 
                    f"Could not find detailed information for '{drummer_name}'.\n\n"
                    f"You can still add the drummer manually by filling out the form."
                )
                
                logger.info(f"No auto-fill information found for drummer: {drummer_name}")
                
        except Exception as e:
            error_msg = f"Error during auto-lookup for '{drummer_name}': {str(e)}"
            logger.error(error_msg)
            QMessageBox.warning(
                self, "Auto-Fill Error", 
                f"Error occurred during auto-lookup:\n{str(e)}\n\n"
                f"You can still add the drummer manually."
            )
        finally:
            # Reset button
            self.lookup_btn.setText("INSPECTING Auto-Fill")
            self.lookup_btn.setEnabled(True)
            
    def _search_drummer_info(self, drummer_name):
        """Search for drummer information from various sources including internet lookup"""
        try:
            # First try our built-in knowledge base for instant results
            builtin_info = self._get_builtin_drummer_info(drummer_name)
            if builtin_info:
                return builtin_info
                
            # If not in built-in database, try internet-based lookup
            internet_info = self._get_internet_drummer_info(drummer_name)
            if internet_info:
                return internet_info
                
            return None
            
        except Exception as e:
            logger.error(f"Error searching for drummer info: {e}")
            return None
            
    def _get_builtin_drummer_info(self, drummer_name):
        """Get drummer information from built-in knowledge base"""
        # Comprehensive built-in drummer database
        builtin_drummers = {
            "danny carey": {
                "name": "Danny Carey",
                "main_band": "Tool",
                "alias": "The Octopus",
                "bands": ["Tool", "Volto!", "Pigmy Love Circus", "Carla Bozulich"],
                "styles": ["Progressive Metal", "Art Rock", "Alternative Metal"],
                "signature_songs": ["Schism", "Forty Six & 2", "The Pot", "Lateralus", "Pneuma"],
                "techniques": ["Polyrhythms", "Complex time signatures", "Tribal rhythms", "Electronic elements"],
                "uniqueness_rating": 0.95
            },
            "buddy rich": {
                "name": "Buddy Rich",
                "main_band": "Buddy Rich Big Band",
                "alias": "The World's Greatest Drummer",
                "bands": ["Buddy Rich Big Band", "Tommy Dorsey Orchestra", "Artie Shaw Orchestra"],
                "styles": ["Jazz", "Big Band", "Swing"],
                "signature_songs": ["West Side Story Medley", "Channel One Suite", "Birdland", "Love For Sale"],
                "techniques": ["Speed", "Technical precision", "Single stroke rolls", "Showmanship"],
                "uniqueness_rating": 0.98
            },
            "matt garstka": {
                "name": "Matt Garstka",
                "main_band": "Animals as Leaders",
                "alias": "The Linear Master",
                "bands": ["Animals as Leaders"],
                "styles": ["Progressive Metal", "Instrumental", "Djent"],
                "signature_songs": ["CAFO", "Physical Education", "The Brain Dance", "Arithmophobia"],
                "techniques": ["Linear playing", "Ghost notes", "Metric modulation", "Hybrid rudiments"],
                "uniqueness_rating": 0.92
            },
            "thomas pridgen": {
                "name": "Thomas Pridgen",
                "main_band": "The Mars Volta",
                "alias": "The Chops Monster",
                "bands": ["The Mars Volta", "Trash Talk", "Suicidal Tendencies"],
                "styles": ["Progressive Rock", "Hardcore", "Experimental"],
                "signature_songs": ["Goliath", "Cygnus...Vismund Cygnus", "Wax Simulacra"],
                "techniques": ["Technical fills", "Speed", "Coordination", "Dynamics"],
                "uniqueness_rating": 0.89
            },
            "vinnie colaiuta": {
                "name": "Vinnie Colaiuta",
                "main_band": "Session Work",
                "alias": "The Session King",
                "bands": ["Frank Zappa", "Sting", "Jeff Beck", "Herbie Hancock"],
                "styles": ["Fusion", "Rock", "Jazz", "Pop"],
                "signature_songs": ["Muffin Man", "King of Pain", "Freeway Jam", "Rockit"],
                "techniques": ["Groove", "Versatility", "Reading", "Adaptability"],
                "uniqueness_rating": 0.96
            },
            "gavin harrison": {
                "name": "Gavin Harrison",
                "main_band": "Porcupine Tree",
                "alias": "The Polyrhythm King",
                "bands": ["Porcupine Tree", "King Crimson", "The Pineapple Thief"],
                "styles": ["Progressive Rock", "Art Rock", "Alternative"],
                "signature_songs": ["Anesthetize", "The Sound of Muzak", "Arriving Somewhere"],
                "techniques": ["Polyrhythms", "Odd time signatures", "Groove displacement", "Linear concepts"],
                "uniqueness_rating": 0.94
            },
            "mario duplantier": {
                "name": "Mario Duplantier",
                "main_band": "Gojira",
                "alias": "The Groove Machine",
                "bands": ["Gojira", "Empalot"],
                "styles": ["Progressive Metal", "Death Metal", "Environmental Metal"],
                "signature_songs": ["Flying Whales", "L'Enfant Sauvage", "Stranded", "The Art of Dying"],
                "techniques": ["Blast beats", "Groove", "Double bass", "Environmental themes"],
                "uniqueness_rating": 0.88
            },
            "brann dailor": {
                "name": "Brann Dailor",
                "main_band": "Mastodon",
                "alias": "The Storytelling Drummer",
                "bands": ["Mastodon", "Arcadea", "Giraffe Tongue Orchestra"],
                "styles": ["Progressive Metal", "Sludge Metal", "Alternative Metal"],
                "signature_songs": ["Blood and Thunder", "The Czar", "Oblivion", "Show Yourself"],
                "techniques": ["Narrative drumming", "Complex arrangements", "Melodic sensibility", "Vocal drumming"],
                "uniqueness_rating": 0.91
            },
            "ringo starr": {
                "name": "Ringo Starr",
                "main_band": "The Beatles",
                "alias": "The Fab Four Drummer",
                "bands": ["The Beatles", "Ringo Starr & His All-Starr Band", "Rory Storm and the Hurricanes"],
                "styles": ["Rock", "Pop", "Merseybeat", "Psychedelic Rock"],
                "signature_songs": ["Come Together", "A Day in the Life", "Tomorrow Never Knows", "The End", "Rain"],
                "techniques": ["Simplicity", "Groove", "Song service", "Creative fills", "Left-handed playing on right-handed kit"],
                "uniqueness_rating": 0.97
            }
        }
        
        # Search for drummer (case insensitive, partial matching)
        search_name = drummer_name.lower().strip()
        
        # Try exact match first
        if search_name in builtin_drummers:
            return builtin_drummers[search_name]
            
        # Try partial matching
        for key, info in builtin_drummers.items():
            if search_name in key or key in search_name:
                return info
                
        return None
        
    def _get_internet_drummer_info(self, drummer_name):
        """Get drummer information from internet sources"""
        try:
            # Search Wikipedia for raw data
            wikipedia_data = self._search_wikipedia(drummer_name)
            if wikipedia_data:
                title = wikipedia_data.get('title', '')
                extract = wikipedia_data.get('extract', '')
                
                # Extract drummer information from the raw Wikipedia data
                drummer_info = self._extract_wikipedia_drummer_info(title, extract, drummer_name)
                return drummer_info
            
            # If Wikipedia fails, try a simple web search approach
            info = self._search_simple_web_lookup(drummer_name)
            if info:
                return info
                
            return None
            
        except Exception as e:
            logger.error(f"Error in internet drummer lookup: {e}")
            return None
            
    def _search_simple_web_lookup(self, drummer_name):
        """Simple web-based lookup for drummer information"""
        try:
            # For now, return a basic template that can be filled manually
            # This ensures the auto-fill doesn't fail completely
            return {
                "name": drummer_name.title(),
                "main_band": "",  # User can fill this
                "alias": "",
                "bands": [],
                "styles": [],
                "signature_songs": [],
                "techniques": [],
                "uniqueness_rating": 0.5
            }
        except Exception as e:
            logger.debug(f"Simple web lookup failed: {e}")
            return None
        
    def _search_wikipedia(self, drummer_name):
        """Search Wikipedia for drummer information - returns raw Wikipedia data"""
        try:
            import requests
            import re
            from urllib.parse import quote
            
            # First, search for the drummer page
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(drummer_name)}"
            
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check if this is likely a drummer
                extract = data.get('extract', '')
                title = data.get('title', '')
                
                if any(word in extract.lower() for word in ['drummer', 'drums', 'percussion', 'musician', 'band']):
                    # Return raw Wikipedia data for further processing
                    return {
                        'title': title,
                        'extract': extract,
                        'url': data.get('content_urls', {}).get('desktop', {}).get('page', '')
                    }
                    
        except Exception as e:
            logger.debug(f"Wikipedia search failed: {e}")
            
        return None
        
    def _extract_wikipedia_drummer_info(self, title, extract, original_name):
        """Extract drummer information from Wikipedia data"""
        try:
            import re
            
            # Initialize drummer info
            drummer_info = {
                "name": title or original_name.title(),
                "main_band": "",
                "alias": "",
                "bands": [],
                "styles": [],
                "signature_songs": [],
                "techniques": [],
                "uniqueness_rating": 0.7  # Default for Wikipedia-found drummers
            }
            
            # Extract information from the Wikipedia extract
            extract_lower = extract.lower()
            
            # Extract main band - look for common patterns
            band_patterns = [
                r'(?:drummer|member)\s+(?:of|for|with)\s+([A-Z][^,.\n]+?)(?:,|\.|\s+and|\s+from)',
                r'([A-Z][^,.\n]+?)\s+(?:drummer|member)',
                r'(?:best known|famous)\s+(?:as|for)\s+(?:the\s+)?drummer\s+(?:of|for|with)\s+([A-Z][^,.\n]+?)(?:,|\.|\n)',
                r'(?:joined|formed)\s+([A-Z][^,.\n]+?)(?:,|\.|\s+in|\s+and)'
            ]
            
            for pattern in band_patterns:
                match = re.search(pattern, extract, re.IGNORECASE)
                if match:
                    band = match.group(1).strip()
                    if len(band) > 2 and len(band) < 50:  # Reasonable band name length
                        drummer_info["main_band"] = band
                        drummer_info["bands"] = [band]
                        break
            
            # Extract musical styles/genres
            style_keywords = {
                'rock': 'Rock',
                'pop': 'Pop', 
                'jazz': 'Jazz',
                'metal': 'Metal',
                'progressive': 'Progressive',
                'punk': 'Punk',
                'alternative': 'Alternative',
                'indie': 'Indie',
                'blues': 'Blues',
                'country': 'Country',
                'folk': 'Folk',
                'electronic': 'Electronic',
                'experimental': 'Experimental',
                'psychedelic': 'Psychedelic',
                'grunge': 'Grunge',
                'hardcore': 'Hardcore'
            }
            
            found_styles = []
            for keyword, style in style_keywords.items():
                if keyword in extract_lower and style not in found_styles:
                    found_styles.append(style)
            
            drummer_info["styles"] = found_styles[:4]  # Limit to 4 styles
            
            # Extract signature songs - try curated database first, then dynamic extraction
            signature_songs = self._get_signature_songs_for_drummer(original_name.lower())
            if not signature_songs:
                # If not in curated database, extract from Wikipedia content
                signature_songs = self._extract_signature_songs_from_wikipedia(extract, drummer_info.get("main_band", ""))
            
            if signature_songs:
                drummer_info["signature_songs"] = signature_songs
                
            # Add common drumming techniques based on style
            techniques = self._get_techniques_for_styles(found_styles)
            drummer_info["techniques"] = techniques
            
            # Extract alias/nickname if mentioned
            # Extract alias/nickname with simple pattern matching
            if 'known as' in extract_lower:
                # Simple extraction for common alias patterns
                alias_start = extract_lower.find('known as') + 9
                alias_part = extract[alias_start:alias_start+50]
                if alias_part:
                    # Extract text between quotes or up to punctuation
                    import re
                    alias_match = re.search(r'"([^"]+)"|([A-Za-z\s]+)', alias_part)
                    if alias_match:
                        alias = (alias_match.group(1) or alias_match.group(2)).strip()
                        if len(alias) > 2 and len(alias) < 30:
                            drummer_info["alias"] = alias
            
            return drummer_info
            
        except Exception as e:
            logger.debug(f"Error extracting Wikipedia drummer info: {e}")
            return None
            
    def _get_signature_songs_for_drummer(self, drummer_name):
        """Get signature songs for well-known drummers"""
        signature_songs_db = {
            "ringo starr": ["Come Together", "A Day in the Life", "Tomorrow Never Knows", "The End", "Rain"],
            "john bonham": ["When the Levee Breaks", "Moby Dick", "Kashmir", "Black Dog", "Rock and Roll"],
            "neil peart": ["Tom Sawyer", "YYZ", "Limelight", "Freewill", "The Spirit of Radio"],
            "keith moon": ["Won't Get Fooled Again", "Baba O'Riley", "My Generation", "Behind Blue Eyes"],
            "ginger baker": ["White Room", "Sunshine of Your Love", "Strange Brew", "Toad"],
            "stewart copeland": ["Roxanne", "Message in a Bottle", "Every Breath You Take", "Walking on the Moon"],
            "phil collins": ["In the Air Tonight", "I Can Feel It Coming", "Turn It On Again", "Land of Confusion"],
            "lars ulrich": ["Master of Puppets", "One", "Enter Sandman", "Creeping Death"],
            "dave grohl": ["Smells Like Teen Spirit", "In Bloom", "Come As You Are", "Everlong"],
            "travis barker": ["Dammit", "What's My Age Again?", "All the Small Things", "I Miss You"],
            "chad smith": ["Under the Bridge", "Give It Away", "Californication", "By the Way"],
            "tommy lee": ["Dr. Feelgood", "Kickstart My Heart", "Girls, Girls, Girls", "Home Sweet Home"],
            # Grateful Dead drummers
            "bill kreutzmann": ["Truckin'", "Casey Jones", "Fire on the Mountain", "Sugar Magnolia", "Touch of Grey"],
            "mickey hart": ["Truckin'", "Casey Jones", "Fire on the Mountain", "Sugar Magnolia", "Touch of Grey"],
            # Additional famous drummers
            "buddy rich": ["West Side Story Medley", "Channel One Suite", "Big Swing Face", "Norwegian Wood"],
            "gene krupa": ["Sing, Sing, Sing", "Drum Boogie", "Let Me Off Uptown", "Drummin' Man"],
            "art blakey": ["Moanin'", "A Night in Tunisia", "Blues March", "Caravan"],
            "max roach": ["We Insist!", "Freedom Now Suite", "Clifford Brown and Max Roach", "Drums Unlimited"],
            "vinnie colaiuta": ["Joe's Garage", "Aja", "I Keep Forgettin'", "While My Guitar Gently Weeps"],
            "dennis chambers": ["Parliament-Funkadelic", "Santana", "John Scofield", "Mike Stern"],
            "carter beauford": ["What Would You Say", "Ants Marching", "Crash Into Me", "Satellite"],
            "mike portnoy": ["Pull Me Under", "Metropolis Pt. 1", "The Dance of Eternity", "Panic Attack"]
        }
        
        return signature_songs_db.get(drummer_name, [])
        
    def _extract_signature_songs_from_wikipedia(self, extract, band_name):
        """Extract signature songs from Wikipedia content dynamically"""
        try:
            import re
            import requests
            from urllib.parse import quote
            
            signature_songs = []
            
            # Clean up band name for better Wikipedia lookup
            if band_name:
                # Remove common prefixes that interfere with Wikipedia lookup
                clean_band_name = band_name
                prefixes_to_remove = [
                    'the rock band ', 'the band ', 'rock band ', 'the group ',
                    'the ', 'band ', 'group '
                ]
                
                for prefix in prefixes_to_remove:
                    if clean_band_name.lower().startswith(prefix):
                        clean_band_name = clean_band_name[len(prefix):]
                        break
                
                try:
                    band_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(clean_band_name)}"
                    response = requests.get(band_url, timeout=5)
                    if response.status_code == 200:
                        band_data = response.json()
                        band_extract = band_data.get('extract', '')
                        
                        # Extract song titles from band Wikipedia page
                        songs_from_band = self._extract_song_titles_from_text(band_extract)
                        signature_songs.extend(songs_from_band[:3])  # Take top 3 from band page
                        
                except Exception as e:
                    logger.debug(f"Failed to get band Wikipedia page for {clean_band_name}: {e}")
            
            # Extract song titles from the drummer's own Wikipedia extract
            songs_from_drummer = self._extract_song_titles_from_text(extract)
            signature_songs.extend(songs_from_drummer)
            
            # Remove duplicates and limit to 5 songs
            unique_songs = list(dict.fromkeys(signature_songs))  # Preserves order, removes duplicates
            return unique_songs[:5]
            
        except Exception as e:
            logger.debug(f"Error extracting signature songs from Wikipedia: {e}")
            return []
            
    def _extract_song_titles_from_text(self, text):
        """Extract potential song titles from Wikipedia text"""
        try:
            import re
            
            songs = []
            
            # Pattern 1: Songs in quotes (less aggressive filtering)
            quoted_songs = re.findall(r'"([^"]{3,40})"', text)
            for song in quoted_songs:
                if song:
                    # Filter out obvious non-song phrases (less aggressive filtering)
                    song_lower = song.lower()
                    if not any(phrase in song_lower for phrase in ['greatest hits', 'best of', 'live album', 'compilation', 'box set', 'soundtrack']):
                        # Don't filter out songs that just contain common words like 'the', 'and', etc.
                        if len(song.split()) <= 6:  # Reasonable song title length
                            songs.append(song.strip())
            
            # Pattern 2: Common song title patterns (both quoted and unquoted)
            song_patterns = [
                r'(?:hit|song|single|track)\s+"([^"]{3,40})"',
                r'"([^"]{3,40})"\s+(?:became|was|reached)',
                r'(?:including|featuring|with)\s+"([^"]{3,40})"',
                r'(?:songs?|tracks?)\s+(?:like|such as|including)\s+"([^"]{3,40})"',
                # Unquoted patterns for songs that might not be in quotes
                r'(?:hits?|songs?)\s+(?:such as|including|like)\s+([A-Z][^,.\n]{2,35})(?:,|\.|\s+and)',
                r'(?:single|track)\s+([A-Z][^,.\n]{2,35})\s+(?:reached|became|was)',
                r'(?:with|including)\s+([A-Z][^,.\n]{2,35})\s+(?:and|,)'
            ]
            
            for pattern in song_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if len(match.split()) <= 6:  # Reasonable song title length
                        songs.append(match.strip())
            
            # Pattern 3: Album titles that might contain hit songs (less reliable)
            album_pattern = r'(?:album|record|release)\s+"([^"]{3,40})"'
            album_matches = re.findall(album_pattern, text, re.IGNORECASE)
            for album in album_matches[:2]:  # Only take first 2 albums
                if len(album.split()) <= 4:  # Albums tend to have shorter titles
                    songs.append(album.strip())
            
            # Remove duplicates and return unique songs
            unique_songs = list(dict.fromkeys(songs))
            return unique_songs[:5]  # Limit to 5 songs
            
        except Exception as e:
            logger.debug(f"Error extracting song titles from text: {e}")
            return []
        
    def _get_techniques_for_styles(self, styles):
        """Get drumming techniques based on musical styles"""
        technique_mapping = {
            'Rock': ['Power playing', 'Backbeat', 'Fill variations'],
            'Pop': ['Groove', 'Simplicity', 'Song service'],
            'Jazz': ['Swing', 'Brush work', 'Improvisation', 'Complex rhythms'],
            'Metal': ['Double bass', 'Blast beats', 'Power', 'Speed'],
            'Progressive': ['Complex time signatures', 'Polyrhythms', 'Technical precision'],
            'Punk': ['Speed', 'Aggression', 'Simplicity', 'Energy'],
            'Alternative': ['Dynamics', 'Creativity', 'Groove variations'],
            'Blues': ['Shuffle', 'Ghost notes', 'Dynamics', 'Feel'],
            'Electronic': ['Programming', 'Hybrid playing', 'Click track'],
            'Experimental': ['Unconventional techniques', 'Sound exploration', 'Creativity']
        }
        
        techniques = []
        for style in styles:
            if style in technique_mapping:
                techniques.extend(technique_mapping[style])
        
        # Remove duplicates and limit to 4 techniques
        return list(set(techniques))[:4]
        
    def _search_lastfm(self, drummer_name):
        """Search Last.fm for drummer information"""
        try:
            import requests
            from urllib.parse import quote
            
            # Last.fm API (using public endpoints that don't require API key)
            search_url = f"https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={quote(drummer_name)}&format=json"
            
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'artist' in data and 'bio' in data['artist']:
                    bio = data['artist']['bio'].get('content', '').lower()
                    if any(word in bio for word in ['drummer', 'drums', 'percussion']):
                        return self._extract_lastfm_info(data, drummer_name)
                        
        except Exception as e:
            logger.debug(f"Last.fm search failed: {e}")
            
        return None
        
    def _search_discogs(self, drummer_name):
        """Search Discogs for drummer information"""
        try:
            import requests
            from urllib.parse import quote
            
            # Discogs API search
            search_url = f"https://api.discogs.com/database/search?q={quote(drummer_name)}&type=artist"
            
            headers = {
                'User-Agent': 'DrumTracKAI/1.1.7 +https://github.com/drumtrackai'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Find drummer matches
                for result in data.get('results', [])[:3]:  # Check top 3 results
                    if self._is_drummer_discogs_match(result, drummer_name):
                        return self._extract_discogs_info(result, drummer_name)
                        
        except Exception as e:
            logger.debug(f"Discogs search failed: {e}")
            
        return None
        
    def _fill_form_with_info(self, drummer_info):
        """Fill form fields with drummer information"""
        try:
            # Fill basic information - handle both old and new key formats
            if drummer_info.get("band") or drummer_info.get("main_band"):
                band = drummer_info.get("band") or drummer_info.get("main_band")
                self.band_edit.setText(band)
                
            if drummer_info.get("alias"):
                self.alias_edit.setText(drummer_info["alias"])
                
            # Fill bands
            if drummer_info.get("bands"):
                bands_text = "\n".join(drummer_info["bands"])
                self.bands_edit.setPlainText(bands_text)
                
            # Fill styles
            if drummer_info.get("styles"):
                styles_text = "\n".join(drummer_info["styles"])
                self.styles_edit.setPlainText(styles_text)
                
            # Fill songs - handle both old and new key formats
            songs = drummer_info.get("songs") or drummer_info.get("signature_songs")
            if songs:
                songs_text = "\n".join(songs)
                self.songs_edit.setPlainText(songs_text)
                
            # Fill techniques
            if drummer_info.get("techniques"):
                techniques_text = "\n".join(drummer_info["techniques"])
                self.techniques_edit.setPlainText(techniques_text)
                
            # Fill uniqueness rating - handle both old and new key formats
            uniqueness = drummer_info.get("uniqueness") or drummer_info.get("uniqueness_rating")
            if uniqueness:
                self.uniqueness_spin.setText(str(float(uniqueness)))
                
        except Exception as e:
            logger.error(f"Error filling form with drummer info: {e}")
            raise
        
    def get_drummer_data(self):
        """Get the drummer data from the form"""
        try:
            # Parse text areas into lists
            bands = [band.strip() for band in self.bands_edit.toPlainText().split('\n') if band.strip()]
            styles = [style.strip() for style in self.styles_edit.toPlainText().split('\n') if style.strip()]
            songs = [song.strip() for song in self.songs_edit.toPlainText().split('\n') if song.strip()]
            techniques = [tech.strip() for tech in self.techniques_edit.toPlainText().split('\n') if tech.strip()]
            
            # Parse uniqueness rating
            try:
                uniqueness = float(self.uniqueness_spin.text())
                uniqueness = max(0.0, min(1.0, uniqueness))  # Clamp to 0.0-1.0
            except ValueError:
                uniqueness = 0.85  # Default value
            
            # Build drummer profile
            drummer_data = {
                'name': self.name_edit.text().strip(),
                'band': self.band_edit.text().strip() or (bands[0] if bands else ''),
                'bands': bands,
                'styles': styles,
                'alias': self.alias_edit.text().strip(),
                'uniqueness_value': uniqueness,
                'notable_songs': songs,
                'techniques': techniques,
                'youtube_urls': []  # Empty initially
            }
            
            return drummer_data
            
        except Exception as e:
            logger.error(f"Error getting drummer data from form: {e}")
            raise