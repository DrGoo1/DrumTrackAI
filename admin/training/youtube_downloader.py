"""
YouTube Downloader for Training Data
Downloads drum performances from YouTube for AI training
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    logger.warning("yt-dlp not available - install with: pip install yt-dlp")
    YT_DLP_AVAILABLE = False


class YouTubeDrumDownloader:
    """
    Download drum performances from YouTube for training
    
    Features:
    - Audio-only downloads (faster, smaller)
    - Automatic metadata extraction (drummer, style)
    - Integration with training pipeline
    """
    
    def __init__(self, download_dir: Path = None):
        if not YT_DLP_AVAILABLE:
            raise ImportError("yt-dlp not installed. Run: pip install yt-dlp")
        
        self.download_dir = download_dir or Path("admin/data/youtube_downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata file to track downloads
        self.metadata_file = self.download_dir / "download_metadata.json"
        self.metadata = self._load_metadata()
        
        logger.info(f"YouTube Downloader initialized: {self.download_dir}")
    
    def _load_metadata(self) -> Dict:
        """Load download metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                return json.load(f)
        return {'downloads': []}
    
    def _save_metadata(self):
        """Save download metadata"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def download_video(self, 
                      url: str,
                      drummer_name: str = None,
                      style: str = None,
                      extract_audio_only: bool = True) -> Optional[Path]:
        """
        Download a YouTube video/audio
        
        Args:
            url: YouTube video URL
            drummer_name: Name of drummer (e.g., "Jeff Porcaro")
            style: Drum style (e.g., "rock", "jazz", "funk")
            extract_audio_only: Download audio only (faster, smaller)
        
        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best' if extract_audio_only else 'best',
                'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                }] if extract_audio_only else []
            }
            
            # Download
            logger.info(f"Downloading from YouTube: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info
                info = ydl.extract_info(url, download=True)
                
                # Get downloaded file path
                if extract_audio_only:
                    filename = ydl.prepare_filename(info)
                    # Replace extension with .wav
                    audio_file = Path(filename).with_suffix('.wav')
                else:
                    audio_file = Path(ydl.prepare_filename(info))
                
                # Save metadata
                download_metadata = {
                    'url': url,
                    'title': info.get('title', 'Unknown'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'file_path': str(audio_file),
                    'drummer_name': drummer_name or self._extract_drummer_from_title(info.get('title', '')),
                    'style': style or 'unknown',
                    'download_date': info.get('upload_date', 'unknown')
                }
                
                self.metadata['downloads'].append(download_metadata)
                self._save_metadata()
                
                logger.info(f"✅ Downloaded: {audio_file.name}")
                return audio_file
                
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def download_playlist(self,
                         playlist_url: str,
                         drummer_name: str = None,
                         style: str = None,
                         max_videos: int = None) -> List[Path]:
        """
        Download all videos from a YouTube playlist
        
        Args:
            playlist_url: YouTube playlist URL
            drummer_name: Drummer name for all videos
            style: Style for all videos
            max_videos: Maximum number of videos to download
        
        Returns:
            List of downloaded file paths
        """
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'extract_flat': True,
                'quiet': True
            }
            
            # Get playlist info
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                
                if 'entries' not in playlist_info:
                    logger.error("No videos found in playlist")
                    return []
                
                entries = playlist_info['entries']
                if max_videos:
                    entries = entries[:max_videos]
                
                logger.info(f"Downloading {len(entries)} videos from playlist...")
                
                downloaded_files = []
                for i, entry in enumerate(entries, 1):
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    logger.info(f"\n[{i}/{len(entries)}] Downloading: {entry.get('title', 'Unknown')}")
                    
                    file_path = self.download_video(video_url, drummer_name, style)
                    if file_path:
                        downloaded_files.append(file_path)
                
                logger.info(f"\n✅ Downloaded {len(downloaded_files)} videos from playlist")
                return downloaded_files
                
        except Exception as e:
            logger.error(f"Playlist download failed: {e}")
            return []
    
    def download_search_results(self,
                                search_query: str,
                                max_results: int = 10,
                                drummer_name: str = None,
                                style: str = None) -> List[Path]:
        """
        Search YouTube and download results
        
        Args:
            search_query: Search query (e.g., "Jeff Porcaro drum solo")
            max_results: Maximum results to download
            drummer_name: Drummer name
            style: Drum style
        
        Returns:
            List of downloaded file paths
        """
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'default_search': 'ytsearch',
                'quiet': True
            }
            
            # Search
            search_url = f"ytsearch{max_results}:{search_query}"
            logger.info(f"Searching YouTube: {search_query}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(search_url, download=False)
                
                if 'entries' not in search_results:
                    logger.error("No search results found")
                    return []
                
                downloaded_files = []
                for i, entry in enumerate(search_results['entries'], 1):
                    video_url = entry['url']
                    logger.info(f"\n[{i}/{max_results}] Downloading: {entry.get('title', 'Unknown')}")
                    
                    file_path = self.download_video(video_url, drummer_name, style)
                    if file_path:
                        downloaded_files.append(file_path)
                
                logger.info(f"\n✅ Downloaded {len(downloaded_files)} videos")
                return downloaded_files
                
        except Exception as e:
            logger.error(f"Search download failed: {e}")
            return []
    
    def _extract_drummer_from_title(self, title: str) -> str:
        """Try to extract drummer name from video title"""
        # Common drummer names to look for
        famous_drummers = [
            'Jeff Porcaro', 'John Bonham', 'Neil Peart', 'Dave Grohl',
            'Travis Barker', 'Danny Carey', 'Tony Williams', 'Buddy Rich',
            'Steve Gadd', 'Vinnie Colaiuta', 'Dave Weckl', 'Carter Beauford',
            'Terry Bozzio', 'Mike Portnoy', 'Stewart Copeland', 'Ginger Baker',
            'Keith Moon', 'Ringo Starr', 'Lars Ulrich', 'Joey Jordison'
        ]
        
        title_lower = title.lower()
        for drummer in famous_drummers:
            if drummer.lower() in title_lower:
                return drummer
        
        return "Unknown"
    
    def get_download_history(self) -> List[Dict]:
        """Get list of all downloaded videos"""
        return self.metadata['downloads']
    
    def get_downloaded_files(self) -> List[Path]:
        """Get list of all downloaded file paths"""
        return [Path(d['file_path']) for d in self.metadata['downloads']]


# Predefined drummer playlists and searches
FAMOUS_DRUMMER_SEARCHES = {
    'Jeff Porcaro': [
        'Jeff Porcaro drum solo',
        'Jeff Porcaro Rosanna',
        'Jeff Porcaro isolated drums',
        'Jeff Porcaro drum cam'
    ],
    'John Bonham': [
        'John Bonham drum solo',
        'John Bonham Moby Dick',
        'John Bonham isolated drums',
        'Bonham drum sound'
    ],
    'Neil Peart': [
        'Neil Peart drum solo',
        'Neil Peart YYZ drums',
        'Neil Peart isolated tracks',
        'Rush drum cam'
    ],
    'Dave Grohl': [
        'Dave Grohl drum cam',
        'Dave Grohl drum solo',
        'Foo Fighters drum isolated',
        'Nirvana drum tracks'
    ],
    'Steve Gadd': [
        'Steve Gadd drum solo',
        'Steve Gadd Aja drums',
        'Steve Gadd clinic',
        'Steve Gadd isolated drums'
    ]
}


def batch_download_drummer(downloader: YouTubeDrumDownloader, 
                          drummer_name: str,
                          style: str = 'rock',
                          max_per_search: int = 3) -> List[Path]:
    """
    Download multiple videos of a specific drummer
    
    Args:
        downloader: YouTubeDrumDownloader instance
        drummer_name: Drummer name (must be in FAMOUS_DRUMMER_SEARCHES)
        style: Drum style
        max_per_search: Max videos per search query
    
    Returns:
        List of downloaded files
    """
    if drummer_name not in FAMOUS_DRUMMER_SEARCHES:
        logger.warning(f"No predefined searches for {drummer_name}")
        return []
    
    searches = FAMOUS_DRUMMER_SEARCHES[drummer_name]
    all_files = []
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Batch downloading: {drummer_name}")
    logger.info(f"{'='*70}")
    
    for search in searches:
        logger.info(f"\nSearching: {search}")
        files = downloader.download_search_results(
            search,
            max_results=max_per_search,
            drummer_name=drummer_name,
            style=style
        )
        all_files.extend(files)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"✅ Total downloaded for {drummer_name}: {len(all_files)} files")
    logger.info(f"{'='*70}")
    
    return all_files


def test_youtube_downloader():
    """Test the YouTube downloader"""
    print("🧪 Testing YouTube Downloader")
    print("=" * 60)
    
    if not YT_DLP_AVAILABLE:
        print("❌ yt-dlp not installed")
        print("\nInstall with: pip install yt-dlp")
        return
    
    downloader = YouTubeDrumDownloader()
    print(f"✅ Downloader initialized")
    print(f"   Download directory: {downloader.download_dir}")
    
    # Show available drummers
    print("\n📋 Available drummer searches:")
    for drummer in FAMOUS_DRUMMER_SEARCHES.keys():
        print(f"   - {drummer}")
    
    print("\n" + "=" * 60)
    print("Ready to download drum performances from YouTube!")
    print("\nExample usage:")
    print("  downloader.download_video('https://youtube.com/watch?v=...')")
    print("  downloader.download_search_results('Jeff Porcaro drum solo', max_results=5)")
    print("  batch_download_drummer(downloader, 'Jeff Porcaro', style='rock')")


if __name__ == "__main__":
    test_youtube_downloader()
