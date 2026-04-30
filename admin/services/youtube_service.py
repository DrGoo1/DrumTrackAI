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

    def __init__(self, youtube_id, output_path, search_query=None):
        """
        Initialize the YouTube download thread.

        Args:
            youtube_id (str): The YouTube video ID or URL
            output_path (str): The path to save the downloaded audio file
        """
        super().__init__()
        self.youtube_id = youtube_id
        self.output_path = output_path
        self.search_query = search_query
        self.canceled = False
        self._progress_callback = None
        self._completion_callback = None
        self._error_callback = None

    def _resolve_alternative_url(self, ydl_opts, query: str) -> str:
        try:
            q = str(query or '').strip()
            if not q:
                return ''

            search_opts = dict(ydl_opts)
            search_opts.pop('postprocessors', None)
            search_opts.pop('progress_hooks', None)
            search_opts['noplaylist'] = True
            search_opts['extract_flat'] = True
            search_opts['skip_download'] = True
            search_opts['quiet'] = True
            search_opts['no_warnings'] = True

            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(f"ytsearch10:{q}", download=False)

            entries = (info or {}).get('entries') or []
            best = None
            best_score = -10**9

            for e in entries:
                if not isinstance(e, dict):
                    continue
                vid = str(e.get('id') or '').strip()
                title = str(e.get('title') or '').strip()
                if not vid:
                    continue
                lt = title.lower()

                score = 0
                if 'official audio' in lt:
                    score -= 50
                if 'topic' in lt:
                    score -= 15
                if 'lyrics' in lt or 'lyric' in lt:
                    score += 10
                if 'live' in lt:
                    score += 6
                if 'drum' in lt or 'drums' in lt:
                    score += 3
                if 'cover' in lt:
                    score -= 8

                dur = e.get('duration')
                try:
                    dur = int(dur) if dur is not None else None
                except Exception:
                    dur = None
                if dur is not None:
                    if dur < 60:
                        score -= 30
                    elif dur > 1200:
                        score -= 10

                if score > best_score:
                    best_score = score
                    best = e

            if not best:
                return ''

            vid = str(best.get('id') or '').strip()
            if not vid:
                return ''
            return f"https://www.youtube.com/watch?v={vid}"
        except Exception:
            return ''

    def _detect_ffmpeg_location(self, configured: str) -> str:
        try:
            cand = str(configured or '').strip()
            if cand:
                try:
                    if os.path.isdir(cand):
                        ffmpeg_exe = os.path.join(cand, 'ffmpeg.exe')
                        ffprobe_exe = os.path.join(cand, 'ffprobe.exe')
                        if os.path.exists(ffmpeg_exe):
                            return cand
                        bin_dir = os.path.join(cand, 'bin')
                        ffmpeg_exe2 = os.path.join(bin_dir, 'ffmpeg.exe')
                        ffprobe_exe2 = os.path.join(bin_dir, 'ffprobe.exe')
                        if os.path.exists(ffmpeg_exe2):
                            return bin_dir
                    else:
                        return cand
                except Exception:
                    return cand

            candidates = [
                r"E:\\ffmpeg\\bin",
                r"E:\\ffmpeg",
                r"C:\\ffmpeg\\bin",
                r"C:\\ffmpeg",
            ]
            for d in candidates:
                try:
                    ffmpeg_exe = os.path.join(d, 'ffmpeg.exe')
                    ffprobe_exe = os.path.join(d, 'ffprobe.exe')
                    if os.path.exists(ffmpeg_exe):
                        return d
                except Exception:
                    continue
            return ''
        except Exception:
            return ''

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

                # Update UI with progress (percentage may be -1 for indeterminate)
                try:
                    logger.info(f"YouTube download progress: {percentage}%")
                except Exception:
                    pass
                self.progress_updated.emit(percentage)
                try:
                    if callable(self._progress_callback):
                        self._progress_callback(percentage)
                except Exception:
                    pass
                    
            elif d['status'] == 'finished':
                try:
                    logger.info("YouTube download finished, now converting...")
                except Exception:
                    pass
                self.progress_updated.emit(95)  # Show high percentage during conversion
                try:
                    if callable(self._progress_callback):
                        self._progress_callback(95)
                except Exception:
                    pass
                
        except Exception as e:
            try:
                logger.warning(f"Error in yt-dlp progress hook: {e}")
            except Exception:
                pass

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
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'progress_hooks': [self._progress_hook],
                    'verbose': True,
                    'no_warnings': False,
                    'ignoreerrors': False,
                    'noplaylist': True,
                    'extract_flat': False,
                    'postprocessors': [],
                    'fixup': 'never',
                    # Enhanced reliability
                    'retries': 5,
                    'fragment_retries': 5,
                    'skip_unavailable_fragments': False,
                    'socket_timeout': 60,
                    'writeinfojson': False,  # Don't clutter with info files
                    'overwrites': True,
                    'nopart': True,
                }

                ffmpeg_location_cfg = str(
                    os.environ.get('DTK_YTDLP_FFMPEG_LOCATION', '')
                    or os.environ.get('DTK_FFMPEG_LOCATION', '')
                    or ''
                ).strip()
                ffmpeg_location = self._detect_ffmpeg_location(ffmpeg_location_cfg)
                if ffmpeg_location:
                    ydl_opts['ffmpeg_location'] = ffmpeg_location
                    print(f"Using ffmpeg_location: {ffmpeg_location}")

                cookies_from_browser = str(os.environ.get('DTK_YTDLP_COOKIES_FROM_BROWSER', '') or '').strip()
                if cookies_from_browser:
                    parts = [p.strip() for p in cookies_from_browser.split(':') if p.strip()]
                    if len(parts) == 1:
                        ydl_opts['cookiesfrombrowser'] = (parts[0],)
                    elif len(parts) == 2:
                        ydl_opts['cookiesfrombrowser'] = (parts[0], parts[1])
                    else:
                        ydl_opts['cookiesfrombrowser'] = (parts[0], parts[1], parts[2])

                cookies_file = str(os.environ.get('DTK_YTDLP_COOKIES_FILE', '') or '').strip()
                if cookies_file:
                    ydl_opts['cookiefile'] = cookies_file

                deno_dir = str(os.environ.get('DTK_YTDLP_DENO_DIR', '') or '').strip()
                if deno_dir and os.path.isdir(deno_dir):
                    try:
                        current_path = os.environ.get('PATH', '')
                        if deno_dir not in current_path.split(os.pathsep):
                            os.environ['PATH'] = deno_dir + os.pathsep + current_path
                    except Exception:
                        pass

                js_runtimes = str(os.environ.get('DTK_YTDLP_JS_RUNTIMES', '') or '').strip()
                if js_runtimes:
                    # Example values: "deno", "node", "bun", "quickjs"
                    runtimes = []
                    for part in js_runtimes.replace(';', ',').split(','):
                        p = part.strip()
                        if not p:
                            continue
                        runtimes.append(p)
                    ydl_opts['js_runtimes'] = {rt: {} for rt in runtimes}

                remote_components = str(os.environ.get('DTK_YTDLP_REMOTE_COMPONENTS', '') or '').strip()
                if remote_components:
                    # Example values: "ejs:npm" or "ejs:github"
                    ydl_opts['remote_components'] = remote_components
                
                # Download the audio
                print("Starting yt-dlp download...")
                try:
                    self.progress_updated.emit(-1)
                except Exception:
                    pass
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        try:
                            logger.info("yt-dlp extract_info starting (includes download + postprocess)")
                        except Exception:
                            pass
                        info = ydl.extract_info(url, download=True)
                        try:
                            logger.info("yt-dlp extract_info finished")
                        except Exception:
                            pass
                except Exception as first_e:
                    msg = str(first_e)
                    lower_msg = msg.lower()
                    is_cookie_copy_err = ('cookie database' in lower_msg and 'could not copy' in lower_msg)
                    is_dpapi_cookie_err = (
                        'failed to decrypt with dpapi' in lower_msg
                        or ('dpapi' in lower_msg and 'decrypt' in lower_msg)
                        or ('cookieloaderror' in lower_msg)
                        or ('failed to load cookies' in lower_msg)
                    )
                    is_unavailable = (
                        'video unavailable' in lower_msg
                        or 'account associated with this video has been terminated' in lower_msg
                        or 'this video is no longer available' in lower_msg
                        or 'copyright claim' in lower_msg
                        or 'uploader has not made this video available' in lower_msg
                    )

                    if is_dpapi_cookie_err and 'cookiesfrombrowser' in ydl_opts:
                        try:
                            self.error_occurred.emit(
                                "Browser cookies could not be decrypted on this machine (DPAPI). "
                                "Please use DTK_YTDLP_COOKIES_FILE (cookies.txt export) instead of DTK_YTDLP_COOKIES_FROM_BROWSER. "
                                "Retrying once without browser cookies..."
                            )
                        except Exception:
                            pass
                        print("DPAPI cookie decrypt failed; retrying without cookies-from-browser...")
                        retry_opts = dict(ydl_opts)
                        retry_opts.pop('cookiesfrombrowser', None)
                        with yt_dlp.YoutubeDL(retry_opts) as ydl:
                            info = ydl.extract_info(url, download=True)
                    if is_cookie_copy_err:
                        # Browser cookie DBs can be locked; retry with Edge, then try without browser cookies.
                        try:
                            print("Browser cookie DB locked; retrying cookies-from-browser=edge...")
                            retry_opts = dict(ydl_opts)
                            retry_opts['cookiesfrombrowser'] = ('edge',)
                            with yt_dlp.YoutubeDL(retry_opts) as ydl:
                                info = ydl.extract_info(url, download=True)
                        except Exception:
                            print("Edge cookies failed; retrying without cookies-from-browser...")
                            retry_opts = dict(ydl_opts)
                            retry_opts.pop('cookiesfrombrowser', None)
                            with yt_dlp.YoutubeDL(retry_opts) as ydl:
                                info = ydl.extract_info(url, download=True)
                    elif is_unavailable and self.search_query:
                        alt = self._resolve_alternative_url(ydl_opts, self.search_query)
                        if alt:
                            print(f"Original video unavailable; retrying with resolved URL: {alt}")
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                info = ydl.extract_info(alt, download=True)
                        else:
                            raise
                    else:
                        raise

                if not info:
                    raise Exception("No video information extracted")

                print(f"Video title: {info.get('title', 'Unknown')}")
                print(f"Duration: {info.get('duration', 'Unknown')} seconds")

                # Find the downloaded source audio file (m4a/webm/etc.)
                downloaded_src = None
                for file in os.listdir(temp_dir):
                    if file.lower().endswith(('.m4a', '.webm', '.mp4', '.opus', '.aac', '.mkv')):
                        downloaded_src = os.path.join(temp_dir, file)
                        break

                if not downloaded_src or not os.path.exists(downloaded_src):
                    raise Exception("Downloaded source audio file not found in temp directory")

                file_size = os.path.getsize(downloaded_src)
                print(f"Downloaded source file: {downloaded_src} ({file_size} bytes)")
                if file_size == 0:
                    raise Exception("Downloaded source file is empty (0 bytes)")

                # Convert to mp3 explicitly (prevents yt-dlp postprocessor hangs)
                try:
                    logger.info("Starting ffmpeg conversion to mp3...")
                except Exception:
                    pass
                try:
                    self.progress_updated.emit(95)
                except Exception:
                    pass
                try:
                    if callable(self._progress_callback):
                        self._progress_callback(95)
                except Exception:
                    pass

                if os.path.exists(self.output_path):
                    os.remove(self.output_path)

                ffmpeg_location_cfg = str(
                    os.environ.get('DTK_YTDLP_FFMPEG_LOCATION', '')
                    or os.environ.get('DTK_FFMPEG_LOCATION', '')
                    or ''
                ).strip()
                ffmpeg_location = self._detect_ffmpeg_location(ffmpeg_location_cfg)
                ffmpeg_exe = None
                if ffmpeg_location:
                    if os.path.isdir(ffmpeg_location):
                        ffmpeg_exe = os.path.join(ffmpeg_location, 'ffmpeg.exe')
                        if not os.path.exists(ffmpeg_exe):
                            ffmpeg_exe = None
                    else:
                        ffmpeg_exe = ffmpeg_location
                if not ffmpeg_exe:
                    ffmpeg_exe = 'ffmpeg'

                ffmpeg_cmd = [
                    ffmpeg_exe,
                    '-y',
                    '-nostdin',
                    '-i', downloaded_src,
                    '-vn',
                    '-acodec', 'libmp3lame',
                    '-b:a', '192k',
                    self.output_path,
                ]

                try:
                    proc = subprocess.run(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=int(os.environ.get('DTK_FFMPEG_TIMEOUT_SECONDS', '900')),
                    )
                except subprocess.TimeoutExpired:
                    raise Exception("ffmpeg conversion timed out")

                if proc.returncode != 0:
                    err = (proc.stderr or proc.stdout or '').strip()
                    raise Exception(f"ffmpeg conversion failed (code {proc.returncode}):\n{err}")

                # Verify final file
                final_size = os.path.getsize(self.output_path)
                print(f"Final file: {self.output_path} ({final_size} bytes)")

                if final_size == 0:
                    raise Exception("Final file is empty after move")

                try:
                    self.progress_updated.emit(100)
                except Exception:
                    pass

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
            base_err = str(e)
            hint = ""
            lower = base_err.lower()
            if 'cookie database' in lower and 'could not copy' in lower:
                hint = "\n\nHint: yt-dlp could not access Chrome's cookies (Chrome often locks its cookie DB)." \
                       "\n- Close all Chrome windows (and background Chrome processes) and retry, OR" \
                       "\n- Use Edge instead: set DTK_YTDLP_COOKIES_FROM_BROWSER=edge, OR" \
                       "\n- Export cookies to a file and set DTK_YTDLP_COOKIES_FILE=C:\\path\\to\\cookies.txt"
            error_msg = f"Error downloading video: {base_err}{hint}\n{error_trace}"
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
                       error_callback=None,
                       search_query=None):
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
        download_thread = YouTubeDownloadThread(youtube_id, output_path, search_query=search_query)

        try:
            download_thread._progress_callback = progress_callback
            download_thread._completion_callback = completion_callback
            download_thread._error_callback = error_callback
        except Exception:
            pass

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
