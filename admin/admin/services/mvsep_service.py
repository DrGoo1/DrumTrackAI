"""
MVSep Service - CLEAN FIXED VERSION
===================================
Orchestrates the two-step stemming process with correct model parameters:
1. HDemucs (sep_type=20, add_opt1=0) to generate multiple stereo stems
2. DrumSep Melband Roformer (sep_type=37, add_opt1=7) to separate drum components

All duplicate imports, syntax errors, and structural issues have been resolved.
"""
import asyncio
import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple, Any

import aiofiles
import aiohttp

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - GPU monitoring disabled")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - resource monitoring disabled")


class MVSepService:
    """
    Service that orchestrates the MVSep API calls for the two-step stemming process.
    Enhanced with model caching, network resilience, and resource monitoring.
    """

    # Model cache settings
    MODEL_CACHE_VERSION = "1.0.0"
    MODEL_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".drumtrackai", "model_cache")
    
    # Model details
    HDEMUCS_MODEL_ID = "20"  # Demucs4 HT model ID
    DRUMSEP_MODEL_ID = "37"  # DrumSep Melband Roformer model ID
    
    # Network settings
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0

    def __init__(self, api_key: str, base_url: str = "https://mvsep.com/api"):
        """
        Initialize the MVSep service.

        Args:
            api_key: MVSep API key for authentication
            base_url: Base URL for the MVSep API
        """
        if not api_key or api_key.strip() == "":
            raise ValueError("API key cannot be empty")

        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip('/')
        self._active_jobs = {}
        self._cancelled = False
        self._session = None

        # Initialize model caching
        self._init_model_cache()

        # Initialize system resource monitoring
        self._init_resource_monitoring()

        logger.info(f"MVSep Service initialized with base URL: {self.base_url}")

    def _init_model_cache(self):
        """Initialize the model cache directory and metadata"""
        os.makedirs(self.MODEL_CACHE_DIR, exist_ok=True)

        metadata_path = os.path.join(self.MODEL_CACHE_DIR, "metadata.json")
        if not os.path.exists(metadata_path):
            metadata = {
                "version": self.MODEL_CACHE_VERSION,
                "last_validated": None,
                "models": {}
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        else:
            # Check if we need to upgrade the cache
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            if metadata.get("version") != self.MODEL_CACHE_VERSION:
                logger.info(f"Upgrading model cache from v{metadata.get('version')} to v{self.MODEL_CACHE_VERSION}")
                self.clear_model_cache()
                metadata["version"] = self.MODEL_CACHE_VERSION
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

        logger.info(f"Model cache initialized at {self.MODEL_CACHE_DIR}")

    def _init_resource_monitoring(self):
        """Initialize system resource monitoring"""
        self._resource_stats = {
            "cpu_percent": 0,
            "memory_percent": 0,
            "gpu_utilization": None,
            "last_updated": None
        }

        # Try to detect GPU
        if TORCH_AVAILABLE:
            try:
                if torch.cuda.is_available():
                    self._resource_stats["gpu_available"] = True
                    self._resource_stats["gpu_name"] = torch.cuda.get_device_name(0)
                    logger.info(f"GPU detected: {self._resource_stats['gpu_name']}")
                else:
                    self._resource_stats["gpu_available"] = False
                    logger.info("No GPU detected")
            except Exception as e:
                self._resource_stats["gpu_available"] = False
                logger.warning(f"Error detecting GPU: {e}")
        else:
            self._resource_stats["gpu_available"] = False

    async def _get_session(self):
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10)
            timeout = aiohttp.ClientTimeout(total=300)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "DrumTracKAI MVSep Client/1.0"
                }
            )
        return self._session

    async def process_audio_file(
        self,
        input_file: str,
        output_dir: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        skip_stage_1: bool = False,
        keep_original_mix: bool = False,
        keep_drum_stem: bool = False
    ) -> Dict[str, str]:
        """
        Process an audio file through the two-step stemming process.

        Args:
            input_file: Path to the input audio file
            output_dir: Directory to save the output stems
            progress_callback: Callback function for progress updates
            skip_stage_1: Skip first stage if input is already isolated drums
            keep_original_mix: Keep a copy of the original mix
            keep_drum_stem: Keep the isolated drum stem

        Returns:
            Dict mapping stem names to file paths
        """
        self._cancelled = False

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")

        os.makedirs(output_dir, exist_ok=True)
        result_files = {}

        if progress_callback:
            progress_callback(0.01, "Initializing MVSep processing...")

        try:
            if skip_stage_1:
                logger.info("Skipping stage 1 - processing with DrumSep directly")
                if progress_callback:
                    progress_callback(0.05, "Processing with DrumSep (isolated drum track)")

                drum_components = await self._process_drumsep(input_file, output_dir, progress_callback)
                if drum_components:
                    result_files.update(drum_components)
                else:
                    logger.warning("DrumSep processing produced no results")
                    result_files['drums'] = input_file
            else:
                # Standard two-stage process
                if progress_callback:
                    progress_callback(0.05, "Starting HDemucs stem separation")

                hdemucs_stems = await self._process_hdemucs(input_file, output_dir, progress_callback)

                if self._cancelled:
                    logger.info("Processing was cancelled during HDemucs stage")
                    return {}

                if not hdemucs_stems:
                    raise Exception("HDemucs processing did not produce any stems")

                # Get the drum stem for further processing
                drum_stem = hdemucs_stems.get('drums') or hdemucs_stems.get('drum')
                if not drum_stem:
                    available_stems = list(hdemucs_stems.keys())
                    raise Exception(f"No drum stem found. Available: {available_stems}")

                if not os.path.exists(drum_stem):
                    raise Exception(f"Drum stem file not found: {drum_stem}")

                # Save other stems to results
                logger.info(f"HTDemucs processing complete. Generated {len(hdemucs_stems)} stems: {list(hdemucs_stems.keys())}")
                for stem_name, stem_path in hdemucs_stems.items():
                    if stem_name not in ['drums', 'drum']:
                        result_files[stem_name] = stem_path
                        logger.info(f"Added HTDemucs stem to results: {stem_name} -> {stem_path}")

                # Keep original mix if requested
                if keep_original_mix:
                    output_file = os.path.join(output_dir, os.path.basename(input_file))
                    shutil.copy2(input_file, output_file)
                    result_files["original_mix"] = output_file
                    logger.info(f"Kept original mix: {output_file}")

                if not self._cancelled:
                    if progress_callback:
                        progress_callback(0.5, "Stage 1 complete: processing drum components...")

                    # Keep drum stem if requested
                    if keep_drum_stem:
                        result_files["drum_stem"] = drum_stem
                        logger.info(f"Kept drum stem: {drum_stem}")

                    logger.info(f"Starting DrumSep stage 2 processing with drum stem: {drum_stem}")
                    logger.info(f"Current result_files before DrumSep: {list(result_files.keys())}")
                    
                    # Process the drum stem with DrumSep
                    drum_components = await self._process_drumsep(drum_stem, output_dir, progress_callback)
                    if drum_components:
                        logger.info(f"DrumSep returned {len(drum_components)} components: {list(drum_components.keys())}")
                        result_files.update(drum_components)
                        logger.info(f"Updated result_files after DrumSep: {list(result_files.keys())}")
                    else:
                        logger.warning("DrumSep processing produced no drum components")
                        result_files['drums'] = drum_stem
                        logger.info(f"Fallback: Using original drum stem as 'drums': {drum_stem}")

            if progress_callback:
                progress_callback(1.0, "Processing complete")

            logger.info(f"Processing complete. Generated {len(result_files)} stems: {list(result_files.keys())}")
            return result_files

        except Exception as e:
            logger.error(f"Error in MVSep processing: {str(e)}")
            if progress_callback:
                progress_callback(0.0, f"Error: {str(e)}")
            raise
        finally:
            await self._cleanup_jobs()

    async def _process_hdemucs(
        self,
        input_file: str,
        output_dir: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, str]:
        """
        Process the first stage using HDemucs to separate audio into stems.
        Uses correct model parameters: sep_type=20, add_opt1=0
        """
        try:
            if progress_callback:
                progress_callback(0.05, "Uploading to HDemucs")

            def hdemucs_progress(prog: float, msg: str):
                if progress_callback:
                    scaled_progress = 0.05 + (prog * 0.4)
                    progress_callback(scaled_progress, f"HDemucs: {msg}")

            logger.info(f"Starting HDemucs upload for: {input_file}")

            # REAL MVSep API processing - NO SIMULATION/PLACEHOLDERS
            job_id = await self._upload_to_mvsep_api(input_file, sep_type=20, add_opt1=0)
            self._active_jobs['hdemucs'] = job_id
            logger.info(f"HDemucs job started with ID: {job_id}")

            stems = await self._download_mvsep_results(
                job_id,
                output_dir,
                progress_callback=hdemucs_progress,
                job_type="HDemucs"
            )

            return stems

        except Exception as e:
            logger.error(f"Error in HDemucs processing: {str(e)}")
            raise Exception(f"HDemucs processing failed: {str(e)}")

    async def _process_drumsep(
        self,
        drum_stem: str,
        output_dir: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, str]:
        """
        Process the second stage using DrumSep to separate drum components.
        Uses correct model parameters: sep_type=37, add_opt1=7 (DrumSep MelBand Roformer 6 stems)
        Saves DrumSep stems to a dedicated subdirectory to avoid conflicts.
        """
        try:
            if progress_callback:
                progress_callback(0.5, "Uploading to DrumSep")

            def drumsep_progress(prog: float, msg: str):
                if progress_callback:
                    scaled_progress = 0.5 + (prog * 0.45)
                    progress_callback(scaled_progress, f"DrumSep: {msg}")

            # Create dedicated subdirectory for DrumSep components
            drumsep_output_dir = os.path.join(output_dir, "drumsep_components")
            os.makedirs(drumsep_output_dir, exist_ok=True)
            
            logger.info(f"Starting DrumSep upload for: {drum_stem}")
            logger.info(f"DrumSep output directory: {drumsep_output_dir}")
            logger.info(f"Original output directory: {output_dir}")

            # REAL MVSep API processing for DrumSep - NO SIMULATION/PLACEHOLDERS
            # Use correct DrumSep parameters: sep_type=37 (DrumSep base), add_opt1=7 (MelBand Roformer 6 stems)
            job_id = await self._upload_to_mvsep_api(drum_stem, sep_type=37, add_opt1=7)
            self._active_jobs['drumsep'] = job_id
            logger.info(f"DrumSep job started with ID: {job_id}")

            components = await self._download_mvsep_results(
                job_id,
                drumsep_output_dir,  # Use dedicated subdirectory
                progress_callback=drumsep_progress,
                job_type="DrumSep"
            )
            
            # Log the DrumSep results for debugging
            logger.info(f"DrumSep processing completed. Generated {len(components)} components: {list(components.keys())}")
            for comp_name, comp_path in components.items():
                logger.info(f"  DrumSep component '{comp_name}': {comp_path}")
                if os.path.exists(comp_path):
                    file_size = os.path.getsize(comp_path)
                    logger.info(f"    File exists, size: {file_size} bytes")
                else:
                    logger.error(f"    File does not exist: {comp_path}")

            return components

        except Exception as e:
            logger.error(f"Error in DrumSep processing: {str(e)}")
            raise Exception(f"DrumSep processing failed: {str(e)}")

    async def _upload_to_mvsep_api(self, file_path: str, sep_type: int, add_opt1: int = 0) -> str:
        """Upload file to real MVSep API and return job ID - NO SIMULATION"""
        if not self.api_key:
            raise Exception("MVSep API key is required for processing. Set MVSEP_API_KEY environment variable.")
        
        if not os.path.exists(file_path):
            raise Exception(f"Input file not found: {file_path}")
        
        try:
            # Real MVSep API upload using correct endpoint from documentation
            upload_url = "https://mvsep.com/api/separation/create"
            
            # Create multipart form data using correct MVSep API parameters
            data = aiohttp.FormData()
            data.add_field('sep_type', str(sep_type))
            data.add_field('add_opt1', str(add_opt1))
            data.add_field('api_token', self.api_key)  # Correct parameter name is 'api_token'
            data.add_field('output_format', '1')  # WAV format
            
            # Add audio file using correct parameter name
            with open(file_path, 'rb') as audio_file:
                data.add_field('audiofile', audio_file, filename=os.path.basename(file_path), content_type='audio/mpeg')
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(upload_url, data=data) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"MVSep API upload failed: {response.status} - {error_text}")
                        
                        result = await response.json()
                        
                        # MVSep API returns success response with hash in data
                        if result.get('success') is True:
                            # Extract hash from the response data
                            data = result.get('data', {})
                            job_hash = data.get('hash')
                            
                            if not job_hash:
                                raise Exception("MVSep API did not return a hash in the response")
                            
                            logger.info(f"Successfully uploaded to MVSep API. Hash: {job_hash}")
                            return job_hash
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            raise Exception(f"MVSep API upload failed: {error_msg}")
                        
        except Exception as e:
            logger.error(f"Error uploading to MVSep API: {str(e)}")
            raise
    
    async def _download_mvsep_results(
        self,
        job_id: str,
        output_dir: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        job_type: str = "Processing"
    ) -> Dict[str, str]:
        """Monitor real MVSep job and download results - NO SIMULATION"""
        if not self.api_key:
            raise Exception("MVSep API key is required for processing")
        
        max_wait_time = 600  # 10 minutes max wait
        check_interval = 5   # Check every 5 seconds
        max_checks = max_wait_time // check_interval
        
        try:
            # Use correct MVSep API endpoint for getting results
            status_url = "https://mvsep.com/api/separation/get"
            
            async with aiohttp.ClientSession() as session:
                # Monitor job status
                for check_num in range(max_checks):
                    if self._cancelled:
                        logger.info(f"{job_type} job {job_id} cancelled by user")
                        break
                    
                    # Check job status using correct parameters
                    async with session.get(status_url, params={'hash': job_id}) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"MVSep status check failed: {response.status} - {error_text}")
                        
                        status_data = await response.json()
                        status = status_data.get('status')
                        progress = status_data.get('progress', 0)
                        
                        if progress_callback:
                            progress_callback(progress / 100.0, f"{job_type}: {status} ({progress}%)")
                        
                        if status == 'done':
                            # Download results - MVSep API provides download links in the response
                            if progress_callback:
                                progress_callback(0.95, f"{job_type}: Downloading results")
                            
                            # Extract download links from the correct MVSep API format
                            data = status_data.get('data', {})
                            files_list = data.get('files', [])
                            
                            if not files_list:
                                logger.error(f"No files found in MVSep response. Full response: {status_data}")
                                raise Exception(f"No files found in MVSep response. Available keys: {list(status_data.keys())}")
                            
                            # Convert files list to download_links dict mapping stem type to URL
                            download_links = {}
                            for file_info in files_list:
                                stem_type = file_info.get('type', '').lower()
                                download_url = file_info.get('url')
                                
                                if stem_type and download_url:
                                    download_links[stem_type] = download_url
                                    logger.info(f"Found {stem_type} stem: {download_url}")
                            
                            if not download_links:
                                logger.error(f"No valid download URLs found in files list: {files_list}")
                                raise Exception("No valid download URLs found in MVSep files")
                            
                            logger.info(f"Successfully extracted {len(download_links)} download links: {list(download_links.keys())}")
                            return await self._download_stems_from_links(session, download_links, output_dir, job_type)
                        
                        elif status == 'failed':
                            error_msg = status_data.get('error', 'Unknown error')
                            raise Exception(f"MVSep processing failed: {error_msg}")
                    
                    await asyncio.sleep(check_interval)
                
                raise Exception(f"{job_type} job timed out after {max_wait_time} seconds")
                
        except Exception as e:
            logger.error(f"Error monitoring MVSep job {job_id}: {str(e)}")
            raise
    
    async def _download_stems_from_links(self, session: aiohttp.ClientSession, download_links: Dict, output_dir: str, job_type: str) -> Dict[str, str]:
        """Download real audio stems from MVSep API using download links - NO SIMULATION"""
        try:
            result_files = {}
            
            logger.info(f"Starting {job_type} stem downloads to: {output_dir}")
            logger.info(f"Found {len(download_links)} download links: {list(download_links.keys())}")
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Output directory created/verified: {output_dir}")
            
            # Download each stem file from the provided links
            for stem_name, download_url in download_links.items():
                if not download_url:
                    logger.warning(f"Empty download URL for {stem_name}, skipping")
                    continue
                    
                logger.info(f"[{job_type}] Downloading {stem_name} stem from: {download_url}")
                
                try:
                    async with session.get(download_url) as response:
                        if response.status != 200:
                            logger.error(f"[{job_type}] Failed to download {stem_name}: HTTP {response.status}")
                            continue
                        
                        # Get content length for logging
                        content_length = response.headers.get('content-length', 'unknown')
                        logger.info(f"[{job_type}] Response for {stem_name}: {response.status}, Content-Length: {content_length}")
                        
                        # Save the audio file with job_type prefix for DrumSep
                        if job_type == "DrumSep":
                            stem_filename = f"drumsep_{stem_name}.wav"
                        else:
                            stem_filename = f"{stem_name}.wav"
                        
                        stem_path = os.path.join(output_dir, stem_filename)
                        logger.info(f"[{job_type}] Saving {stem_name} to: {stem_path}")
                        
                        audio_content = await response.read()
                        with open(stem_path, 'wb') as f:
                            f.write(audio_content)
                        
                        # Verify file was written successfully
                        if os.path.exists(stem_path):
                            file_size = os.path.getsize(stem_path)
                            logger.info(f"[{job_type}] Successfully downloaded {stem_name} stem: {stem_path} ({file_size} bytes)")
                            result_files[stem_name] = stem_path
                        else:
                            logger.error(f"[{job_type}] File was not created: {stem_path}")
                            
                except Exception as download_error:
                    logger.error(f"[{job_type}] Error downloading {stem_name}: {str(download_error)}")
                    continue
            
            logger.info(f"[{job_type}] Download completed. Successfully downloaded {len(result_files)} stems: {list(result_files.keys())}")
            
            if not result_files:
                raise Exception(f"No {job_type} audio stems could be downloaded from MVSep")
            
            # Final verification of all downloaded files
            for stem_name, stem_path in result_files.items():
                if os.path.exists(stem_path):
                    file_size = os.path.getsize(stem_path)
                    logger.info(f"[{job_type}] Final verification - {stem_name}: {stem_path} ({file_size} bytes) ")
                else:
                    logger.error(f"[{job_type}] Final verification - {stem_name}: {stem_path} MISSING ")
            
            return result_files
                
        except Exception as e:
            logger.error(f"Error downloading stems from links: {str(e)}")
            raise

    async def cancel_processing(self):
        """Cancel any active processing jobs"""
        self._cancelled = True
        logger.info("Processing cancellation requested")
        await self._cleanup_jobs()

    async def _cleanup_jobs(self):
        """Clean up any active jobs"""
        if not self._active_jobs:
            return

        logger.info(f"Cleaning up {len(self._active_jobs)} active jobs")
        self._active_jobs.clear()

        # Close session if it exists
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def get_status(self) -> Dict:
        """Get service status"""
        cached_models = self.get_cached_model_info()
        cache_size = sum(model.get("size", 0) for model in cached_models.values())

        self._update_resource_stats()

        return {
            'api_key_set': bool(self.api_key),
            'active_jobs': len(self._active_jobs),
            'cancelled': self._cancelled,
            'cache': {
                'enabled': True,
                'version': self.MODEL_CACHE_VERSION,
                'size_mb': round(cache_size / (1024 * 1024), 2),
                'models': cached_models
            },
            'resources': self._resource_stats
        }

    def _update_resource_stats(self):
        """Update system resource statistics"""
        try:
            if PSUTIL_AVAILABLE:
                self._resource_stats["cpu_percent"] = psutil.cpu_percent(interval=0.1)
                self._resource_stats["memory_percent"] = psutil.virtual_memory().percent
            
            self._resource_stats["last_updated"] = datetime.now().isoformat()

            # Update GPU usage if available
            if self._resource_stats.get("gpu_available", False) and TORCH_AVAILABLE:
                try:
                    if torch.cuda.is_available():
                        allocated = torch.cuda.memory_allocated(0)
                        reserved = torch.cuda.memory_reserved(0)
                        total = torch.cuda.get_device_properties(0).total_memory
                        
                        self._resource_stats["gpu_memory_used_mb"] = round(allocated / (1024 * 1024), 2)
                        self._resource_stats["gpu_memory_reserved_mb"] = round(reserved / (1024 * 1024), 2)
                        self._resource_stats["gpu_memory_total_mb"] = round(total / (1024 * 1024), 2)
                        self._resource_stats["gpu_utilization"] = round((reserved / total) * 100, 2)
                except Exception as e:
                    logger.warning(f"Error updating GPU stats: {e}")
                    
        except Exception as e:
            logger.warning(f"Error updating resource stats: {e}")

    def get_cached_model_info(self) -> Dict[str, Dict]:
        """Get information about cached models"""
        try:
            metadata_path = os.path.join(self.MODEL_CACHE_DIR, "metadata.json")
            if not os.path.exists(metadata_path):
                return {}

            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            return metadata.get("models", {})
        except Exception as e:
            logger.error(f"Error getting cached model info: {e}")
            return {}

    def clear_model_cache(self):
        """Clear all cached models"""
        try:
            # Remove all files except metadata.json
            for item in os.listdir(self.MODEL_CACHE_DIR):
                if item != "metadata.json":
                    item_path = os.path.join(self.MODEL_CACHE_DIR, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)

            # Reset metadata
            metadata_path = os.path.join(self.MODEL_CACHE_DIR, "metadata.json")
            metadata = {
                "version": self.MODEL_CACHE_VERSION,
                "last_validated": datetime.now().isoformat(),
                "models": {}
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info("Model cache cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing model cache: {e}")
            return False

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup_jobs()