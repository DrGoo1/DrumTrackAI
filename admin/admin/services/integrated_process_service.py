#!/usr/bin/env python3
"""
Integrated Process Service for DrumTracKAI Admin App
==================================================

Connects admin app widgets to the integrated process management system.
Provides real-time synchronization between UI and actual processes.
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication

# Import the integrated systems (with path adjustment)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from robust_checkpoint_system import get_checkpoint_system, ProcessType, ProcessState
    from process_state_bridge import get_process_bridge
    from integrated_process_manager import get_integrated_manager
except ImportError as e:
    print(f"Warning: Could not import integrated systems: {e}")
    # Create mock objects for development
    class MockCheckpointSystem:
        def get_all_processes(self): return {}
        def start_process(self, *args, **kwargs): return None
        def update_progress(self, *args, **kwargs): pass
        def complete_process(self, *args, **kwargs): pass
    
    class MockProcessBridge:
        def register_admin_widget(self, *args, **kwargs): pass
        def start_websocket_server(self, *args, **kwargs): pass
        def get_api_status(self): return {}
    
    class MockIntegratedManager:
        def get_system_status(self): return {}
        def start_all_systems(self): pass
    
    def get_checkpoint_system(): return MockCheckpointSystem()
    def get_process_bridge(): return MockProcessBridge()
    def get_integrated_manager(): return MockIntegratedManager()

class IntegratedProcessService(QObject):
    """Service to integrate admin app with process management systems"""
    
    # Signals for UI updates
    process_started = Signal(str, dict)  # process_id, process_data
    process_updated = Signal(str, dict)  # process_id, process_data
    process_completed = Signal(str, bool)  # process_id, success
    system_status_changed = Signal(dict)  # system_status
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize integrated systems
        self.checkpoint_system = get_checkpoint_system()
        self.process_bridge = get_process_bridge()
        self.integrated_manager = get_integrated_manager()
        
        # Widget registry
        self.registered_widgets: Dict[str, Any] = {}
        
        # Update timer for periodic sync
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_all_widgets)
        self.sync_timer.start(2000)  # Update every 2 seconds
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Integrated Process Service initialized")
    
    def initialize_systems(self):
        """Initialize all integrated systems"""
        
        try:
            # Start integrated systems if not already running
            self.integrated_manager.start_all_systems()
            
            # Register this service with the process bridge
            self.process_bridge.register_admin_widget("integrated_service", self)
            
            self.logger.info("Integrated systems initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize integrated systems: {e}")
            return False
    
    def register_widget(self, widget_id: str, widget_instance: Any):
        """Register an admin widget for real-time updates"""
        
        self.registered_widgets[widget_id] = widget_instance
        
        # Register with process bridge
        self.process_bridge.register_admin_widget(widget_id, widget_instance)
        
        # Immediately sync the widget
        self.sync_widget(widget_id)
        
        self.logger.info(f"Registered widget: {widget_id}")
    
    def unregister_widget(self, widget_id: str):
        """Unregister a widget"""
        
        if widget_id in self.registered_widgets:
            del self.registered_widgets[widget_id]
            self.logger.info(f"Unregistered widget: {widget_id}")
    
    def sync_widget(self, widget_id: str):
        """Synchronize a specific widget with current process state"""
        
        if widget_id not in self.registered_widgets:
            return
        
        widget = self.registered_widgets[widget_id]
        all_processes = self.checkpoint_system.get_all_processes()
        
        try:
            # Call widget-specific update methods
            if hasattr(widget, 'update_from_process_state'):
                widget.update_from_process_state(all_processes)
            
            # Widget-type specific updates
            if 'batch' in widget_id.lower():
                self.sync_batch_widget(widget, all_processes)
            elif 'training' in widget_id.lower():
                self.sync_training_widget(widget, all_processes)
            elif 'mvsep' in widget_id.lower():
                self.sync_mvsep_widget(widget, all_processes)
                
        except Exception as e:
            self.logger.error(f"Failed to sync widget {widget_id}: {e}")
    
    def sync_batch_widget(self, widget: Any, processes: Dict):
        """Sync batch processor widget"""
        
        batch_processes = {k: v for k, v in processes.items() 
                          if v.get('process_type') == 'batch_processing'}
        
        try:
            # Update progress displays
            for process_id, process_data in batch_processes.items():
                progress = process_data.get('progress_percent', 0)
                status = process_data.get('current_step', 'Unknown')
                current_item = process_data.get('current_item', '')
                
                # Thread-safe UI updates
                QApplication.instance().processEvents()
                
                if hasattr(widget, 'update_batch_progress'):
                    widget.update_batch_progress(process_id, progress, status, current_item)
                
                if hasattr(widget, 'set_progress_bar'):
                    widget.set_progress_bar(int(progress))
                
                if hasattr(widget, 'update_status_label'):
                    widget.update_status_label(status)
            
            # Update button states based on running processes
            has_running = any(p.get('state') == 'running' for p in batch_processes.values())
            
            if hasattr(widget, 'update_button_states'):
                widget.update_button_states(has_running)
                
        except Exception as e:
            self.logger.error(f"Failed to sync batch widget: {e}")
    
    def sync_training_widget(self, widget: Any, processes: Dict):
        """Sync training widget"""
        
        training_processes = {k: v for k, v in processes.items() 
                            if v.get('process_type') == 'llm_training'}
        
        try:
            for process_id, process_data in training_processes.items():
                progress = process_data.get('progress_percent', 0)
                current_step = process_data.get('current_step', 'Unknown')
                metadata = process_data.get('metadata', {})
                
                # Thread-safe UI updates
                QApplication.instance().processEvents()
                
                if hasattr(widget, 'update_training_progress'):
                    widget.update_training_progress(process_id, progress, current_step)
                
                if hasattr(widget, 'update_training_metrics'):
                    widget.update_training_metrics(process_id, metadata)
                
                if hasattr(widget, 'set_training_status'):
                    widget.set_training_status(current_step)
                    
        except Exception as e:
            self.logger.error(f"Failed to sync training widget: {e}")
    
    def sync_mvsep_widget(self, widget: Any, processes: Dict):
        """Sync MVSep widget"""
        
        mvsep_processes = {k: v for k, v in processes.items() 
                          if v.get('process_type') == 'mvsep_processing'}
        
        try:
            for process_id, process_data in mvsep_processes.items():
                progress = process_data.get('progress_percent', 0)
                status = process_data.get('current_step', 'Unknown')
                
                # Thread-safe UI updates
                QApplication.instance().processEvents()
                
                if hasattr(widget, 'update_mvsep_progress'):
                    widget.update_mvsep_progress(process_id, progress, status)
                
                if hasattr(widget, 'set_processing_status'):
                    widget.set_processing_status(status)
                    
        except Exception as e:
            self.logger.error(f"Failed to sync MVSep widget: {e}")
    
    def sync_all_widgets(self):
        """Synchronize all registered widgets"""
        
        for widget_id in list(self.registered_widgets.keys()):
            self.sync_widget(widget_id)
        
        # Emit system status update
        system_status = self.integrated_manager.get_system_status()
        self.system_status_changed.emit(system_status)
    
    def start_batch_process(self, config: Dict = None) -> Optional[str]:
        """Start a batch processing operation"""
        
        try:
            process_id = f"batch_{int(time.time())}"
            
            # Start process with checkpoint system
            checkpoint = self.checkpoint_system.start_process(
                process_id,
                ProcessType.BATCH_PROCESSING,
                total_items=config.get('total_items', 50),  # Default 50 songs
                metadata=config or {}
            )
            
            # Start actual batch processing in background
            def run_batch():
                try:
                    from production_batch_10_drummers import ProductionBatchProcessor
                    
                    batch_processor = ProductionBatchProcessor()
                    
                    # Run with progress callbacks
                    asyncio.run(batch_processor.run_production_batch())
                    
                    self.checkpoint_system.complete_process(process_id, success=True)
                    self.process_completed.emit(process_id, True)
                    
                except Exception as e:
                    self.checkpoint_system.update_progress(process_id, error=str(e))
                    self.checkpoint_system.complete_process(process_id, success=False)
                    self.process_completed.emit(process_id, False)
                    self.logger.error(f"Batch process failed: {e}")
            
            batch_thread = threading.Thread(target=run_batch, daemon=True)
            batch_thread.start()
            
            self.process_started.emit(process_id, checkpoint.to_dict())
            self.logger.info(f"Started batch process: {process_id}")
            
            return process_id
            
        except Exception as e:
            self.logger.error(f"Failed to start batch process: {e}")
            return None
    
    def start_training_process(self, config: Dict = None) -> Optional[str]:
        """Start an LLM training process"""
        
        try:
            process_id = f"training_{int(time.time())}"
            
            # Start process with checkpoint system
            checkpoint = self.checkpoint_system.start_process(
                process_id,
                ProcessType.LLM_TRAINING,
                total_items=config.get('total_epochs', 100),
                metadata=config or {}
            )
            
            # Start actual training in background
            def run_training():
                try:
                    from gpu_training_tfr_pattern import GPUTrainingTFRPattern
                    
                    trainer = GPUTrainingTFRPattern()
                    
                    # Run with progress callbacks
                    trainer.run_comprehensive_training()
                    
                    self.checkpoint_system.complete_process(process_id, success=True)
                    self.process_completed.emit(process_id, True)
                    
                except Exception as e:
                    self.checkpoint_system.update_progress(process_id, error=str(e))
                    self.checkpoint_system.complete_process(process_id, success=False)
                    self.process_completed.emit(process_id, False)
                    self.logger.error(f"Training process failed: {e}")
            
            training_thread = threading.Thread(target=run_training, daemon=True)
            training_thread.start()
            
            self.process_started.emit(process_id, checkpoint.to_dict())
            self.logger.info(f"Started training process: {process_id}")
            
            return process_id
            
        except Exception as e:
            self.logger.error(f"Failed to start training process: {e}")
            return None
    
    def get_process_status(self, process_id: str) -> Optional[Dict]:
        """Get status of a specific process"""
        
        return self.checkpoint_system.get_process_status(process_id)
    
    def get_all_processes(self) -> Dict:
        """Get status of all processes"""
        
        return self.checkpoint_system.get_all_processes()
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        
        return self.integrated_manager.get_system_status()
    
    def pause_process(self, process_id: str) -> bool:
        """Pause a running process"""
        
        try:
            # Update checkpoint state
            self.checkpoint_system.update_progress(
                process_id, 
                current_step="paused",
                metadata_update={'paused_at': datetime.now().isoformat()}
            )
            
            # TODO: Implement actual process pausing logic
            self.logger.info(f"Paused process: {process_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pause process {process_id}: {e}")
            return False
    
    def resume_process(self, process_id: str) -> bool:
        """Resume a paused process"""
        
        try:
            # Resume from checkpoint
            checkpoint = self.checkpoint_system.resume_process(process_id)
            if checkpoint:
                self.logger.info(f"Resumed process: {process_id}")
                return True
            else:
                self.logger.error(f"Failed to resume process: {process_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to resume process {process_id}: {e}")
            return False
    
    def stop_process(self, process_id: str) -> bool:
        """Stop a running process"""
        
        try:
            # Mark as completed (stopped)
            self.checkpoint_system.complete_process(process_id, success=False)
            
            # TODO: Implement actual process stopping logic
            self.logger.info(f"Stopped process: {process_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop process {process_id}: {e}")
            return False

# Global service instance
_integrated_service = None

def get_integrated_process_service() -> IntegratedProcessService:
    """Get the global integrated process service instance"""
    
    global _integrated_service
    if _integrated_service is None:
        _integrated_service = IntegratedProcessService()
    
    return _integrated_service

def initialize_integrated_service() -> bool:
    """Initialize the integrated process service"""
    
    service = get_integrated_process_service()
    return service.initialize_systems()
