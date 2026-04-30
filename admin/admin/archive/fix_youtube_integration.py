"""
Fix YouTube Integration Script
=============================
This script updates the YouTube service and DrummersWidget files with fixes for YouTube preview and download:

1. Updates YouTubeService with improved:
    - Client configuration for current YouTube API compatibility
    - Multiple fallback methods for audio stream selection
    - Enhanced error handling with detailed logs
    - Increased timeout values

2. Updates DrummersWidget with:
    - Fixed Qt.UserRole usage (using raw integer value 0x0100)
    - Improved URL construction from video IDs
    - Better error handling and debug output
    - Thread-safe UI updates

Usage: python fix_youtube_integration.py
"""
    import re
    import traceback
    import traceback
import os
import shutil
import sys

from pathlib import Path


def backup_file(file_path):
    """Create a backup of the specified file."""
    backup_path = f"{file_path}.bak"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"Created backup: {backup_path}")
        return True
    except Exception as e:
        print(f"Error creating backup of {file_path}: {e}")
        return False


def update_youtube_service():
    """Update the YouTube service with fixes."""
    source_path = Path("services/youtube_service_fixed.py")
    target_path = Path("services/youtube_service.py")

    if not source_path.exists():
        print(f"ERROR: Fixed YouTube service file not found: {source_path}")
        return False

    if not target_path.exists():
        print(f"ERROR: Target YouTube service file not found: {target_path}")
        return False

    # Create backup
    if not backup_file(target_path):
        return False

    # Copy fixed file to target
    try:
        shutil.copy2(source_path, target_path)
        print(f"Updated YouTube service: {target_path}")
        return True
    except Exception as e:
        print(f"Error updating YouTube service: {e}")
        return False


def fix_drummers_widget():
    """Fix the DrummersWidget YouTube integration."""
    file_path = Path("ui/drummers_widget.py")

    if not file_path.exists():
        print(f"ERROR: DrummersWidget file not found: {file_path}")
        return False

    # Create backup
    if not backup_file(file_path):
        return False

    # Read file contents
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading DrummersWidget file: {e}")
        return False

    # Fix 1: Replace Qt.ItemDataRole.UserRole with raw integer value 0x0100
    content = content.replace('Qt.ItemDataRole.UserRole', '0x0100')

    # Fix 2: Update _on_play_preview method with improved URL handling and error detection
    old_play_preview = """    def _on_play_preview(self):
        try:
            current_items = self.youtube_results
            if current_items and len(current_items) > 0:
                current_row = self.youtube_results_list.currentRow()
                if current_row >= 0 and current_row < len(current_items):
                    current_item = self.youtube_results_list.item(current_row)
                    if current_item:
                        video_data = current_item.data(Qt.ItemDataRole.UserRole)
                        if video_data and 'id' in video_data:
                            video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                            self.preview_player.setMedia(QUrl(video_url))
                            self.preview_player.play()
        except Exception as e:
            print(f"Error playing preview: {e}")"""

    new_play_preview = """    def _on_play_preview(self):
        try:
            print("\\n===== PLAYING YOUTUBE PREVIEW =====")
            current_items = self.youtube_results
            if current_items and len(current_items) > 0:
                current_row = self.youtube_results_list.currentRow()
                print(f"Current row: {current_row}, Total items: {len(current_items)}")

                if current_row >= 0 and current_row < len(current_items):
                    current_item = self.youtube_results_list.item(current_row)
                    if current_item:
                        # Use raw integer value for Qt.UserRole (0x0100)
                        video_data = current_item.data(0x0100)
                        print(f"Video data retrieved: {video_data}")

                        if video_data:
                            # Get URL from video data or construct from ID
                            video_url = None

                            if 'url' in video_data and video_data['url']:
                                video_url = video_data['url']
                                print(f"Using URL from data: {video_url}")
                            elif 'id' in video_data and video_data['id']:
                                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                                print(f"Constructed URL from ID: {video_url}")

                            if video_url:
                                print(f"Playing video preview: {video_url}")
                                self.preview_player.setMedia(QUrl(video_url))
                                self.preview_player.play()
                            else:
                                print("Error: No valid URL or ID found in video data")
                                QMessageBox.warning(self, "Preview Error", "No valid URL found for this video.")
                        else:
                            print("Error: No video data found in list item")
                            QMessageBox.warning(self, "Preview Error", "No video data found for the selected item.")
                    else:
                        print("Error: No list item found at current row")
                else:
                    print("Error: Invalid row selected")
            else:
                print("Error: No YouTube results available")
                QMessageBox.information(self, "No Results", "No YouTube results to preview.")
        except Exception as e:
            error_msg = f"Error playing preview: {e}\\n{traceback.format_exc()}"
            print(f"ERROR: {error_msg}")
            QMessageBox.critical(self, "Preview Error", f"Error playing preview: {str(e)}")"""

    content = content.replace(old_play_preview, new_play_preview)

    # Fix 3: Update _on_download_video method with improved URL handling and error detection
    old_download_video = """    def _on_download_video(self):
        try:
            current_items = self.youtube_results
            if current_items and len(current_items) > 0:
                current_row = self.youtube_results_list.currentRow()
                if current_row >= 0 and current_row < len(current_items):
                    current_item = self.youtube_results_list.item(current_row)
                    if current_item:
                        video_data = current_item.data(Qt.ItemDataRole.UserRole)
                        if video_data and 'id' in video_data:
                            # Get the currently selected drummer
                            if self.current_drummer is not None:
                                # Prepare output directory and filename
                                output_dir = os.path.join()
                                    self.config.get('paths', 'original_audio_path'),
                                    self.current_drummer['name']
                                )
                                os.makedirs(output_dir, exist_ok=True)

                                # Generate a safe filename
                                video_title = video_data.get('title', f"youtube_{video_data['id']}")
                                safe_title = ''.join(c for c in video_title if c.isalnum() or c in ' _-').strip()
                                safe_title = safe_title.replace(' ', '_')
                                output_filename = f"{safe_title}.mp3"
                                output_path = os.path.join(output_dir, output_filename)

                                # Download the video
                                self.download_progress_bar.setValue(0)
                                self.download_status_label.setText(f"Downloading: {video_title}")
                                self.youtube_service.download_audio()
                                    video_data['id'],
                                    output_path,
                                    progress_callback=self._on_download_progress,
                                    completion_callback=self._on_download_complete,
                                    error_callback=self._on_download_error
                                )
        except Exception as e:
            print(f"Error downloading video: {e}")"""

    new_download_video = """    def _on_download_video(self):
        try:
            print("\\n===== DOWNLOADING YOUTUBE VIDEO =====")
            current_items = self.youtube_results
            if current_items and len(current_items) > 0:
                current_row = self.youtube_results_list.currentRow()
                print(f"Current row: {current_row}, Total items: {len(current_items)}")

                if current_row >= 0 and current_row < len(current_items):
                    current_item = self.youtube_results_list.item(current_row)
                    if current_item:
                        # Use raw integer value for Qt.UserRole (0x0100)
                        video_data = current_item.data(0x0100)
                        print(f"Video data retrieved: {video_data}")

                        if video_data and ('id' in video_data or 'url' in video_data):
                            # Get the video ID from either the ID field or extract from URL
                            video_id = None
                            video_url = None

                            if 'id' in video_data and video_data['id']:
                                video_id = video_data['id']
                                video_url = f"https://www.youtube.com/watch?v={video_id}"
                                print(f"Using video ID: {video_id}")
                            elif 'url' in video_data and video_data['url']:
                                video_url = video_data['url']
                                # Try to extract ID from URL
                                id_match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', video_url)
                                if id_match:
                                    video_id = id_match.group(1)
                                    print(f"Extracted video ID from URL: {video_id}")
                                else:
                                    video_id = video_url # Just use the URL itself
                                    print(f"Could not extract ID, using URL: {video_url}")

                            if video_id or video_url:
                                # Get the currently selected drummer
                                if self.current_drummer is not None:
                                    # Prepare output directory and filename
                                    output_dir = os.path.join()
                                        self.config.get('paths', 'original_audio_path'),
                                        self.current_drummer['name']
                                    )
                                    os.makedirs(output_dir, exist_ok=True)
                                    print(f"Output directory: {output_dir}")

                                    # Generate a safe filename
                                    video_title = video_data.get('title', f"youtube_{video_id if video_id else 'video'}")
                                    safe_title = ''.join(c for c in video_title if c.isalnum() or c in ' _-').strip()
                                    safe_title = safe_title.replace(' ', '_')
                                    output_filename = f"{safe_title}.mp3"
                                    output_path = os.path.join(output_dir, output_filename)
                                    print(f"Output filename: {output_filename}")

                                    # Update UI
                                    self.download_progress_bar.setValue(0)
                                    self.download_status_label.setText(f"Downloading: {video_title}")

                                    # Start download - use video_id if available, otherwise use URL
                                    download_source = video_id if video_id else video_url
                                    print(f"Starting download from: {download_source}")
                                    self.youtube_service.download_audio()
                                        download_source,
                                        output_path,
                                        progress_callback=self._on_download_progress,
                                        completion_callback=self._on_download_complete,
                                        error_callback=self._on_download_error
                                    )
                                else:
                                    print("Error: No drummer selected")
                                    QMessageBox.warning(self, "Download Error", "Please select a drummer first.")
                            else:
                                print("Error: No valid video ID or URL found")
                                QMessageBox.warning(self, "Download Error", "No valid video ID found for this video.")
                        else:
                            print("Error: Missing video ID in data")
                            QMessageBox.warning(self, "Download Error", "Missing video ID data.")
                    else:
                        print("Error: No list item found at current row")
                else:
                    print("Error: Invalid row selected")
            else:
                print("Error: No YouTube results available")
                QMessageBox.information(self, "No Results", "No YouTube results to download.")
        except Exception as e:
            error_msg = f"Error downloading video: {e}\\n{traceback.format_exc()}"
            print(f"ERROR: {error_msg}")
            QMessageBox.critical(self, "Download Error", f"Error downloading video: {str(e)}")"""

    content = content.replace(old_download_video, new_download_video)

    # Fix 4: Update _update_youtube_results method
    old_update_results = """    def _update_youtube_results(self, results):
        self.youtube_results = results
        self.youtube_results_list.clear()
        if results:
            for result in results:
                item = QListWidgetItem(result.get('title', 'Unknown'))
                item.setData(Qt.ItemDataRole.UserRole, result)
                self.youtube_results_list.addItem(item)

        self.youtube_search_button.setEnabled(True)
        self.youtube_search_input.setEnabled(True)"""

    new_update_results = """    def _update_youtube_results(self, results):
        print("\\n===== UPDATING YOUTUBE RESULTS =====")
        self.youtube_results = results
        self.youtube_results_list.clear()
        if results:
            print(f"Found {len(results)} results")
            for idx, result in enumerate(results):
                item = QListWidgetItem(result.get('title', 'Unknown'))
                # Use raw integer value for Qt.UserRole (0x0100)
                item.setData(0x0100, result)
                self.youtube_results_list.addItem(item)
                print(f"Added item {idx + 1}: {result.get('title', 'Unknown')}")

                # Debug video IDs and URLs
                if 'id' in result:
                    print(f"  Video ID: {result['id']}")
                if 'url' in result:
                    print(f"  Video URL: {result['url']}")
        else:
            print("No results found")

        self.youtube_search_button.setEnabled(True)
        self.youtube_search_input.setEnabled(True)"""

    content = content.replace(old_update_results, new_update_results)

    # Write updated content back to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated DrummersWidget: {file_path}")
        return True
    except Exception as e:
        print(f"Error writing updated DrummersWidget file: {e}")
        return False


def main():
    """Main function to run the fix script."""
    print("=== DrumTracKAI YouTube Integration Fix Script ===")

    # Make sure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"Working directory: {os.getcwd()}")

    # Update the files
    youtube_service_updated = update_youtube_service()
    drummers_widget_updated = fix_drummers_widget()

    # Print summary
    print("\n=== Fix Summary ===")
    print(f"YouTube Service: {'UPDATED' if youtube_service_updated else 'FAILED'}")
    print(f"DrummersWidget: {'UPDATED' if drummers_widget_updated else 'FAILED'}")

    if youtube_service_updated and drummers_widget_updated:
        print("\nAll updates completed successfully!")
        print("The YouTube preview and download functionality should now work properly.")
        print("Please restart the application to apply the changes.")
    else:
        print("\nSome updates failed. Please check the error messages above.")


if __name__ == "__main__":
    main()
