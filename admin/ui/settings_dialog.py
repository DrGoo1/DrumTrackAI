"""
Settings Dialog
==============
Dialog for managing application settings such as API keys
"""
import os
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QWidget, QFormLayout, QMessageBox, QCheckBox, QGroupBox
)

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Dialog for configuring application settings including API keys."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DrumTracKAI Settings")
        self.resize(600, 350)
        
        # Initialize variables
        self.api_key_changed = False
        self.settings_changed = False
        
        # Current environment values
        self.current_mvsep_api_key = os.environ.get("MVSEP_API_KEY", "")
        
        # Create UI elements
        self._setup_ui()
        
        logger.debug("Settings dialog initialized")
        
    def _setup_ui(self):
        """Setup the user interface."""
        main_layout = QVBoxLayout(self)
        
        # Create tabs
        tab_widget = QTabWidget()
        api_keys_tab = QWidget()
        settings_tab = QWidget()
        
        tab_widget.addTab(api_keys_tab, "API Keys")
        tab_widget.addTab(settings_tab, "General Settings")
        
        # Setup API keys tab
        self._setup_api_keys_tab(api_keys_tab)
        
        # Setup settings tab
        self._setup_settings_tab(settings_tab)
        
        # Add tabs to main layout
        main_layout.addWidget(tab_widget)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._on_save)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def _setup_api_keys_tab(self, tab_widget):
        """Setup the API Keys tab."""
        layout = QVBoxLayout(tab_widget)
        
        # MVSep API Key section
        mvsep_group = QGroupBox("MVSep API")
        mvsep_layout = QFormLayout()
        
        self.mvsep_key_input = QLineEdit()
        self.mvsep_key_input.setText(self.current_mvsep_api_key)
        self.mvsep_key_input.setEchoMode(QLineEdit.Password)
        self.mvsep_key_input.textChanged.connect(self._on_mvsep_key_changed)
        
        self.show_mvsep_key = QCheckBox("Show key")
        self.show_mvsep_key.stateChanged.connect(self._on_show_mvsep_key_changed)
        
        key_layout = QHBoxLayout()
        key_layout.addWidget(self.mvsep_key_input)
        key_layout.addWidget(self.show_mvsep_key)
        
        mvsep_layout.addRow("MVSep API Key:", key_layout)
        
        # Add help text
        help_label = QLabel(
            "API key is required for MVSep stem separation. Sign up at https://mvsep.com to get your API key."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666; font-size: 10pt;")
        mvsep_layout.addRow("", help_label)
        
        # Add status indicator
        key_status_layout = QHBoxLayout()
        self.key_status_icon = QLabel("")
        
        if self.current_mvsep_api_key:
            self.key_status_icon.setStyleSheet("color: green;")
            status_text = "API key is configured"
        else:
            self.key_status_icon.setStyleSheet("color: red;")
            status_text = "API key is not configured - MVSep processing will not work"
        
        self.key_status_text = QLabel(status_text)
        key_status_layout.addWidget(self.key_status_icon)
        key_status_layout.addWidget(self.key_status_text)
        key_status_layout.addStretch()
        
        mvsep_layout.addRow("Status:", key_status_layout)
        
        mvsep_group.setLayout(mvsep_layout)
        layout.addWidget(mvsep_group)
        
        # Additional API sections could be added here in the future
        
        layout.addStretch()
        
    def _setup_settings_tab(self, tab_widget):
        """Setup the General Settings tab."""
        layout = QVBoxLayout(tab_widget)
        
        # Processing Settings
        processing_group = QGroupBox("MVSep Processing")
        processing_layout = QFormLayout()
        
        self.keep_original_mix = QCheckBox("Keep original mix stems")
        self.keep_original_mix.setChecked(True)
        self.keep_original_mix.stateChanged.connect(self._on_setting_changed)
        
        self.keep_drum_stem = QCheckBox("Keep drum stem")
        self.keep_drum_stem.setChecked(True)
        self.keep_drum_stem.stateChanged.connect(self._on_setting_changed)
        
        self.auto_route_stems = QCheckBox("Automatically route extracted stems for analysis")
        self.auto_route_stems.setChecked(True)
        self.auto_route_stems.stateChanged.connect(self._on_setting_changed)
        
        processing_layout.addRow("", self.keep_original_mix)
        processing_layout.addRow("", self.keep_drum_stem)
        processing_layout.addRow("", self.auto_route_stems)
        
        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)
        
        # Add more settings groups here as needed
        
        layout.addStretch()
        
    def _on_mvsep_key_changed(self):
        """Handle MVSep API key changes."""
        self.api_key_changed = True
        new_key = self.mvsep_key_input.text().strip()
        
        if new_key:
            self.key_status_icon.setStyleSheet("color: green;")
            self.key_status_text.setText("API key is ready to be saved")
        else:
            self.key_status_icon.setStyleSheet("color: red;")
            self.key_status_text.setText("API key is empty - MVSep processing will not work")
    
    def _on_show_mvsep_key_changed(self, state):
        """Toggle showing or hiding the MVSep API key."""
        if state == Qt.Checked:
            self.mvsep_key_input.setEchoMode(QLineEdit.Normal)
        else:
            self.mvsep_key_input.setEchoMode(QLineEdit.Password)
    
    def _on_setting_changed(self):
        """Handle settings changes."""
        self.settings_changed = True
    
    def _on_save(self):
        """Save settings."""
        try:
            # Check if any changes were made
            if not self.api_key_changed and not self.settings_changed:
                self.accept()
                return
            
            # Handle API key changes
            if self.api_key_changed:
                new_key = self.mvsep_key_input.text().strip()
                
                # Update environment variable - affects current session
                if new_key:
                    os.environ["MVSEP_API_KEY"] = new_key
                    logger.info("MVSep API key updated")
                else:
                    if "MVSEP_API_KEY" in os.environ:
                        del os.environ["MVSEP_API_KEY"]
                        logger.info("MVSep API key removed")
                
                # Store settings in memory - to be used across the app
                # In a real implementation, this would save to a config file
                self.current_mvsep_api_key = new_key
            
            # Handle other settings (would save to config in real implementation)
            
            # Show success message
            QMessageBox.information(self, "Settings Saved", "Settings have been updated successfully.")
            
            # Accept the dialog (close with success)
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
