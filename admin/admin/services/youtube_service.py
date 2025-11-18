"""
YouTube Download Service - FIXED VERSION
========================================
Service for downloading audio from YouTube videos using yt-dlp.
Provides a thread-safe implementation with progress updates.
FIXED: Proper file handling and temp directory usage to prevent empty files.
"""
import os
import sys
import subprocess
import time
import traceback
import logging
import shutil
import threading
import tempfile
import yt_dlp
from pathlib import Path

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class YouTubeDownloadThread(QObject):
    """Thread for downloading YouTube videos as audio files using yt-dlp."""

    progress_updated = Signal(int)
    download_complete = Signal(str)
    download_error = Signal(str)

    def __init__(self, youtube_id, output_path):
        """
        Initialize the YouTube download thread.

        Args:
            youtube_id (str): The YouTube video ID or URL
            output_path (str): The path to save the downloaded audio file
        """
        super().__init__()
        self.youtube_id = youtube_id
        self.output_path = output_path
        self.canceled = False

    def _progress_hook(self, d):
        """
        Progress callback for yt-dlp.
        
        Args:
            d (dict): Progress information from yt-dlp
        """
        if self.canceled:
            raise Exception("Download canceled by user")
            
        try:
            if d['status'] == 'downloading':
                # Calculate progress
                if 'total_bytes' in d and d['total_bytes'] > 0:
                    percentage = int(d['downloaded_bytes'] / d['total_bytes'] * 100)
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                    percentage = int(d['downloaded_bytes'] / d['total_bytes_estimate'] * 100)
                else:
                    # If we can't calculate percentage, use a placeholder
                    # This might happen with some YouTube streams
                    percentage = -1
                    
                if percentage >= 0:
                    # Update UI with progress
                    print(f"Download progress: {percentage}%")
                    self.progress_updated.emit(percentage)
                    
            elif d['status'] == 'finished':
                print("Download finished, now converting...")
                self.progress_updated.emit(95)  # Show high percentage during conversion
                
        except Exception as e:
            print(f"Error in progress callback: {e}")

    def download(self):
        """Download the YouTube video as audio with enhanced error handling."""
        try:
            print("\n===== YOUTUBE DOWNLOAD STARTED =====")
            print(f"YouTube ID/URL: {self.youtube_id}")
            print(f"Output path: {self.output_path}")

            # Make sure target directory exists
            output_dir = os.path.dirname(self.output_path)
            if output_dir:  # Only create directory if path contains one
                os.makedirs(output_dir, exist_ok=True)

            # If input is just an ID, convert to full URL
            if not self.youtube_id.startswith(('http://', 'https://')):
                url = f'https://www.youtube.com/watch?v={self.youtube_id}'
            else:
                url = self.youtube_id
                
            print(f"Using URL: {url}")
            
            # Use a temporary directory for download
            temp_dir = tempfile.mkdtemp(prefix="youtube_download_")
            print(f"Temporary directory: {temp_dir}")
            
            try:
                # Enhanced yt-dlp options
                ydl_opts = {
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'progress_hooks': [self._progress_hook],
                    'verbose': True,
                    'no_warnings': False,
                    'ignoreerrors': False,
                    'noplaylist': True,
                    'extract_flat': False,
                    # Enhanced reliability
                    'retries': 5,
                    'fragment_retries': 5,
                    'skip_unavailable_fragments': False,
                    'socket_timeout': 60,
                    'writeinfojson': False,  # Don't clutter with info files
                }
                
                # Download the audio
                print("Starting yt-dlp download...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                    if not info:
                        raise Exception("No video information extracted")
                    
                    print(f"Video title: {info.get('title', 'Unknown')}")
                    print(f"Duration: {info.get('duration', 'Unknown')} seconds")
                    
                    # Find the downloaded MP3 file
                    downloaded_file = None
                    for file in os.listdir(temp_dir):
                        if file.endswith('.mp3'):
                            downloaded_file = os.path.join(temp_dir, file)
                            break
                    
                    if not downloaded_file or not os.path.exists(downloaded_file):
                        raise Exception("Downloaded MP3 file not found in temp directory")
                    
                    file_size = os.path.getsize(downloaded_file)
                    print(f"Downloaded file: {downloaded_file} ({file_size} bytes)")
                    
                    if file_size == 0:
                        raise Exception("Downloaded file is empty (0 bytes)")
                    
                    # Move to final destination
                    if os.path.exists(self.output_path):
                        os.remove(self.output_path)
                        
                    shutil.move(downloaded_file, self.output_path)
                    
                    # Verify final file
                    final_size = os.path.getsize(self.output_path)
                    print(f"Final file: {self.output_path} ({final_size} bytes)")
                    
                    if final_size == 0:
                        raise Exception("Final file is empty after move")
                    
                    print("\n===== YOUTUBE DOWNLOAD COMPLETED =====")
                    self.download_complete.emit(self.output_path)
                    
            finally:
                # Clean up temp directory
                try:
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    print(f"Failed to clean up temp directory: {e}")

        except Exception as e:
            error_trace = traceback.format_exc()
            error_msg = f"Error downloading video: {str(e)}\n{error_trace}"
            print(f"\n===== YOUTUBE DOWNLOAD ERROR =====\n{error_msg}")
            self.download_error.emit(error_msg)

    def cancel(self):
        """Cancel the download."""
        self.canceled = True


class YouTubeService:
    """Service for downloading audio from YouTube videos using yt-dlp."""

    def __init__(self):
        """Initialize the YouTube service."""
        pass

    def download_audio(self, youtube_id, output_path,
                       progress_callback=None,
                       completion_callback=None,
                       error_callback=None):
        """
        Download audio from a YouTube video.

        Args:
            youtube_id (str): The YouTube video ID or URL
            output_path (str): The path to save the downloaded audio file
            progress_callback (function): Callback function for progress updates
            completion_callback (function): Callback function for download completion
            error_callback (function): Callback function for download errors

        Returns:
            YouTubeDownloadThread: The download thread object
            threading.Thread: The thread object
        """
        # Create download thread
        download_thread = YouTubeDownloadThread(youtube_id, output_path)

        # Connect signals to callbacks if provided
        if progress_callback:
            download_thread.progress_updated.connect(progress_callback)

        if completion_callback:
            download_thread.download_complete.connect(completion_callback)

        if error_callback:
            download_thread.download_error.connect(error_callback)

        # Create and start thread
        thread = threading.Thread(target=download_thread.download)
        thread.daemon = True
        thread.start()

        # Return the download thread object so it can be canceled if needed
        return download_thread, thread
