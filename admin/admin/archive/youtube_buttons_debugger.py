import pytube
import logging
import os
import sys
import traceback

from admin.services.youtube_service import YouTubeService
from admin.utils.youtube_search import YouTubeSearchAPI
from PySide6.QtCore import Qt, QUrl, QObject, Signal, QThread
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import ()


#!/usr/bin/env python3
"""
YouTube Button Functions Debugger
This tool creates a standalone window with YouTube search results and tests both the preview
and download functions with detailed debug output.
"""

    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QProgressBar, QMessageBox, QTextEdit
)

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    # Import YouTubeSearchAPI and YouTubeService

    # Set up basic logging
    logging.basicConfig(level=logging.DEBUG,)
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    logger = logging.getLogger("YouTubeButtonsDebugger")

except ImportError as e:
    print(f"Error importing required modules: {e}")
    print(f"Make sure you're running this from the DrumTracKAI project root directory")
    sys.exit(1)


class ThreadSafeUpdater(QObject):
    """Helper class for thread-safe UI updates"""
    update_signal = Signal(object, tuple)

    def run_in_main_thread(self, func, *args):
        self.update_signal.emit(func, args)

    def _process_update(self, func, args):
        try:
            func(*args)
        except Exception as e:
            print(f"Error in thread-safe update: {e}")
            traceback.print_exc()


class YouTubeButtonsDebugger(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Buttons Debugger")
        self.setMinimumSize(800, 600)

        # Set up the central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout
        self.layout = QVBoxLayout(self.central_widget)

        # Search area
        self.search_layout = QHBoxLayout()
        self.search_edit = QLineEdit("Rosanna Toto")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.on_search)
        self.search_layout.addWidget(QLabel("Search:"))
        self.search_layout.addWidget(self.search_edit)
        self.search_layout.addWidget(self.search_button)

        # Results list
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QListWidget.SingleSelection)

        # Buttons layout
        self.buttons_layout = QHBoxLayout()
        self.preview_button = QPushButton("Play Preview")
        self.download_button = QPushButton("Download Selected")
        self.preview_button.clicked.connect(self.on_play_preview)
        self.download_button.clicked.connect(self.on_download_video)
        self.buttons_layout.addWidget(self.preview_button)
        self.buttons_layout.addWidget(self.download_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Debug output area
        self.debug_output = QTextEdit()
        self.debug_output.setReadOnly(True)

        # Add everything to the main layout
        self.layout.addLayout(self.search_layout)
        self.layout.addWidget(self.results_list)
        self.layout.addLayout(self.buttons_layout)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(QLabel("Debug Output:"))
        self.layout.addWidget(self.debug_output)

        # Set up YouTube API and service
        self.youtube_api = YouTubeSearchAPI()
        self.youtube_service = YouTubeService()
        self.download_threads = []

        # Set up thread-safe updater
        self.thread_safe = ThreadSafeUpdater()
        self.thread_safe.update_signal.connect(self.thread_safe._process_update)

        # Add to log
        self.log("YouTubeButtonsDebugger initialized")

        # Output Qt version
        self.log(f"Qt Version: {Qt.qVersion()}")
        self.log(f"Qt.UserRole value: {Qt.UserRole} (should be 32)")

        # Get system info
        self.log(f"Python version: {sys.version}")
        try:
            self.log(f"PyTube version: {pytube.__version__}")
        except:
            self.log("PyTube version: Not found")

    def log(self, message):
        """Add a message to the debug output""":
        self.debug_output.append(message)
        print(message) # Also print to console

    def on_search(self):
        """Handle search button click""":
        query = self.search_edit.text().strip()
        if not query:
            self.log("Error: Search query is empty")
            return

        self.log(f"Searching for: {query}")
        self.results_list.clear()
        self.results_list.addItem("Searching...")

        try:
            # Perform search
            results = self.youtube_api.search(query, max_results=10)
            self.log(f"Search returned {len(results)} results")

            # Clear the "Searching..." item
            self.results_list.clear()

            # Update the list with results
            self.update_youtube_results(results)
        except Exception as e:
            self.log(f"Error searching: {e}")
            self.log(traceback.format_exc())

    def update_youtube_results(self, results):
        """Update YouTube results list""":
        try:
            self.log("=== Updating YouTube results ===")

            if not results:
                self.log("No results found")
                self.results_list.addItem("No results found")
                return

            # Add items to the list
            for i, result in enumerate(results):
                item = QListWidgetItem(result.get("title", "Unknown"))

                # Store data using Qt.UserRole directly as integer
                raw_user_role = 0x0100 # Qt.UserRole raw value
                item.setData(raw_user_role, result)

                # Also store using Qt.UserRole enum for comparison
                item.setData(Qt.UserRole, result)

                # Log info
                video_id = result.get("id", "Unknown")
                self.log(f"Item {i}: {result.get('title')} - ID: {video_id}")
                self.log(f"  URL: {result.get('url', 'None')}")

                # Add to list
                self.results_list.addItem(item)

            # Select the first result
            self.results_list.setCurrentRow(0)
            self.log("YouTube results updated")

        except Exception as e:
            self.log(f"Error updating results: {e}")
            self.log(traceback.format_exc())

    def on_play_preview(self):
        """Test the play preview functionality""":
        self.log("\n=== PLAY PREVIEW TEST ===")
        try:
            # Get selected item
            current_items = self.results_list.selectedItems()
            if not current_items:
                self.log("No item selected")
                QMessageBox.warning(self, "Preview Error", "Please select a video to preview")
                return

            # Try both ways to get data - direct integer and Qt.UserRole
            direct_data = None
            enum_data = None

            try:
                direct_data = current_items[0].data(0x0100) # Direct integer value for Qt.UserRole
                self.log(f"Direct integer data type: {type(direct_data)}")
                self.log(f"Direct integer data: {direct_data}")
            except Exception as e:
                self.log(f"Error getting direct data: {e}")

            try:
                enum_data = current_items[0].data(Qt.UserRole) # Qt.UserRole enum
                self.log(f"Qt.UserRole enum data type: {type(enum_data)}")
                self.log(f"Qt.UserRole enum data: {enum_data}")
            except Exception as e:
                self.log(f"Error getting enum data: {e}")

            # Use whichever data we got successfully
            video_data = direct_data if direct_data is not None else enum_data

            if not video_data or not isinstance(video_data, dict):
                self.log("Invalid video data")
                QMessageBox.warning(self, "Preview Error", "Invalid video data")
                return

            # Try to get URL from data
            video_url = None
            if "url" in video_data and video_data["url"]:
                video_url = video_data["url"]
                self.log(f"Using URL from data: {video_url}")
            elif "id" in video_data and video_data["id"]:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                self.log(f"Constructed URL from ID: {video_url}")

            if not video_url:
                self.log("No URL found in video data")
                QMessageBox.warning(self, "Preview Error", "No URL found for this video")
                return

            # Open the URL
            self.log(f"Opening URL in browser: {video_url}")
            QDesktopServices.openUrl(QUrl(video_url))
            self.log("Preview successful")

        except Exception as e:
            self.log(f"Error playing preview: {e}")
            self.log(traceback.format_exc())
            QMessageBox.critical(self, "Preview Error", f"Failed to play preview: {str(e)}")

    def on_download_video(self):
        """Test the download video functionality""":
        self.log("\n=== DOWNLOAD TEST ===")
        try:
            # Get selected item
            current_items = self.results_list.selectedItems()
            if not current_items:
                self.log("No item selected")
                QMessageBox.warning(self, "Download Error", "Please select a video to download")
                return

            # Try both ways to get data - direct integer and Qt.UserRole
            direct_data = None
            enum_data = None

            try:
                direct_data = current_items[0].data(0x0100) # Direct integer value for Qt.UserRole
                self.log(f"Direct integer data type: {type(direct_data)}")
                self.log(f"Direct integer data: {direct_data}")
            except Exception as e:
                self.log(f"Error getting direct data: {e}")

            try:
                enum_data = current_items[0].data(Qt.UserRole) # Qt.UserRole enum
                self.log(f"Qt.UserRole enum data type: {type(enum_data)}")
                self.log(f"Qt.UserRole enum data: {enum_data}")
            except Exception as e:
                self.log(f"Error getting enum data: {e}")

            # Use whichever data we got successfully
            video_data = direct_data if direct_data is not None else enum_data

            if not video_data or not isinstance(video_data, dict):
                self.log("Invalid video data")
                QMessageBox.warning(self, "Download Error", "Invalid video data")
                return

            # Try to get URL from data
            video_url = None
            if "url" in video_data and video_data["url"]:
                video_url = video_data["url"]
                self.log(f"Using URL from data: {video_url}")
            elif "id" in video_data and video_data["id"]:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                self.log(f"Constructed URL from ID: {video_url}")

            if not video_url:
                self.log("No URL found in video data")
                QMessageBox.warning(self, "Download Error", "No URL found for this video")
                return

            # Create output path
            video_id = video_data.get("id", "unknown")
            title = video_data.get("title", "unknown")

            # Sanitize filename
            def sanitize_filename(name):
                return "".join(c for c in name if c.isalnum() or c in " ._-").strip()

            filename = f"{video_id}_{sanitize_filename(title)[:30]}.mp3"
            download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "DrumTracKAI_YT_Tests")
            os.makedirs(download_dir, exist_ok=True)
            output_path = os.path.join(download_dir, filename)

            self.log(f"Output path: {output_path}")

            # Reset progress bar
            self.progress_bar.setValue(0)

            # Start download
            try:
                self.log("Starting download...")
                self.download_button.setEnabled(False)
                self.download_button.setText("Downloading...")

                # Start download using YouTubeService
                download_thread, thread = self.youtube_service.download_audio()
                    video_url,
                    output_path,
                    self.on_download_progress,
                    self.on_download_complete,
                    lambda error: self.thread_safe.run_in_main_thread()
                        lambda: self.on_download_error(error)
                    )
                )

                # Store thread objects
                self.download_threads.append((download_thread, thread))
                self.log("Download started successfully")

            except Exception as e:
                self.log(f"Error starting download: {e}")
                self.log(traceback.format_exc())
                self.download_button.setEnabled(True)
                self.download_button.setText("Download Selected")
                QMessageBox.critical(self, "Download Error", f"Failed to start download: {str(e)}")

        except Exception as e:
            self.log(f"Error in download process: {e}")
            self.log(traceback.format_exc())
            QMessageBox.critical(self, "Download Error", f"Failed to download: {str(e)}")

    def on_download_progress(self, progress):
        """Handle download progress updates""":
        try:
            self.log(f"Download progress: {progress}%")

            def update_ui():
                self.progress_bar.setValue(progress)
                self.download_button.setText(f"Downloading... {progress}%")

            self.thread_safe.run_in_main_thread(update_ui)
        except Exception as e:
            self.log(f"Error updating progress: {e}")

    def on_download_complete(self, result_path):
        """Handle download completion""":
        try:
            self.log(f"Download completed: {result_path}")

            def update_ui():
                self.download_button.setEnabled(True)
                self.download_button.setText("Download Selected")
                self.progress_bar.setValue(100)

                if result_path:
                    self.log(f"Download successful: {result_path}")
                    QMessageBox.information()
                        self, "Download Complete",
                        f"Downloaded successfully to:\n{result_path}"
                    )
                else:
                    self.log("Download failed - no result path")
                    QMessageBox.critical()
                        self, "Download Failed",
                        "Failed to download the video. Check the logs for details."
                    )

            self.thread_safe.run_in_main_thread(update_ui)

        except Exception as e:
            self.log(f"Error handling download completion: {e}")
            self.log(traceback.format_exc())

    def on_download_error(self, error_msg):
        """Handle download error""":
        self.log(f"Download error: {error_msg}")
        QMessageBox.critical(self, "Download Error", f"Failed to download: {error_msg}")
        self.download_button.setEnabled(True)
        self.download_button.setText("Download Selected")


def main():
    app = QApplication(sys.argv)
    window = YouTubeButtonsDebugger()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
