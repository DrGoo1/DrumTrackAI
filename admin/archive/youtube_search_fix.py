import logging
import os
import sys
import traceback

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLineEdit, QListWidget, QLabel, QMessageBox, QProgressBar
from services.youtube_service import YouTubeService
from utils.youtube_search import YouTubeSearchAPI

#!/usr/bin/env python
"""
YouTube Search Fix - Diagnostic and Fix Tool
===========================================

This tool helps diagnose and fix issues with the YouTube search functionality
in the DrumTracKAI Admin application.
"""


# Set up logging
logging.basicConfig(level=logging.INFO,)
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
logger = logging.getLogger("youtube_search_fix")

# Add parent directory to path
sys.path.insert(0, os.path.abspath('.'))

# Import our modules

class YouTubeSearchFixApp(QWidget):
    def __init__(self):
        super().__init__()
        self.youtube_api = YouTubeSearchAPI()
        self.youtube_service = YouTubeService()
        self.setup_ui()
        self.current_result = None

    def setup_ui(self):
        """Setup the UI""":
        self.setWindowTitle("YouTube Search Fix Tool")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Search section
        self.search_label = QLabel("Enter search query:")
        layout.addWidget(self.search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g., 'metallica enter sandman'")
        layout.addWidget(self.search_input)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        layout.addWidget(self.search_button)

        # Results list
        self.results_label = QLabel("Search Results:")
        layout.addWidget(self.results_label)

        self.results_list = QListWidget()
        self.results_list.itemSelectionChanged.connect(self.on_result_selected)
        layout.addWidget(self.results_list)

        # Download section
        self.download_label = QLabel("Download:")
        layout.addWidget(self.download_label)

        self.download_button = QPushButton("Download Selected")
        self.download_button.clicked.connect(self.download_selected)
        self.download_button.setEnabled(False)
        layout.addWidget(self.download_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def perform_search(self):
        """Perform a YouTube search using the fixed API""":
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Search Error", "Please enter a search query")
            return

        self.status_label.setText("Searching...")
        self.results_list.clear()
        self.download_button.setEnabled(False)

        try:
            logger.info(f"Performing search for: {query}")
            results = self.youtube_api.search(query, max_results=10)
            logger.info(f"Search complete. Found {len(results)} results")

            if not results:
                self.results_list.addItem("No results found")
                self.status_label.setText("No results found")
                return

            # Display results
            self.results = results
            for result in results:
                self.results_list.addItem(f"{result.get('title', 'Unknown')}")

            self.status_label.setText(f"Found {len(results)} results")

        except Exception as e:
            logger.error(f"Error performing search: {e}")
            traceback.print_exc()
            self.results_list.addItem(f"Error: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")

    def on_result_selected(self):
        """Handle result selection""":
        selected_items = self.results_list.selectedItems()
        if selected_items:
            index = self.results_list.row(selected_items[0])
            if 0 <= index < len(self.results):
                self.current_result = self.results[index]
                self.download_button.setEnabled(True)
                self.status_label.setText(f"Selected: {self.current_result.get('title', 'Unknown')}")
        else:
            self.current_result = None
            self.download_button.setEnabled(False)

    def download_selected(self):
        """Download the selected video""":
        if not self.current_result:
            return

        video_id = self.current_result.get('id')
        if not video_id:
            QMessageBox.warning(self, "Download Error", "Invalid video ID")
            return

        url = f"https://www.youtube.com/watch?v={video_id}"
        output_dir = os.path.abspath("youtube_downloads")
        os.makedirs(output_dir, exist_ok=True)

        self.status_label.setText(f"Downloading: {self.current_result.get('title', 'Unknown')}")
        self.download_button.setEnabled(False)
        self.progress_bar.setValue(0)

        # Define callbacks
        def on_progress(progress):
            self.progress_bar.setValue(int(progress * 100))

        def on_complete(result_path):
            self.progress_bar.setValue(100)
            self.status_label.setText(f"Download complete: {result_path}")
            self.download_button.setEnabled(True)
            QMessageBox.information(self, "Download Complete", f"File saved to: {result_path}")

        def on_error(error):
            self.progress_bar.setValue(0)
            self.status_label.setText(f"Download error: {error}")
            self.download_button.setEnabled(True)
            QMessageBox.warning(self, "Download Error", f"Failed to download: {error}")

        try:
            # Use our service to download
            self.youtube_service.download_audio()
                url=url,
                output_dir=output_dir,
                progress_callback=on_progress,
                completion_callback=on_complete,
                error_callback=on_error
            )
        except Exception as e:
            logger.error(f"Error starting download: {e}")
            traceback.print_exc()
            self.status_label.setText(f"Download error: {str(e)}")
            self.download_button.setEnabled(True)

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = YouTubeSearchFixApp()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
