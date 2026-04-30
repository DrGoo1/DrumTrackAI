"""
Test script for the DrumTracKAI Admin application
================================================
This script runs a simple test of the YouTube functionality
to verify that our yt-dlp based solution works correctly.
"""
import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QMessageBox
from PySide6.QtCore import Qt, QSize
from services.youtube_service import YouTubeService

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DrumTracKAI Admin YouTube Test")
        self.setMinimumSize(QSize(600, 400))
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add status label
        self.status_label = QLabel("Ready to test YouTube download")
        layout.addWidget(self.status_label)
        
        # Add progress label
        self.progress_label = QLabel("Progress: 0%")
        layout.addWidget(self.progress_label)
        
        # Add test button
        self.test_button = QPushButton("Test YouTube Download")
        self.test_button.clicked.connect(self.run_youtube_test)
        layout.addWidget(self.test_button)
        
        # Initialize YouTube service
        self.youtube_service = YouTubeService()
        
        # For storing thread references
        self.download_thread = None
        self.thread = None
    
    def run_youtube_test(self):
        """Run a test of the YouTube download functionality"""
        try:
            # Disable button during test
            self.test_button.setEnabled(False)
            self.status_label.setText("Starting YouTube download test...")
            
            # Create output directory if it doesn't exist
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
            os.makedirs(output_dir, exist_ok=True)
            
            # Set output file path
            output_path = os.path.join(output_dir, "test_download.mp3")
            
            # Test video ID (Toto - Rosanna)
            video_id = "qmOLtTGvsbM"
            
            # Start download
            self.status_label.setText(f"Downloading video ID: {video_id}")
            self.download_thread, self.thread = self.youtube_service.download_audio(
                video_id,
                output_path,
                self.on_progress_update,
                self.on_download_complete,
                self.on_download_error
            )
            
        except Exception as e:
            self.status_label.setText(f"Error starting test: {str(e)}")
            self.test_button.setEnabled(True)
    
    def on_progress_update(self, percentage):
        """Update progress display"""
        self.progress_label.setText(f"Progress: {percentage}%")
    
    def on_download_complete(self, file_path):
        """Handle download completion"""
        self.status_label.setText(f"Download complete: {file_path}")
        self.test_button.setEnabled(True)
        QMessageBox.information(self, "Download Complete", f"Successfully downloaded to:\n{file_path}")
    
    def on_download_error(self, error_msg):
        """Handle download error"""
        self.status_label.setText(f"Download failed")
        self.test_button.setEnabled(True)
        QMessageBox.critical(self, "Download Error", f"Failed to download:\n{error_msg}")

def main():
    # Create the application and window
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
