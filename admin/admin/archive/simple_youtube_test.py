import pytube
import pytube
import subprocess
import os
import sys
import traceback

from pytube.innertube import InnerTube

#!/usr/bin/env python3
"""
Simple YouTube Test Script
"""

try:
    print("Step 1: Importing pytube...")
    print(f"PyTube version: {pytube.__version__}")
except ImportError:
    print("PyTube not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytube"])
    print(f"Installed PyTube version: {pytube.__version__}")

# Test video URL
VIDEO_URL = "https://www.youtube.com/watch?v=qmOLtTGvsbM"  # Toto - Rosanna
OUTPUT_DIR = os.path.expanduser("~/Downloads")

def main():
    print(f"\nTesting YouTube download from: {VIDEO_URL}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Configure PyTube
    try:
        print("\nStep 2: Configuring PyTube clients...")

        # Configure clients
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

        print("PyTube clients configured")
    except Exception as e:
        print(f"Error configuring PyTube: {e}")
        traceback.print_exc()

    # Create YouTube object
    try:
        print("\nStep 3: Creating YouTube object...")
        yt = pytube.YouTube(VIDEO_URL)
        print(f"Video title: {yt.title}")
        print(f"Video author: {yt.author}")
        print(f"Video length: {yt.length} seconds")
    except Exception as e:
        print(f"Error creating YouTube object: {e}")
        traceback.print_exc()
        return

    # Try to get streams
    try:
        print("\nStep 4: Getting audio streams...")
        audio_streams = yt.streams.filter(only_audio=True)
        print(f"Found {len(audio_streams)} audio streams")

        if not audio_streams:
            print("No audio streams found, trying progressive streams...")
            audio_streams = yt.streams.filter(progressive=True)
            print(f"Found {len(audio_streams)} progressive streams")

        if not audio_streams:
            print("No streams found at all, trying any stream...")
            audio_streams = yt.streams
            print(f"Found {len(audio_streams)} total streams")

        # Print available streams
        for i, stream in enumerate(audio_streams[:5]):
            print(f"Stream {i+1}: {stream}")

        # Get best stream
        best_stream = audio_streams.first()
        if not best_stream:
            print("No streams available for download")
            return

        print(f"\nSelected stream: {best_stream}")
    except Exception as e:
        print(f"Error getting streams: {e}")
        traceback.print_exc()
        return

    # Try to download
    try:
        print("\nStep 5: Downloading...")
        output_file = best_stream.download(output_path=OUTPUT_DIR)

        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024*1024)
            print(f"\nDownload SUCCESS: {output_file}")
            print(f"File size: {file_size:.2f} MB")
        else:
            print("\nDownload FAILED: File not found")
    except Exception as e:
        print(f"\nError downloading: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
