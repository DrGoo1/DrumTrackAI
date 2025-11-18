"""
Test script for YouTube download using yt-dlp
============================================
This script tests the yt-dlp based YouTube download functionality.
"""
import sys
import os
from services.youtube_service_ytdlp import YouTubeService

def main():
    if len(sys.argv) < 2:
        print("Usage: python ytdlp_test.py <youtube_url_or_id> [output_directory]")
        print("Example: python ytdlp_test.py dQw4w9WgXcQ ./downloads")
        return
    
    video_url_or_id = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "downloads"
    
    # Make sure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare output file path
    output_path = os.path.join(output_dir, "downloaded_audio.mp3")
    
    # Progress callback
    def on_progress(percentage):
        print(f"Download progress: {percentage}%")
    
    # Completion callback
    def on_complete(file_path):
        print(f"Download complete: {file_path}")
    
    # Error callback
    def on_error(error_msg):
        print(f"Download error: {error_msg}")
    
    # Create YouTube service and start download
    youtube_service = YouTubeService()
    download_thread, thread = youtube_service.download_audio(
        video_url_or_id,
        output_path,
        on_progress,
        on_complete,
        on_error
    )
    
    # Wait for download to complete
    print("Waiting for download to complete...")
    thread.join()
    print("Thread finished")

if __name__ == "__main__":
    main()
