"""
Offline Sectionalization Test Suite
Perfects section detection using local audio file before integrating into main app

Features:
- Direct audio file loading (no upload needed)
- Multiple sectionalization algorithms
- Detailed visualization and metrics
- Parameter tuning interface
- Validation against known structure
"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
import json
import subprocess
import sys

# Configuration
AUDIO_FILE = r"F:\Audio_Test_Files\Peg_No_Drums.mp3"
RUST_BINARY = r"F:\DrumTracKAI_v1.1.16_Clean\audio-core\target\release\audio-core.exe"

# Expected structure from sheet music analysis
EXPECTED_STRUCTURE = {
    "tempo": 161.5,  # BPM from sheet music
    "time_sig": [4, 4],
    "sections": [
        {"name": "Intro", "bars": 7, "approx_duration": 10},
        {"name": "Verse 1", "bars": 8, "approx_duration": 15},
        {"name": "Verse 2", "bars": 8, "approx_duration": 15},
        {"name": "Refrain", "bars": 6, "approx_duration": 10},
        {"name": "Instrumental", "bars": 8, "approx_duration": 15},
        {"name": "Verse 3", "bars": 8, "approx_duration": 15},
        {"name": "Outro", "bars": -1, "approx_duration": -1}  # Fade out
    ]
}


class SectionalizationTester:
    def __init__(self, audio_path):
        self.audio_path = Path(audio_path)
        if not self.audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        print(f"🎵 Loading: {self.audio_path.name}")
        self.y, self.sr = librosa.load(str(self.audio_path), sr=None, mono=True)
        self.duration = len(self.y) / self.sr
        print(f"   Duration: {self.duration:.1f}s")
        print(f"   Sample rate: {self.sr} Hz")
        print()
        
    def detect_tempo(self):
        """Detect global tempo"""
        print("🎼 Detecting Global Tempo...")
        tempo, beats = librosa.beat.beat_track(y=self.y, sr=self.sr)
        beat_times = librosa.frames_to_time(beats, sr=self.sr)
        
        # Convert tempo to scalar if it's an array
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if len(tempo) > 0 else float(tempo)
        else:
            tempo = float(tempo)
        
        print(f"   Detected: {tempo:.1f} BPM")
        print(f"   Expected: {EXPECTED_STRUCTURE['tempo']:.1f} BPM")
        print(f"   Difference: {abs(tempo - EXPECTED_STRUCTURE['tempo']):.1f} BPM")
        print(f"   Beat count: {len(beat_times)}")
        print()
        
        return tempo, beat_times
    
    def method_1_energy_based(self, tempo, hop_length=512):
        """Energy-based segmentation with onset detection"""
        print("📊 Method 1: Energy-Based Segmentation")
        print("   Computing onset strength envelope...")
        
        # Compute onset strength
        onset_env = librosa.onset.onset_strength(y=self.y, sr=self.sr, hop_length=hop_length)
        times = librosa.frames_to_time(np.arange(len(onset_env)), sr=self.sr, hop_length=hop_length)
        
        # Smooth the envelope
        from scipy.ndimage import gaussian_filter1d
        onset_smooth = gaussian_filter1d(onset_env, sigma=20)
        
        # Find peaks in smoothed envelope
        from scipy.signal import find_peaks
        peaks, properties = find_peaks(onset_smooth, distance=int(self.sr / hop_length * 8), prominence=0.3)
        
        # Convert to sections
        sections = []
        section_times = [0.0] + list(times[peaks]) + [self.duration]
        
        for i in range(len(section_times) - 1):
            start = section_times[i]
            end = section_times[i + 1]
            duration = end - start
            bars = int(duration / (60.0 / tempo * 4))
            
            sections.append({
                "start": start,
                "end": end,
                "duration": duration,
                "bars": bars,
                "method": "energy"
            })
        
        print(f"   Found {len(sections)} sections")
        self._print_sections(sections)
        return sections
    
    def method_2_spectral_clustering(self, tempo, n_sections=7):
        """Spectral clustering based on timbre similarity"""
        print(f"🎨 Method 2: Spectral Clustering (target: {n_sections} sections)")
        print("   Computing chroma features...")
        
        # Compute chroma features
        chroma = librosa.feature.chroma_cqt(y=self.y, sr=self.sr)
        
        # Compute recurrence matrix
        from sklearn.cluster import SpectralClustering
        
        # Normalize and cluster
        chroma_norm = librosa.util.normalize(chroma, axis=0)
        
        # Time frames
        hop_length = 512
        times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=self.sr, hop_length=hop_length)
        
        # Cluster
        clustering = SpectralClustering(n_clusters=n_sections, affinity='nearest_neighbors', random_state=42)
        labels = clustering.fit_predict(chroma_norm.T)
        
        # Convert clusters to sections
        sections = []
        current_label = labels[0]
        start_idx = 0
        
        for i in range(1, len(labels)):
            if labels[i] != current_label:
                start = times[start_idx]
                end = times[i]
                duration = end - start
                bars = int(duration / (60.0 / tempo * 4))
                
                sections.append({
                    "start": start,
                    "end": end,
                    "duration": duration,
                    "bars": bars,
                    "method": "spectral",
                    "cluster": int(current_label)
                })
                
                current_label = labels[i]
                start_idx = i
        
        # Add last section
        start = times[start_idx]
        end = self.duration
        duration = end - start
        bars = int(duration / (60.0 / tempo * 4))
        sections.append({
            "start": start,
            "end": end,
            "duration": duration,
            "bars": bars,
            "method": "spectral",
            "cluster": int(current_label)
        })
        
        print(f"   Found {len(sections)} sections")
        self._print_sections(sections)
        return sections
    
    def method_3_repetition_structure(self, tempo):
        """Repetition-based structure analysis"""
        print("🔁 Method 3: Repetition Structure Analysis")
        print("   Computing self-similarity matrix...")
        
        # Compute MFCC features
        mfcc = librosa.feature.mfcc(y=self.y, sr=self.sr, n_mfcc=13)
        mfcc_norm = librosa.util.normalize(mfcc, axis=1)
        
        # Compute recurrence matrix
        from scipy.spatial.distance import cdist
        R = 1 - cdist(mfcc_norm.T, mfcc_norm.T, metric='cosine')
        
        # Find diagonal structures (repetitions)
        # Use librosa's segmentation
        from librosa import segment
        hop_length = 512
        
        # Compute segment boundaries based on recurrence
        # Simple peak detection on diagonal sum
        diag_sum = np.sum(R, axis=0)
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(-diag_sum, distance=int(self.sr / hop_length * 10))
        
        times = librosa.frames_to_time(np.arange(R.shape[0]), sr=self.sr, hop_length=hop_length)
        
        sections = []
        section_times = [0.0] + list(times[peaks]) + [self.duration]
        
        for i in range(len(section_times) - 1):
            start = section_times[i]
            end = section_times[i + 1]
            duration = end - start
            bars = int(duration / (60.0 / tempo * 4))
            
            sections.append({
                "start": start,
                "end": end,
                "duration": duration,
                "bars": bars,
                "method": "repetition"
            })
        
        print(f"   Found {len(sections)} sections")
        self._print_sections(sections)
        return sections
    
    def method_4_rust_smart_sectionize(self, tempo, min_bars=4, max_bars=16):
        """Use Rust implementation if available"""
        print(f"⚙️  Method 4: Rust Smart Sectionization")
        
        rust_bin = Path(RUST_BINARY)
        if not rust_bin.exists():
            print(f"   ⚠️  Rust binary not found: {rust_bin}")
            print(f"   Skipping this method")
            return None
        
        try:
            # Call Rust binary
            cmd = [
                str(rust_bin),
                "sectionize-smart",
                str(self.audio_path),
                "--bpm", str(tempo),
                "--min-bars", str(min_bars),
                "--max-bars", str(max_bars)
            ]
            
            print(f"   Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"   ❌ Error: {result.stderr}")
                return None
            
            # Parse JSON output
            data = json.loads(result.stdout)
            sections = data.get("sections", [])
            
            print(f"   ✅ Found {len(sections)} sections")
            self._print_sections(sections)
            return sections
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return None
    
    def method_5_combined_approach(self, tempo):
        """Combine multiple signals for robust detection"""
        print("🎯 Method 5: Combined Multi-Signal Approach")
        print("   Analyzing multiple features...")
        
        hop_length = 512
        
        # 1. Energy/Onset strength
        onset_env = librosa.onset.onset_strength(y=self.y, sr=self.sr, hop_length=hop_length)
        
        # 2. Spectral contrast (timbre changes)
        contrast = librosa.feature.spectral_contrast(y=self.y, sr=self.sr, hop_length=hop_length)
        contrast_mean = np.mean(contrast, axis=0)
        
        # 3. Chroma (harmonic changes)
        chroma = librosa.feature.chroma_cqt(y=self.y, sr=self.sr, hop_length=hop_length)
        chroma_var = np.var(chroma, axis=0)
        
        # Combine signals
        from scipy.ndimage import gaussian_filter1d
        onset_smooth = gaussian_filter1d(onset_env, sigma=10)
        contrast_smooth = gaussian_filter1d(contrast_mean, sigma=10)
        chroma_smooth = gaussian_filter1d(chroma_var, sigma=10)
        
        # Normalize
        onset_norm = (onset_smooth - np.min(onset_smooth)) / (np.max(onset_smooth) - np.min(onset_smooth) + 1e-8)
        contrast_norm = (contrast_smooth - np.min(contrast_smooth)) / (np.max(contrast_smooth) - np.min(contrast_smooth) + 1e-8)
        chroma_norm = (chroma_smooth - np.min(chroma_smooth)) / (np.max(chroma_smooth) - np.min(chroma_smooth) + 1e-8)
        
        # Weighted combination
        combined = 0.4 * onset_norm + 0.3 * contrast_norm + 0.3 * chroma_norm
        
        # Find peaks in combined signal
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(combined, distance=int(self.sr / hop_length * 8), prominence=0.2)
        
        times = librosa.frames_to_time(np.arange(len(combined)), sr=self.sr, hop_length=hop_length)
        
        sections = []
        section_times = [0.0] + list(times[peaks]) + [self.duration]
        
        for i in range(len(section_times) - 1):
            start = section_times[i]
            end = section_times[i + 1]
            duration = end - start
            bars = int(duration / (60.0 / tempo * 4))
            
            # Calculate confidence based on signal strength at boundary
            if i < len(peaks):
                confidence = float(combined[peaks[i]])
            else:
                confidence = 0.5
            
            sections.append({
                "start": start,
                "end": end,
                "duration": duration,
                "bars": bars,
                "method": "combined",
                "confidence": confidence
            })
        
        print(f"   Found {len(sections)} sections")
        self._print_sections(sections)
        return sections
    
    def _print_sections(self, sections):
        """Pretty print section list"""
        print()
        print("   ┌────┬──────────┬──────────┬──────────┬──────┐")
        print("   │ #  │ Start    │ End      │ Duration │ Bars │")
        print("   ├────┼──────────┼──────────┼──────────┼──────┤")
        for i, sec in enumerate(sections, 1):
            start = sec['start']
            end = sec['end']
            dur = sec.get('duration', end - start)
            bars = sec.get('bars', '?')
            print(f"   │ {i:2d} │ {start:6.1f}s  │ {end:6.1f}s │ {dur:6.1f}s  │ {bars:4d} │")
        print("   └────┴──────────┴──────────┴──────────┴──────┘")
        print()
    
    def evaluate_against_expected(self, sections):
        """Compare detected sections against known structure"""
        print("📏 Evaluation Against Sheet Music Structure")
        print()
        
        expected_sections = EXPECTED_STRUCTURE["sections"]
        num_expected = len([s for s in expected_sections if s["approx_duration"] > 0])
        num_detected = len(sections)
        
        print(f"   Expected sections: {num_expected}")
        print(f"   Detected sections: {num_detected}")
        print(f"   Difference: {abs(num_expected - num_detected)}")
        print()
        
        # Check section lengths
        print("   Expected vs Detected Durations:")
        cumulative = 0
        for i, exp in enumerate(expected_sections):
            if exp["approx_duration"] < 0:
                continue
            
            expected_dur = exp["approx_duration"]
            
            # Find closest detected section
            if i < len(sections):
                detected_dur = sections[i].get('duration', sections[i]['end'] - sections[i]['start'])
                diff = abs(expected_dur - detected_dur)
                match = "✓" if diff < 5 else "✗"
                print(f"   {match} {exp['name']:15s}: Expected ~{expected_dur:2d}s, Got {detected_dur:5.1f}s (Δ{diff:4.1f}s)")
            else:
                print(f"   ✗ {exp['name']:15s}: Expected ~{expected_dur:2d}s, Not detected")
            
            cumulative += expected_dur
        
        print()
        
        # Calculate score
        section_count_score = max(0, 100 - abs(num_expected - num_detected) * 15)
        print(f"   Section count score: {section_count_score:.0f}/100")
        print()
        
        return {
            "expected": num_expected,
            "detected": num_detected,
            "score": section_count_score
        }
    
    def run_all_methods(self):
        """Run all sectionalization methods and compare"""
        print("="*70)
        print("  OFFLINE SECTIONALIZATION TEST SUITE - Peg (Steely Dan)")
        print("="*70)
        print()
        
        # Detect tempo first
        tempo, beats = self.detect_tempo()
        
        results = {}
        
        # Method 1: Energy-based
        print("-" * 70)
        results['energy'] = self.method_1_energy_based(tempo)
        
        # Method 2: Spectral clustering
        print("-" * 70)
        results['spectral'] = self.method_2_spectral_clustering(tempo, n_sections=7)
        
        # Method 3: Repetition structure
        print("-" * 70)
        results['repetition'] = self.method_3_repetition_structure(tempo)
        
        # Method 4: Rust implementation
        print("-" * 70)
        results['rust'] = self.method_4_rust_smart_sectionize(tempo, min_bars=4, max_bars=16)
        
        # Method 5: Combined approach
        print("-" * 70)
        results['combined'] = self.method_5_combined_approach(tempo)
        
        # Evaluation
        print("="*70)
        print("  EVALUATION SUMMARY")
        print("="*70)
        print()
        
        for method_name, sections in results.items():
            if sections is None:
                continue
            print(f"📊 {method_name.upper()} Method:")
            eval_result = self.evaluate_against_expected(sections)
            print()
        
        # Recommendation
        print("="*70)
        print("  RECOMMENDATION")
        print("="*70)
        print()
        
        best_method = None
        best_score = 0
        for method_name, sections in results.items():
            if sections is None:
                continue
            eval_result = self.evaluate_against_expected(sections)
            if eval_result['score'] > best_score:
                best_score = eval_result['score']
                best_method = method_name
        
        if best_method:
            print(f"✅ Best method: {best_method.upper()} (score: {best_score:.0f}/100)")
            print()
            print("Next steps:")
            print("1. Fine-tune parameters for this method")
            print("2. Implement in main app")
            print("3. Test with more audio files")
        
        return results


def main():
    try:
        tester = SectionalizationTester(AUDIO_FILE)
        results = tester.run_all_methods()
        
        # Save results to JSON
        output_file = "sectionalization_test_results.json"
        with open(output_file, 'w') as f:
            # Convert to serializable format
            serializable = {}
            for method, sections in results.items():
                if sections:
                    serializable[method] = sections
            json.dump(serializable, f, indent=2)
        
        print()
        print(f"💾 Results saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
