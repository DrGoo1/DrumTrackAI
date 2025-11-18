"""
YouTube Functionality Fix Patch
==============================
This patch applies fixes to both the YouTube search API and the DrummersWidget
to ensure proper functioning of play preview and download buttons.
"""
import re
import logging
import os
import sys
import traceback

from pathlib import Path


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def patch_drummers_widget():
    """Apply patches to drummers_widget.py"""
    try:
        logger.info("Applying patch to drummers_widget.py...")

        # Path to the drummers_widget.py file
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui', 'drummers_widget.py'))

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Make the required changes
        # 1. Fix _update_youtube_results method
        update_results_patch = """    def _update_youtube_results(self, results):
        """Update YouTube search results in UI""":
        try:
            self.youtube_results = results
            self.youtube_results_list.clear()

            if not results:
                self.youtube_results_list.addItem("No results found")
                return

            for result in results:
                item = QListWidgetItem(result.get("title", "Unknown"))
                # Store data directly with Qt.UserRole (integer constant) for compatibility
                item.setData(0x0100, result) # 0x0100 is the raw value of Qt.UserRole
                self.youtube_results_list.addItem(item)

            # Select the first result
            self.youtube_results_list.setCurrentRow(0)
            self._update_button_states()

        except Exception as e:
            print(f"CONSOLE DEBUG: Error updating YouTube results: {e}")
            logger.error(f"Error updating YouTube results: {e}")
            traceback.print_exc()"""

        # 2. Fix _on_play_preview method
        play_preview_patch = """    def _on_play_preview(self):
        """Play a preview of the selected YouTube video""":
        try:
            print("\\n====== CONSOLE DEBUG: PLAY PREVIEW TRIGGERED ======")
            current_items = self.youtube_results_list.selectedItems()
            if not current_items:
                print("CONSOLE DEBUG: No items selected in YouTube results list")
                QMessageBox.warning(self, "Preview Error", "Please select a video to preview")
                return

            # Use direct integer value for Qt.UserRole (0x0100) for maximum compatibility
            video_data = current_items[0].data(0x0100)
            print(f"CONSOLE DEBUG: Selected video data type: {type(video_data)}")
            print(f"CONSOLE DEBUG: Selected video data: {video_data}")

            if not video_data or not isinstance(video_data, dict):
                print("CONSOLE DEBUG: Invalid video data type")
                QMessageBox.warning(self, "Preview Error", "Invalid video data")
                return

            video_url = None
            # Try to get URL from video data
            if "url" in video_data and video_data["url"]:
                video_url = video_data["url"]
            # If no URL, try to construct from ID
            elif "id" in video_data and video_data["id"]:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                print(f"CONSOLE DEBUG: Constructed URL from ID: {video_url}")

            if not video_url:
                print("CONSOLE DEBUG: No URL or ID found in video data")
                QMessageBox.warning(self, "Preview Error", "No URL found for this video")
                return

            # Open the URL in the default browser
            print(f"CONSOLE DEBUG: Opening URL: {video_url}")
            QDesktopServices.openUrl(QUrl(video_url))
            print("CONSOLE DEBUG: URL opened in browser")

        except Exception as e:
            print(f"CONSOLE DEBUG: Error playing preview: {e}")
            logger.error(f"Error playing preview: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Preview Error", f"Failed to play preview: {str(e)}")

        print("====== CONSOLE DEBUG: PLAY PREVIEW COMPLETE ======\\n")"""

        # 3. Fix _on_download_video method
        download_video_patch = """    def _on_download_video(self):
        """Handle YouTube download button click""":
        try:
            print("\\n====== CONSOLE DEBUG: DOWNLOAD VIDEO TRIGGERED ======")
            current_items = self.youtube_results_list.selectedItems()
            if not current_items:
                print("CONSOLE DEBUG: No items selected in YouTube results list")
                QMessageBox.warning(self, "Download Error", "Please select a video to download")
                return

            # Use direct integer value for Qt.UserRole (0x0100) for maximum compatibility
            video_data = current_items[0].data(0x0100)
            print(f"CONSOLE DEBUG: Selected video data type: {type(video_data)}")
            print(f"CONSOLE DEBUG: Selected video data: {video_data}")

            if not video_data or not isinstance(video_data, dict):
                print("CONSOLE DEBUG: Invalid video data type")
                QMessageBox.warning(self, "Download Error", "Invalid video data")
                return

            # Make sure we have either URL or ID
            video_url = None
            if "url" in video_data and video_data["url"]:
                video_url = video_data["url"]
            elif "id" in video_data and video_data["id"]:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                print(f"CONSOLE DEBUG: Constructed URL from ID: {video_url}")

            if not video_url:
                print("CONSOLE DEBUG: No URL or ID found in video data")
                QMessageBox.warning(self, "Download Error", "No URL found for this video")
                return

            print(f"CONSOLE DEBUG: Using video URL: {video_url}")

            # If we have a current song selected, use its title
            song_title = None
            if self.current_song:
                song_title = self.current_song.get("title")
                print(f"CONSOLE DEBUG: Using current song title: {song_title}")

            # Otherwise use the video title
            if not song_title:
                song_title = video_data.get("title", "Unknown")
                print(f"CONSOLE DEBUG: Using video title: {song_title}")

            # Create output filename
            filename = None
            if self.current_drummer:
                filename = f"{self.current_drummer['id']}_{self._sanitize_filename(song_title)}.mp3"

            # If no drummer context, use video ID
            if not filename:
                video_id = video_data.get('id', 'unknown')
                filename = f"{video_id}_{self._sanitize_filename(song_title)}.mp3"

            output_path = os.path.join(self.download_path, filename)
            print(f"CONSOLE DEBUG: Output path: {output_path}")

            # Reset progress bar
            self.download_progress.setValue(0)
            self.download_progress.setMaximum(100)

            print(f"CONSOLE DEBUG: Starting download from URL: {video_url}")

            # Start download using YouTubeService
            try:
                download_thread, thread = self.youtube_service.download_audio()
                    video_url,
                    output_path,
                    self._on_download_progress,
                    self._on_download_complete,
                    lambda error: self.thread_safe.run_in_main_thread()
                        lambda: QMessageBox.critical(self, "Download Error", f"Failed to download: {error}")
                    )
                )

                # Store the download thread objects for potential cancellation later
                self.download_threads.append((download_thread, thread))

                # Disable download button during download
                self.download_btn.setEnabled(False)
                self.download_btn.setText("Downloading...")
                print("CONSOLE DEBUG: Download started successfully")

            except Exception as e:
                print(f"CONSOLE DEBUG: Error starting download: {e}")
                logger.error(f"Error starting download: {e}")
                traceback.print_exc()
                QMessageBox.critical(self, "Download Error", f"Failed to start download: {str(e)}")

        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            QMessageBox.critical(self, "Download Error", f"Failed to download: {str(e)}")"""

        # Apply all patches
        patched_content = content

        # Find and replace the _update_youtube_results method
        update_results_pattern = re.compile(r'def _update_youtube_results\(self, results\):.*?(?=\n def|\n\n)', re.DOTALL)
        patched_content = re.sub(update_results_pattern, update_results_patch, patched_content)

        # Find and replace the _on_play_preview method
        play_preview_pattern = re.compile(r'def _on_play_preview\(self\):.*?(?=\n def|\n\n)', re.DOTALL)
        patched_content = re.sub(play_preview_pattern, play_preview_patch, patched_content)

        # Find and replace the _on_download_video method
        download_video_pattern = re.compile(r'def _on_download_video\(self\):.*?(?=\n def|\n\n)', re.DOTALL)
        patched_content = re.sub(download_video_pattern, download_video_patch, patched_content)

        # Create backup
        backup_path = file_path + '.bak'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Write patched content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(patched_content)

        logger.info(f"Successfully patched {file_path}")
        logger.info(f"Backup saved to {backup_path}")

        return True

    except Exception as e:
        logger.error(f"Error applying patch: {e}")
        traceback.print_exc()
        return False

def main():
    """Apply all patches"""
    success = patch_drummers_widget()

    if success:
        print("Patches successfully applied!")
        print("Please restart the application for changes to take effect.")
    else:
        print("Failed to apply patches. See log for details.")

if __name__ == "__main__":
    main()
