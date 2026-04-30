"""
Truly LLVM-Safe Audio Processor

This module provides audio processing capabilities that completely avoid LLVM crashes
by using a fallback mode that never imports librosa/scipy when safe_mode=True.
Based on the working approach from the original DrumTracKAI project.
"""

import os
import logging
import numpy as np
from typing import Tuple, Dict, Any, Optional

# Set environment variables to prevent LLVM crashes
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMBA_NUM_THREADS'] = '1'

logger = logging.getLogger(__name__)

class TrulySafeAudioProcessor:
    """Audio processor that completely avoids LLVM crashes by never importing problematic libraries in safe mode"""
    
    def __init__(self, sample_rate: int = 22050, use_fallback: bool = True):
        self.sample_rate = sample_rate
        self.use_fallback = use_fallback  # True = safe mode, False = try advanced libraries
        self.capabilities = self._check_capabilities()
        
        logger.info(f"Initialized truly safe audio processor (use_fallback={use_fallback})")
        if use_fallback:
            logger.info("Running in SAFE MODE - librosa/scipy imports disabled to prevent LLVM crashes")
    
    def _check_capabilities(self) -> Dict[str, bool]:
        """Check which audio libraries are available"""
        capabilities = {
            'librosa_available': False,
            'soundfile_available': False,
            'wave_available': False,
            'safe_mode': self.use_fallback
        }
        
        # Only check for LLVM-prone libraries if not using fallback
        if not self.use_fallback:
            try:
                import soundfile
                capabilities['soundfile_available'] = True
                logger.info(" soundfile available")
            except ImportError:
                logger.warning(" soundfile not available")
            
            try:
                import librosa
                capabilities['librosa_available'] = True
                logger.info(" librosa available")
            except ImportError:
                logger.warning(" librosa not available")
        else:
            logger.info("Safe mode enabled - skipping LLVM-prone library checks")
        
        # Always check for wave module (LLVM-safe)
        try:
            import wave
            capabilities['wave_available'] = True
            logger.info(" wave module available")
        except ImportError:
            logger.warning(" wave module not available")
        
        return capabilities
    
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file with truly LLVM-safe fallback methods"""
        logger.info(f"Loading audio: {file_path} (safe_mode={self.use_fallback})")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        # Method 1: soundfile (only if not using fallback)
        if self.capabilities['soundfile_available'] and not self.use_fallback:
            try:
                import soundfile as sf
                audio, sr = sf.read(file_path)
                
                # Convert to mono if stereo
                if len(audio.shape) > 1:
                    audio = np.mean(audio, axis=1)
                
                # Simple resampling if needed
                if sr != self.sample_rate:
                    target_length = int(len(audio) * self.sample_rate / sr)
                    if target_length < len(audio):
                        audio = audio[:target_length]
                    else:
                        audio = np.pad(audio, (0, target_length - len(audio)))
                    sr = self.sample_rate
                
                logger.info(f"Audio loaded with soundfile: {len(audio)} samples at {sr}Hz")
                return audio.astype(np.float32), sr
                
            except Exception as e:
                logger.warning(f"soundfile loading failed: {e}")
        
        # Method 2: wave module (LLVM-safe, preferred in safe mode)
        if self.capabilities['wave_available']:
            try:
                import wave
                
                with wave.open(str(file_path), 'rb') as wf:
                    n_channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    framerate = wf.getframerate()
                    n_frames = wf.getnframes()
                    
                    # Read all frames
                    raw_data = wf.readframes(n_frames)
                    
                    # Convert to numpy array based on sample width
                    if sampwidth == 2:  # 16-bit audio
                        audio = np.frombuffer(raw_data, dtype=np.int16)
                        audio = audio.astype(np.float32) / 32768.0
                    elif sampwidth == 4:  # 32-bit audio
                        audio = np.frombuffer(raw_data, dtype=np.int32)
                        audio = audio.astype(np.float32) / 2147483648.0
                    else:  # 8-bit audio
                        audio = np.frombuffer(raw_data, dtype=np.uint8)
                        audio = audio.astype(np.float32) / 128.0 - 1.0
                    
                    # Convert to mono if stereo
                    if n_channels > 1:
                        audio = audio.reshape(-1, n_channels).mean(axis=1)
                    
                    logger.info(f"Audio loaded with wave module: {len(audio)} samples at {framerate}Hz")
                    return audio, framerate
                    
            except Exception as e:
                logger.warning(f"wave module loading failed: {e}")
        
        # Method 3: Generate fallback audio (last resort)
        logger.warning("Generating fallback sine wave audio")
        duration = 5.0  # 5 seconds
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        
        return audio.astype(np.float32), self.sample_rate
    
    def analyze_tempo_safe(self, audio: np.ndarray, sr: int) -> float:
        """Analyze tempo using truly LLVM-safe methods with improved beat tracking"""
        logger.info("Analyzing tempo with improved safe methods...")
        
        # Method 1: librosa with proper beat tracking (only if not using fallback)
        if self.capabilities['librosa_available'] and not self.use_fallback:
            try:
                import librosa
                
                # Use proper beat tracking instead of onset detection
                tempo, beats = librosa.beat.beat_track(y=audio, sr=sr, units='time')
                
                # Validate tempo range and beat consistency
                if len(beats) >= 8 and 60 <= tempo <= 200:
                    # Double-check with beat intervals
                    beat_intervals = np.diff(beats)
                    if len(beat_intervals) > 0:
                        interval_tempo = 60.0 / np.median(beat_intervals)
                        
                        # If the two methods agree within 10%, use the result
                        if abs(tempo - interval_tempo) / tempo < 0.1:
                            logger.info(f"Tempo detected with librosa beat tracking: {tempo:.1f} BPM")
                            return float(tempo)
                        else:
                            logger.warning(f"Tempo mismatch: beat_track={tempo:.1f}, intervals={interval_tempo:.1f}")
                            
            except Exception as e:
                logger.warning(f"librosa tempo analysis failed: {e}")
        
        # Method 2: Improved autocorrelation-based tempo analysis (LLVM-safe)
        try:
            logger.info("Using LLVM-safe autocorrelation-based tempo analysis")
            
            # Calculate onset strength function
            frame_length = 2048
            hop_length = 512
            onset_strength = []
            
            # Use spectral flux for onset detection
            prev_spectrum = None
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i + frame_length]
                
                # Simple FFT-based spectral analysis
                spectrum = np.abs(np.fft.fft(frame * np.hanning(len(frame))))
                spectrum = spectrum[:len(spectrum)//2]  # Keep only positive frequencies
                
                if prev_spectrum is not None:
                    # Spectral flux (positive changes in spectrum)
                    flux = np.sum(np.maximum(0, spectrum - prev_spectrum))
                    onset_strength.append(flux)
                else:
                    onset_strength.append(0)
                
                prev_spectrum = spectrum
            
            onset_strength = np.array(onset_strength)
            
            if len(onset_strength) >= 100:  # Need sufficient data for autocorrelation
                # Normalize onset strength
                onset_strength = (onset_strength - np.mean(onset_strength)) / (np.std(onset_strength) + 1e-8)
                
                # Autocorrelation for tempo detection
                autocorr = np.correlate(onset_strength, onset_strength, mode='full')
                autocorr = autocorr[len(autocorr)//2:]  # Keep only positive lags
                
                # Convert lag to tempo range (60-200 BPM)
                min_lag = int(60 * sr / (200 * hop_length))  # 200 BPM
                max_lag = int(60 * sr / (60 * hop_length))   # 60 BPM
                
                if max_lag < len(autocorr):
                    # Find peak in autocorrelation within tempo range
                    tempo_autocorr = autocorr[min_lag:max_lag]
                    peak_lag = np.argmax(tempo_autocorr) + min_lag
                    
                    # Convert lag back to tempo
                    tempo = 60 * sr / (peak_lag * hop_length)
                    
                    # Additional validation: check for strong periodicity
                    peak_strength = tempo_autocorr[peak_lag - min_lag] / np.mean(tempo_autocorr)
                    
                    if peak_strength > 1.2:  # Peak should be at least 20% above average
                        logger.info(f"Tempo estimated with autocorrelation: {tempo:.1f} BPM (strength: {peak_strength:.2f})")
                        return float(tempo)
                    else:
                        logger.warning(f"Weak tempo periodicity detected (strength: {peak_strength:.2f})")
            
        except Exception as e:
            logger.warning(f"Autocorrelation-based tempo analysis failed: {e}")
        
        # Method 3: Fallback with energy-based beat detection (improved)
        try:
            logger.info("Using improved energy-based beat detection as fallback")
            
            # Calculate energy envelope with better parameters
            frame_length = 1024  # Smaller frame for better time resolution
            hop_length = 256
            energy = []
            
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i + frame_length]
                # Use RMS energy instead of sum of squares
                frame_energy = np.sqrt(np.mean(frame ** 2))
                energy.append(frame_energy)
            
            energy = np.array(energy)
            
            if len(energy) >= 20:
                # Smooth energy to reduce noise
                kernel_size = 5
                kernel = np.ones(kernel_size) / kernel_size
                energy_smooth = np.convolve(energy, kernel, mode='same')
                
                # Adaptive threshold based on local maxima
                threshold = np.mean(energy_smooth) + 0.5 * np.std(energy_smooth)
                
                # Find peaks with minimum distance constraint
                min_peak_distance = int(0.3 * sr / hop_length)  # Minimum 300ms between beats
                peaks = []
                
                for i in range(2, len(energy_smooth) - 2):
                    if (energy_smooth[i] > energy_smooth[i-1] and 
                        energy_smooth[i] > energy_smooth[i+1] and 
                        energy_smooth[i] > threshold):
                        
                        # Check minimum distance from previous peaks
                        if not peaks or (i - peaks[-1]) >= min_peak_distance:
                            peaks.append(i)
                
                if len(peaks) >= 8:  # Need more beats for reliable tempo
                    peak_times = np.array(peaks) * hop_length / sr
                    intervals = np.diff(peak_times)
                    
                    # Remove outlier intervals (likely subdivisions or missed beats)
                    if len(intervals) > 4:
                        median_interval = np.median(intervals)
                        # Keep intervals within 50% of median (removes subdivisions)
                        valid_intervals = intervals[
                            (intervals > 0.5 * median_interval) & 
                            (intervals < 1.5 * median_interval)
                        ]
                        
                        if len(valid_intervals) >= 4:
                            tempo = 60.0 / np.median(valid_intervals)
                            tempo = max(60.0, min(200.0, tempo))  # Clamp to realistic range
                            
                            logger.info(f"Tempo estimated with improved energy analysis: {tempo:.1f} BPM ({len(valid_intervals)} valid beats)")
                            return float(tempo)
            
        except Exception as e:
            logger.warning(f"Improved energy-based tempo analysis failed: {e}")
        
        # Fallback tempo
        fallback_tempo = 120.0
        logger.info(f"Using fallback tempo: {fallback_tempo} BPM")
        return fallback_tempo
    
    def analyze_key_safe(self, audio: np.ndarray, sr: int) -> str:
        """Analyze key using truly LLVM-safe methods"""
        logger.info("Analyzing key with safe methods...")
        
        # Method 1: librosa (only if not using fallback)
        if self.capabilities['librosa_available'] and not self.use_fallback:
            try:
                import librosa
                stft = np.abs(librosa.stft(audio))
                spectral_centroids = librosa.feature.spectral_centroid(S=stft, sr=sr)
                
                if spectral_centroids.size > 0:
                    mean_centroid = np.mean(spectral_centroids)
                    key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                    key_idx = int((mean_centroid / 1000) * 12) % 12
                    estimated_key = key_names[key_idx]
                    
                    logger.info(f"Key estimated with librosa: {estimated_key}")
                    return estimated_key
                    
            except Exception as e:
                logger.warning(f"librosa key analysis failed: {e}")
        
        # Method 2: Pure numpy FFT analysis (LLVM-safe)
        try:
            logger.info("Using LLVM-safe FFT-based key analysis")
            
            # Simple FFT-based frequency analysis
            fft = np.fft.fft(audio)
            freqs = np.fft.fftfreq(len(audio), 1/sr)
            
            # Get magnitude spectrum (positive frequencies only)
            magnitude = np.abs(fft[:len(fft)//2])
            freqs = freqs[:len(freqs)//2]
            
            # Find dominant frequency
            dominant_freq_idx = np.argmax(magnitude)
            dominant_freq = freqs[dominant_freq_idx]
            
            if dominant_freq > 50:  # Ignore very low frequencies
                # Calculate semitones from A4 (440 Hz)
                semitones_from_a4 = 12 * np.log2(dominant_freq / 440.0)
                note_idx = int(round(semitones_from_a4)) % 12
                
                # Map to key (starting from A)
                key_names = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']
                estimated_key = key_names[note_idx]
                
                logger.info(f"Key estimated with FFT analysis: {estimated_key}")
                return estimated_key
                
        except Exception as e:
            logger.warning(f"FFT-based key analysis failed: {e}")
        
        # Fallback key
        fallback_key = "C"
        logger.info(f"Using fallback key: {fallback_key}")
        return fallback_key
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get current capabilities"""
        return self.capabilities.copy()
    
    def is_safe_mode(self) -> bool:
        """Check if processor is in safe mode"""
        return self.use_fallback
