#!/usr/bin/env python3
"""
Superior Drummer 3 API Server for DrumTracKAI
Provides real-time monitoring of SD3 sample extraction process
"""

import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    logger.error("Flask not available. Install with: pip install flask flask-cors")
    FLASK_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil not available. System monitoring will be limited.")
    PSUTIL_AVAILABLE = False

if not FLASK_AVAILABLE:
    print("ERROR: Flask is required to run the API server.")
    print("Install with: pip install flask flask-cors")
    exit(1)

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

class SD3ExtractionMonitor:
    """Monitor Superior Drummer 3 sample extraction progress"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.midi_dir = self.base_path / "sd3_midi_patterns"
        self.output_dir = self.base_path / "sd3_extracted_samples"
        self.db_path = self.base_path / "sd3_real_training.db"
        
        # Initialize extraction status
        self.extraction_status = {
            'status': 'idle',  # idle, running, completed, error
            'progress': 0,
            'total_patterns': 0,
            'completed_patterns': 0,
            'current_pattern': '',
            'start_time': None,
            'estimated_completion': None,
            'samples_extracted': 0,
            'errors': [],
            'extraction_rate': 0,  # samples per minute
            'time_remaining': 0,   # minutes
            'last_update': datetime.now().isoformat()
        }
        
        # Start monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_extraction, daemon=True)
        self.monitor_thread.start()
        
        logger.info("SD3 Extraction Monitor initialized")
    
    def _monitor_extraction(self):
        """Background monitoring of extraction progress"""
        while self.monitoring:
            try:
                self._update_extraction_status()
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                logger.error(f"Error in monitoring thread: {e}")
                time.sleep(5)
    
    def _update_extraction_status(self):
        """Update extraction status based on file system"""
        try:
            # Count total MIDI patterns
            if self.midi_dir.exists():
                midi_files = list(self.midi_dir.glob("*.mid"))
                self.extraction_status['total_patterns'] = len(midi_files)
            else:
                self.extraction_status['total_patterns'] = 0
            
            # Count extracted samples
            if self.output_dir.exists():
                wav_files = list(self.output_dir.glob("*.wav"))
                current_samples = len(wav_files)
                
                # Check if extraction is active
                if current_samples > self.extraction_status['samples_extracted']:
                    if self.extraction_status['status'] == 'idle':
                        self.extraction_status['status'] = 'running'
                        self.extraction_status['start_time'] = datetime.now().isoformat()
                    
                    # Calculate extraction rate
                    if self.extraction_status['start_time']:
                        start_time = datetime.fromisoformat(self.extraction_status['start_time'])
                        elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
                        if elapsed_minutes > 0:
                            self.extraction_status['extraction_rate'] = current_samples / elapsed_minutes
                    
                    self.extraction_status['samples_extracted'] = current_samples
                    self.extraction_status['completed_patterns'] = current_samples
                
                # Calculate progress
                if self.extraction_status['total_patterns'] > 0:
                    self.extraction_status['progress'] = (current_samples / self.extraction_status['total_patterns']) * 100
                
                # Calculate time remaining
                if self.extraction_status['extraction_rate'] > 0 and current_samples < self.extraction_status['total_patterns']:
                    remaining_samples = self.extraction_status['total_patterns'] - current_samples
                    self.extraction_status['time_remaining'] = remaining_samples / self.extraction_status['extraction_rate']
                
                # Check if completed
                if current_samples >= self.extraction_status['total_patterns'] and self.extraction_status['total_patterns'] > 0:
                    if self.extraction_status['status'] == 'running':
                        self.extraction_status['status'] = 'completed'
            
            self.extraction_status['last_update'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Error updating extraction status: {e}")
            self.extraction_status['errors'].append(str(e))
    
    def get_extraction_status(self):
        """Get current extraction status"""
        return self.extraction_status.copy()
    
    def get_sample_details(self):
        """Get details about extracted samples"""
        try:
            samples = []
            if self.output_dir.exists():
                for wav_file in self.output_dir.glob("*.wav"):
                    stat = wav_file.stat()
                    samples.append({
                        'name': wav_file.name,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            return sorted(samples, key=lambda x: x['created'], reverse=True)
        except Exception as e:
            logger.error(f"Error getting sample details: {e}")
            return []
    
    def get_database_status(self):
        """Get database training status"""
        try:
            if not self.db_path.exists():
                return {
                    'exists': False,
                    'samples_in_db': 0,
                    'last_training': None,
                    'training_status': 'not_started'
                }
            
            # Connect to database and get status
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Get sample count
            cursor.execute("SELECT COUNT(*) FROM samples")
            sample_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'exists': True,
                'samples_in_db': sample_count,
                'last_training': None,  # TODO: Implement training tracking
                'training_status': 'ready' if sample_count > 0 else 'no_data'
            }
        except Exception as e:
            logger.error(f"Error getting database status: {e}")
            return {
                'exists': False,
                'error': str(e),
                'samples_in_db': 0,
                'last_training': None,
                'training_status': 'error'
            }

# Initialize monitor
try:
    monitor = SD3ExtractionMonitor()
    logger.info("SD3 Monitor initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize SD3 monitor: {e}")
    monitor = None

# API Routes
@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'monitor_active': monitor is not None
    })

@app.route('/api/sd3')
def get_sd3_status():
    """Get SD3 extraction status"""
    try:
        if not monitor:
            return jsonify({'error': 'Monitor not initialized'}), 500
        return jsonify(monitor.get_extraction_status())
    except Exception as e:
        logger.error(f"Error getting SD3 status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/samples')
def get_samples():
    """Get extracted samples details"""
    try:
        if not monitor:
            return jsonify({'error': 'Monitor not initialized'}), 500
        return jsonify(monitor.get_sample_details())
    except Exception as e:
        logger.error(f"Error getting samples: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/database')
def get_database_status():
    """Get database training status"""
    try:
        if not monitor:
            return jsonify({'error': 'Monitor not initialized'}), 500
        return jsonify(monitor.get_database_status())
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get overall statistics"""
    try:
        if not monitor:
            return jsonify({'error': 'Monitor not initialized'}), 500
        
        extraction = monitor.get_extraction_status()
        samples = monitor.get_sample_details()
        database = monitor.get_database_status()
        
        stats = {
            'extraction': {
                'status': extraction['status'],
                'progress': extraction['progress'],
                'total_patterns': extraction['total_patterns'],
                'samples_extracted': extraction['samples_extracted'],
                'extraction_rate': extraction['extraction_rate']
            },
            'samples': {
                'count': len(samples),
                'total_size': sum(s['size'] for s in samples),
                'latest': samples[0]['created'] if samples else None
            },
            'database': {
                'samples_in_db': database['samples_in_db'],
                'training_status': database['training_status']
            }
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system')
def get_system_status():
    """Get system health data"""
    try:
        system_data = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_usage': 0
        }
        
        if PSUTIL_AVAILABLE:
            system_data.update({
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('.').percent
            })
        
        return jsonify(system_data)
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("DrumTracKAI Superior Drummer 3 API Server")
    print("=" * 60)
    print("API endpoints available:")
    print("  - http://localhost:5001/api/health")
    print("  - http://localhost:5001/api/sd3")
    print("  - http://localhost:5001/api/samples")
    print("  - http://localhost:5001/api/database")
    print("  - http://localhost:5001/api/stats")
    print("  - http://localhost:5001/api/system")
    print()
    print("SD3 Web Monitor: sd3_web_monitor.html")
    print()
    print("Dependencies status:")
    print(f"  - Flask: {'' if FLASK_AVAILABLE else ''}")
    print(f"  - psutil: {'' if PSUTIL_AVAILABLE else ''}")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=False)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        if monitor:
            monitor.monitoring = False
    except Exception as e:
        print(f"Server error: {e}")
        logger.error(f"Server startup error: {e}")
        logger.error(traceback.format_exc())
