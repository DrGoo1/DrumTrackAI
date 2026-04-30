"""
Audio Player Tab Widget
======================
Provides audio playback functionality for the DrumTracKAI Admin application.
"""

import os
import logging
from pathlib import Path
from PySide6.QtCore import QUrl, Qt, Signal, Slot, QTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QSlider, QLabel, QFileDialog, QListWidget, 
    QListWidgetItem, QStyle, QSplitter
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

logger = logging.getLogger(__name__)

class AudioPlayerTab(QWidget):
    """Audio player widget with playlist capabilities"""

    status_updated = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_player()
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface components"""
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - playlist
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Playlist controls
        playlist_controls = QHBoxLayout()
        self.add_file_btn = QPushButton("Add File")
        self.add_folder_btn = QPushButton("Add Folder")
        self.clear_playlist_btn = QPushButton("Clear")
        
        playlist_controls.addWidget(self.add_file_btn)
        playlist_controls.addWidget(self.add_folder_btn)
        playlist_controls.addWidget(self.clear_playlist_btn)
        left_layout.addLayout(playlist_controls)
        
        # Playlist
        self.playlist = QListWidget()
        left_layout.addWidget(QLabel("Playlist:"))
        left_layout.addWidget(self.playlist)
        
        # Right panel - player controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Now playing info
        self.now_playing_label = QLabel("No file loaded")
        self.now_playing_label.setAlignment(Qt.AlignCenter)
        self.now_playing_label.setWordWrap(True)
        self.now_playing_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.now_playing_label)
        
        # Time display
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.duration_label = QLabel("0:00")
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.duration_label)
        right_layout.addLayout(time_layout)
        
        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        right_layout.addWidget(self.progress_slider)
        
        # Player controls
        controls_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.setMinimumWidth(60)
        
        self.next_btn = QPushButton()
        self.next_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(100)
        
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Volume:"))
        controls_layout.addWidget(self.volume_slider)
        
        right_layout.addLayout(controls_layout)
        right_layout.addStretch()
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 400])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
        
        self.connect_signals()
    
    def setup_player(self):
        """Initialize the media player"""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        self.current_file = None
        self.playlist_items = []
        
        # Connect player signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.errorOccurred.connect(self._on_error)
    
    def connect_signals(self):
        """Connect UI signals"""
        # Playlist controls
        self.add_file_btn.clicked.connect(self._on_add_file)
        self.add_folder_btn.clicked.connect(self._on_add_folder)
        self.clear_playlist_btn.clicked.connect(self._on_clear_playlist)
        self.playlist.itemDoubleClicked.connect(self._on_playlist_item_double_clicked)
        
        # Player controls
        self.play_btn.clicked.connect(self._on_play_pause)
        self.stop_btn.clicked.connect(self._on_stop)
        self.prev_btn.clicked.connect(self._on_previous)
        self.next_btn.clicked.connect(self._on_next)
        
        # Sliders
        self.progress_slider.sliderMoved.connect(self._seek_position)
        self.volume_slider.valueChanged.connect(self._set_volume)
        
        # Set initial volume
        self._set_volume(self.volume_slider.value())
    
    def _on_add_file(self):
        """Add audio file to playlist"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*.*)"
        )
        
        if files:
            self._add_files_to_playlist(files)
    
    def _on_add_folder(self):
        """Add all audio files from a folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            audio_files = []
            for ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a']:
                audio_files.extend(Path(folder).glob(f"**/*{ext}"))
            
            if audio_files:
                self._add_files_to_playlist([str(f) for f in audio_files])
                self.status_label.setText(f"Added {len(audio_files)} files from folder")
            else:
                self.status_label.setText("No audio files found in selected folder")
    
    def _add_files_to_playlist(self, file_paths):
        """Add multiple files to the playlist"""
        for file_path in file_paths:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                item = QListWidgetItem(filename)
                item.setData(Qt.UserRole, file_path)
                self.playlist.addItem(item)
                self.playlist_items.append(file_path)
        
        if not self.current_file and self.playlist_items:
            # Auto-select first item if nothing is playing
            self.playlist.setCurrentRow(0)
    
    def _on_clear_playlist(self):
        """Clear the playlist"""
        self.playlist.clear()
        self.playlist_items = []
        self.status_label.setText("Playlist cleared")
    
    def _on_playlist_item_double_clicked(self, item):
        """Handle playlist item selection"""
        file_path = item.data(Qt.UserRole)
        self.play_file(file_path)
    
    def play_file(self, file_path):
        """Play the selected audio file"""
        if os.path.exists(file_path):
            self.current_file = file_path
            self.player.setSource(QUrl.fromLocalFile(file_path))
            self.audio_output.setVolume(self.volume_slider.value() / 100)
            self.player.play()
            
            # Update display
            filename = os.path.basename(file_path)
            self.now_playing_label.setText(filename)
            self.status_label.setText(f"Playing: {filename}")
        else:
            self.status_label.setText(f"File not found: {os.path.basename(file_path)}")
    
    def _on_play_pause(self):
        """Toggle play/pause"""
        if not self.current_file and self.playlist_items:
            # Play first item if nothing selected
            if self.playlist.currentRow() < 0:
                self.playlist.setCurrentRow(0)
            item = self.playlist.currentItem()
            if item:
                self.play_file(item.data(Qt.UserRole))
        elif self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.status_label.setText("Paused")
        else:
            self.player.play()
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
    
    def _on_stop(self):
        """Stop playback"""
        self.player.stop()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.status_label.setText("Stopped")
    
    def _on_previous(self):
        """Play previous track"""
        current_row = self.playlist.currentRow()
        if current_row > 0:
            self.playlist.setCurrentRow(current_row - 1)
            item = self.playlist.currentItem()
            if item:
                self.play_file(item.data(Qt.UserRole))
    
    def _on_next(self):
        """Play next track"""
        current_row = self.playlist.currentRow()
        if current_row < self.playlist.count() - 1:
            self.playlist.setCurrentRow(current_row + 1)
            item = self.playlist.currentItem()
            if item:
                self.play_file(item.data(Qt.UserRole))
    
    def _seek_position(self, position):
        """Seek to position in current track"""
        self.player.setPosition(int(position / 100 * self.player.duration()))
    
    def _set_volume(self, volume):
        """Set player volume"""
        self.audio_output.setVolume(volume / 100)
    
    def _on_position_changed(self, position):
        """Update position display"""
        self.progress_slider.setValue(int(position / self.player.duration() * 100) if self.player.duration() > 0 else 0)
        self.current_time_label.setText(self._format_time(position))
    
    def _on_duration_changed(self, duration):
        """Update duration display"""
        self.duration_label.setText(self._format_time(duration))
    
    def _on_state_changed(self, state):
        """Handle player state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            
            # Auto-play next track if reached the end
            if state == QMediaPlayer.PlaybackState.StoppedState and self.player.position() > 0:
                current_row = self.playlist.currentRow()
                if current_row < self.playlist.count() - 1:
                    self._on_next()
    
    def _on_error(self, error, error_string):
        """Handle player errors"""
        self.status_label.setText(f"Error: {error_string}")
        logger.error(f"Media player error {error}: {error_string}")
    
    def _format_time(self, ms):
        """Format milliseconds as mm:ss"""
        total_seconds = int(ms / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def add_audio_file(self, file_path):
        """Add and play an audio file (public API method)"""
        if os.path.exists(file_path):
            self._add_files_to_playlist([file_path])
            # Select and play the newly added file
            self.playlist.setCurrentRow(self.playlist.count() - 1)
            self.play_file(file_path)
            return True
        return False
