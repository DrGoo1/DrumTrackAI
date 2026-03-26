#!/usr/bin/env python3
"""
LLVM-Safe Audio Processor for DrumTracKAI v1.1.7

This module provides a fallback-based audio processing system that avoids
LLVM crashes by gracefully handling librosa/scipy/soundfile failures.

Based on the proven working approach from the original DrumTracKAI project.
"""

import os
import sys
import logging
import numpy as np
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class LLVMSafeAudioProcessor:
    """
    LLVM-Safe Audio Processor with multiple implementation fallbacks.
    
    This class provides audio processing capabilities while avoiding LLVM crashes
    by implementing fallback methods when librosa/scipy/soundfile fail.
    """
    
    def __init__(self, use_fallback=False, sample_rate=22050):
        self.sample_rate = sample_rate
        self.use_fallback = use_fallback
        
        # Track available libraries
        self.librosa_available = False
        self.soundfile_available = False
        self.scipy_available = False
        self.wave_available = False
        
        # Set LLVM crash prevention environment variables
        self._set_llvm_safe_environment()
        
        # Initialize available libraries
        self._initialize_libraries()
    
    def _set_llvm_safe_environment(self):
        """Set environment variables to prevent LLVM crashes."""
        env_vars = {
            'OMP_NUM_THREADS': '1',
            'MKL_NUM_THREADS': '1',
            'NUMEXPR_NUM_THREADS': '1',
            'OPENBLAS_NUM_THREADS': '1',
            'VECLIB_MAXIMUM_THREADS': '1',
            'NUMBA_NUM_THREADS': '1'
        }
        
        for var, value in env_vars.items():
            if var not in os.environ:
                os.environ[var] = value
                logger.debug(f"Set {var}={value} for LLVM safety")
    
    def _initialize_libraries(self):
        """Initialize available audio processing libraries with LLVM crash protection."""
        if not self.use_fallback:
            # Try soundfile first (safer than librosa)
            try:
                import soundfile as sf
                self.sf = sf
                self.soundfile_available = True
                logger.info(" soundfile available for audio I/O")
            except Exception as e:
                logger.warning(f"soundfile not available: {e}")
            
            # Try scipy for basic signal processing
            try:
                import scipy.signal
                self.scipy = scipy
                self.scipy_available = True
                logger.info(" scipy available for signal processing")
            except Exception as e:
                logger.warning(f"scipy not available: {e}")
            
            # Try librosa last (most likely to cause LLVM crashes)
            try:
                import librosa
                self.librosa = librosa
                self.librosa_available = True
                logger.info(" librosa available for advanced audio analysis")
            except Exception as e:
                logger.warning(f"librosa not available (LLVM crash protection): {e}")
        
        # Always try to import wave as ultimate fallback
        try:
            import wave
            self.wave = wave
            self.wave_available = True
            logger.info(" wave module available as fallback")
        except Exception as e:
            logger.error(f"wave module not available: {e}")
    
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file with LLVM-safe fallbacks.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
            
        Raises:
            Exception: If all loading methods fail
        """
        file_path = str(file_path)
        
        # Method 1: soundfile (safest)
        if self.soundfile_available and not self.use_fallback:
            try:
                audio, sr = self.sf.read(file_path, dtype='float32')
                
                # Convert to mono if stereo
                if len(audio.shape) > 1:
                    audio = np.mean(audio, axis=1)
                
                # Simple resampling if needed
                if sr != self.sample_rate:
                    target_length = int(len(audio) * self.sample_rate / sr)
                    if target_length < len(audio):
                        audio = audio[:target_length]
                    else:
                        # Pad with zeros
                        padded = np.zeros(target_length)
                        padded[:len(audio)] = audio
                        audio = padded
                    sr = self.sample_rate
                
                logger.debug(f"Loaded audio with soundfile: {audio.shape}, {sr}Hz")
                return audio, sr
                
            except Exception as e:
                logger.warning(f"soundfile load failed: {e}")
        
        # Method 2: librosa (with LLVM crash protection)
        if self.librosa_available and not self.use_fallback:
            try:
                # This might cause LLVM crash, but we try with protection
                audio, sr = self.librosa.load(file_path, sr=self.sample_rate, mono=True)
                logger.debug(f"Loaded audio with librosa: {audio.shape}, {sr}Hz")
                return audio, sr
                
            except Exception as e:
                logger.warning(f"librosa load failed (LLVM crash protection): {e}")
        
        # Method 3: wave module fallback (basic but safe)
        if self.wave_available:
            try:
                with self.wave.open(file_path, 'rb') as wav_file:
                    frames = wav_file.readframes(-1)
                    sr = wav_file.getframerate()
                    channels = wav_file.getnchannels()
                    sample_width = wav_file.getsampwidth()
                    
                    # Convert bytes to numpy array
                    if sample_width == 1:
                        audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 127.5 - 1.0
                    elif sample_width == 2:
                        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
                    elif sample_width == 4:
                        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483647.0
                    else:
                        raise ValueError(f"Unsupported sample width: {sample_width}")
                    
                    # Convert to mono if stereo
                    if channels > 1:
                        audio = audio.reshape(-1, channels).mean(axis=1)
                    
                    logger.debug(f"Loaded audio with wave module: {audio.shape}, {sr}Hz")
                    return audio, sr
                    
            except Exception as e:
                logger.warning(f"wave module load failed: {e}")
        
        raise Exception(f"Failed to load audio file {file_path} with all available methods")
    
    def analyze_tempo_safe(self, audio: np.ndarray, sr: int) -> float:
        """
        Analyze tempo with LLVM-safe methods using improved beat tracking.
        
        Args:
            audio: Audio data
            sr: Sample rate
            
        Returns:
            Estimated tempo in BPM
        """
        try:
            # Method 1: librosa beat tracking with validation (if available and safe)
            if self.librosa_available and not self.use_fallback:
                try:
                    tempo, beats = self.librosa.beat.beat_track(y=audio, sr=sr, units='time')
                    
                    # Validate tempo range and beat consistency
                    if len(beats) >= 8 and 60 <= tempo <= 200:
                        # Double-check with beat intervals
                        beat_intervals = np.diff(beats)
                        if len(beat_intervals) > 0:
                            interval_tempo = 60.0 / np.median(beat_intervals)
                            
                            # If the two methods agree within 10%, use the result
                            if abs(tempo - interval_tempo) / tempo < 0.1:
                                logger.debug(f"Tempo detected with librosa beat tracking: {tempo:.1f} BPM")
                                return float(tempo)
                            else:
                                logger.warning(f"Tempo mismatch: beat_track={tempo:.1f}, intervals={interval_tempo:.1f}")
                                
                except Exception as e:
                    logger.warning(f"librosa tempo analysis failed (LLVM protection): {e}")
            
            # Method 2: Improved autocorrelation fallback
            return self._estimate_tempo_autocorr(audio, sr)
            
        except Exception as e:
            logger.error(f"All tempo analysis methods failed: {e}")
            return 120.0  # Default tempo
    
    def analyze_key_safe(self, audio: np.ndarray, sr: int) -> str:
        """
        Analyze musical key with LLVM-safe methods.
        
        Args:
            audio: Audio data
            sr: Sample rate
            
        Returns:
            Estimated key (e.g., 'C', 'F#', etc.)
        """
        try:
            # Method 1: librosa chroma analysis (if available and safe)
            if self.librosa_available and not self.use_fallback:
                try:
                    chroma = self.librosa.feature.chroma_stft(y=audio, sr=sr)
                    key_idx = np.argmax(np.mean(chroma, axis=1))
                    key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                    key = key_names[key_idx]
                    logger.debug(f"Key detected with librosa chroma: {key}")
                    return key
                except Exception as e:
                    logger.warning(f"librosa key analysis failed (LLVM protection): {e}")
            
            # Method 2: Spectral centroid-based key estimation (safer)
            if self.librosa_available:
                try:
                    stft = np.abs(self.librosa.stft(audio))
                    spectral_centroids = self.librosa.feature.spectral_centroid(S=stft, sr=sr)
                    mean_centroid = np.mean(spectral_centroids)
                    
                    if 100 <= mean_centroid <= 8000:
                        key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                        key_idx = int((mean_centroid / 1000) * 12) % 12
                        key = key_names[key_idx]
                        logger.debug(f"Key estimated from spectral centroid: {key}")
                        return key
                except Exception as e:
                    logger.warning(f"spectral centroid key analysis failed: {e}")
            
            # Method 3: Simple frequency analysis fallback
            return self._estimate_key_frequency(audio, sr)
            
        except Exception as e:
            logger.error(f"All key analysis methods failed: {e}")
            return 'C'  # Default key
    
    def _estimate_tempo_autocorr(self, audio: np.ndarray, sr: int) -> float:
        """Estimate tempo using autocorrelation (fallback method)."""
        try:
            # Simple autocorrelation-based tempo estimation
            # This is a basic implementation that doesn't require librosa
            
            # Calculate autocorrelation
            correlation = np.correlate(audio, audio, mode='full')
            correlation = correlation[len(correlation)//2:]
            
            # Find peaks in autocorrelation
            min_period = int(sr * 60 / 200)  # 200 BPM max
            max_period = int(sr * 60 / 40)   # 40 BPM min
            
            if max_period < len(correlation):
                correlation_segment = correlation[min_period:max_period]
                peak_idx = np.argmax(correlation_segment) + min_period
                tempo = 60.0 * sr / peak_idx
                
                if 40 <= tempo <= 200:
                    logger.debug(f"Tempo estimated with autocorrelation: {tempo:.1f} BPM")
                    return float(tempo)
            
            return 120.0  # Default
            
        except Exception as e:
            logger.warning(f"Autocorrelation tempo estimation failed: {e}")
            return 120.0
    
    def _estimate_key_frequency(self, audio: np.ndarray, sr: int) -> str:
        """Estimate key using frequency analysis (fallback method)."""
        try:
            # Simple FFT-based key estimation
            fft = np.fft.fft(audio)
            freqs = np.fft.fftfreq(len(fft), 1/sr)
            
            # Find dominant frequency
            magnitude = np.abs(fft)
            dominant_freq_idx = np.argmax(magnitude[:len(magnitude)//2])
            dominant_freq = abs(freqs[dominant_freq_idx])
            
            # Map frequency to musical key (very basic)
            if dominant_freq > 0:
                # A4 = 440 Hz, use this as reference
                semitones_from_a = 12 * np.log2(dominant_freq / 440.0)
                key_idx = int(semitones_from_a) % 12
                key_names = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']
                key = key_names[key_idx]
                logger.debug(f"Key estimated from dominant frequency: {key}")
                return key
            
            return 'C'  # Default
            
        except Exception as e:
            logger.warning(f"Frequency-based key estimation failed: {e}")
            return 'C'
    
    def is_safe_mode(self) -> bool:
        """Check if running in LLVM-safe mode (fallback only)."""
        return self.use_fallback or not (self.librosa_available or self.soundfile_available)
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get current audio processing capabilities."""
        return {
            'librosa_available': self.librosa_available,
            'soundfile_available': self.soundfile_available,
            'scipy_available': self.scipy_available,
            'wave_available': self.wave_available,
            'safe_mode': self.is_safe_mode()
        }
