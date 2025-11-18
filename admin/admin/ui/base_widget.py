"""
Base Widget for DrumTracKAI Admin
=================================
Provides common functionality for all widgets in the application.
"""

import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal, Qt

logger = logging.getLogger(__name__)

class BaseWidget(QWidget):
    """Base widget class with common functionality for all app widgets"""
    
    status_updated = Signal(str)
    
    def __init__(self, parent=None, name="BaseWidget", event_bus=None):
        """Initialize base widget
        
        Args:
            parent: Parent widget
            name: Name of the widget for logging
            event_bus: Application event bus for communication
        """
        super().__init__(parent)
        self.widget_name = name
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"ui.{name.lower().replace(' ', '_')}")
        self.logger.info(f"Initializing {name}")
        
        # Common attributes
        self.main_layout = QVBoxLayout(self)
        self.status_label = None
    
    def setup_status_label(self):
        """Set up a status label at the bottom of the widget"""
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        self.main_layout.addWidget(self.status_label)
        
    def set_status(self, message):
        """Set status message in the status label if it exists"""
        if self.status_label:
            self.status_label.setText(message)
        self.logger.info(message)
        self.status_updated.emit(message)
    
    def on_event(self, event):
        """Handle events from the event bus"""
        # Base implementation does nothing, override in subclasses
        pass
