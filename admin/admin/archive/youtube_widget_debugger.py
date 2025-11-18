"""
YouTube Widget Deep Debugger
===========================
This tool helps diagnose issues with YouTube functionality in DrummersWidget
"""
import pytube
import json
import logging
import os
import sys
import traceback

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import ()
from pathlib import Path


    QApplication, QWidget, QVBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QTextEdit, QGridLayout, QGroupBox
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class YouTubeDebugWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Widget Deep Debugger")
        self.resize(800, 600)

        self.setup_ui()
        self.populate_test_data()

    def setup_ui(self):
        main_layout = QVBoxLayout()

        # Debug Output
        self.debug_output = QTextEdit()
        self.debug_output.setReadOnly(True)
        self.debug_output.setPlaceholderText("Debug output will appear here")
        main_layout.addWidget(QLabel("Debug Output:"))
        main_layout.addWidget(self.debug_output)

        # List widget with test data
        list_group = QGroupBox("YouTube Results List")
        list_layout = QVBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_item_selected)
        list_layout.addWidget(self.list_widget)

        list_group.setLayout(list_layout)
        main_layout.addWidget(list_group)

        # Button group
        button_grid = QGridLayout()

        # Test buttons
        self.preview_btn = QPushButton("Test Preview")
        self.preview_btn.clicked.connect(self.on_preview)
        button_grid.addWidget(self.preview_btn, 0, 0)

        self.download_btn = QPushButton("Test Download")
        self.download_btn.clicked.connect(self.on_download)
        button_grid.addWidget(self.download_btn, 0, 1)

        self.data_btn = QPushButton("Inspect Item Data")
        self.data_btn.clicked.connect(self.inspect_item_data)
        button_grid.addWidget(self.data_btn, 0, 2)

        self.test_pt_btn = QPushButton("Try PyTube")
        self.test_pt_btn.clicked.connect(self.test_pytube)
        button_grid.addWidget(self.test_pt_btn, 0, 3)

        main_layout.addLayout(button_grid)

        self.setLayout(main_layout)

    def log_message(self, message):
        """Add message to debug output""":
        self.debug_output.append(message)
        print(message)

    def populate_test_data(self):
        """Add test items to the list widget""":
        try:
            self.log_message("Populating test data...")
            test_data = [
                {
                    "title": "Test Video 1",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "id": "dQw4w9WgXcQ"
                },
                {
                    "title": "Test Video 2 (ID only)",
                    "id": "oHg5SJYRHA0"
                }
            ]

            self.list_widget.clear()

            for i, data in enumerate(test_data):
                item = QListWidgetItem(data["title"])

                # Try multiple role storage methods to see what works
                item.setData(Qt.UserRole, data)
                item.setData(Qt.ItemDataRole.UserRole, data) # Another way

                # Store some test indicators to see what's retrieved
                item.setData(Qt.ToolTipRole, f"Item {i}: {data['title']}")

                self.list_widget.addItem(item)

            # Select first item
            self.list_widget.setCurrentRow(0)
            self.log_message("Test data loaded successfully")

        except Exception as e:
            self.log_message(f"Error setting test data: {str(e)}")
            traceback.print_exc()

    def on_item_selected(self):
        """Handle item selection""":
        try:
            current_items = self.list_widget.selectedItems()
            if current_items:
                self.log_message(f"Selected item: {current_items[0].text()}")
            else:
                self.log_message("No item selected")
        except Exception as e:
            self.log_message(f"Error in item selection: {str(e)}")

    def inspect_item_data(self):
        """Inspect selected item data to see what's stored and how""":
        try:
            current_items = self.list_widget.selectedItems()
            if not current_items:
                self.log_message("No item selected to inspect")
                return

            item = current_items[0]
            self.log_message("\n--- ITEM DATA INSPECTION ---")

            # Check various ways to access the data
            data_qt_userrole = item.data(Qt.UserRole)
            data_qt_userrole_enum = item.data(Qt.ItemDataRole.UserRole)

            self.log_message(f"Qt.UserRole (integer value: {int(Qt.UserRole)})")
            self.log_message(f"Type: {type(data_qt_userrole)}")
            self.log_message(f"Content: {json.dumps(data_qt_userrole, indent=2) if data_qt_userrole else 'None'}")

            self.log_message(f"\nQt.ItemDataRole.UserRole (integer value: {int(Qt.ItemDataRole.UserRole)})")
            self.log_message(f"Type: {type(data_qt_userrole_enum)}")
            self.log_message(f"Content: {json.dumps(data_qt_userrole_enum, indent=2) if data_qt_userrole_enum else 'None'}")

            self.log_message("\nChecking equality:")
            self.log_message(f"Qt.UserRole == Qt.ItemDataRole.UserRole: {Qt.UserRole == Qt.ItemDataRole.UserRole}")
            self.log_message(f"data from Qt.UserRole == data from Qt.ItemDataRole.UserRole: {data_qt_userrole == data_qt_userrole_enum}")

            # Try to access url
            if data_qt_userrole and isinstance(data_qt_userrole, dict) and "url" in data_qt_userrole:
                self.log_message(f"\nURL from Qt.UserRole: {data_qt_userrole.get('url')}")
            else:
                self.log_message("\nNo URL found in Qt.UserRole data")

            if data_qt_userrole_enum and isinstance(data_qt_userrole_enum, dict) and "url" in data_qt_userrole_enum:
                self.log_message(f"URL from Qt.ItemDataRole.UserRole: {data_qt_userrole_enum.get('url')}")
            else:
                self.log_message("No URL found in Qt.ItemDataRole.UserRole data")

        except Exception as e:
            self.log_message(f"Error inspecting item data: {str(e)}")
            traceback.print_exc()

    def on_preview(self):
        """Test preview functionality""":
        try:
            self.log_message("\n--- TESTING PREVIEW ---")
            current_items = self.list_widget.selectedItems()
            if not current_items:
                self.log_message("No items selected")
                return

            # Try both ways to get data
            self.log_message("Attempting to get data with Qt.UserRole...")
            video_data = current_items[0].data(Qt.UserRole)
            self.log_message(f"Data type: {type(video_data)}")
            self.log_message(f"Data content: {video_data}")

            if not video_data or not isinstance(video_data, dict):
                self.log_message("Invalid data type or None returned")
                return

            # Try to get URL
            video_url = video_data.get("url")
            if not video_url and "id" in video_data:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                self.log_message(f"Constructed URL from ID: {video_url}")

            if not video_url:
                self.log_message("No URL or ID found in video data")
                return

            # Try opening the URL
            self.log_message(f"Opening URL: {video_url}")
            QDesktopServices.openUrl(QUrl(video_url))
            self.log_message("URL opened in browser")

        except Exception as e:
            self.log_message(f"Error playing preview: {str(e)}")
            traceback.print_exc()

    def on_download(self):
        """Test download functionality""":
        try:
            self.log_message("\n--- TESTING DOWNLOAD ---")
            current_items = self.list_widget.selectedItems()
            if not current_items:
                self.log_message("No items selected")
                return

            # Try both ways to get data
            self.log_message("Attempting to get data with Qt.UserRole...")
            video_data = current_items[0].data(Qt.UserRole)
            self.log_message(f"Data type: {type(video_data)}")
            self.log_message(f"Data content: {video_data}")

            if not video_data or not isinstance(video_data, dict):
                self.log_message("Invalid data type or None returned")
                return

            # Try to get URL
            video_url = video_data.get("url")
            if not video_url and "id" in video_data:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                self.log_message(f"Constructed URL from ID: {video_url}")

            if not video_url:
                self.log_message("No URL or ID found in video data")
                return

            # Instead of actually downloading, just verify the URL is valid
            self.log_message(f"Valid download URL: {video_url}")

        except Exception as e:
            self.log_message(f"Error testing download: {str(e)}")
            traceback.print_exc()

    def test_pytube(self):
        """Test if pytube is installed and working""":
        try:
            self.log_message("\n--- TESTING PYTUBE ---")
            self.log_message(f"PyTube version: {pytube.__version__}")

            test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            self.log_message(f"Testing PyTube with URL: {test_url}")

            youtube = pytube.YouTube(test_url)
            self.log_message(f"Video title: {youtube.title}")
            self.log_message(f"Available streams: {len(youtube.streams.all())}")
            self.log_message("PyTube working correctly!")

        except ImportError:
            self.log_message("PyTube is not installed. Run: pip install pytube")
        except Exception as e:
            self.log_message(f"Error testing PyTube: {str(e)}")
            traceback.print_exc()

def main():
    app = QApplication(sys.argv)
    window = YouTubeDebugWidget()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
