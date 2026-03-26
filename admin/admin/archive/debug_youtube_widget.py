"""
YouTube Widget Debug Tool
========================
Diagnoses issues with the YouTube integration in the DrummersWidget
"""

import os
import sys
import logging
import traceback

from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem, QVBoxLayout, QWidget, QPushButton, QLabel
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class YouTubeDebugWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Widget Debug Tool")

        layout = QVBoxLayout()

        self.status_label = QLabel("Testing YouTube integration...")
        layout.addWidget(self.status_label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        self.preview_btn = QPushButton("Test Preview")
        self.preview_btn.clicked.connect(self.test_preview)
        layout.addWidget(self.preview_btn)

        self.data_info_label = QLabel("Data role info will appear here")
        layout.addWidget(self.data_info_label)

        self.setLayout(layout)

        # Populate test data
        self.populate_test_data()

    def populate_test_data(self):
        try:
            # Add test items
            test_data = [
                {
                    "title": "Test Video 1",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "id": "dQw4w9WgXcQ"
                },
                {
                    "title": "Test Video 2",
                    "url": "https://www.youtube.com/watch?v=oHg5SJYRHA0",
                    "id": "oHg5SJYRHA0"
                }
            ]

            self.list_widget.clear()
            for data in test_data:
                item = QListWidgetItem(data["title"])

                # Store data with different roles to test which one works
                item.setData(Qt.UserRole, data)

                # Also store some debug info for verification
                item.setData(Qt.ToolTipRole, f"URL: {data['url']}")

                self.list_widget.addItem(item)

            # Select the first item
            self.list_widget.setCurrentRow(0)

            self.status_label.setText("Test data loaded successfully")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            logger.error(f"Error setting test data: {e}")
            traceback.print_exc()

    def test_preview(self):
        try:
            current_items = self.list_widget.selectedItems()

            if not current_items:
                self.status_label.setText("Error: No items selected")
                return

            # Log available roles for debugging
            item = current_items[0]

            # Try getting data with Qt.UserRole (this should work)
            user_role_data = item.data(Qt.UserRole)

            # Display debug info
            debug_info = f"Data with Qt.UserRole: {user_role_data}\n"
            self.data_info_label.setText(debug_info)

            if not user_role_data or "url" not in user_role_data:
                self.status_label.setText("Error: Invalid video data or missing URL")
                return

            # Open the URL in the default browser
            QDesktopServices.openUrl(QUrl(user_role_data["url"]))
            self.status_label.setText(f"Opening URL: {user_role_data['url']}")

        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            logger.error(f"Error playing preview: {e}")
            traceback.print_exc()

def main():
    app = QApplication(sys.argv)
    window = YouTubeDebugWidget()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
