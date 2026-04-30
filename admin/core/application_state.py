"""
Application State Manager
========================
Manages the application lifecycle states, transitions, and initialization flow.
Controls the startup, loading, and shutdown processes with proper error handling.
"""
import logging
import os
import sys
import time
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPixmap
from PySide6.QtWidgets import QSplashScreen, QApplication, QMessageBox

from .event_bus import EventBus, Event, EventType
from .service_container import ServiceContainer, ServiceTier, ServiceNotFoundError

logger = logging.getLogger(__name__)


class AppState(Enum):
    """Application states during lifecycle"""
    NOT_STARTED = auto()
    STARTING = auto()
    LOADING_CRITICAL = auto()
    LOADING_IMPORTANT = auto()
    LOADING_OPTIONAL = auto()
    RUNNING = auto()
    SHUTTING_DOWN = auto()
    ERROR = auto()
    TERMINATED = auto()


class ApplicationStateManager(QObject):
    """
    Manages the application lifecycle and state transitions.
    Controls initialization flow, service loading, and error handling.
    """

    # Qt signals for UI updates
    state_changed = Signal(object, str)  # (AppState, message)
    progress_updated = Signal(int, str)  # (percentage, message)
    initialization_complete = Signal()
    initialization_failed = Signal(str)  # Error message

    def __init__(self):
        super().__init__()
        self._state = AppState.NOT_STARTED
        self._container: Optional[ServiceContainer] = None
        self._event_bus: Optional[EventBus] = None
        self._splash_screen: Optional[QSplashScreen] = None
        self._main_window = None
        self._error_message: Optional[str] = None
        self._startup_time = 0
        self._service_results: Dict[str, bool] = {}
        self._initialization_steps = [
            (AppState.LOADING_CRITICAL, "Loading critical services", ServiceTier.CRITICAL, 30),
            (AppState.LOADING_IMPORTANT, "Loading important services", ServiceTier.IMPORTANT, 60),
            (AppState.LOADING_OPTIONAL, "Loading optional services", ServiceTier.OPTIONAL, 90),
        ]

    @property
    def container(self) -> Optional[ServiceContainer]:
        return self._container

    @property
    def event_bus(self) -> Optional[EventBus]:
        return self._event_bus

    @event_bus.setter
    def event_bus(self, value: EventBus):
        self._event_bus = value

    @property
    def current_state(self) -> AppState:
        return self._state

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    def _set_state(self, state: AppState, message: str = ""):
        """Change application state and emit signals"""
        prev_state = self._state
        self._state = state
        logger.info(f"Application state changed: {prev_state.name} -> {state.name} {message}")
        self.state_changed.emit(state, message)

    def _log_state_change(self, state: AppState, message: str):
        """Callback for state change signals to update splash screen"""
        if self._splash_screen and state != AppState.RUNNING:
            self._splash_screen.showMessage(
                f"{message}...",
                alignment=Qt.AlignBottom | Qt.AlignHCenter
            )

    def _show_splash_screen(self):
        """Display the splash screen with logo"""
        try:
            # Look for splash image in resources
            splash_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "resources", "splash.png"
            )

            # Use a default or bundled splash if available
            if os.path.exists(splash_path):
                pixmap = QPixmap(splash_path)
            else:
                # Create a basic splash if image not found
                img = QImage(600, 400, QImage.Format_ARGB32)
                painter = QPainter(img)
                painter.fillRect(0, 0, 600, 400, QColor(40, 0, 60))  # Dark purple background
                font = QFont()
                font.setPointSize(24)
                painter.setFont(font)
                painter.setPen(QColor(255, 215, 0))  # Gold text
                painter.drawText(img.rect(), Qt.AlignCenter, "DrumTracKAI Admin\nv1.1.7")
                painter.end()
                pixmap = QPixmap.fromImage(img)

            self._splash_screen = QSplashScreen(pixmap)
            self._splash_screen.show()
            
            # Show initial message
            try:
                self._splash_screen.showMessage("Starting application...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            except Exception as e:
                logger.warning(f"Could not show initial splash message: {e}")
                
            self.progress_updated.connect(
                lambda p, m: self._splash_screen.showMessage(
                    f"{m} ({p}%)...",
                    alignment=Qt.AlignBottom | Qt.AlignHCenter
                ) if self._splash_screen else None
            )
            QApplication.processEvents()
            
        except Exception as e:
            logger.error(f"Failed to show splash screen: {e}")
            self._splash_screen = None

    def start_application(self, show_splash: bool = True) -> bool:
        """Start the application initialization process"""
        try:
            logger.info("Starting DrumTracKAI Admin application")
            self._startup_time = time.time()
            self._set_state(AppState.STARTING, "Starting application")

            if show_splash:
                self._show_splash_screen()

            # Emit initial progress
            self.progress_updated.emit(10, "Initializing core components")

            # Create core components
            self._container = ServiceContainer()
            self._event_bus = EventBus()

            # Connect state logging
            self.state_changed.connect(self._log_state_change)

            # Initialize critical services (20%)
            self.progress_updated.emit(20, "Loading critical services")
            return True

        except Exception as e:
            self._handle_startup_error(f"Failed to start application: {e}")
            return False

    def initialize_services(self) -> bool:
        """Initialize all services in the service container"""
        try:
            if not self._container:
                raise RuntimeError("Service container not initialized")

            # Process each initialization step
            for state, message, tier, progress in self._initialization_steps:
                self._set_state(state, message)
                self.progress_updated.emit(progress - 10, message)

                # Initialize services of the current tier
                results = self._container.initialize_tier(tier)
                self._service_results.update(results)

                # Check if critical services failed
                if tier == ServiceTier.CRITICAL and not all(results.values()):
                    failed_services = [s for s, success in results.items() if not success]
                    error_msg = f"Critical services failed to initialize: {', '.join(failed_services)}"
                    self._handle_startup_error(error_msg)
                    return False

                # Wait a moment for UI updates
                QApplication.processEvents()

            # All services initialized
            elapsed = time.time() - self._startup_time
            logger.info(f"Application initialization completed in {elapsed:.2f} seconds")
            self.progress_updated.emit(100, "Application ready")

            # Return success based on critical services
            return True

        except Exception as e:
            self._handle_startup_error(f"Service initialization failed: {e}")
            return False

    def complete_initialization(self, main_window: Any) -> bool:
        """Complete the initialization process and transition to running state"""
        try:
            if not self._container or not self._event_bus:
                raise RuntimeError("Core components not initialized")

            self._main_window = main_window
            self.progress_updated.emit(100, "Application ready")

            # Allow a moment to see "100% ready" message
            QTimer.singleShot(500, self._finalize_startup)

            return True
        except Exception as e:
            self._handle_startup_error(f"Failed to complete initialization: {e}")
            return False

    def _finalize_startup(self):
        """Finalize the startup process after a brief delay"""
        try:
            # Hide splash screen if exists
            if self._splash_screen:
                self._splash_screen.finish(self._main_window)
                self._splash_screen = None

            # Show main window if exists
            if self._main_window:
                self._main_window.show()

            # Set running state
            self._set_state(AppState.RUNNING, "Application running")

            # Emit initialization complete signal
            self.initialization_complete.emit()

            # Log successful startup
            elapsed = time.time() - self._startup_time
            logger.info(f"Application started successfully in {elapsed:.2f}s")

            # Notify via event bus
            if self._event_bus:
                self._event_bus.emit_status("application", "Application started successfully")

        except Exception as e:
            self._handle_startup_error(f"Failed to finalize startup: {e}")

    def _handle_startup_error(self, error_msg: str):
        """Handle errors during startup process"""
        logger.error(error_msg)
        self._error_message = error_msg
        self._set_state(AppState.ERROR, error_msg)

        # Hide splash screen if it exists
        if self._splash_screen:
            self._splash_screen.hide()
            self._splash_screen = None

        # Emit error signal
        self.initialization_failed.emit(error_msg)

        # Show error message if no UI yet
        if not self._main_window or not self._main_window.isVisible():
            QMessageBox.critical(None, "Startup Error", error_msg)

    def initiate_shutdown(self):
        """Start the application shutdown process"""
        logger.info("Initiating application shutdown")
        self._set_state(AppState.SHUTTING_DOWN, "Shutting down")

        # Notify via event bus
        if self._event_bus:
            self._event_bus.emit_status("application", "Shutting down")

        # Shut down services through container
        if self._container:
            try:
                self._container.shutdown_all()
            except Exception as e:
                logger.error(f"Error during service shutdown: {e}")

        # Final state
        self._set_state(AppState.TERMINATED, "Application terminated")

        # Let the main application handle the actual quit
        return True

    def get_service(self, service_name: str) -> Any:
        """
        Get a service instance from the container
        Convenience method to avoid direct container access
        """
        if not self._container:
            raise RuntimeError("Service container not initialized")

        try:
            return self._container.get(service_name)
        except ServiceNotFoundError:
            logger.warning(f"Attempted to access non-existent service: {service_name}")
            return None

    def register_service(self, service_name: str, factory: Callable,
                        dependencies: List[str] = None,
                        tier: ServiceTier = ServiceTier.OPTIONAL,
                        singleton: bool = True) -> bool:
        """
        Register a service in the container
        Convenience method to avoid direct container access
        """
        if not self._container:
            raise RuntimeError("Service container not initialized")

        try:
            self._container.register(
                service_name=service_name,
                factory=factory,
                dependencies=dependencies,
                tier=tier,
                singleton=singleton
            )
            return True
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
            return False
