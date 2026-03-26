import subprocess
import traceback
import pytube
import pytube
import subprocess
import os
import sys
import time

from pytube.innertube import InnerTube

#!/usr/bin/env python3
"""
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
        print(f"\nSUCCESS: Downloaded to {result}")

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
        print("\nFAILURE: Download failed")

if __name__ == "__main__":
    main()
