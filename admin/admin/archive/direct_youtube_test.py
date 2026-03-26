import traceback
import traceback
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
Direct YouTube Test
This script directly tests the YouTube functionality without the UI components
to isolate PyTube and download issues.
"""


# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    print(f"PyTube version: {pytube.__version__}")
except ImportError:
    print("PyTube not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytube"])
    print(f"Installed PyTube version: {pytube.__version__}")

def print_sep(title):
    """Print a separator with title"""
    print("\n" + "="*80)
    print(f" {title} ".center(80, "="))
    print("="*80 + "\n")

def test_video_info(video_id):
    """Test fetching video info"""
    print_sep("Testing Video Info")

    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"Video URL: {url}")

    try:
        # Set up InnerTube clients
        InnerTube._default_clients['WEB'] = {
            'context': {
                'client': {
                    'clientName': 'WEB',
                    'clientVersion': '2.20240101.00.00',
                    'hl': 'en',
                    'gl': 'US',
                }
            },
            'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
        }

        # Create YouTube object
        yt = pytube.YouTube(url)

        # Print basic info
        print(f"Title: {yt.title}")
        print(f"Author: {yt.author}")
        print(f"Length: {yt.length} seconds")
        print(f"Views: {yt.views}")

        return yt

    except Exception as e:
        print(f"Error getting video info: {e}")
        traceback.print_exc()
        return None

def test_available_streams(yt):
    """Test listing available streams"""
    if not yt:
        return None

    print_sep("Testing Available Streams")

    try:
        # Method 1: Filter by only_audio
        print("Method 1: Filter by only_audio")
        try:
            audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
            if audio_streams:
                print(f"Found {len(audio_streams)} audio-only streams")
                for i, stream in enumerate(audio_streams):
                    print(f"{i+1}. {stream}")
                return audio_streams.first()
            else:
                print("No audio-only streams found")
        except Exception as e:
            print(f"Error with Method 1: {e}")

        # Method 2: Filter manually
        print("\nMethod 2: Filter manually by includes_audio_track")
        try:
            all_streams = yt.streams.all()
            audio_streams = [s for s in all_streams if hasattr(s, 'includes_audio_track')
                            and s.includes_audio_track and not s.includes_video_track]
            if audio_streams:
                print(f"Found {len(audio_streams)} audio streams manually")
                for i, stream in enumerate(audio_streams):
                    print(f"{i+1}. {stream}")
                return audio_streams[0]
            else:
                print("No audio streams found manually")
        except Exception as e:
            print(f"Error with Method 2: {e}")

        # Method 3: Progressive streams
        print("\nMethod 3: Progressive streams")
        try:
            prog_streams = yt.streams.filter(progressive=True).order_by('resolution')
            if prog_streams:
                print(f"Found {len(prog_streams)} progressive streams")
                for i, stream in enumerate(prog_streams):
                    print(f"{i+1}. {stream}")
                return prog_streams.first()
            else:
                print("No progressive streams found")
        except Exception as e:
            print(f"Error with Method 3: {e}")

        # Method 4: Any stream
        print("\nMethod 4: Any stream")
        try:
            any_stream = yt.streams.first()
            if any_stream:
                print(f"First available stream: {any_stream}")
                return any_stream
            else:
                print("No streams found at all")
        except Exception as e:
            print(f"Error with Method 4: {e}")

        return None

    except Exception as e:
        print(f"Error testing streams: {e}")
        traceback.print_exc()
        return None

def test_download(stream, output_dir):
    """Test downloading a stream"""
    if not stream:
        print("No stream to download")
        return False

    print_sep("Testing Download")

    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Get info
        print(f"Stream: {stream}")
        print(f"Output directory: {output_dir}")

        # Start download
        print("Starting download...")
        start_time = time.time()

        # Download the file
        output_file = stream.download(output_path=output_dir)

        # Check result
        duration = time.time() - start_time

        if os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"Download successful! File: {output_file}")
            print(f"Size: {size_mb:.2f} MB")
            print(f"Duration: {duration:.2f} seconds")
            return output_file
        else:
            print("Download failed - file not found")
            return False

    except Exception as e:
        print(f"Error downloading: {e}")
        traceback.print_exc()
        return False

def main():
    # Test video ID (Toto - Rosanna)
    video_id = "qmOLtTGvsbM"

    # Output directory
    output_dir = os.path.join(os.path.expanduser("~"), "Downloads", "DrumTracKAI_YT_Tests")

    # Run tests
    yt = test_video_info(video_id)
    if yt:
        stream = test_available_streams(yt)
        if stream:
            output_file = test_download(stream, output_dir)
            if output_file:
                print_sep("SUCCESS")
                print(f"Successfully downloaded to: {output_file}")
            else:
                print_sep("FAILURE")
                print("Download failed")
        else:
            print_sep("FAILURE")
            print("No streams available")
    else:
        print_sep("FAILURE")
        print("Could not get video info")

if __name__ == "__main__":
    main()
