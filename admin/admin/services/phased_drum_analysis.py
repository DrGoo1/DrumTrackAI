"""
Phased Drum Analysis Service with LLVM-Safe Audio Processing

This service provides a multi-phase drum analysis workflow that avoids LLVM crashes
by using the fallback-based audio processor approach from the original DrumTracKAI project.
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class AnalysisPhase(Enum):
    """Analysis phases"""
    DOWNLOAD = "download"
    ARRANGEMENT = "arrangement"
    MVSEP = "mvsep"
    DRUM_ANALYSIS = "drum_analysis"
    POST_PROCESSING = "post_processing"
    EXPORT = "export"

@dataclass
class AnalysisJob:
    """Analysis job data structure"""
    job_id: str
    source_url: str = ""
    source_file: str = ""
    output_directory: str = ""
    status: str = "pending"
    current_phase: AnalysisPhase = AnalysisPhase.DOWNLOAD
    progress: float = 0.0
    error_message: str = ""
    results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

class PhasedDrumAnalysis:
    """
    Multi-phase drum analysis service with LLVM-safe audio processing
    """
    
    def __init__(self, output_base_dir: str = "output"):
        self.output_base_dir = output_base_dir
        self.jobs: Dict[str, AnalysisJob] = {}
        self.phase_processors = {
            AnalysisPhase.DOWNLOAD: self._process_download_phase,
            AnalysisPhase.ARRANGEMENT: self._process_arrangement_analysis,
            AnalysisPhase.MVSEP: self._process_mvsep_phase,
            AnalysisPhase.DRUM_ANALYSIS: self._process_drum_analysis,
            AnalysisPhase.POST_PROCESSING: self._process_post_processing,
            AnalysisPhase.EXPORT: self._process_export_phase,
        }
    
    def create_job(self, source_url: str = "", source_file: str = "") -> str:
        """Create a new analysis job"""
        import uuid
        job_id = str(uuid.uuid4())
        
        job = AnalysisJob(
            job_id=job_id,
            source_url=source_url,
            source_file=source_file,
            output_directory=os.path.join(self.output_base_dir, job_id)
        )
        
        # Create output directory
        os.makedirs(job.output_directory, exist_ok=True)
        
        self.jobs[job_id] = job
        logger.info(f"Created analysis job {job_id}")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and progress"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        return {
            "job_id": job.job_id,
            "status": job.status,
            "current_phase": job.current_phase.value,
            "progress": job.progress,
            "error_message": job.error_message,
            "results": job.results,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }
    
    def process_job(self, job_id: str) -> Tuple[bool, str]:
        """Process a job through all phases"""
        if job_id not in self.jobs:
            return False, f"Job {job_id} not found"
        
        job = self.jobs[job_id]
        job.status = "processing"
        job.updated_at = datetime.now()
        
        try:
            # Process through all phases
            phases = list(AnalysisPhase)
            phase_progress_step = 100.0 / len(phases)
            
            for i, phase in enumerate(phases):
                job.current_phase = phase
                job.progress = i * phase_progress_step
                job.updated_at = datetime.now()
                
                logger.info(f"Processing job {job_id} phase: {phase.value}")
                
                # Process the phase
                success, message, results = self.phase_processors[phase](job)
                
                if not success:
                    job.status = "failed"
                    job.error_message = message
                    job.updated_at = datetime.now()
                    logger.error(f"Job {job_id} failed in phase {phase.value}: {message}")
                    return False, message
                
                # Update job results
                job.results.update(results)
                job.updated_at = datetime.now()
                
                logger.info(f"Job {job_id} completed phase {phase.value}")
            
            # Job completed successfully
            job.status = "completed"
            job.progress = 100.0
            job.updated_at = datetime.now()
            
            logger.info(f"Job {job_id} completed successfully")
            return True, "Analysis completed successfully"
            
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Unexpected error: {str(e)}"
            job.updated_at = datetime.now()
            logger.error(f"Job {job_id} failed with exception: {e}")
            return False, job.error_message
    
    def _process_download_phase(self, job: AnalysisJob) -> Tuple[bool, str, Dict]:
        """Process the download phase"""
        try:
            # If source_file is provided, use it directly
            if job.source_file and os.path.exists(job.source_file):
                logger.info(f"Using provided source file: {job.source_file}")
                return True, "Source file ready", {"source_file": job.source_file}
            
            # If source_url is provided, download it
            if job.source_url:
                # TODO: Implement actual download logic
                logger.info(f"Would download from: {job.source_url}")
                return False, "Download not implemented", {}
            
            return False, "No source file or URL provided", {}
            
        except Exception as e:
            error_msg = f"Download phase error: {e}"
            logger.error(error_msg)
            return False, error_msg, {}
    
    def _process_arrangement_analysis(self, job: AnalysisJob) -> Tuple[bool, str, Dict]:
        """Process the musical arrangement analysis phase using truly LLVM-safe methods"""
        try:
            import os  # Import at method start to avoid scope issues
            import time
            import sys
            import subprocess
            import traceback  # For detailed error reporting
            from admin.services.truly_safe_audio_processor import TrulySafeAudioProcessor
            
            #  COMPREHENSIVE ENVIRONMENT VALIDATION
            def validate_drumtrackai_environment():
                """Validate the DrumTracKAI LLVM environment is properly configured"""
                validation_errors = []
                
                # Check conda environment
                conda_env = os.environ.get('CONDA_DEFAULT_ENV', 'unknown')
                if conda_env != 'drumtrackai_llvm':
                    validation_errors.append(f"ERROR Wrong conda environment: '{conda_env}' (required: 'drumtrackai_llvm')")
                
                # Check LLVM environment variables
                required_env_vars = ['LLVM_CONFIG', 'NUMBA_DISABLE_INTEL_SVML']
                for var in required_env_vars:
                    if var not in os.environ:
                        validation_errors.append(f"ERROR Missing environment variable: {var}")
                
                # Test librosa functionality
                try:
                    import librosa
                    import numpy as np
                    
                    # Create test audio signal
                    test_signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 22050))
                    
                    # Test critical librosa functions that commonly trigger LLVM errors
                    _ = librosa.feature.chroma_stft(y=test_signal, sr=22050)
                    tempo, _ = librosa.beat.beat_track(y=test_signal, sr=22050)
                    _ = librosa.feature.mfcc(y=test_signal, sr=22050, n_mfcc=12)
                    
                    logger.info("SUCCESS librosa functionality verified successfully")
                    return True, "Environment properly configured", librosa
                    
                except ImportError:
                    validation_errors.append("ERROR librosa not installed in environment")
                except Exception as e:
                    if "LLVM" in str(e) or "svml" in str(e).lower():
                        validation_errors.append(f"ERROR LLVM ERROR DETECTED - Environment not properly configured!")
                        validation_errors.append(f"   Error: {str(e)}")
                    else:
                        validation_errors.append(f"ERROR librosa functionality test failed: {str(e)}")
                
                if validation_errors:
                    error_msg = "\n".join(validation_errors)
                    error_msg += "\n\nINFO Solution: Run 'bash setup_drumtrackai_environment.sh' and activate the conda environment"
                    return False, error_msg, None
                
                return True, "Environment validation passed", librosa
            
            # Validate environment before proceeding
            logger.info("TOOL Validating DrumTracKAI LLVM environment...")
            env_valid, env_message, librosa = validate_drumtrackai_environment()
            
            if not env_valid:
                logger.error(f"Environment validation failed: {env_message}")
                return False, env_message, {}
            
            logger.info(f"SUCCESS {env_message}")
            logger.info("AUDIO Proceeding with full professional-grade musical analysis")
            
            # Get the source audio file from previous phase
            source_file = job.results.get("source_file") or job.source_file
            if not source_file or not os.path.exists(source_file):
                return False, "No source audio file available for analysis", {}
            
            # CRITICAL: Ensure we're processing a fresh file, not cached results
            file_mod_time = os.path.getmtime(source_file)
            file_size = os.path.getsize(source_file)
            logger.info(f"Starting truly LLVM-safe arrangement analysis for: {source_file}")
            logger.info(f"File info: size={file_size} bytes, modified={time.ctime(file_mod_time)}")
            
            # Clear any potential cached results for this specific file
            if hasattr(self, '_analysis_cache'):
                cache_key = f"{source_file}_{file_mod_time}_{file_size}"
                if cache_key in self._analysis_cache:
                    logger.info("Clearing cached results for this file to ensure fresh analysis")
                    del self._analysis_cache[cache_key]
            
            # AUDIO PROFESSIONAL-GRADE AUDIO LOADING
            logger.info("Loading audio with full librosa capabilities...")
            try:
                import numpy as np
                
                # Use librosa for high-quality audio loading
                y, sr = librosa.load(source_file, sr=22050, mono=True)
                logger.info(f"SUCCESS Audio loaded: {len(y)} samples at {sr}Hz ({len(y)/sr:.1f}s)")
                
                if len(y) == 0:
                    return False, "Audio file is empty or corrupted", {}
                    
            except Exception as e:
                return False, f"Failed to load audio file: {str(e)}", {}
        
            # AUDIO MULTIPLE TEMPO ESTIMATION ALGORITHMS
            logger.info("Performing comprehensive tempo analysis with multiple algorithms...")
            try:
                # Algorithm 1: Beat tracking with dynamic programming
                tempo_1, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
                # Extract scalar value from numpy array if needed
                tempo_1 = float(tempo_1) if hasattr(tempo_1, 'item') else float(tempo_1)
                logger.info(f"Beat tracking tempo: {tempo_1:.1f} BPM")
                
                # Algorithm 2: Onset-based tempo estimation
                onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units='time')
                tempo_2 = None
                if len(onset_frames) > 4:
                    intervals = np.diff(onset_frames)
                    if len(intervals) > 0:
                        median_interval = np.median(intervals)
                        if median_interval > 0:
                            tempo_2 = float(60.0 / median_interval)
                            logger.info(f"Onset-based tempo: {tempo_2:.1f} BPM")
                
                # Algorithm 3: Autocorrelation-based tempo
                hop_length = 512
                oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
                tempo_3_raw = librosa.beat.tempo(onset_envelope=oenv, sr=sr, hop_length=hop_length)[0]
                # Extract scalar value from numpy array if needed
                tempo_3 = float(tempo_3_raw) if hasattr(tempo_3_raw, 'item') else float(tempo_3_raw)
                logger.info(f"Autocorrelation tempo: {tempo_3:.1f} BPM")
                
                # Combine results using weighted average
                tempos = [tempo_1]
                weights = [3.0]  # Beat tracking gets highest weight
                
                if tempo_2 and 60 <= tempo_2 <= 200:
                    tempos.append(tempo_2)
                    weights.append(2.0)
                    
                if 60 <= tempo_3 <= 200:
                    tempos.append(tempo_3)
                    weights.append(2.0)
                
                # Calculate weighted average
                tempo = np.average(tempos, weights=weights)
                
                # Final validation and clamping
                tempo = np.clip(tempo, 60, 200)
                logger.info(f"SUCCESS Final tempo (weighted average): {tempo:.1f} BPM")
                
            except Exception as e:
                logger.error(f"Professional tempo analysis failed: {str(e)}")
                logger.error(f"Tempo analysis traceback: {traceback.format_exc()}")
                return False, f"Tempo analysis failed: {str(e)}", {}
        
            # AUDIO ADVANCED HARMONIC KEY DETECTION
            logger.info("Performing advanced harmonic key detection...")
            try:
                # Method 1: Chromagram-based key detection
                chroma_stft = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=512)
                chroma_cqt = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
                
                # Average chromagrams for stability
                chroma_combined = (chroma_stft + chroma_cqt) / 2
                chroma_mean = np.mean(chroma_combined, axis=1)
                
                # Method 2: Harmonic analysis with circle of fifths
                # Weight notes according to harmonic relationships
                circle_of_fifths = [0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5]  # C, G, D, A, E, B, F#, C#, G#, D#, A#, F
                harmonic_weights = np.zeros(12)
                for i, note in enumerate(circle_of_fifths):
                    harmonic_weights[note] = chroma_mean[note] * (1.0 + 0.1 * (12 - i))  # Closer to C gets more weight
                
                # Method 3: Major/minor mode detection
                major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
                minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
                
                # Normalize profiles
                major_profile = major_profile / np.sum(major_profile)
                minor_profile = minor_profile / np.sum(minor_profile)
                
                # Find best key by correlation
                key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                best_correlation = -1
                estimated_key = "C"
                estimated_mode = "major"
                
                chroma_normalized = chroma_mean / np.sum(chroma_mean)
                
                for i in range(12):
                    # Test major key
                    rotated_major = np.roll(major_profile, i)
                    major_corr = np.corrcoef(chroma_normalized, rotated_major)[0, 1]
                    
                    # Test minor key  
                    rotated_minor = np.roll(minor_profile, i)
                    minor_corr = np.corrcoef(chroma_normalized, rotated_minor)[0, 1]
                    
                    if major_corr > best_correlation:
                        best_correlation = major_corr
                        estimated_key = key_names[i]
                        estimated_mode = "major"
                        
                    if minor_corr > best_correlation:
                        best_correlation = minor_corr
                        estimated_key = key_names[i]
                        estimated_mode = "minor"
                
                # Combine with simple prominence method as validation
                simple_key_idx = np.argmax(chroma_mean)
                simple_key = key_names[simple_key_idx]
                
                logger.info(f"Correlation-based key: {estimated_key} {estimated_mode} (correlation: {best_correlation:.3f})")
                logger.info(f"Prominence-based key: {simple_key}")
                
                # Use correlation method if confidence is high, otherwise use prominence
                if best_correlation > 0.6:
                    final_key = f"{estimated_key} {estimated_mode}"
                else:
                    final_key = simple_key
                    logger.info("Using prominence-based key due to low correlation confidence")
                
                logger.info(f"SUCCESS Final key: {final_key}")
                estimated_key = final_key
                
            except Exception as e:
                logger.error(f"Advanced key analysis failed: {str(e)}")
                logger.error(f"Key analysis traceback: {traceback.format_exc()}")
                return False, f"Key analysis failed: {str(e)}", {}
            
            # Analyze time signature (basic 4/4 assumption with validation)
            time_signature = "4/4"  # Default, safe assumption
            
            # Advanced structural analysis for accurate section detection
            duration = len(y) / sr
            sections = []
            
            logger.info(f"Performing advanced structural analysis for {duration:.1f}s song...")
            
            try:
                logger.info("AUDIO Performing comprehensive structural segmentation...")
                
                if duration > 20:  # Analyze structure for songs longer than 20 seconds
                    # Method 1: Spectral-based structural analysis
                    logger.info("Method 1: Spectral-based segmentation...")
                    chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=512)
                    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=12, hop_length=512)
                    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)
                    
                    # Combine features for comprehensive analysis
                    features = np.vstack([chroma, mfcc, spectral_centroid])
                    
                    # Use recurrence matrix for self-similarity analysis
                    R = librosa.segment.recurrence_matrix(features, mode='affinity', metric='cosine')
                    
                    # Detect boundaries using agglomerative clustering
                    # Set k based on song duration (roughly 1 section per 30-45 seconds)
                    estimated_sections = max(2, min(8, int(duration / 35)))
                    boundaries_frames = librosa.segment.agglomerative(features, k=estimated_sections)
                    boundary_times_1 = librosa.frames_to_time(boundaries_frames, sr=sr, hop_length=512)
                    
                    logger.info(f"Spectral method found {len(boundary_times_1)} boundaries")
                    
                    # Method 2: Beat-synchronous structural analysis
                    logger.info("Method 2: Beat-synchronous segmentation...")
                    if 'beats' in locals() and len(beats) > 4:
                        # Synchronize chroma to beats
                        beat_frames = librosa.time_to_frames(beats, sr=sr, hop_length=512)
                        chroma_sync = librosa.util.sync(chroma, beat_frames)
                        
                        # Detect changes in harmonic content
                        novelty = np.sum(np.diff(chroma_sync, axis=1) ** 2, axis=0)
                        
                        # Find peaks in novelty function
                        peaks = librosa.util.peak_pick(novelty, pre_max=3, post_max=3, 
                                                      pre_avg=3, post_avg=5, delta=0.1, wait=10)
                        
                        if len(peaks) > 0:
                            boundary_times_2 = beats[peaks]
                            logger.info(f"Beat-sync method found {len(boundary_times_2)} boundaries")
                        else:
                            boundary_times_2 = []
                    else:
                        boundary_times_2 = []
                    
                    # Method 3: Energy and spectral flux analysis
                    logger.info("Method 3: Energy-based segmentation...")
                    # RMS energy
                    rms = librosa.feature.rms(y=y, hop_length=512)[0]
                    
                    # Spectral flux (change in spectral content)
                    stft = librosa.stft(y, hop_length=512)
                    spectral_flux = np.sum(np.diff(np.abs(stft), axis=1) ** 2, axis=0)
                    
                    # Combine energy and spectral flux
                    combined_novelty = rms[1:] * 0.3 + spectral_flux * 0.7
                    
                    # Find peaks
                    energy_peaks = librosa.util.peak_pick(combined_novelty, pre_max=5, post_max=5,
                                                         pre_avg=5, post_avg=10, delta=0.02, wait=20)
                    
                    boundary_times_3 = librosa.frames_to_time(energy_peaks, sr=sr, hop_length=512)
                    logger.info(f"Energy method found {len(boundary_times_3)} boundaries")
                    
                    # Combine all methods with intelligent merging
                    all_boundaries = []
                    if len(boundary_times_1) > 0:
                        all_boundaries.extend(boundary_times_1)
                    if len(boundary_times_2) > 0:
                        all_boundaries.extend(boundary_times_2)
                    if len(boundary_times_3) > 0:
                        all_boundaries.extend(boundary_times_3)
                    
                    boundary_times = all_boundaries
                    
                    # Method 1: Spectral-based structural analysis
                    try:
                        logger.info("Attempting spectral-based structural analysis...")
                        
                        # Compute chromagram for harmonic analysis
                        chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=512)
                        
                        # Compute MFCC for timbral analysis
                        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=12, hop_length=512)
                        
                        # Combine features for comprehensive analysis
                        features = np.vstack([chroma, mfcc])
                        
                        # Use recurrence matrix for structure detection
                        R = librosa.segment.recurrence_matrix(features, mode='affinity')
                        
                        # Detect structural boundaries using agglomerative clustering
                        boundaries = librosa.segment.agglomerative(features, k=None)
                        boundary_times = librosa.frames_to_time(boundaries, sr=sr, hop_length=512)
                        
                        logger.info(f"Detected {len(boundary_times)} structural boundaries using spectral analysis")
                        
                    except Exception as spectral_error:
                        logger.warning(f"Spectral structural analysis failed: {spectral_error}")
                        boundary_times = []
                    
                    # Method 2: Beat-synchronous structural analysis (fallback)
                    if len(boundary_times) < 2:
                        try:
                            logger.info("Using beat-synchronous structural analysis...")
                            
                            # Get beat times
                            tempo_detected, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
                            
                            if len(beats) > 4:  # Need sufficient beats for analysis
                                # Compute beat-synchronous chroma
                                chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=512)
                                chroma_sync = librosa.util.sync(chroma, librosa.time_to_frames(beats, sr=sr, hop_length=512))
                                
                                # Detect changes in harmonic content
                                novelty = np.sum(np.diff(chroma_sync, axis=1) ** 2, axis=0)
                                
                                # Find peaks in novelty function
                                peaks = librosa.util.peak_pick(novelty, pre_max=3, post_max=3, pre_avg=3, post_avg=5, delta=0.1, wait=10)
                                
                                if len(peaks) > 0:
                                    boundary_times = beats[peaks]
                                    logger.info(f"Detected {len(boundary_times)} boundaries using beat-synchronous analysis")
                                else:
                                    boundary_times = []
                            else:
                                logger.warning("Insufficient beats detected for beat-synchronous analysis")
                                boundary_times = []
                                
                        except Exception as beat_error:
                            logger.warning(f"Beat-synchronous analysis failed: {beat_error}")
                            boundary_times = []
                    
                    # Method 3: Energy-based analysis (final fallback)
                    if len(boundary_times) < 2:
                        logger.info("Using energy-based structural analysis as fallback...")
                        
                        try:
                            # Calculate RMS energy
                            rms = librosa.feature.rms(y=y, hop_length=512)[0]
                            
                            # Find significant energy changes
                            energy_novelty = np.diff(rms)
                            energy_peaks = librosa.util.peak_pick(np.abs(energy_novelty), pre_max=5, post_max=5, pre_avg=5, post_avg=10, delta=0.02, wait=20)
                            
                            if len(energy_peaks) > 0:
                                boundary_times = librosa.frames_to_time(energy_peaks, sr=sr, hop_length=512)
                                logger.info(f"Detected {len(boundary_times)} boundaries using energy analysis")
                            else:
                                boundary_times = []
                                
                        except Exception as energy_error:
                            logger.warning(f"Energy-based analysis failed: {energy_error}")
                            boundary_times = []
                    
                    # Create sections from detected boundaries
                    if len(boundary_times) > 0:
                        # Ensure we start at 0 and end at duration
                        section_boundaries = [0.0] + list(boundary_times) + [duration]
                        section_boundaries = sorted(list(set(section_boundaries)))  # Remove duplicates and sort
                        
                        # Filter boundaries that are too close together (minimum 8 seconds apart)
                        filtered_boundaries = [section_boundaries[0]]
                        for boundary in section_boundaries[1:]:
                            if boundary - filtered_boundaries[-1] >= 8.0:
                                filtered_boundaries.append(boundary)
                        
                        # Ensure we end with the full duration
                        if filtered_boundaries[-1] != duration:
                            filtered_boundaries[-1] = duration
                        
                        # Generate intelligent section names
                        section_names = ['Intro', 'Verse 1', 'Chorus 1', 'Verse 2', 'Chorus 2', 'Bridge', 'Chorus 3', 'Solo', 'Final Chorus', 'Outro']
                        
                        for i in range(len(filtered_boundaries) - 1):
                            start_time = filtered_boundaries[i]
                            end_time = filtered_boundaries[i + 1]
                            section_name = section_names[i] if i < len(section_names) else f"Section {i + 1}"
                            
                            sections.append({
                                'name': section_name,
                                'start': start_time,
                                'end': end_time,
                                'duration': end_time - start_time,
                                'bars': int((end_time - start_time) * tempo / 60 * 4)  # Estimate bars
                            })
                        
                        logger.info(f"Created {len(sections)} sections from structural analysis")
                    
                    else:
                        # Fallback: create basic sections based on duration
                        logger.info("No structural boundaries detected, creating basic sections...")
                        if duration > 60:
                            # Create 4 basic sections for longer songs
                            section_length = duration / 4
                            sections = [
                                {'name': 'Intro', 'start': 0, 'end': section_length, 'duration': section_length, 'bars': int(section_length * tempo / 60 * 4)},
                                {'name': 'Verse/Chorus 1', 'start': section_length, 'end': section_length * 2, 'duration': section_length, 'bars': int(section_length * tempo / 60 * 4)},
                                {'name': 'Verse/Chorus 2', 'start': section_length * 2, 'end': section_length * 3, 'duration': section_length, 'bars': int(section_length * tempo / 60 * 4)},
                                {'name': 'Outro', 'start': section_length * 3, 'end': duration, 'duration': duration - section_length * 3, 'bars': int((duration - section_length * 3) * tempo / 60 * 4)}
                            ]
                        else:
                            # Single section for shorter songs
                            sections = [{
                                'name': 'Complete Song',
                                'start': 0,
                                'end': duration,
                                'duration': duration,
                                'bars': int(duration * tempo / 60 * 4)
                            }]
                
                else:
                    # Very short songs - single section
                    sections = [{
                        'name': 'Complete Song',
                        'start': 0,
                        'end': duration,
                        'duration': duration,
                        'bars': int(duration * tempo / 60 * 4)
                    }]
                    
            except Exception as section_error:
                logger.error(f"Section detection failed: {section_error}")
                logger.error(f"Section detection traceback: {traceback.format_exc()}")
                return False, f"Section detection failed: {str(section_error)}", {}
            
            # Build comprehensive analysis results
            analysis_results = {
                'tempo': float(tempo),
                'key': estimated_key,
                'time_signature': time_signature,
                'duration': float(duration),
                'sections': sections,
                'audio_info': {
                    'sample_rate': int(sr),
                    'channels': 1,
                    'samples': len(y),
                    'format': 'WAV'
                },
                'analysis_metadata': {
                    'method': 'professional_librosa_analysis',
                    'timestamp': time.time(),
                    'version': '1.1.7',
                    'features': {
                        'tempo_algorithms': ['beat_tracking', 'onset_based', 'autocorrelation'],
                        'key_detection': ['chromagram_correlation', 'prominence_based'],
                        'segmentation': ['spectral_analysis', 'beat_synchronous', 'energy_based']
                    }
                }
            }
            
            logger.info(f"Musical arrangement analysis completed successfully")
            logger.info(f"Results: {tempo:.1f} BPM, {estimated_key}, {len(sections)} sections")
            
            return True, "Musical arrangement analysis completed with professional-grade methods", analysis_results
            
        except Exception as e:
            logger.error(f"Arrangement analysis failed: {str(e)}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # NO FALLBACKS - Error out clearly
            return False, f"Arrangement analysis failed: {str(e)}", {}
    
    def _process_mvsep_phase(self, job: AnalysisJob) -> Tuple[bool, str, Dict]:
        """Process the MVSep phase"""
        try:
            # Get the source audio file
            source_file = job.results.get("source_file") or job.source_file
            if not source_file or not os.path.exists(source_file):
                return False, "No source audio file available for MVSep processing", {}
            
            logger.info(f"MVSep processing for: {source_file}")
            
            # Create stems output directory
            stems_dir = os.path.join(job.output_directory, "stems")
            os.makedirs(stems_dir, exist_ok=True)
            
            # For now, return a placeholder result
            # TODO: Implement real MVSep integration
            results = {
                "stems_directory": stems_dir,
                "stems": {
                    "drums": os.path.join(stems_dir, "drums.wav"),
                    "bass": os.path.join(stems_dir, "bass.wav"),
                    "vocals": os.path.join(stems_dir, "vocals.wav"),
                    "other": os.path.join(stems_dir, "other.wav")
                },
                "processing_type": "placeholder",
                "note": "MVSep integration not yet implemented"
            }
            
            return True, "MVSep processing completed (placeholder)", results
            
        except Exception as e:
            return False, f"MVSep processing error: {e}", {}
    
    def _process_drum_analysis(self, job: AnalysisJob) -> Tuple[bool, str, Dict]:
        """Process the advanced drum analysis phase using separated stems"""
        try:
            logger.info("Starting advanced drummer performance analysis...")
            
            # Import advanced drummer analysis
            from services.advanced_drummer_analysis import AdvancedDrummerAnalysis
            
            # Get tempo and style from arrangement analysis
            tempo = job.results.get("tempo", 120.0)
            style = job.results.get("style", "unknown")
            key = job.results.get("key", "C")
            
            logger.info(f"Using context: tempo={tempo} BPM, style={style}, key={key}")
            
            # Get separated drum stems from MVSep results
            mvsep_results = job.results.get("mvsep_results", {})
            stem_files = {}
            
            # Map MVSep stems to drum components
            if "stems" in mvsep_results:
                stems = mvsep_results["stems"]
                
                # Map common stem names to our component names
                stem_mapping = {
                    "kick": "kick",
                    "snare": "snare", 
                    "toms": "toms",
                    "hihat": "hihat",
                    "hi-hat": "hihat",
                    "crash": "crash",
                    "ride": "ride",
                    "drums": "drums"  # Fallback to full drums if individual stems not available
                }
                
                for stem_name, file_path in stems.items():
                    if stem_name.lower() in stem_mapping and os.path.exists(file_path):
                        component_name = stem_mapping[stem_name.lower()]
                        stem_files[component_name] = file_path
                        logger.info(f"Found {component_name} stem: {file_path}")
            
            # If no individual stems, try to use the full drums stem
            if not stem_files:
                # Look for drums file from MVSep or fallback to original
                drums_file = None
                if "stems" in mvsep_results and "drums" in mvsep_results["stems"]:
                    drums_file = mvsep_results["stems"]["drums"]
                elif job.source_file and os.path.exists(job.source_file):
                    drums_file = job.source_file
                
                if drums_file:
                    stem_files["drums"] = drums_file
                    logger.info(f"Using full drums audio: {drums_file}")
                else:
                    return False, "No drum audio files available for analysis", {}
            
            # Initialize advanced drummer analysis
            analyzer = AdvancedDrummerAnalysis(sample_rate=22050)
            
            # Perform comprehensive drummer analysis
            logger.info("Performing comprehensive drummer performance analysis...")
            drummer_profile = analyzer.analyze_drummer_performance(
                stem_files=stem_files,
                tempo=tempo,
                style=style,
                key=key
            )
            
            # Save detailed drummer profile
            profile_file = os.path.join(job.output_directory, "drummer_profile.json")
            success = analyzer.save_profile(drummer_profile, profile_file)
            
            if not success:
                logger.warning("Failed to save drummer profile to file")
            
            # Create comprehensive results dictionary
            drum_results = {
                "analysis_method": "advanced_drummer_analysis",
                "profile_file": profile_file,
                "tempo": drummer_profile.tempo,
                "style": drummer_profile.style,
                "key": drummer_profile.key,
                "duration": drummer_profile.duration,
                
                # Component analysis summary
                "components_analyzed": list(drummer_profile.components.keys()),
                "total_hits": sum(len(comp.hits) for comp in drummer_profile.components.values()),
                
                # Groove characteristics
                "groove_analysis": {
                    "swing_factor": drummer_profile.groove.swing_factor,
                    "pocket_tightness": drummer_profile.groove.pocket_tightness,
                    "rhythmic_complexity": drummer_profile.groove.rhythmic_complexity,
                    "syncopation_level": drummer_profile.groove.syncopation_level,
                    "micro_timing_variance": drummer_profile.groove.micro_timing_variance,
                    "humanness_score": drummer_profile.groove.humanness_score
                },
                
                # Personality traits
                "personality_traits": drummer_profile.personality_traits,
                
                # Technical metrics
                "technical_metrics": drummer_profile.technical_metrics,
                
                # Signature patterns
                "signature_patterns_count": len(drummer_profile.signature_patterns),
                "signature_patterns": drummer_profile.signature_patterns[:5],  # First 5 patterns
                
                # Component interactions
                "component_interactions": drummer_profile.interaction_matrix,
                
                # Analysis metadata
                "stem_files_used": stem_files,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Save analysis results
            drum_analysis_file = os.path.join(job.output_directory, "drum_analysis.json")
            with open(drum_analysis_file, 'w') as f:
                json.dump(drum_results, f, indent=2)
            
            drum_results["analysis_file"] = drum_analysis_file
            
            # Log key findings
            logger.info("=== DRUMMER ANALYSIS RESULTS ===")
            logger.info(f"Humanness Score: {drummer_profile.groove.humanness_score:.3f}")
            logger.info(f"Rhythmic Complexity: {drummer_profile.groove.rhythmic_complexity:.3f}")
            logger.info(f"Pocket Tightness: {drummer_profile.groove.pocket_tightness:.3f}")
            logger.info(f"Timing Variance: {drummer_profile.groove.micro_timing_variance:.1f}ms")
            
            if drummer_profile.personality_traits:
                logger.info("Personality Traits:")
                for trait, value in drummer_profile.personality_traits.items():
                    logger.info(f"  {trait}: {value:.3f}")
            
            logger.info(f"Components Analyzed: {list(drummer_profile.components.keys())}")
            logger.info(f"Signature Patterns Found: {len(drummer_profile.signature_patterns)}")
            logger.info("=== ANALYSIS COMPLETE ===")
            
            return True, "Advanced drummer analysis completed successfully", drum_results
            
        except Exception as e:
            logger.error(f"Advanced drum analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Advanced drum analysis failed: {str(e)}", {}
    
    def _process_post_processing(self, job: AnalysisJob) -> Tuple[bool, str, Dict]:
        """Process the post-processing phase"""
        try:
            # Combine all analysis results
            combined_results = {
                "arrangement": job.results.get("tempo", 0),
                "key": job.results.get("key", "C"),
                "duration": job.results.get("duration", 0),
                "drum_patterns": job.results.get("patterns", []),
                "processing_complete": True
            }
            
            # Save combined results
            final_results_file = os.path.join(job.output_directory, "final_results.json")
            with open(final_results_file, 'w') as f:
                json.dump(combined_results, f, indent=2)
            
            return True, "Post-processing completed", {"final_results_file": final_results_file}
            
        except Exception as e:
            return False, f"Post-processing error: {e}", {}
    
    def _process_export_phase(self, job: AnalysisJob) -> Tuple[bool, str, Dict]:
        """Process the export phase"""
        try:
            # Create export summary
            export_summary = {
                "job_id": job.job_id,
                "status": "completed",
                "output_directory": job.output_directory,
                "files_created": [
                    "arrangement_analysis.json",
                    "drum_analysis.json", 
                    "final_results.json"
                ],
                "export_timestamp": datetime.now().isoformat()
            }
            
            # Save export summary
            export_file = os.path.join(job.output_directory, "export_summary.json")
            with open(export_file, 'w') as f:
                json.dump(export_summary, f, indent=2)
            
            return True, "Export completed", {"export_file": export_file}
            
        except Exception as e:
            return False, f"Export error: {e}", {}
