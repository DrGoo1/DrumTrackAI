"""
Event Bus System
===============
Provides a decoupled event-based communication mechanism between components.
Allows for loose coupling while maintaining component communication.
"""

import logging
import time
import uuid
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Callable, Any, Optional, Set

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Standard event types in the application"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    STATUS = "status"
    PROGRESS = "progress"
    DATA = "data"
    COMMAND = "command"
    RESPONSE = "response"


@dataclass
class Event:
    """An event in the system with metadata"""
    event_type: EventType
    source: str
    topic: str
    data: Any
    timestamp: float = None
    event_id: str = None

    def __post_init__(self):
        """Initialize timestamp and ID if not provided"""
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())


class EventBus(QObject):
    """
    Central event bus for application-wide communication.
    Using Qt signals for thread safety between UI and background threads.
    """

    # Qt signals for cross-thread event handling
    event_occurred = Signal(object)  # Emits Event objects

    def __init__(self):
        super().__init__()

        self._subscribers: Dict[str, List[Callable]] = {}
        self._topic_listeners: Dict[str, List[Callable]] = {}
        self._type_listeners: Dict[EventType, List[Callable]] = {}
        self._global_listeners: List[Callable] = []
        self._active_subscriptions: Set[str] = set()

        # Connect the internal signal to our dispatcher
        self.event_occurred.connect(self._dispatch_event)

        logger.info("Event bus initialized")

    def subscribe(self, callback: Callable, topic: str = None,
                  event_type: EventType = None, source: str = None) -> str:
        """
        Subscribe to events with optional filtering by topic, type, and source.
        Returns a subscription ID for later unsubscribe.
        """
        subscription_id = str(uuid.uuid4())

        if topic is not None:
            if topic not in self._topic_listeners:
                self._topic_listeners[topic] = []
            self._topic_listeners[topic].append((subscription_id, callback, source, event_type))
        elif event_type is not None:
            if event_type not in self._type_listeners:
                self._type_listeners[event_type] = []
            self._type_listeners[event_type].append((subscription_id, callback, source))
        else:
            # Global listener gets all events
            self._global_listeners.append((subscription_id, callback, source))

        self._active_subscriptions.add(subscription_id)
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe using the subscription ID returned from subscribe"""

        if subscription_id not in self._active_subscriptions:
            return False

        # Remove from topic listeners
        for topic, listeners in self._topic_listeners.items():
            self._topic_listeners[topic] = [l for l in listeners if l[0] != subscription_id]

        # Remove from type listeners
        for event_type, listeners in self._type_listeners.items():
            self._type_listeners[event_type] = [l for l in listeners if l[0] != subscription_id]

        # Remove from global listeners
        self._global_listeners = [l for l in self._global_listeners if l[0] != subscription_id]

        # Remove from active subscriptions
        self._active_subscriptions.remove(subscription_id)

        return True

    def emit(self, event: Event):
        """Emit an event to the bus"""
        # Use Qt signal to ensure thread safety
        self.event_occurred.emit(event)

    def _dispatch_event(self, event: Event):
        """Internal dispatcher for events (connected to Qt signal)"""

        try:
            # First call topic listeners for exact match
            if event.topic in self._topic_listeners:
                for subscription_id, callback, source_filter, type_filter in self._topic_listeners[event.topic]:
                    if self._should_deliver(event, source_filter, type_filter):
                        try:
                            callback(event)
                        except Exception as e:
                            logger.error(f"Error in event handler: {e}")

            # Then call event type listeners
            if event.event_type in self._type_listeners:
                for subscription_id, callback, source_filter in self._type_listeners[event.event_type]:
                    if source_filter is None or source_filter == event.source:
                        try:
                            callback(event)
                        except Exception as e:
                            logger.error(f"Error in event handler: {e}")

            # Finally call global listeners
            for subscription_id, callback, source_filter in self._global_listeners:
                if source_filter is None or source_filter == event.source:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")

        except Exception as e:
            logger.error(f"Error dispatching event: {e}")

    def _should_deliver(self, event: Event, source_filter: Optional[str],
                        type_filter: Optional[EventType]) -> bool:
        """Check if an event should be delivered based on source and type filters"""
        source_match = source_filter is None or source_filter == event.source
        type_match = type_filter is None or type_filter == event.event_type
        return source_match and type_match

    # Convenience methods for common event types
    def emit_info(self, source: str, topic: str, message: str):
        """Emit an info event"""
        self.emit(Event(
            event_type=EventType.INFO,
            source=source,
            topic=topic,
            data=message
        ))

    def emit_warning(self, source: str, topic: str, message: str):
        """Emit a warning event"""
        self.emit(Event(
            event_type=EventType.WARNING,
            source=source,
            topic=topic,
            data=message
        ))

    def emit_error(self, source: str, message: str):
        """Emit an error event"""
        self.emit(Event(
            event_type=EventType.ERROR,
            source=source,
            topic="error",
            data=message
        ))
        logger.error(f"Error from {source}: {message}")

    def emit_status(self, source: str, status: str):
        """Emit a status update event"""
        self.emit(Event(
            event_type=EventType.STATUS,
            source=source,
            topic="status",
            data=status
        ))

    def emit_progress(self, source: str, topic: str, percentage: float, message: str = None):
        """Emit a progress update event"""
        self.emit(Event(
            event_type=EventType.PROGRESS,
            source=source,
            topic=topic,
            data={
                "percentage": percentage,
                "message": message
            }
        ))

    def emit_command(self, source: str, command: str, params: Dict = None):
        """Emit a command event"""
        self.emit(Event(
            event_type=EventType.COMMAND,
            source=source,
            topic=command,
            data=params or {}
        ))

    def emit_response(self, source: str, command: str, result: Any):
        """Emit a command response event"""
        self.emit(Event(
            event_type=EventType.RESPONSE,
            source=source,
            topic=command,
            data=result
        ))
