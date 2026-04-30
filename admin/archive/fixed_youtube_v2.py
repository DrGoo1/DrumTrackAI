import traceback
import subprocess
import traceback
import traceback
import traceback
import traceback
import pytube
import pytube
import pytube
import pytube
import subprocess
import subprocess
import datetime
import importlib
import os
import os
import shutil
import sys
import sys
import time
import traceback

from pytube.innertube import InnerTube

#!/usr/bin/env python3
"""
Fixed YouTube Integration for DrumTracKAI Admin App

This script directly patches the critical components of the YouTube integration
to ensure both preview and download functionality work properly.

Run this script directly to apply the fixes.
"""


# Make sure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Paths to files that need to be fixed
DRUMMERS_WIDGET_PATH = os.path.join(os.path.dirname(__file__), 'ui', 'drummers_widget.py')
YOUTUBE_SERVICE_PATH = os.path.join(os.path.dirname(__file__), 'services', 'youtube_service.py')
YOUTUBE_SEARCH_PATH = os.path.join(os.path.dirname(__file__), 'utils', 'youtube_search.py')

# Ensure pytube is installed
try:
    print(f"PyTube version: {pytube.__version__}")
except ImportError:
    print("PyTube not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytube"])
    print(f"Installed PyTube version: {pytube.__version__}")

def backup_file(file_path):
    """Create a backup of a file before modifying it"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"Created backup: {backup_path}")
        return True
    except Exception as e:
        print(f"Failed to create backup for {file_path}: {e}")
        return False

def fix_youtube_service():
    """Fix the YouTube service implementation"""
    print("\n=== Fixing YouTube Service ===")

    if not backup_file(YOUTUBE_SERVICE_PATH):
        return False

    try:
        # Read the current file
        with open(YOUTUBE_SERVICE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add key debugging to the YouTubeDownloadThread.download method
        if "def download(self):" in content:
            # Add debugging at the start of the method
            content = content.replace()
                "def download(self):",
                """def download(self):
        print("\\n===== YOUTUBE DOWNLOAD STARTED =====")
        print(f"YouTube ID/URL: {self.youtube_id}")
        print(f"Output path: {self.output_path}")"""
            )

            # Fix the YouTube object creation to use all available client types
            if "from pytube.innertube import InnerTube" in content:
                content = content.replace()
                    "from pytube.innertube import InnerTube",
                    """from pytube.innertube import InnerTube
                # Configure multiple clients for better compatibility
                InnerTube._default_clients['WEB'] = {
                    'context': {
                        'client': {
                            'clientName': 'WEB',
                            'clientVersion': '2.20240101.01.01',
                            'hl': 'en',
                            'gl': 'US',
                        }
                    },
                    'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
                }

                # Mobile client often works when others fail
                InnerTube._default_clients['ANDROID_MUSIC'] = {
                    'context': {
                        'client': {
                            'clientName': 'ANDROID_MUSIC',
                            'clientVersion': '5.16.51',
                            'hl': 'en',
                            'gl': 'US',
                        }
                    },
                    'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
                }"""
                )

            # Add more debugging during stream selection
            if "# Get best audio stream" in content:
                content = content.replace()
                    "# Get best audio stream",
                    """# Get best audio stream
                        print("Attempting to get audio streams...")
                        # Force refresh stream list
                        try:
                            yt.bypass_age_gate()
                            yt.streams._streams = []
                            yt.streams._fmt_streams = []
                        except Exception as e:
                            print(f"Stream refresh error (non-critical): {e}")"""
                )

            # Ensure socket timeout is set properly
            if "socket.setdefaulttimeout(" in content:)
                content = content.replace()
                    "socket.setdefaulttimeout(",)
                    """print("Setting socket timeout...")
            socket.setdefaulttimeout(""")
                )

            # Add debugging for download completion
            if "self.download_complete.emit(output_file)" in content:
                content = content.replace()
                    "self.download_complete.emit(output_file)",
                    """print(f"\\n===== YOUTUBE DOWNLOAD COMPLETED =====\\nFile: {output_file}")
                            self.download_complete.emit(output_file)"""
                )

            # Improve error handling
            if "self.download_error.emit(error_msg)" in content:
                content = content.replace()
                    "self.download_error.emit(error_msg)",
                    """print(f"\\n===== YOUTUBE DOWNLOAD ERROR =====\\n{error_msg}")
                    self.download_error.emit(error_msg)"""
                )

        # Write the updated content
        with open(YOUTUBE_SERVICE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

        print("YouTube Service fixed successfully!")
        return True

    except Exception as e:
        print(f"Failed to fix YouTube Service: {e}")
        traceback.print_exc()
        return False

def fix_drummers_widget():
    """Fix the DrummersWidget YouTube functionality"""
    print("\n=== Fixing DrummersWidget ===")

    if not backup_file(DRUMMERS_WIDGET_PATH):
        return False

    try:
        # Read the current file
        with open(DRUMMERS_WIDGET_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # Fix the _update_youtube_results method to correctly store data
        if "def _update_youtube_results(self, results):" in content:
            # Find the method content
            start_idx = content.find("def _update_youtube_results(self, results):")
            end_idx = content.find("def ", start_idx + 1)
            if end_idx == -1:
                end_idx = len(content)

            method_content = content[start_idx:end_idx]

            # Fix the method to ensure correct data storage
            fixed_method = """def _update_youtube_results(self, results):
        # Update YouTube search results in UI
        try:
            print("\\n===== UPDATING YOUTUBE RESULTS =====")
            self.youtube_results = results
            self.youtube_results_list.clear()

            if not results:
                print("No results to display")
                self.youtube_results_list.addItem("No results found")
                return

            print(f"Displaying {len(results)} YouTube results")
            for i, result in enumerate(results):
                item = QListWidgetItem(result.get("title", "Unknown"))
                # Store data using direct integer value for Qt.UserRole
                item.setData(0x0100, result) # 0x0100 is the raw integer value of Qt.UserRole
                print(f"Item {i}: {result.get('title')} - ID: {result.get('id')}")
                self.youtube_results_list.addItem(item)

            # Select the first result
            self.youtube_results_list.setCurrentRow(0)
            self._update_button_states()
            print("===== YOUTUBE RESULTS UPDATED =====\\n")

        except Exception as e:
            print(f"Error updating YouTube results: {e}")
            logger.error(f"Error updating YouTube results: {e}")
            traceback.print_exc()
"""

            # Replace the method in the content
            content = content[:start_idx] + fixed_method + content[end_idx:]

        # Fix the _on_play_preview method
        if "def _on_play_preview(self):" in content:
            # Find the method content
            start_idx = content.find("def _on_play_preview(self):")
            end_idx = content.find("def ", start_idx + 1)
            if end_idx == -1:
                end_idx = len(content)

            method_content = content[start_idx:end_idx]

            # Fix the method
            fixed_method = """def _on_play_preview(self):
        # Play a preview of the selected YouTube video
        try:
            print("\\n===== PLAY PREVIEW TRIGGERED =====")
            current_items = self.youtube_results_list.selectedItems()
            if not current_items:
                print("No items selected in YouTube results list")
                QMessageBox.warning(self, "Preview Error", "Please select a video to preview")
                return

            # Try to get data using direct integer value for Qt.UserRole
            video_data = current_items[0].data(0x0100)
            print(f"Video data type: {type(video_data)}")
            print(f"Video data: {video_data}")

            if not video_data or not isinstance(video_data, dict):
                print("Invalid video data")
                QMessageBox.warning(self, "Preview Error", "Invalid video data")
                return

            video_url = None
            # Try to get URL from video data
            if "url" in video_data and video_data["url"]:
                video_url = video_data["url"]
                print(f"Using URL from data: {video_url}")
            # If no URL, try to construct from ID
            elif "id" in video_data and video_data["id"]:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                print(f"Constructed URL from ID: {video_url}")

            if not video_url:
                print("No URL found in video data")
                QMessageBox.warning(self, "Preview Error", "No URL found for this video")
                return

            # Open the URL in the default browser
            print(f"Opening URL: {video_url}")
            QDesktopServices.openUrl(QUrl(video_url))
            print("URL opened in browser")
            print("===== PLAY PREVIEW COMPLETE =====\\n")

        except Exception as e:
            print(f"Error playing preview: {e}")
            logger.error(f"Error playing preview: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Preview Error", f"Failed to play preview: {str(e)}")
"""

            # Replace the method in the content
            content = content[:start_idx] + fixed_method + content[end_idx:]

        # Fix the _on_download_video method
        if "def _on_download_video(self):" in content:
            # Find the method content
            start_idx = content.find("def _on_download_video(self):")
            end_idx = content.find("def ", start_idx + 1)
            if end_idx == -1:
                end_idx = len(content)

            method_content = content[start_idx:end_idx]

            # Fix the method to handle downloading
            fixed_method = """def _on_download_video(self):
        # Handle YouTube download button click
        try:
            print("\\n===== DOWNLOAD VIDEO TRIGGERED =====")
            current_items = self.youtube_results_list.selectedItems()
            if not current_items:
                print("No items selected in YouTube results list")
                QMessageBox.warning(self, "Download Error", "Please select a video to download")
                return

            # Try to get data using direct integer value for Qt.UserRole
            video_data = current_items[0].data(0x0100)
            print(f"Video data type: {type(video_data)}")
            print(f"Video data: {video_data}")

            if not video_data or not isinstance(video_data, dict):
                print("Invalid video data type")
                QMessageBox.warning(self, "Download Error", "Invalid video data")
                return

            # Make sure we have either URL or ID
            video_url = None
            if "url" in video_data and video_data["url"]:
                video_url = video_data["url"]
                print(f"Using URL from data: {video_url}")
            elif "id" in video_data and video_data["id"]:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                print(f"Constructed URL from ID: {video_url}")

            if not video_url:
                print("No URL found in video data")
                QMessageBox.warning(self, "Download Error", "No URL found for this video")
                return

            print(f"Using video URL: {video_url}")

            # If we have a current song selected, use its title
            song_title = None
            if self.current_song:
                song_title = self.current_song.get("title")
                print(f"Using current song title: {song_title}")

            # Otherwise use the video title
            if not song_title:
                song_title = video_data.get("title", "Unknown")
                print(f"Using video title: {song_title}")

            # Create output filename
            filename = None
            if self.current_drummer:
                filename = f"{self.current_drummer['id']}_{self._sanitize_filename(song_title)}.mp3"

            # If no drummer context, use video ID
            if not filename:
                video_id = video_data.get('id', 'unknown')
                filename = f"{video_id}_{self._sanitize_filename(song_title)}.mp3"

            output_path = os.path.join(self.download_path, filename)
            print(f"Output path: {output_path}")

            # Reset progress bar
            self.download_progress.setValue(0)
            self.download_progress.setMaximum(100)

            print(f"Starting download from URL: {video_url}")

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
                print("Download started successfully")

            except Exception as e:
                print(f"Error starting download: {e}")
                logger.error(f"Error starting download: {e}")
                traceback.print_exc()
                QMessageBox.critical(self, "Download Error", f"Failed to start download: {str(e)}")

        except Exception as e:
            print(f"Error downloading video: {e}")
            logger.error(f"Error downloading video: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Download Error", f"Failed to download: {str(e)}")

        print("===== DOWNLOAD VIDEO REQUEST COMPLETE =====\\n")
"""

            # Replace the method in the content
            content = content[:start_idx] + fixed_method + content[end_idx:]

        # Write the updated content
        with open(DRUMMERS_WIDGET_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

        print("DrummersWidget fixed successfully!")
        return True

    except Exception as e:
        print(f"Failed to fix DrummersWidget: {e}")
        traceback.print_exc()
        return False

def create_direct_youtube_tester():
    """Create a direct YouTube tester tool"""
    print("\n=== Creating Direct YouTube Tester ===")

    tester_path = os.path.join(os.path.dirname(__file__), 'direct_youtube_tester.py')

    try:
        with open(tester_path, 'w', encoding='utf-8') as f:
            f.write('''#!/usr/bin/env python3)
""":
Direct YouTube Tester for DrumTracKAI

This tool directly tests YouTube video functionality outside of the main app.
"""


# Make sure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import PyTube
try:
    print(f"PyTube version: {pytube.__version__}")
except ImportError:
    print("PyTube not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytube"])
    print(f"Installed PyTube version: {pytube.__version__}")

def configure_pytube():
    """Configure PyTube with multiple client types"""
    try:

        # Web client
        InnerTube._default_clients['WEB'] = {
            'context': {
                'client': {
                    'clientName': 'WEB',
                    'clientVersion': '2.20240101.01.01',
                    'hl': 'en',
                    'gl': 'US',
                }
            },
            'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
        }

        # Android client
        InnerTube._default_clients['ANDROID'] = {
            'context': {
                'client': {
                    'clientName': 'ANDROID',
                    'clientVersion': '17.31.35',
                    'hl': 'en',
                    'gl': 'US',
                }
            },
            'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
        }

        # iOS client
        InnerTube._default_clients['IOS'] = {
            'context': {
                'client': {
                    'clientName': 'IOS',
                    'clientVersion': '17.33.2',
                    'hl': 'en',
                    'gl': 'US',
                }
            },
            'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
        }

        # Music client
        InnerTube._default_clients['ANDROID_MUSIC'] = {
            'context': {
                'client': {
                    'clientName': 'ANDROID_MUSIC',
                    'clientVersion': '5.16.51',
                    'hl': 'en',
                    'gl': 'US',
                }
            },
            'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
        }

        print("PyTube clients configured successfully")
        return True

    except Exception as e:
        print(f"Error configuring PyTube: {e}")
        return False

def download_video(video_id, output_path):
    """Download a video directly using PyTube"""
    print(f"Downloading video: {video_id}")

    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"URL: {url}")

    # Configure PyTube
    configure_pytube()

    try:
        # Create YouTube object
        yt = pytube.YouTube(url)

        # Print video info
        print(f"Title: {yt.title}")
        print(f"Author: {yt.author}")
        print(f"Length: {yt.length} seconds")

        # Try to get an audio stream
        print("Searching for audio stream...")
        audio_stream = None

        # Method 1: Filter by only_audio
        try:
            print("Method 1: Filter by only_audio")
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if audio_stream:
                print(f"Found audio stream with method 1: {audio_stream}")
        except Exception as e1:
            print(f"Method 1 failed: {e1}")

        # Method 2: Manual filter
        if not audio_stream:
            try:
                print("Method 2: Manual filter")
                all_streams = yt.streams.all()
                audio_streams = [s for s in all_streams if hasattr(s, 'includes_audio_track') and s.includes_audio_track]
                if audio_streams:
                    audio_stream = audio_streams[0]
                    print(f"Found audio stream with method 2: {audio_stream}")
            except Exception as e2:
                print(f"Method 2 failed: {e2}")

        # Method 3: Progressive streams
        if not audio_stream:
            try:
                print("Method 3: Progressive streams")
                prog_streams = yt.streams.filter(progressive=True)
                if prog_streams:
                    audio_stream = prog_streams.first()
                    print(f"Found stream with method 3: {audio_stream}")
            except Exception as e3:
                print(f"Method 3 failed: {e3}")

        # Method 4: Any stream
        if not audio_stream:
            try:
                print("Method 4: Any stream")
                audio_stream = yt.streams.first()
                if audio_stream:
                    print(f"Found stream with method 4: {audio_stream}")
            except Exception as e4:
                print(f"Method 4 failed: {e4}")

        # If we got a stream, try to download it
        if audio_stream:
            print(f"Starting download of stream: {audio_stream}")

            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Remove existing file if it exists
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    print(f"Removed existing file: {output_path}")
                except Exception as e:
                    print(f"Failed to remove existing file: {e}")

            # Start download
            print(f"Downloading to: {output_path}")
            output_file = audio_stream.download()
                output_path=os.path.dirname(output_path),
                filename=os.path.basename(output_path)
            )

            # Check result
            if os.path.exists(output_file):
                print(f"Download successful! File: {output_file}")
                return output_file
            else:
                print("Download failed - file not found")
                return None
        else:
            print("No stream found")
            return None

    except Exception as e:
        print(f"Error downloading: {e}")
        traceback.print_exc()
        return None

def main():
    # Test video ID (Toto - Rosanna)
    video_id = "qmOLtTGvsbM"

    # Output directory in user's Downloads folder
    output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    output_path = os.path.join(output_dir, f"{video_id}_test.mp3")

    # Download the video
    result = download_video(video_id, output_path)

    if result:
        print(f"\\nSUCCESS: Downloaded to {result}")

        # Try to open it
        try:
            print(f"Attempting to open the file...")
            if sys.platform.startswith('win'):
                os.startfile(result)
            elif sys.platform == 'darwin': # macOS
                subprocess.call(['open', result])
            else: # Linux
                subprocess.call(['xdg-open', result])
            print("File opened!")
        except Exception as e:
            print(f"Error opening file: {e}")
    else:
        print("\\nFAILURE: Download failed")

if __name__ == "__main__":
    main()
''')

        print(f"Created Direct YouTube Tester at: {tester_path}")
        return True
    except Exception as e:
        print(f"Failed to create Direct YouTube Tester: {e}")
        return False

def main():
    """Apply all the fixes"""
    print("=== DrumTracKAI YouTube Fix Script ===\n")

    # Fix YouTube service
    if not fix_youtube_service():
        print("Failed to fix YouTube service. Aborting.")
        return

    # Fix DrummersWidget
    if not fix_drummers_widget():
        print("Failed to fix DrummersWidget. Aborting.")
        return

    # Create direct YouTube tester
    create_direct_youtube_tester()

    print("\n=== All fixes applied successfully! ===")
    print(""")
To test the YouTube functionality:
1. Run the main application and try the Preview and Download buttons
2. Alternatively, run the direct_youtube_tester.py script to test PyTube directly

If you encounter any issues, please check the console output for detailed error messages.
""")

if __name__ == "__main__":
    main()
