#!/usr/bin/env python3
"""
Advanced Time-Frequency Reassignment System
Integrates sophisticated TFR analysis from analytic tools into DrumTracKAI
"""

import numpy as np
import torch
import torch.nn.functional as F
from scipy import signal
from scipy.fft import fft, ifft, fftfreq
import logging
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
import warnings

# Try to import GPU acceleration libraries
try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    cp = None

try:
    from numba import jit, cuda
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

# Lazy import librosa to avoid LLVM issues
librosa = None

logger = logging.getLogger(__name__)

@dataclass
class ReassignedSpectrogramData:
    """Contains reassigned spectrogram and associated data"""
    reassigned_stft: np.ndarray
    time_reassignment: np.ndarray
    freq_reassignment: np.ndarray
    original_stft: np.ndarray
    frequencies: np.ndarray
    times: np.ndarray
    instantaneous_frequency: np.ndarray
    group_delay: np.ndarray

@dataclass
class TFRAnalysisResult:
    """Complete TFR analysis result for a drum hit"""
    attack_time: float
    attack_sharpness: float
    transient_strength: float
    spectral_centroid_evolution: np.ndarray
    frequency_modulation: Dict
    spectral_flux: np.ndarray
    reassigned_data: ReassignedSpectrogramData

class AdvancedTimeFrequencyReassignment:
    """
    Advanced time-frequency reassignment for precise drum analysis.
    Uses synchrosqueezing and reassignment techniques for better resolution.
    """
    
    def __init__(self, sample_rate=44100, use_gpu=True):
        self.sr = sample_rate
        self.use_gpu = use_gpu and torch.cuda.is_available()
        
        # Initialize librosa lazily
        global librosa
        if librosa is None:
            try:
                import librosa as lib
                librosa = lib
                logger.info("Librosa imported successfully for TFR analysis")
            except Exception as e:
                logger.error(f"Failed to import librosa: {e}")
                raise ImportError("Librosa required for TFR analysis")
        
        if self.use_gpu:
            self.device = torch.device("cuda")
            logger.info("Using GPU for time-frequency reassignment")
        else:
            self.device = torch.device("cpu")
            if use_gpu:
                logger.warning("GPU requested but not available, using CPU")
    
    def compute_reassigned_spectrogram(self, audio: np.ndarray, 
                                     n_fft: int = 2048,
                                     hop_length: int = 128,
                                     window: str = 'hann') -> ReassignedSpectrogramData:
        """
        Compute reassigned spectrogram with improved time-frequency localization.
        """
        
        if self.use_gpu and torch.cuda.is_available():
            return self._compute_reassigned_gpu(audio, n_fft, hop_length, window)
        else:
            return self._compute_reassigned_cpu(audio, n_fft, hop_length, window)
    
    def _compute_reassigned_cpu(self, audio: np.ndarray, n_fft: int, 
                               hop_length: int, window: str) -> ReassignedSpectrogramData:
        """CPU implementation of reassigned spectrogram"""
        
        # Create windows
        win = signal.get_window(window, n_fft)
        win_norm = win / np.sum(win**2)
        
        # Derivative window for time reassignment
        win_derivative = np.gradient(win)
        
        # Time-ramped window for frequency reassignment
        time_ramp = np.arange(n_fft) - n_fft//2
        win_ramped = win * time_ramp
        
        # Compute STFTs
        stft_original = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length, 
                                    window=window, center=True)
        
        # STFT with derivative window
        stft_derivative = self._stft_custom(audio, win_derivative, n_fft, hop_length)
        
        # STFT with ramped window
        stft_ramped = self._stft_custom(audio, win_ramped, n_fft, hop_length)
        
        # Compute instantaneous frequency and group delay
        epsilon = 1e-10
        
        # Instantaneous frequency (frequency reassignment)
        instantaneous_freq = np.real(
            -1j * stft_ramped / (stft_original + epsilon)
        ) / (2 * np.pi)
        
        # Group delay (time reassignment)
        group_delay = np.real(
            stft_derivative / (stft_original + epsilon)
        )
        
        # Create time and frequency axes
        times = librosa.frames_to_time(np.arange(stft_original.shape[1]), 
                                      sr=self.sr, hop_length=hop_length)
        frequencies = librosa.fft_frequencies(sr=self.sr, n_fft=n_fft)
        
        # Reassignment matrices
        time_matrix = np.tile(times, (stft_original.shape[0], 1))
        freq_matrix = np.tile(frequencies[:, np.newaxis], (1, stft_original.shape[1]))
        
        # Apply reassignment
        time_reassigned = time_matrix + group_delay / self.sr
        freq_reassigned = freq_matrix + instantaneous_freq
        
        # Create reassigned spectrogram
        reassigned_stft = self._apply_reassignment(
            stft_original, time_reassigned, freq_reassigned, times, frequencies
        )
        
        return ReassignedSpectrogramData(
            reassigned_stft=reassigned_stft,
            time_reassignment=time_reassigned,
            freq_reassignment=freq_reassigned,
            original_stft=stft_original,
            frequencies=frequencies,
            times=times,
            instantaneous_frequency=instantaneous_freq,
            group_delay=group_delay
        )
    
    def _compute_reassigned_gpu(self, audio: np.ndarray, n_fft: int,
                              hop_length: int, window: str) -> ReassignedSpectrogramData:
        """GPU-accelerated implementation using PyTorch"""
        
        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio).float().to(self.device)
        
        # Create windows
        win = torch.from_numpy(signal.get_window(window, n_fft)).float().to(self.device)
        
        # Derivative and ramped windows
        win_derivative = torch.gradient(win)[0]
        time_ramp = torch.arange(n_fft, device=self.device).float() - n_fft//2
        win_ramped = win * time_ramp
        
        # Compute STFTs using PyTorch
        stft_original = torch.stft(audio_tensor, n_fft=n_fft, hop_length=hop_length,
                                  window=win, return_complex=True)
        
        # Custom STFT for derivative and ramped windows
        stft_derivative = self._stft_custom_gpu(audio_tensor, win_derivative, n_fft, hop_length)
        stft_ramped = self._stft_custom_gpu(audio_tensor, win_ramped, n_fft, hop_length)
        
        # Compute reassignment
        epsilon = 1e-10
        
        # Instantaneous frequency
        instantaneous_freq = torch.real(
            -1j * stft_ramped / (stft_original + epsilon)
        ) / (2 * np.pi)
        
        # Group delay
        group_delay = torch.real(
            stft_derivative / (stft_original + epsilon)
        )
        
        # Convert back to numpy
        stft_original_np = stft_original.cpu().numpy()
        instantaneous_freq_np = instantaneous_freq.cpu().numpy()
        group_delay_np = group_delay.cpu().numpy()
        
        # Create time and frequency axes
        times = librosa.frames_to_time(np.arange(stft_original_np.shape[1]), 
                                      sr=self.sr, hop_length=hop_length)
        frequencies = librosa.fft_frequencies(sr=self.sr, n_fft=n_fft)
        
        # Reassignment matrices
        time_matrix = np.tile(times, (stft_original_np.shape[0], 1))
        freq_matrix = np.tile(frequencies[:, np.newaxis], (1, stft_original_np.shape[1]))
        
        # Apply reassignment
        time_reassigned = time_matrix + group_delay_np / self.sr
        freq_reassigned = freq_matrix + instantaneous_freq_np
        
        # Create reassigned spectrogram
        reassigned_stft = self._apply_reassignment(
            stft_original_np, time_reassigned, freq_reassigned, times, frequencies
        )
        
        return ReassignedSpectrogramData(
            reassigned_stft=reassigned_stft,
            time_reassignment=time_reassigned,
            freq_reassignment=freq_reassigned,
            original_stft=stft_original_np,
            frequencies=frequencies,
            times=times,
            instantaneous_frequency=instantaneous_freq_np,
            group_delay=group_delay_np
        )
    
    def _stft_custom(self, audio: np.ndarray, window: np.ndarray, 
                    n_fft: int, hop_length: int) -> np.ndarray:
        """Custom STFT implementation for arbitrary windows"""
        
        # Pad audio
        audio_padded = np.pad(audio, n_fft//2, mode='reflect')
        
        # Compute STFT frames
        n_frames = 1 + (len(audio_padded) - n_fft) // hop_length
        stft = np.zeros((n_fft//2 + 1, n_frames), dtype=complex)
        
        for i in range(n_frames):
            start = i * hop_length
            frame = audio_padded[start:start + n_fft] * window
            stft[:, i] = fft(frame)[:n_fft//2 + 1]
        
        return stft
    
    def _stft_custom_gpu(self, audio_tensor: torch.Tensor, window: torch.Tensor,
                        n_fft: int, hop_length: int) -> torch.Tensor:
        """Custom STFT implementation for GPU with arbitrary windows"""
        
        # Pad audio
        audio_padded = F.pad(audio_tensor, (n_fft//2, n_fft//2), mode='reflect')
        
        # Unfold to create frames
        frames = audio_padded.unfold(0, n_fft, hop_length)
        
        # Apply window
        windowed_frames = frames * window.unsqueeze(0)
        
        # Compute FFT
        stft = torch.fft.fft(windowed_frames, dim=1)
        
        # Take positive frequencies only
        stft = stft[:, :n_fft//2 + 1]
        
        return stft.transpose(0, 1)
    
    def _apply_reassignment(self, stft: np.ndarray, time_reassigned: np.ndarray,
                          freq_reassigned: np.ndarray, times: np.ndarray,
                          frequencies: np.ndarray) -> np.ndarray:
        """Apply reassignment to create sharper time-frequency representation"""
        
        # Initialize reassigned spectrogram
        reassigned = np.zeros_like(stft)
        
        # Get grid spacing
        dt = times[1] - times[0] if len(times) > 1 else 1.0
        df = frequencies[1] - frequencies[0] if len(frequencies) > 1 else 1.0
        
        # Apply reassignment
        for i in range(stft.shape[0]):
            for j in range(stft.shape[1]):
                if np.abs(stft[i, j]) > 1e-10:  # Only reassign significant values
                    
                    # Find reassigned indices
                    new_time = time_reassigned[i, j]
                    new_freq = freq_reassigned[i, j]
                    
                    # Convert to indices
                    time_idx = int(np.round((new_time - times[0]) / dt))
                    freq_idx = int(np.round((new_freq - frequencies[0]) / df))
                    
                    # Check bounds
                    if (0 <= time_idx < stft.shape[1] and 
                        0 <= freq_idx < stft.shape[0]):
                        reassigned[freq_idx, time_idx] += stft[i, j]
        
        return reassigned
    
    def synchrosqueeze_transform(self, audio: np.ndarray, n_fft: int = 2048,
                                hop_length: int = 128) -> Dict:
        """
        Compute synchrosqueezed transform for even sharper time-frequency localization.
        Particularly good for analyzing drum attacks and transients.
        """
        
        # Get reassigned spectrogram
        reassigned_data = self.compute_reassigned_spectrogram(audio, n_fft, hop_length)
        
        # Synchrosqueezing threshold
        threshold = 0.1 * np.max(np.abs(reassigned_data.original_stft))
        
        # Initialize synchrosqueezed representation
        synchrosqueezed = np.zeros_like(reassigned_data.original_stft)
        
        # Apply synchrosqueezing
        for i in range(reassigned_data.original_stft.shape[0]):
            for j in range(reassigned_data.original_stft.shape[1]):
                magnitude = np.abs(reassigned_data.original_stft[i, j])
                
                if magnitude > threshold:
                    # Get instantaneous frequency
                    inst_freq = reassigned_data.instantaneous_frequency[i, j]
                    
                    # Find corresponding frequency bin
                    freq_bin = np.argmin(np.abs(reassigned_data.frequencies - inst_freq))
                    
                    # Add to synchrosqueezed representation
                    if 0 <= freq_bin < synchrosqueezed.shape[0]:
                        synchrosqueezed[freq_bin, j] += reassigned_data.original_stft[i, j]
        
        # Extract ridge curves
        ridge_curves = self._extract_ridge_curves(synchrosqueezed, reassigned_data.times)
        
        return {
            'synchrosqueezed': synchrosqueezed,
            'reassigned_data': reassigned_data,
            'ridge_curves': ridge_curves
        }
    
    def _extract_ridge_curves(self, squeezed: np.ndarray, times: np.ndarray) -> List[Dict]:
        """Extract ridge curves from synchrosqueezed representation"""
        
        ridge_curves = []
        
        # Find peaks in each time frame
        for j in range(squeezed.shape[1]):
            column = np.abs(squeezed[:, j])
            peaks, properties = signal.find_peaks(column, height=np.max(column) * 0.1)
            
            for peak in peaks:
                ridge_curves.append({
                    'time': times[j],
                    'frequency_bin': peak,
                    'magnitude': column[peak]
                })
        
        return ridge_curves
    
    def analyze_drum_attack(self, audio: np.ndarray, onset_time: float,
                          window_size: float = 0.05) -> TFRAnalysisResult:
        """
        Detailed analysis of drum attack using reassignment.
        
        Args:
            audio: Full audio signal
            onset_time: Time of drum onset in seconds
            window_size: Analysis window size in seconds
        
        Returns:
            TFRAnalysisResult with attack characteristics
        """
        
        # Extract window around onset
        start_sample = int(max(0, (onset_time - window_size/2) * self.sr))
        end_sample = int(min(len(audio), (onset_time + window_size/2) * self.sr))
        
        if end_sample <= start_sample:
            # Return empty result for invalid window
            return TFRAnalysisResult(
                attack_time=0.0,
                attack_sharpness=0.0,
                transient_strength=0.0,
                spectral_centroid_evolution=np.array([]),
                frequency_modulation={},
                spectral_flux=np.array([]),
                reassigned_data=None
            )
        
        window_audio = audio[start_sample:end_sample]
        
        # Compute reassigned spectrogram
        reassigned_data = self.compute_reassigned_spectrogram(
            window_audio, n_fft=1024, hop_length=64
        )
        
        # Compute spectral flux
        spectral_flux = self._compute_spectral_flux(reassigned_data.reassigned_stft)
        
        # Estimate precise attack time
        attack_time = self._estimate_attack_time(reassigned_data)
        
        # Track spectral centroid evolution
        spectral_centroid_evolution = self._track_spectral_centroid(reassigned_data)
        
        # Analyze frequency modulation
        frequency_modulation = self._analyze_frequency_modulation(reassigned_data)
        
        # Measure transient strength
        transient_strength = self._measure_transient_strength(reassigned_data)
        
        # Calculate attack sharpness
        attack_sharpness = np.max(spectral_flux) if len(spectral_flux) > 0 else 0.0
        
        return TFRAnalysisResult(
            attack_time=attack_time,
            attack_sharpness=attack_sharpness,
            transient_strength=transient_strength,
            spectral_centroid_evolution=spectral_centroid_evolution,
            frequency_modulation=frequency_modulation,
            spectral_flux=spectral_flux,
            reassigned_data=reassigned_data
        )
    
    def _compute_spectral_flux(self, spectrogram: np.ndarray) -> np.ndarray:
        """Compute spectral flux from reassigned spectrogram"""
        magnitude = np.abs(spectrogram)
        flux = np.sum(np.diff(magnitude, axis=1)**2, axis=0)
        return flux
    
    def _estimate_attack_time(self, reassigned: ReassignedSpectrogramData) -> float:
        """Estimate precise attack time using reassignment"""
        # Find time of maximum spectral flux
        flux = self._compute_spectral_flux(reassigned.reassigned_stft)
        if len(flux) > 0:
            max_flux_idx = np.argmax(flux)
            return reassigned.times[max_flux_idx] if max_flux_idx < len(reassigned.times) else 0.0
        return 0.0
    
    def _track_spectral_centroid(self, reassigned: ReassignedSpectrogramData) -> np.ndarray:
        """Track spectral centroid evolution"""
        magnitude = np.abs(reassigned.reassigned_stft)
        
        centroids = []
        for j in range(magnitude.shape[1]):
            column = magnitude[:, j]
            if np.sum(column) > 0:
                centroid = np.sum(reassigned.frequencies * column) / np.sum(column)
                centroids.append(centroid)
            else:
                centroids.append(0.0)
        
        return np.array(centroids)
    
    def _analyze_frequency_modulation(self, reassigned: ReassignedSpectrogramData) -> Dict:
        """Analyze frequency modulation in drum sound"""
        
        # Track dominant frequency over time
        magnitude = np.abs(reassigned.reassigned_stft)
        dominant_freqs = []
        
        for j in range(magnitude.shape[1]):
            column = magnitude[:, j]
            if np.max(column) > 0:
                dominant_idx = np.argmax(column)
                dominant_freqs.append(reassigned.frequencies[dominant_idx])
            else:
                dominant_freqs.append(0.0)
        
        dominant_freqs = np.array(dominant_freqs)
        
        # Calculate modulation characteristics
        if len(dominant_freqs) > 1:
            freq_variation = np.std(dominant_freqs)
            modulation_rate = self._estimate_modulation_rate(dominant_freqs)
            modulation_depth = np.max(dominant_freqs) - np.min(dominant_freqs)
        else:
            freq_variation = 0.0
            modulation_rate = 0.0
            modulation_depth = 0.0
        
        return {
            'frequency_trajectory': dominant_freqs,
            'frequency_variation': freq_variation,
            'modulation_rate': modulation_rate,
            'modulation_depth': modulation_depth
        }
    
    def _estimate_modulation_rate(self, frequency_trajectory: np.ndarray) -> float:
        """Estimate modulation rate from frequency trajectory"""
        if len(frequency_trajectory) < 4:
            return 0.0
        
        # Remove DC component
        trajectory_ac = frequency_trajectory - np.mean(frequency_trajectory)
        
        # Compute autocorrelation
        autocorr = np.correlate(trajectory_ac, trajectory_ac, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find first peak after zero lag
        if len(autocorr) > 1:
            peaks = signal.find_peaks(autocorr[1:])[0]
            if len(peaks) > 0:
                # Convert to rate (Hz)
                time_per_sample = 1.0 / self.sr * 64  # Assuming hop_length=64
                period_samples = peaks[0] + 1
                modulation_rate = 1.0 / (period_samples * time_per_sample)
                return modulation_rate
        
        return 0.0
    
    def _measure_transient_strength(self, reassigned: ReassignedSpectrogramData) -> float:
        """Measure transient strength using reassignment quality"""
        
        # Calculate reassignment quality (how much energy is concentrated)
        original_energy = np.sum(np.abs(reassigned.original_stft)**2)
        reassigned_energy = np.sum(np.abs(reassigned.reassigned_stft)**2)
        
        if original_energy > 0:
            concentration_ratio = reassigned_energy / original_energy
            return float(concentration_ratio)
        
        return 0.0
    
    def compare_drum_timbres(self, drum1_audio: np.ndarray, drum2_audio: np.ndarray,
                           onset1: float, onset2: float) -> Dict:
        """
        Compare timbres of two drums using reassigned spectrograms.
        
        Returns:
            Dictionary with similarity metrics
        """
        
        # Analyze both drums
        analysis1 = self.analyze_drum_attack(drum1_audio, onset1)
        analysis2 = self.analyze_drum_attack(drum2_audio, onset2)
        
        # Compare spectral centroids
        centroid_similarity = self._compare_centroid_evolution(
            analysis1.spectral_centroid_evolution,
            analysis2.spectral_centroid_evolution
        )
        
        # Compare attack characteristics
        attack_similarity = 1.0 / (1.0 + abs(analysis1.attack_sharpness - analysis2.attack_sharpness))
        
        # Compare frequency modulation
        modulation_similarity = self._compare_modulation(
            analysis1.frequency_modulation,
            analysis2.frequency_modulation
        )
        
        # Combine similarities
        overall_similarity = (
            centroid_similarity * 0.4 +
            attack_similarity * 0.3 +
            modulation_similarity * 0.3
        )
        
        return {
            'overall_similarity': overall_similarity,
            'centroid_similarity': centroid_similarity,
            'attack_similarity': attack_similarity,
            'modulation_similarity': modulation_similarity
        }
    
    def _compare_centroid_evolution(self, centroid1: np.ndarray, centroid2: np.ndarray) -> float:
        """Compare spectral centroid evolution between two drums"""
        if len(centroid1) == 0 or len(centroid2) == 0:
            return 0.0
        
        # Normalize lengths
        min_len = min(len(centroid1), len(centroid2))
        c1 = centroid1[:min_len]
        c2 = centroid2[:min_len]
        
        # Calculate correlation
        if np.std(c1) > 0 and np.std(c2) > 0:
            correlation = np.corrcoef(c1, c2)[0, 1]
            return max(0.0, correlation)
        
        return 0.0
    
    def _compare_modulation(self, analysis1: Dict, analysis2: Dict) -> float:
        """Compare frequency modulation characteristics"""
        if not analysis1 or not analysis2:
            return 0.0
        
        mod1_depth = analysis1.get('modulation_depth', 0.0)
        mod2_depth = analysis2.get('modulation_depth', 0.0)
        mod1_rate = analysis1.get('modulation_rate', 0.0)
        mod2_rate = analysis2.get('modulation_rate', 0.0)
        
        # Compare modulation depths and rates
        depth_diff = abs(mod1_depth - mod2_depth)
        rate_diff = abs(mod1_rate - mod2_rate)
        
        # Normalize and combine
        depth_similarity = 1.0 / (1.0 + depth_diff / 100)  # Assuming Hz scale
        rate_similarity = 1.0 / (1.0 + rate_diff)
        
        return (depth_similarity + rate_similarity) / 2
