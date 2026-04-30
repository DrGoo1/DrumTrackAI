#!/usr/bin/env python3
"""
Simple, working DrummersWidget - reverted to basic functionality
that was working before MVSep integration complications
"""

import os
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QListWidgetItem, QPushButton, QLabel, QMenu, QMessageBox)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

class DrummersWidget(QWidget):
    """Simple DrummersWidget focused on core functionality"""
    
    def __init__(self, parent=None):
        """Initialize the DrummersWidget with simple, working approach"""
        super().__init__(parent)
        
        # Simple initialization
        self.current_drummer = None
        self.drummer_profiles = {}
        
        # Create UI and load data immediately
        self.setup_ui()
        self.load_drummer_data()
        self.populate_list()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("DRUM Famous Drummers Analysis")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #FFD700;
                padding: 10px;
                text-align: center;
            }
        """)
        layout.addWidget(title)
        
        # Drummer list
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
        layout.addWidget(self.drummer_list)
        
        # Buttons
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
        """)
        
        button_layout.addWidget(self.analyze_button)
        button_layout.addWidget(self.download_button)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.drummer_list.itemSelectionChanged.connect(self.on_drummer_selected)
        self.drummer_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.drummer_list.customContextMenuRequested.connect(self.show_context_menu)
        self.analyze_button.clicked.connect(self.analyze_song)
        self.download_button.clicked.connect(self.download_song)
        
    def load_drummer_data(self):
        """Load drummer profiles data"""
        self.drummer_profiles = {
            "Neil Peart": {
                "band": "Rush",
                "signature_songs": ["Tom Sawyer", "Limelight", "Freewill"],
                "style": "Progressive Rock",
                "icon": "DRUM"
            },
            "John Bonham": {
                "band": "Led Zeppelin", 
                "signature_songs": ["Stairway to Heaven", "Whole Lotta Love", "Black Dog"],
                "style": "Hard Rock",
                "icon": ""
            },
            "Stewart Copeland": {
                "band": "The Police",
                "signature_songs": ["Roxanne", "Every Breath You Take", "Message in a Bottle"],
                "style": "New Wave/Rock",
                "icon": "AUDIO"
            },
            "Jeff Porcaro": {
                "band": "Toto",
                "signature_songs": ["Rosanna", "Africa", "Hold the Line"],
                "style": "Pop Rock/AOR",
                "icon": "SOUND"
            },
            "Keith Moon": {
                "band": "The Who",
                "signature_songs": ["Won't Get Fooled Again", "Baba O'Riley", "Behind Blue Eyes"],
                "style": "Hard Rock",
                "icon": ""
            },
            "Ginger Baker": {
                "band": "Cream",
                "signature_songs": ["White Room", "Sunshine of Your Love", "Badge"],
                "style": "Blues Rock",
                "icon": "DEBUG"
            }
        }
        
    def populate_list(self):
        """Populate the drummer list"""
        self.drummer_list.clear()
        
        for name, profile in self.drummer_profiles.items():
            icon = profile["icon"]
            band = profile["band"]
            primary_song = profile["signature_songs"][0]
            
            item_text = f"{icon} {name} ({band}) - {primary_song}"
            item = QListWidgetItem(item_text)
            
            # Store complete profile data
            item.setData(Qt.ItemDataRole.UserRole, profile)
            self.drummer_list.addItem(item)
            
        logger.info(f"Populated drummer list with {len(self.drummer_profiles)} drummers")
        
    def on_drummer_selected(self):
        """Handle drummer selection"""
        current_item = self.drummer_list.currentItem()
        if current_item:
            self.current_drummer = current_item.data(Qt.ItemDataRole.UserRole)
            self.analyze_button.setEnabled(True)
            self.download_button.setEnabled(True)
        else:
            self.current_drummer = None
            self.analyze_button.setEnabled(False)
            self.download_button.setEnabled(False)
            
    def show_context_menu(self, position):
        """Show context menu with signature songs"""
        item = self.drummer_list.itemAt(position)
        if not item:
            return
            
        profile = item.data(Qt.ItemDataRole.UserRole)
        if not profile:
            return
            
        menu = QMenu(self)
        signature_songs = profile.get("signature_songs", [])
        
        for song in signature_songs:
            song_menu = menu.addMenu(f"AUDIO {song}")
            
            analyze_action = song_menu.addAction(f"AUDIO Analyze {song}")
            download_action = song_menu.addAction(f" Download {song}")
            youtube_action = song_menu.addAction(f"INSPECTING Find on YouTube")
            
            # Connect with lambda to capture song
            analyze_action.triggered.connect(lambda checked, s=song: self.analyze_specific_song(s))
            download_action.triggered.connect(lambda checked, s=song: self.download_specific_song(s))
            youtube_action.triggered.connect(lambda checked, s=song: self.find_on_youtube(s))
            
        menu.exec(self.drummer_list.mapToGlobal(position))
        
    def analyze_song(self):
        """Analyze selected drummer's primary song"""
        if self.current_drummer:
            song = self.current_drummer["signature_songs"][0]
            self.analyze_specific_song(song)
            
    def download_song(self):
        """Download selected drummer's primary song"""
        if self.current_drummer:
            song = self.current_drummer["signature_songs"][0]
            self.download_specific_song(song)
            
    def analyze_specific_song(self, song):
        """Analyze a specific song"""
        if self.current_drummer:
            drummer_name = None
            for name, profile in self.drummer_profiles.items():
                if profile == self.current_drummer:
                    drummer_name = name
                    break
                    
            QMessageBox.information(self, "Analysis", 
                                  f"Starting analysis for {drummer_name} - {song}")
            logger.info(f"Analysis requested: {drummer_name} - {song}")
            
    def download_specific_song(self, song):
        """Download a specific song"""
        if self.current_drummer:
            drummer_name = None
            for name, profile in self.drummer_profiles.items():
                if profile == self.current_drummer:
                    drummer_name = name
                    break
                    
            QMessageBox.information(self, "Download", 
                                  f"Starting download for {drummer_name} - {song}")
            logger.info(f"Download requested: {drummer_name} - {song}")
            
    def find_on_youtube(self, song):
        """Find song on YouTube"""
        if self.current_drummer:
            drummer_name = None
            for name, profile in self.drummer_profiles.items():
                if profile == self.current_drummer:
                    drummer_name = name
                    break
                    
            QMessageBox.information(self, "YouTube Search", 
                                  f"Searching YouTube for {drummer_name} - {song}")
            logger.info(f"YouTube search requested: {drummer_name} - {song}")
