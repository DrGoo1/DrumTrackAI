"""
Thread-Safe UI Updater
=====================
Utility class for safely updating UI components from background threads
without causing Qt recursive repainting issues.
"""

import logging
import time
from typing import Dict, Any, Callable, Optional
from queue import Queue

from PySide6.QtCore import QObject, QTimer, Signal, Slot, Qt

logger = logging.getLogger(__name__)

class ThreadSafeUIUpdater(QObject):
    """
    Thread-safe UI component updater that uses signals/slots to ensure
    UI updates happen in the main thread to prevent recursive repainting errors.
    
    Usage:
        updater = ThreadSafeUIUpdater()
        updater.register_handler('progress', update_progress_func)
        updater.update('progress', 50)  # can be called from any thread
    """
    
    # Signal for updating UI components
    update_signal = Signal(str, object)
    
    def __init__(self):
        super().__init__()
        self._handlers: Dict[str, Callable] = {}
        self._pending_updates: Queue = Queue()
        self._timer = QTimer()
        self._timer.timeout.connect(self._process_pending_updates)
        self._timer.start(50)  # Process updates every 50ms
        
        # Connect the signal to the slot
        self.update_signal.connect(self._handle_update, Qt.QueuedConnection)
        
    def register_handler(self, component_id: str, handler: Callable):
        """
        Register a handler function for a specific component.
        
        Args:
            component_id: Identifier for the component
            handler: Function that will be called to update the component
        """
        self._handlers[component_id] = handler
        
    def update(self, component_id: str, value: Any):
        """
        Update a UI component safely from any thread.
        
        Args:
            component_id: Identifier for the component to update
            value: Value to update the component with
        """
        # Emit the signal which will be queued to the main thread
        self.update_signal.emit(component_id, value)
        
    def defer_update(self, component_id: str, value: Any):
        """
        Defer an update to be processed in batches.
        
        Args:
            component_id: Identifier for the component to update
            value: Value to update the component with
        """
        self._pending_updates.put((component_id, value))
        
    @Slot(str, object)
    def _handle_update(self, component_id: str, value: Any):
        """
        Handle an update from the signal in the main thread.
        
        Args:
            component_id: Identifier for the component
            value: Update value
        """
        if component_id in self._handlers:
            try:
                self._handlers[component_id](value)
            except Exception as e:
                logger.error(f"Error updating component {component_id}: {str(e)}")
        else:
            logger.warning(f"No handler registered for component {component_id}")
            
    def _process_pending_updates(self):
        """Process any pending updates in the queue"""
        # Process a limited number of updates per cycle to keep UI responsive
        max_updates_per_cycle = 10
        processed = 0
        
        while not self._pending_updates.empty() and processed < max_updates_per_cycle:
            component_id, value = self._pending_updates.get()
            self.update(component_id, value)
            processed += 1
            
    def clear_pending_updates(self):
        """Clear all pending updates"""
        while not self._pending_updates.empty():
            self._pending_updates.get()
            
    def has_handler(self, component_id: str) -> bool:
        """
        Check if a handler is registered for a component.
        
        Args:
            component_id: Identifier for the component
            
        Returns:
            bool: True if a handler is registered
        """
        return component_id in self._handlers
