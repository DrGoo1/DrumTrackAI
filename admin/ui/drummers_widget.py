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
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

try:
    import pytube
except Exception:
    pytube = None
from PySide6.QtCore import Qt, Signal, Slot, QSize, QUrl, QThread, QObject
from PySide6.QtGui import QIcon, QPixmap, QColor, QDesktopServices, QAction
from PySide6.QtWidgets import (
    QWidget, QMessageBox, QPushButton, QTableWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QGroupBox, QListWidget, QListWidgetItem,
    QTabWidget, QTextEdit, QPlainTextEdit, QSplitter, QTableWidgetItem, QHeaderView,
    QProgressBar, QToolButton, QMenu, QDialog,
    QFileDialog, QCheckBox, QRadioButton, QButtonGroup, QScrollArea, QSizePolicy
)

# Configure logging
logger = logging.getLogger(__name__)

# Try to import internal modules with fallbacks
try:
    from admin.services.youtube_service import YouTubeService
except ImportError:
    try:
        from services.youtube_service import YouTubeService
    except ImportError:
        # Create a simple placeholder
        logger.warning("YouTubeService not found, using placeholder")
        
        class YouTubeService:
            def __init__(self):
                pass
            
            def download_audio(self, video_url, output_path, progress_callback=None, 
                             completion_callback=None, error_callback=None, search_query=None, **_kwargs):
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
    from admin.utils.thread_safe_ui_updater import ThreadSafeUIUpdater
except ImportError:
    try:
        from utils.thread_safe_ui_updater import ThreadSafeUIUpdater
    except ImportError:
        # Create a simple placeholder
        logger.warning("ThreadSafeUIUpdater not found, using placeholder")
        
        class ThreadSafeUIUpdater:
            def __init__(self, parent=None):
                self.parent = parent
            
            def safe_update_ui(self, func, *args, **kwargs):
                try:
                    try:
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: func(*args, **kwargs))
                    except Exception:
                        func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in safe_update_ui: {e}")
            
            def run_in_main_thread(self, func, *args, **kwargs):
                try:
                    try:
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: func(*args, **kwargs))
                    except Exception:
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

try:
    from drummer_categories import DRUMMER_CATEGORIES
except Exception:
    DRUMMER_CATEGORIES = {}

try:
    from utils.youtube_search import YouTubeSearchAPI
except Exception:
    try:
        from admin.utils.youtube_search import YouTubeSearchAPI
    except Exception:
        class YouTubeSearchAPI:
            def __init__(self):
                pass

            def search(self, query, max_results=5):
                return []

try:
    from services.llm_proposal_client import LLMProposalClient
except Exception:
    try:
        from admin.services.llm_proposal_client import LLMProposalClient
    except Exception:
        LLMProposalClient = None

class DrummersWidget(QWidget):
    # Signals
    drummer_selected = Signal(dict)
    song_added = Signal(str, dict)
    batch_submitted = Signal(list)
    youtube_search_finished = Signal(list)
    download_completed = Signal(str, dict)
    auto_ingest_started = Signal()

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
        repo_root = Path(__file__).resolve().parents[2]
        self.data_root = str(repo_root / 'database')
        self.profiles_path = os.path.join(self.data_root, 'drummer_profiles.json')
        self._profiles_fallback_paths = [
            str(repo_root / 'admin' / 'data' / 'drummers' / 'profiles.json'),
            str(repo_root / 'admin' / 'admin' / 'data' / 'drummers' / 'profiles.json'),
        ]
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

        self._auto_ingest_state = {}
        self._auto_ingest_row_for_song = {}
        self._auto_ingest_batch_connected = False

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

    def _append_activity(self, message: str) -> None:
        try:
            from PySide6.QtCore import QTimer

            msg = str(message or "").strip()
            if not msg:
                return

            stamp = datetime.now().strftime("%H:%M:%S")
            line = f"[{stamp}] {msg}"

            def _update():
                try:
                    if hasattr(self, "activity_log") and self.activity_log:
                        self.activity_log.appendPlainText(line)
                except Exception:
                    pass

            QTimer.singleShot(0, _update)
        except Exception:
            pass

    def _ai_set_state(self, song: str, stage: str, progress: int = None, details: str = None) -> None:
        try:
            from PySide6.QtCore import QTimer

            s = str(song or '').strip() or 'Unknown'
            st = str(stage or '').strip() or 'UNKNOWN'
            now = time.strftime('%H:%M:%S')
            prev = self._auto_ingest_state.get(s) or {}
            if progress is None:
                progress = prev.get('progress')
            if details is None:
                details = prev.get('details')

            self._auto_ingest_state[s] = {
                'stage': st,
                'progress': progress,
                'updated': now,
                'details': details,
            }

            def _render():
                try:
                    if not hasattr(self, 'auto_ingest_monitor') or not self.auto_ingest_monitor:
                        return

                    row = self._auto_ingest_row_for_song.get(s)
                    if row is None:
                        row = self.auto_ingest_monitor.rowCount()
                        self.auto_ingest_monitor.insertRow(row)
                        self._auto_ingest_row_for_song[s] = row
                        self.auto_ingest_monitor.setItem(row, 0, QTableWidgetItem(s))

                    state = self._auto_ingest_state.get(s) or {}
                    prog = state.get('progress')
                    prog_txt = ''
                    try:
                        if prog is None:
                            prog_txt = ''
                        elif int(prog) < 0:
                            prog_txt = '...'
                        else:
                            prog_txt = f"{int(prog)}%"
                    except Exception:
                        prog_txt = str(prog)

                    self.auto_ingest_monitor.setItem(row, 1, QTableWidgetItem(str(state.get('stage') or '')))
                    self.auto_ingest_monitor.setItem(row, 2, QTableWidgetItem(prog_txt))
                    self.auto_ingest_monitor.setItem(row, 3, QTableWidgetItem(str(state.get('updated') or '')))
                    self.auto_ingest_monitor.setItem(row, 4, QTableWidgetItem(str(state.get('details') or '')))
                    try:
                        self.auto_ingest_monitor.resizeRowToContents(row)
                    except Exception:
                        pass
                except Exception:
                    pass

            QTimer.singleShot(0, _render)
        except Exception:
            pass

    def _on_auto_ingest_download_progress(self, song: str, progress: int) -> None:
        try:
            p = int(progress) if progress is not None else None
        except Exception:
            p = progress

        stage = 'DOWNLOADING'
        try:
            if p is not None and int(p) >= 95:
                stage = 'CONVERTING'
        except Exception:
            pass
        self._ai_set_state(song, stage, progress=p)

    def _on_auto_ingest_analysis_done(self, song: str, ok: bool, details: str = None) -> None:
        if ok:
            self._ai_set_state(song, 'DRUMMERBRAIN_UPDATED', progress=100, details=details or 'ok')
        else:
            self._ai_set_state(song, 'FAILED', details=details or 'analysis failed')

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

        # Fingerprint assignment (copyright-safe)
        assignment_group = QGroupBox("Fingerprint Assignment")
        assignment_layout = QVBoxLayout(assignment_group)

        drummer_id_row = QHBoxLayout()
        drummer_id_row.addWidget(QLabel("Anonymized Drummer ID:"))
        self.anonymized_drummer_id_edit = QLineEdit()
        self.anonymized_drummer_id_edit.setPlaceholderText("e.g. drm_0007")
        drummer_id_row.addWidget(self.anonymized_drummer_id_edit)
        assignment_layout.addLayout(drummer_id_row)

        assignment_layout.addWidget(QLabel("Category IDs:"))
        self.category_ids_list = QListWidget()
        self.category_ids_list.setSelectionMode(QListWidget.MultiSelection)
        for cid, cdata in (DRUMMER_CATEGORIES or {}).items():
            label = str((cdata or {}).get("display_name") or cid)
            item = QListWidgetItem(f"{label} ({cid})")
            item.setData(Qt.ItemDataRole.UserRole, str(cid))
            self.category_ids_list.addItem(item)
        assignment_layout.addWidget(self.category_ids_list)

        details_layout.addWidget(assignment_group)

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
        self.auto_ingest_btn = QPushButton("Auto-Ingest")
        self.local_ingest_btn = QPushButton("Ingest Local Folder")
        song_actions.addWidget(self.add_song_btn)
        song_actions.addWidget(self.find_on_youtube_btn)
        song_actions.addWidget(self.process_all_btn)
        song_actions.addWidget(self.auto_ingest_btn)
        song_actions.addWidget(self.local_ingest_btn)
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

        self.activity_log = QPlainTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(120)
        try:
            self.activity_log.document().setMaximumBlockCount(200)
        except Exception:
            pass
        youtube_layout.addWidget(QLabel("Activity / Steps:"))
        youtube_layout.addWidget(self.activity_log)

        self.auto_ingest_monitor = QTableWidget()
        self.auto_ingest_monitor.setColumnCount(5)
        self.auto_ingest_monitor.setHorizontalHeaderLabels(["Song", "Stage", "Progress", "Updated", "Details"])
        try:
            self.auto_ingest_monitor.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.auto_ingest_monitor.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.auto_ingest_monitor.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.auto_ingest_monitor.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.auto_ingest_monitor.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        except Exception:
            pass
        self.auto_ingest_monitor.setMinimumHeight(120)
        self.auto_ingest_monitor.setMaximumHeight(180)
        youtube_layout.addWidget(QLabel("Auto-Ingest Monitor:"))
        youtube_layout.addWidget(self.auto_ingest_monitor)

        right_layout.addWidget(youtube_group)

        # Add all panels to the splitter
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(center_widget)
        self.main_splitter.addWidget(right_widget)

        # Set initial splitter sizes
        self.main_splitter.setSizes([200, 400, 300])

        # Add splitter to main layout
        main_layout.addWidget(self.main_splitter)

    def connect_signals(self):
        """Connect all UI signals"""
        try:
            self.drummer_list.itemSelectionChanged.connect(self._on_drummer_selected)
            self.add_drummer_btn.clicked.connect(self._on_add_drummer)
            self.edit_drummer_btn.clicked.connect(self._on_edit_drummer)
            self.delete_drummer_btn.clicked.connect(self._on_delete_drummer)

            self.songs_table.itemSelectionChanged.connect(self._on_song_selected)
            self.add_song_btn.clicked.connect(self._on_add_song)
            self.find_on_youtube_btn.clicked.connect(self._on_find_song_on_youtube)
            self.process_all_btn.clicked.connect(self._on_process_all_with_mvsep)
            if hasattr(self, "auto_ingest_btn"):
                self.auto_ingest_btn.clicked.connect(self._on_auto_ingest)
            if hasattr(self, "local_ingest_btn"):
                self.local_ingest_btn.clicked.connect(self._on_ingest_local_folder)

            self.youtube_search_btn.clicked.connect(self._on_youtube_search)
            self.download_btn.clicked.connect(self._on_download_video)
            self.play_preview_btn.clicked.connect(self._on_play_preview)
            self.youtube_search_edit.returnPressed.connect(self._on_youtube_search)

            self.genre_combo.currentIndexChanged.connect(self.populate_drummer_list)
            self.search_edit.textChanged.connect(self.populate_drummer_list)
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            traceback.print_exc()

    def load_drummer_profiles(self):
        try:
            self.drummer_profiles = []

            candidate_paths = [self.profiles_path]
            try:
                candidate_paths.extend(self._profiles_fallback_paths or [])
            except Exception:
                pass

            chosen_path = None
            for p in candidate_paths:
                if p and os.path.exists(p):
                    chosen_path = p
                    break

            if chosen_path:
                with open(chosen_path, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get('profiles'), list):
                    self.drummer_profiles = data.get('profiles') or []
                elif isinstance(data, list):
                    self.drummer_profiles = data
                else:
                    self.drummer_profiles = []
            else:
                self.drummer_profiles = []

            all_genres = set()
            try:
                for drummer in self.drummer_profiles:
                    for style in (drummer or {}).get('styles', []) or []:
                        all_genres.add(str(style))
            except Exception:
                pass

            try:
                self.genre_combo.clear()
                self.genre_combo.addItem('All Genres')
                for g in sorted(all_genres):
                    self.genre_combo.addItem(g)
            except Exception:
                pass

            self.populate_drummer_list()

            logger.info(f"Loaded {len(self.drummer_profiles)} drummer profiles")

        except Exception as e:
            logger.error(f"Error loading drummer profiles: {e}")
            logger.error(traceback.format_exc())
            self.drummer_profiles = []

    def populate_drummer_list(self):
        try:
            self.drummer_list.clear()

            selected_genre = ''
            try:
                selected_genre = str(self.genre_combo.currentText() or '')
            except Exception:
                selected_genre = ''

            search_text = ''
            try:
                search_text = str(self.search_edit.text() or '').lower()
            except Exception:
                search_text = ''

            self.filtered_drummers = []
            for drummer in self.drummer_profiles or []:
                if not isinstance(drummer, dict):
                    continue

                if selected_genre and selected_genre != 'All Genres':
                    styles = drummer.get('styles') or []
                    if selected_genre not in styles:
                        continue

                if search_text:
                    if search_text not in str(drummer.get('name') or '').lower():
                        continue

                self.filtered_drummers.append(drummer)
                item = QListWidgetItem(str(drummer.get('name') or 'Unknown Drummer'))
                item.setData(Qt.ItemDataRole.UserRole, drummer)
                self.drummer_list.addItem(item)

            self.current_drummer = None
            try:
                self.update_drummer_details()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error populating drummer list: {e}")
            logger.error(traceback.format_exc())

    def _on_drummer_selected(self):
        try:
            item = self.drummer_list.currentItem()
            if not item:
                self.current_drummer = None
                self.update_drummer_details()
                self._update_button_states()
                return

            drummer = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(drummer, dict):
                self.current_drummer = drummer
            else:
                self.current_drummer = None

            self.update_drummer_details()
            self._update_button_states()

        except Exception as e:
            logger.error(f"Error handling drummer selection: {e}")

    def update_drummer_details(self):
        try:
            if not self.current_drummer:
                try:
                    self.details_group.setTitle('Drummer Details')
                except Exception:
                    pass
                try:
                    self.drummer_info.clear()
                except Exception:
                    pass
                try:
                    self.songs_table.setRowCount(0)
                except Exception:
                    pass
                return

            name = str(self.current_drummer.get('name') or 'Unknown')
            try:
                self.details_group.setTitle(f"Drummer: {name}")
            except Exception:
                pass

            info_lines = [f"Name: {name}"]
            band = self.current_drummer.get('main_band') or self.current_drummer.get('band')
            if band:
                info_lines.append(f"Band: {band}")
            styles = self.current_drummer.get('styles') or []
            if styles:
                info_lines.append(f"Styles: {', '.join([str(s) for s in styles])}")

            try:
                self.drummer_info.setPlainText('\n'.join(info_lines))
            except Exception:
                try:
                    self.drummer_info.setText('\n'.join(info_lines))
                except Exception:
                    pass

            songs = self.current_drummer.get('signature_songs') or []
            if not isinstance(songs, list):
                songs = []
            try:
                self.songs_table.setRowCount(len(songs))
                for i, s in enumerate(songs):
                    song_title = str(s)
                    item = QTableWidgetItem(song_title)
                    item.setData(Qt.ItemDataRole.UserRole, {'title': song_title, 'file_path': ''})
                    self.songs_table.setItem(i, 0, item)
                    self.songs_table.setItem(i, 1, QTableWidgetItem(''))
                    self.songs_table.setItem(i, 2, QTableWidgetItem(''))
                    self.songs_table.setItem(i, 3, QTableWidgetItem(''))
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error updating drummer details: {e}")

    def _update_button_states(self):
        try:
            has_drummer = bool(self.current_drummer)
            self.edit_drummer_btn.setEnabled(has_drummer)
            self.delete_drummer_btn.setEnabled(has_drummer)
            self.process_all_btn.setEnabled(has_drummer)
            self.local_ingest_btn.setEnabled(has_drummer)
        except Exception:
            pass

    def _on_add_drummer(self):
        try:
            QMessageBox.information(self, "Add Drummer", "Not implemented")
        except Exception:
            pass

    def _on_edit_drummer(self):
        try:
            QMessageBox.information(self, "Edit Drummer", "Not implemented")
        except Exception:
            pass

    def _on_delete_drummer(self):
        try:
            QMessageBox.information(self, "Delete Drummer", "Not implemented")
        except Exception:
            pass

    def _on_song_selected(self):
        try:
            self._update_button_states()
        except Exception:
            pass

    def _on_add_song(self):
        try:
            QMessageBox.information(self, "Add Song", "Not implemented")
        except Exception:
            pass

    def _on_find_song_on_youtube(self):
        try:
            QMessageBox.information(self, "Find on YouTube", "Not implemented")
        except Exception:
            pass

    def _on_find_on_youtube_at_row(self, _row):
        try:
            QMessageBox.information(self, "Find on YouTube", "Not implemented")
        except Exception:
            pass

    def _on_play_song_at_row(self, _row):
        try:
            QMessageBox.information(self, "Play Song", "Not implemented")
        except Exception:
            pass

    def _on_process_all_with_mvsep(self):
        try:
            QMessageBox.information(self, "Process All", "Use 'Ingest Local Folder' or per-song processing")
        except Exception:
            pass

    def _on_auto_ingest(self):
        try:
            QMessageBox.information(self, "Auto-Ingest", "Not implemented")
        except Exception:
            pass

    def _on_youtube_search(self):
        try:
            QMessageBox.information(self, "YouTube Search", "Not implemented")
        except Exception:
            pass

    def _on_download_video(self):
        try:
            QMessageBox.information(self, "Download", "Not implemented")
        except Exception:
            pass

    def _on_play_preview(self):
        try:
            QMessageBox.information(self, "Play Preview", "Not implemented")
        except Exception:
            pass

    def _get_tempo_style_data(self, _audio_file_path):
        return {"tempo": None, "style": "unknown", "sections": [], "key": "C"}

    def analyze_song_arrangement(self, _file_path):
        try:
            QMessageBox.information(self, "Arrangement", "Not implemented")
        except Exception:
            pass

    def _process_with_mvsep(self, _song_info):
        try:
            QMessageBox.information(self, "MVSep", "Use 'Ingest Local Folder' to queue audio for processing")
        except Exception:
            pass

    def _on_ingest_local_folder(self):
        try:
            if not self.current_drummer:
                QMessageBox.warning(self, "Ingest Local Folder", "Select a drummer first.")
                return

            folder = QFileDialog.getExistingDirectory(self, "Select Folder of Audio Files")
            folder = str(folder or "").strip()
            if not folder:
                return

            anon_id = ""
            try:
                anon_id = str(self.anonymized_drummer_id_edit.text() or "").strip()
            except Exception:
                anon_id = ""

            category_ids: List[str] = []
            try:
                for it in self.category_ids_list.selectedItems() or []:
                    cid = it.data(Qt.ItemDataRole.UserRole)
                    if cid:
                        category_ids.append(str(cid))
            except Exception:
                category_ids = []

            exts = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}
            files: List[str] = []
            try:
                for name in os.listdir(folder):
                    p = os.path.join(folder, name)
                    if not os.path.isfile(p):
                        continue
                    if os.path.splitext(name)[1].lower() in exts:
                        files.append(p)
            except Exception as e:
                QMessageBox.critical(self, "Ingest Local Folder", f"Failed to scan folder:\n{e}")
                return

            if not files:
                QMessageBox.information(self, "Ingest Local Folder", "No audio files found in that folder.")
                return

            try:
                if hasattr(self, "auto_ingest_monitor") and self.auto_ingest_monitor:
                    self.auto_ingest_monitor.setRowCount(0)
                self._auto_ingest_state = {}
                self._auto_ingest_row_for_song = {}
            except Exception:
                pass

            queued = 0
            drummer_id = "unknown"
            try:
                drummer_id = (self.current_drummer or {}).get("id") or "unknown"
            except Exception:
                drummer_id = "unknown"

            for audio_path in sorted(files):
                try:
                    title = os.path.splitext(os.path.basename(audio_path))[0]
                    safe_title = title
                    try:
                        safe_title = self._sanitize_filename(title)
                    except Exception:
                        safe_title = title

                    output_dir = os.path.join(self.mvsep_output_path, str(drummer_id), str(safe_title))
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                    except Exception:
                        pass

                    try:
                        self._append_activity(f"Local ingest queued: {title}")
                    except Exception:
                        pass

                    try:
                        self._ai_set_state(title, "QUEUED_TO_MVSEP", progress=0, details=os.path.basename(audio_path))
                    except Exception:
                        pass

                    metadata = {
                        "source": "drummers_tab",
                        "analysis_type": "drum_profiling",
                        "timestamp": datetime.now().isoformat(),
                        "anonymized_drummer_id": anon_id,
                        "category_ids": category_ids,
                        "song_title": title,
                        "local_audio_path": audio_path,
                        "require_bass_stem": True,
                    }

                    ok = False
                    try:
                        ok = bool(
                            self._send_to_batch_processor(
                                audio_path,
                                metadata,
                                output_dir=output_dir,
                                show_message=False,
                                start_processing=False,
                            )
                        )
                    except Exception as e:
                        ok = False
                        try:
                            self._append_activity(f"Local ingest failed to queue: {title} :: {e}")
                        except Exception:
                            pass

                    if ok:
                        queued += 1
                        try:
                            self._ai_set_state(title, "QUEUED_TO_MVSEP", progress=0, details="queued")
                        except Exception:
                            pass
                    else:
                        try:
                            self._ai_set_state(title, "FAILED", details="failed to queue")
                        except Exception:
                            pass

                except Exception as e:
                    logger.error(f"Local ingest error for {audio_path}: {e}")

            try:
                from admin.ui.batch_processor_widget import get_batch_processor

                batch_processor = get_batch_processor()
                self._connect_batch_processor_signals(batch_processor)
                if queued > 0 and not batch_processor.is_processing:
                    batch_processor.start_processing()
            except Exception as e:
                logger.error(f"Failed to start batch processing after local ingest: {e}")

            if queued <= 0:
                QMessageBox.warning(self, "Ingest Local Folder", "No files were queued. Check logs for details.")
            else:
                QMessageBox.information(
                    self,
                    "Ingest Local Folder",
                    f"Queued {queued} file(s) for processing.\n\n"
                    f"Outputs will be written under:\n{os.path.join(self.mvsep_output_path, str(drummer_id))}",
                )

        except Exception as e:
            logger.error(f"Error in local folder ingest: {e}")
            QMessageBox.critical(self, "Ingest Local Folder", f"Failed: {str(e)}")

    def _send_to_batch_processor(self, audio_file_path, metadata=None, output_dir=None, show_message=True, start_processing=True):
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
            auto_md = {
                'source': 'drummers_tab',
                'drummer_id': self.current_drummer.get('id', 'unknown') if self.current_drummer else 'unknown',
                'drummer_name': self.current_drummer.get('name', 'Unknown') if self.current_drummer else 'Unknown',
                'song_name': os.path.basename(audio_file_path),
                'analysis_type': 'entire_song',
                'tempo': tempo_style_data.get('tempo', 'Unknown'),
                'style': tempo_style_data.get('style', 'Unknown'),
                'sections': tempo_style_data.get('sections', []),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

            if isinstance(metadata, dict) and metadata:
                auto_md.update(metadata)

            metadata = auto_md

            logger.info(f"Adding file to batch processor with metadata: {metadata}")

            # Create output directory for MVSep results
            if not output_dir:
                if self.current_drummer:
                    drummer_id = self.current_drummer.get('id', 'unknown')
                else:
                    drummer_id = 'unknown'
                song_name = os.path.splitext(os.path.basename(audio_file_path))[0]
                safe_song_name = song_name
                try:
                    safe_song_name = self._sanitize_filename(song_name)
                except Exception:
                    safe_song_name = song_name
                output_dir = os.path.join(self.mvsep_output_path, str(drummer_id), str(safe_song_name))
            os.makedirs(output_dir, exist_ok=True)

            # Add to batch processor queue with correct parameters
            # Access the actual BatchProcessor service through the widget
            from admin.ui.batch_processor_widget import get_batch_processor

            batch_processor = get_batch_processor()
            self._connect_batch_processor_signals(batch_processor)

            success = batch_processor.add_to_queue(
                input_file=audio_file_path,
                output_dir=output_dir,
                metadata=metadata
            )

            if success:
                logger.info(f"Successfully added {audio_file_path} to batch processing queue")
                if show_message:
                    try:
                        QMessageBox.information(
                            self,
                            "Job Added to Queue",
                            f"'{os.path.basename(audio_file_path)}' has been added to the batch processing queue.\n\n"
                            f"Check the Batch Process tab to monitor progress.",
                        )
                    except Exception:
                        pass

                if start_processing and not batch_processor.is_processing:
                    batch_processor.start_processing()
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


    def _connect_batch_processor_signals(self, batch_processor):
        """Connect to batch processor signals to handle completion and analysis"""
        try:
            if getattr(self, "_auto_ingest_batch_connected", False):
                return
            self._auto_ingest_batch_connected = True

            batch_processor.processing_completed.connect(self._on_batch_processing_completed)
            batch_processor.file_processing_completed.connect(self._on_file_processing_completed)
            if hasattr(batch_processor, "file_processing_started"):
                batch_processor.file_processing_started.connect(self._on_file_processing_started)
            if hasattr(batch_processor, "file_processing_failed"):
                batch_processor.file_processing_failed.connect(self._on_file_processing_failed)
            if hasattr(batch_processor, "progress_updated"):
                batch_processor.progress_updated.connect(self._on_batch_progress_updated)

            logger.info("Connected to batch processor signals for drum analysis workflow")

        except Exception as e:
            logger.error(f"Error connecting batch processor signals: {e}")
            logger.error(traceback.format_exc())


    def _song_title_from_batch(self, file_path: str, metadata: Dict[str, Any] = None) -> str:
        try:
            if isinstance(metadata, dict):
                for k in ("song_title", "title", "song", "name"):
                    v = metadata.get(k)
                    if v:
                        return str(v).strip()
        except Exception:
            pass

        try:
            return os.path.splitext(os.path.basename(str(file_path)))[0]
        except Exception:
            return "Unknown"


    def _on_file_processing_started(self, batch_id, file_path, file_index, total_files):
        try:
            song = self._song_title_from_batch(file_path, None)
            self._ai_set_state(song, "MVSEP_RUNNING", details=f"batch={batch_id} ({file_index}/{total_files})")
        except Exception:
            pass


    def _on_file_processing_failed(self, batch_id, file_path, error, file_index, total_files):
        try:
            song = self._song_title_from_batch(file_path, None)
            msg = str(error or "").strip()
            self._ai_set_state(song, "FAILED", details=(msg[:240] if msg else f"MVSep failed: batch={batch_id}"))
        except Exception:
            pass


    def _on_batch_progress_updated(self, batch_id, progress, message):
        try:
            msg = str(message or "")
            file_name = ""
            if ":" in msg:
                file_name = msg.split(":", 1)[0].strip()
            file_path = file_name

            song = self._song_title_from_batch(file_path, None)
            if not song:
                return

            p = None
            try:
                p = float(progress) if progress is not None else None
            except Exception:
                p = None

            pct = None
            if p is not None:
                if 0.0 <= p <= 1.0:
                    pct = int(p * 100)
                else:
                    pct = int(p)
                if pct < 0:
                    pct = 0
                if pct > 100:
                    pct = 100

            details = ""
            try:
                details = msg[:240]
            except Exception:
                details = ""

            self._ai_set_state(song, "MVSEP_RUNNING", progress=pct, details=details)
        except Exception:
            pass


    def _on_batch_processing_completed(self, batch_id, summary):
        """Handle batch processing completion"""
        try:
            logger.info(f"Batch processing completed: {batch_id}")
        except Exception:
            pass


    def _on_file_processing_completed(self, batch_id, file_path, result, file_index, total_files):
        """Handle individual file processing completion"""
        try:
            logger.info(f"File processing completed: {os.path.basename(file_path)}")

            md = None
            song = None
            try:
                md = (result or {}).get("metadata") if isinstance(result, dict) else None
                song = self._song_title_from_batch(file_path, md)
                self._ai_set_state(song, "MVSEP_DONE", details=f"batch={batch_id} ({file_index}/{total_files})")
            except Exception:
                song = None

            if isinstance(result, dict) and result.get("success") and (result.get("metadata") or {}).get("source") == "drummers_tab":
                try:
                    if song:
                        self._ai_set_state(song, "ANALYSIS_RUNNING")
                    self._run_advanced_drummer_analysis_from_mvsep(file_path, result)
                    if song:
                        self._on_auto_ingest_analysis_done(song, True)
                except Exception as e:
                    logger.error(f"Error running advanced drummer analysis after MVSep: {e}")
                    if song:
                        self._on_auto_ingest_analysis_done(song, False, details=str(e))

        except Exception as e:
            logger.error(f"Error handling file processing completion: {e}")


    def _run_advanced_drummer_analysis_from_mvsep(self, source_file: str, mvsep_result: Dict[str, Any]) -> None:
        """Run AdvancedDrummerAnalysis via PhasedDrumAnalysis using an already-computed MVSep result."""
        if not self.phased_analysis:
            return

        try:
            from services.phased_drum_analysis import AnalysisJob
        except Exception:
            from admin.services.phased_drum_analysis import AnalysisJob

        output_dir = mvsep_result.get("output_dir") or self.mvsep_output_path
        os.makedirs(output_dir, exist_ok=True)

        metadata = mvsep_result.get("metadata") or {}
        tempo = metadata.get("tempo")
        style = metadata.get("style")
        key = metadata.get("key") or "C"

        job = AnalysisJob(
            job_id=str(uuid.uuid4()),
            source_url="",
            source_file=str(source_file),
            output_directory=str(output_dir),
        )

        stems = mvsep_result.get("result_files") or {}
        job.results.update(
            {
                "source_file": str(source_file),
                "tempo": tempo if tempo is not None else 120.0,
                "style": style if style is not None else "unknown",
                "key": key,
                "mvsep_results": {"stems": stems},
            }
        )

        anon_id = (metadata.get("anonymized_drummer_id") or metadata.get("drummer_id") or "").strip()
        if anon_id:
            job.results["anonymized_drummer_id"] = anon_id

        category_ids = metadata.get("category_ids")
        if isinstance(category_ids, str):
            category_ids = [category_ids]
        if isinstance(category_ids, list) and category_ids:
            job.results["category_ids"] = [str(x).strip() for x in category_ids if str(x).strip()]

        success, message, _drum_results = self.phased_analysis._process_drum_analysis(job)
        if not success:
            logger.warning(f"Advanced drummer analysis failed: {message}")
            return

        logger.info(f"Advanced drummer analysis completed: {message}")


    def _sanitize_filename(self, filename):
        invalid_chars = '<>:"/\\|?*'
        for ch in invalid_chars:
            filename = filename.replace(ch, "_")
        filename = re.sub(r"\s+", "_", filename).strip("._ ")
        return filename[:120] if filename else "unknown"


# Auto-ingestion dialog (drummer-name -> propose 3 songs -> approve -> run)
class AutoIngestDialog(QDialog):
    def __init__(self, parent=None, youtube_api=None, proposal_client_cls=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Ingest")
        self.setMinimumSize(900, 600)
        self.setModal(True)

        self.youtube_api = youtube_api
        self.proposal_client_cls = proposal_client_cls

        self._proposal_client = None
        self._plan_rows: List[Dict[str, Any]] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        settings_group = QGroupBox("LLM Settings (Ollama)")
        settings_layout = QHBoxLayout(settings_group)

        settings_layout.addWidget(QLabel("URL:"))
        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setText(os.getenv("DRUMTRACAI_OLLAMA_URL", "http://localhost:11434"))
        settings_layout.addWidget(self.ollama_url_edit)

        settings_layout.addWidget(QLabel("Model:"))
        self.ollama_model_edit = QLineEdit()
        self.ollama_model_edit.setText(os.getenv("DRUMTRACAI_OLLAMA_MODEL", ""))
        self.ollama_model_edit.setPlaceholderText("e.g. qwen2.5:7b-instruct")
        settings_layout.addWidget(self.ollama_model_edit)

        self.use_llm_checkbox = QCheckBox("Use LLM")
        self.use_llm_checkbox.setChecked(True)
        settings_layout.addWidget(self.use_llm_checkbox)

        layout.addWidget(settings_group)

        input_group = QGroupBox("Drummer Names (one per line)")
        input_layout = QVBoxLayout(input_group)
        self.drummer_names_edit = QPlainTextEdit()
        self.drummer_names_edit.setPlaceholderText("John Bonham\nNeil Peart\nBuddy Rich")
        input_layout.addWidget(self.drummer_names_edit)
        layout.addWidget(input_group)

        actions_layout = QHBoxLayout()
        self.propose_btn = QPushButton("Propose")
        self.propose_btn.clicked.connect(self._on_propose)
        actions_layout.addWidget(self.propose_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        self.plan_table = QTableWidget()
        self.plan_table.setColumnCount(7)
        self.plan_table.setHorizontalHeaderLabels([
            "Approve",
            "Drummer",
            "Anon ID",
            "Category IDs (comma)",
            "Song 1",
            "Song 2",
            "Song 3",
        ])
        self.plan_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.plan_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.plan_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.plan_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.plan_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.plan_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.plan_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        layout.addWidget(self.plan_table)

        buttons = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Run")
        ok_btn.clicked.connect(self._on_run)
        ok_btn.setDefault(True)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(ok_btn)
        layout.addLayout(buttons)

    def _on_run(self):
        if not self._plan_rows:
            QMessageBox.information(self, "Auto-Ingest", "Click 'Propose' first to generate a plan.")
            return

        approved = self.get_approved_plan_rows()
        if not approved:
            QMessageBox.information(self, "Auto-Ingest", "No approved rows. Check the 'Approve' box for at least one drummer.")
            return

        has_song = False
        for row in approved:
            songs = row.get("songs") or []
            if not isinstance(songs, list):
                continue
            for song in songs:
                if isinstance(song, dict) and str(song.get("url") or "").strip():
                    has_song = True
                    break
            if has_song:
                break

        if not has_song:
            QMessageBox.warning(self, "Auto-Ingest", "No valid YouTube URLs found in the proposed plan. Try 'Propose' again.")
            return

        self.accept()

    def _make_proposal_client(self):
        if self._proposal_client is not None:
            return self._proposal_client

        if not self.proposal_client_cls:
            self._proposal_client = None
            return None

        try:
            self._proposal_client = self.proposal_client_cls(
                base_url=(self.ollama_url_edit.text() or "").strip(),
                model=(self.ollama_model_edit.text() or "").strip(),
            )
        except Exception:
            self._proposal_client = None
        return self._proposal_client

    def _default_anon_id(self, drummer_name: str) -> str:
        # Stable-ish ID suggestion for curator review.
        v = abs(hash(drummer_name.strip().lower())) % 10000
        return f"drm_{v:04d}"

    def _on_propose(self):
        drummer_names = [ln.strip() for ln in (self.drummer_names_edit.toPlainText() or "").splitlines() if ln.strip()]
        if not drummer_names:
            QMessageBox.warning(self, "Auto-Ingest", "Please enter at least one drummer name.")
            return

        if not self.youtube_api:
            QMessageBox.critical(self, "Auto-Ingest", "YouTube search is not available.")
            return

        proposal_client = self._make_proposal_client()
        use_llm = bool(self.use_llm_checkbox.isChecked())

        self._plan_rows = []
        self.plan_table.setRowCount(0)

        available_category_ids = list((DRUMMER_CATEGORIES or {}).keys())

        for drummer_name in drummer_names:
            try:
                query = f"{drummer_name} signature songs studio version"
                results = self.youtube_api.search(query, max_results=15)

                picked_songs: List[Dict[str, Any]] = []
                if proposal_client:
                    picked, _meta = proposal_client.propose_signature_songs(
                        drummer_name=drummer_name,
                        youtube_results=results,
                        n=3,
                        use_llm=use_llm,
                    )
                    for c in picked:
                        picked_songs.append({"title": c.title, "url": c.url})
                else:
                    # Heuristic fallback: just take first 3 results with url/title.
                    for r in results[:3]:
                        title = str(r.get("title") or "").strip()
                        url = str(r.get("url") or "").strip()
                        if not url and r.get("id"):
                            url = f"https://www.youtube.com/watch?v={r['id']}"
                        if title and url:
                            picked_songs.append({"title": title, "url": url})

                chosen_titles = [s.get("title", "") for s in picked_songs]
                category_ids: List[str] = []
                if proposal_client and available_category_ids:
                    category_ids, _cmeta = proposal_client.propose_category_ids(
                        drummer_name=drummer_name,
                        chosen_titles=chosen_titles,
                        available_category_ids=available_category_ids,
                        use_llm=use_llm,
                    )

                plan_row = {
                    "drummer_name": drummer_name,
                    "anonymized_drummer_id": self._default_anon_id(drummer_name),
                    "category_ids": category_ids,
                    "songs": picked_songs,
                }
                self._plan_rows.append(plan_row)

            except Exception as e:
                logger.error(f"Auto-ingest propose failed for '{drummer_name}': {e}")

        self._render_plan_rows()

    def _render_plan_rows(self):
        self.plan_table.setRowCount(len(self._plan_rows))
        for i, row in enumerate(self._plan_rows):
            approve_item = QTableWidgetItem("")
            approve_item.setFlags(approve_item.flags() | Qt.ItemIsUserCheckable)
            approve_item.setCheckState(Qt.Checked)
            self.plan_table.setItem(i, 0, approve_item)

            self.plan_table.setItem(i, 1, QTableWidgetItem(str(row.get("drummer_name") or "")))

            anon_item = QTableWidgetItem(str(row.get("anonymized_drummer_id") or ""))
            self.plan_table.setItem(i, 2, anon_item)

            cats = row.get("category_ids") or []
            if isinstance(cats, list):
                cats_txt = ",".join([str(x) for x in cats])
            else:
                cats_txt = str(cats)
            self.plan_table.setItem(i, 3, QTableWidgetItem(cats_txt))

            songs = row.get("songs") or []
            for si in range(3):
                title = ""
                if si < len(songs) and isinstance(songs[si], dict):
                    title = str(songs[si].get("title") or "")
                self.plan_table.setItem(i, 4 + si, QTableWidgetItem(title))

        self.plan_table.resizeRowsToContents()

    def get_approved_plan_rows(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for i in range(self.plan_table.rowCount()):
            approve_item = self.plan_table.item(i, 0)
            if not approve_item or approve_item.checkState() != Qt.Checked:
                continue

            if i >= len(self._plan_rows):
                continue

            base = dict(self._plan_rows[i])
            anon_item = self.plan_table.item(i, 2)
            if anon_item:
                base["anonymized_drummer_id"] = str(anon_item.text() or "").strip()

            cat_item = self.plan_table.item(i, 3)
            if cat_item:
                cat_txt = str(cat_item.text() or "")
                base["category_ids"] = [x.strip() for x in cat_txt.split(",") if x.strip()]

            out.append(base)
        return out


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
        self.setWindowTitle("Add Drummer")
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