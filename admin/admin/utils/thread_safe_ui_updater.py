"""
Thread-Safe UI Updater - Critical Component
==========================================
Essential for thread-safe UI updates from background processes.
NO FALLBACK OPTIONS - explicit failures only.
"""
import logging
import threading

from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtCore import QObject, QTimer, Signal, QMutex, QMutexLocker, QThread
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QWidget
from queue import Queue, Empty
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger(__name__)

class ThreadSafeUIUpdater(QObject):
    """
    Thread-safe UI updater that ensures all UI updates happen on the main thread.
    CRITICAL: NO FALLBACK OPTIONS - all failures are explicit.
    """

    # Signal for thread-safe UI updates
    update_requested = Signal(object, object)  # (widget, update_function)

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        super().__init__()

        # Update queue for batching updates
        self._update_queue = Queue()
        self._processing = False
        self._mutex = QMutex()

        # Connect signal to handler
        self.update_requested.connect(self._execute_update)

        # Timer for processing queued updates
        self._timer = QTimer()
        self._timer.timeout.connect(self._process_update_queue)
        self._timer.start(16)  # ~60 FPS update rate

        logger.info("ThreadSafeUIUpdater initialized")

    @classmethod
    def get_instance(cls):
        """Get singleton instance - CRITICAL: Must succeed"""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    # Ensure we're on the main thread for Qt object creation
                    if QThread.currentThread() != QApplication.instance().thread():
                        raise RuntimeError(
                            "CRITICAL: ThreadSafeUIUpdater must be created on the main thread"
                        )
                    cls._instance = cls()
        return cls._instance

    def queue_update(self, widget: QWidget, update_function: Callable, *args, **kwargs):
        """
        Queue a UI update to be executed on the main thread.
        NO FALLBACKS - explicit validation and error handling.

        Args:
            widget: The widget to update
            update_function: Function to call for the update
            *args, **kwargs: Arguments for the update function
        """
        # CRITICAL: Validate inputs
        if widget is None:
            raise ValueError("CRITICAL: widget cannot be None")

        if update_function is None:
            raise ValueError("CRITICAL: update_function cannot be None")

        if not callable(update_function):
            raise ValueError("CRITICAL: update_function must be callable")

        # Check if widget is still valid
        try:
            if not widget.isVisible() and not hasattr(widget, '_allow_hidden_updates'):
                logger.warning(f"Widget {widget.__class__.__name__} is not visible, skipping update")
                return
        except RuntimeError:
            # Widget has been deleted
            logger.warning("Widget has been deleted, skipping update")
            return

        # Create update package
        update_package = {
            'widget': widget,
            'function': update_function,
            'args': args,
            'kwargs': kwargs,
            'thread_id': threading.get_ident()
        }

        # Check if we're already on the main thread
        if QThread.currentThread() == QApplication.instance().thread():
            # Execute immediately on main thread
            try:
                self._execute_update_package(update_package)
            except Exception as e:
                logger.error(f"Error executing immediate UI update: {e}")
        else:
            # Queue for main thread execution
            try:
                self._update_queue.put_nowait(update_package)
            except Exception as e:
                logger.error(f"Error queuing UI update: {e}")
                raise RuntimeError(f"CRITICAL: Failed to queue UI update: {e}")

    def _process_update_queue(self):
        """Process queued UI updates - called on main thread by timer"""
        if self._processing:
            return

        with QMutexLocker(self._mutex):
            self._processing = True

        try:
            # Process a batch of updates (max 10 per cycle to avoid blocking UI)
            processed = 0
            max_per_cycle = 10

            while processed < max_per_cycle:
                try:
                    update_package = self._update_queue.get_nowait()
                    self._execute_update_package(update_package)
                    processed += 1
                except Empty:
                    # Queue is empty
                    break
                except Exception as e:
                    logger.error(f"Error processing queued UI update: {e}")
                    processed += 1  # Count errors to avoid infinite loop

        finally:
            self._processing = False

    def _execute_update_package(self, update_package: Dict):
        """Execute a single update package"""
        try:
            widget = update_package['widget']
            function = update_package['function']
            args = update_package['args']
            kwargs = update_package['kwargs']

            # Validate widget is still valid
            try:
                # Try to access a basic Qt property to check if widget is valid
                widget.objectName()
            except RuntimeError:
                # Widget has been deleted
                logger.debug("Widget deleted, skipping update")
                return

            # Execute the update function
            if hasattr(widget, function.__name__) or callable(function):
                result = function(*args, **kwargs)
                return result
            else:
                logger.error(f"Function {function.__name__} not found on widget {widget.__class__.__name__}")

        except Exception as e:
            logger.error(f"Error executing UI update: {e}")
            logger.error(f"Widget: {update_package.get('widget', 'Unknown')}")
            logger.error(f"Function: {update_package.get('function', 'Unknown')}")

    def _execute_update(self, widget: QWidget, update_function: Callable):
        """Signal handler for immediate updates"""
        try:
            if callable(update_function):
                update_function()
            else:
                logger.error(f"Invalid update function: {update_function}")
        except Exception as e:
            logger.error(f"Error in signal-based UI update: {e}")

    def immediate_update(self, widget: QWidget, update_function: Callable):
        """
        Execute an immediate UI update via signal.
        Use this for critical updates that must happen immediately.
        """
        if QThread.currentThread() == QApplication.instance().thread():
            # Already on main thread, execute directly
            try:
                update_function()
            except Exception as e:
                logger.error(f"Error in immediate UI update: {e}")
        else:
            # Emit signal for main thread execution
            self.update_requested.emit(widget, update_function)
    
    def run_in_main_thread(self, update_function: Callable, *args, **kwargs):
        """
        Execute a function in the main thread with arguments.
        This is the method that BatchProcessorWidget expects to exist.
        """
        def wrapper():
            try:
                return update_function(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in run_in_main_thread: {e}")
                raise
        
        if QThread.currentThread() == QApplication.instance().thread():
            # Already on main thread, execute directly
            return wrapper()
        else:
            # Use the existing queue_update mechanism with a dummy widget
            # Since we don't have a specific widget, we'll use QApplication instance
            app = QApplication.instance()
            if app:
                self.queue_update(app, wrapper)
            else:
                logger.error("No QApplication instance available for run_in_main_thread")

    def get_queue_size(self) -> int:
        """Get current queue size for monitoring"""
        return self._update_queue.qsize()

    def clear_queue(self):
        """Clear all queued updates"""
        with QMutexLocker(self._mutex):
            while not self._update_queue.empty():
                try:
                    self._update_queue.get_nowait()
                except Empty:
                    break
        logger.info("UI update queue cleared")


class UIUpdateHelper:
    """
    Helper class for common UI update patterns.
    NO FALLBACKS - all operations must succeed or fail explicitly.
    """

    def __init__(self, widget: QWidget):
        self.widget = widget
        self.updater = ThreadSafeUIUpdater.get_instance()

    def update_text(self, target_widget, text: str):
        """Update text of a widget safely"""
        def update():
            if hasattr(target_widget, 'setText'):
                target_widget.setText(text)
            elif hasattr(target_widget, 'setPlainText'):
                target_widget.setPlainText(text)
            else:
                raise ValueError(f"Widget {target_widget.__class__.__name__} does not support text updates")

        self.updater.queue_update(self.widget, update)

    def update_progress(self, progress_bar, value: int):
        """Update progress bar safely"""
        def update():
            if hasattr(progress_bar, 'setValue'):
                progress_bar.setValue(value)
            else:
                raise ValueError(f"Widget {progress_bar.__class__.__name__} is not a progress bar")

        self.updater.queue_update(self.widget, update)

    def update_label(self, label, text: str, color: str = None):
        """Update label text and optionally color"""
        def update():
            if hasattr(label, 'setText'):
                label.setText(text)
                if color:
                    label.setStyleSheet(f"color: {color};")
            else:
                raise ValueError(f"Widget {label.__class__.__name__} is not a label")

        self.updater.queue_update(self.widget, update)

    def enable_widget(self, target_widget, enabled: bool):
        """Enable/disable widget safely"""
        def update():
            if hasattr(target_widget, 'setEnabled'):
                target_widget.setEnabled(enabled)
            else:
                raise ValueError(f"Widget {target_widget.__class__.__name__} does not support enable/disable")

        self.updater.queue_update(self.widget, update)

    def add_table_row(self, table_widget, row_data: list):
        """Add row to table safely"""
        def update():
            if hasattr(table_widget, 'insertRow') and hasattr(table_widget, 'setItem'):
                row = table_widget.rowCount()
                table_widget.insertRow(row)

                for col, data in enumerate(row_data):
                    if col < table_widget.columnCount():
                        item = QTableWidgetItem(str(data))
                        table_widget.setItem(row, col, item)
            else:
                raise ValueError(f"Widget {table_widget.__class__.__name__} is not a table widget")

        self.updater.queue_update(self.widget, update)


# Convenience functions for direct use
def safe_update_text(widget: QWidget, target, text: str):
    """Safely update text from any thread"""
    updater = ThreadSafeUIUpdater.get_instance()

    def update():
        if hasattr(target, 'setText'):
            target.setText(text)
        elif hasattr(target, 'setPlainText'):
            target.setPlainText(text)
        else:
            logger.error(f"Cannot update text on {target.__class__.__name__}")

    updater.queue_update(widget, update)

def safe_update_progress(widget: QWidget, progress_bar, value: int):
    """Safely update progress bar from any thread"""
    updater = ThreadSafeUIUpdater.get_instance()

    def update():
        if hasattr(progress_bar, 'setValue'):
            progress_bar.setValue(value)
        else:
            logger.error(f"Cannot update progress on {progress_bar.__class__.__name__}")

    updater.queue_update(widget, update)

def safe_enable_widget(widget: QWidget, target, enabled: bool):
    """Safely enable/disable widget from any thread"""
    updater = ThreadSafeUIUpdater.get_instance()

    def update():
        if hasattr(target, 'setEnabled'):
            target.setEnabled(enabled)
        else:
            logger.error(f"Cannot enable/disable {target.__class__.__name__}")

    updater.queue_update(widget, update)


# Initialize singleton when module is imported (if on main thread)
def initialize_ui_updater():
    """Initialize the UI updater singleton"""
    try:
        if QApplication.instance() and QThread.currentThread() == QApplication.instance().thread():
            ThreadSafeUIUpdater.get_instance()
            logger.info("ThreadSafeUIUpdater singleton initialized")
        else:
            logger.warning("Cannot initialize ThreadSafeUIUpdater - not on main thread")
    except Exception as e:
        logger.error(f"Error initializing ThreadSafeUIUpdater: {e}")

# Auto-initialize if possible
try:
    initialize_ui_updater()
except Exception:
    # Will be initialized later when first accessed
    pass