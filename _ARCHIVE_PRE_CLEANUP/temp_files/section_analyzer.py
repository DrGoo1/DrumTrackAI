"""
Intelligent musical section analysis
Detects intro, verse, chorus, bridge, outro with confidence scores
"""
from pathlib import Path
from typing import List, Dict, Tuple
import logging

# Optional dependencies - gracefully degrade if not available
try:
    import numpy as np
except ImportError:
    np = None

try:
    import soundfile as sf
except ImportError:
    sf = None

LOG = logging.getLogger(__name__)

class SectionAnalyzer:
    """Analyzes sections and assigns intelligent labels"""
    
    def __init__(self, audio_path: str, bpm: float):
        self.audio_path = Path(audio_path)
        self.bpm = bpm
        self.audio = None
        self.sr = None
        
        # Check if dependencies are available
        if sf is None or np is None:
            LOG.warning("soundfile or numpy not available - energy analysis disabled")
            return
        
        try:
            self.audio, self.sr = sf.read(str(audio_path))
            if len(self.audio.shape) > 1:
                self.audio = np.mean(self.audio, axis=1)  # Convert to mono
            LOG.info(f"Loaded audio: {audio_path}, duration: {len(self.audio)/self.sr:.2f}s")
        except Exception as e:
            LOG.error(f"Failed to load audio {audio_path}: {e}")
            self.audio = None
            self.sr = None
    
    def calculate_section_energy(self, start_sec: float, end_sec: float) -> float:
        """Calculate RMS energy for a section"""
        if self.audio is None or self.sr is None or np is None:
            return 0.5  # Default neutral energy
        
        start_sample = int(start_sec * self.sr)
        end_sample = int(end_sec * self.sr)
        
        # Bounds checking
        start_sample = max(0, start_sample)
        end_sample = min(len(self.audio), end_sample)
        
        section_audio = self.audio[start_sample:end_sample]
        
        if len(section_audio) == 0:
            return 0.5
        
        rms = np.sqrt(np.mean(section_audio ** 2))
        return float(rms)
    
    def calculate_spectral_centroid(self, start_sec: float, end_sec: float) -> float:
        """Calculate spectral centroid (brightness) for a section"""
        if self.audio is None or self.sr is None or np is None:
            return 0.5  # Default neutral centroid
        
        start_sample = int(start_sec * self.sr)
        end_sample = int(end_sec * self.sr)
        
        # Bounds checking
        start_sample = max(0, start_sample)
        end_sample = min(len(self.audio), end_sample)
        
        section_audio = self.audio[start_sample:end_sample]
        
        if len(section_audio) < 2048:
            return 0.5
        
        # Simple FFT-based centroid
        spectrum = np.abs(np.fft.rfft(section_audio))
        freqs = np.fft.rfftfreq(len(section_audio), 1/self.sr)
        centroid = np.sum(freqs * spectrum) / (np.sum(spectrum) + 1e-6)
        
        # Normalize to 0-1
        return float(centroid / (self.sr / 2))
    
    def analyze_sections(self, raw_sections: List[Dict]) -> List[Dict]:
        """Analyze sections and add energy/centroid data"""
        analyzed = []
        for section in raw_sections:
            analyzed.append({
                **section,
                'energy': self.calculate_section_energy(section['start'], section['end']),
                'spectral_centroid': self.calculate_spectral_centroid(section['start'], section['end'])
            })
        return analyzed
    
    def group_similar_sections(self, sections: List[Dict], threshold: float = 0.15) -> List[int]:
        """Group sections by similarity (energy + spectral features)"""
        n = len(sections)
        groups = [-1] * n
        next_group = 0
        
        for i in range(n):
            if groups[i] != -1:
                continue
            
            # Start new group
            groups[i] = next_group
            
            # Find similar sections
            for j in range(i+1, n):
                if groups[j] != -1:
                    continue
                
                energy_diff = abs(sections[i]['energy'] - sections[j]['energy'])
                centroid_diff = abs(sections[i]['spectral_centroid'] - sections[j]['spectral_centroid'])
                
                distance = (energy_diff + centroid_diff) / 2
                
                if distance < threshold:
                    groups[j] = next_group
            
            next_group += 1
        
        return groups
    
    def label_sections(self, sections: List[Dict]) -> List[Dict]:
        """Apply intelligent labels to sections"""
        if len(sections) == 0:
            return sections
        
        # Get similarity groups
        groups = self.group_similar_sections(sections)
        
        # Calculate group statistics
        group_counts = {}
        group_energies = {}
        for i, group in enumerate(groups):
            group_counts[group] = group_counts.get(group, 0) + 1
            if group not in group_energies:
                group_energies[group] = []
            group_energies[group].append(sections[i]['energy'])
        
        # Find most repeated group (likely verse or chorus)
        most_repeated_group = max(group_counts.items(), key=lambda x: x[1])[0]
        if np:
            avg_energy_repeated = np.mean(group_energies[most_repeated_group])
        else:
            avg_energy_repeated = sum(group_energies[most_repeated_group]) / len(group_energies[most_repeated_group])
        
        # Overall average energy
        all_energies = [s['energy'] for s in sections]
        if np:
            avg_energy = np.mean(all_energies)
        else:
            avg_energy = sum(all_energies) / len(all_energies) if all_energies else 0.5
        max_energy = max(all_energies) if all_energies else 0.5
        
        # Label each section
        labeled = []
        for i, section in enumerate(sections):
            label = "unknown"
            confidence = 0.5
            
            # Position-based rules
            if i == 0:
                # First section is likely intro
                label = "intro"
                confidence = 0.75
                
            elif i == len(sections) - 1:
                # Last section is likely outro
                label = "outro"
                confidence = 0.75
                
            elif groups[i] == most_repeated_group:
                # Most repeated group: check energy to distinguish verse/chorus
                if section['energy'] > avg_energy * 1.15:
                    label = "chorus"
                    confidence = 0.8
                else:
                    label = "verse"
                    confidence = 0.75
                    
            elif group_counts[groups[i]] == 1:
                # Unique section in middle: likely bridge
                if 0.3 < (i / len(sections)) < 0.7:
                    label = "bridge"
                    confidence = 0.65
                else:
                    label = "break"
                    confidence = 0.6
                    
            else:
                # Multiple occurrences but not most repeated
                # Could be pre-chorus or second verse
                label = "verse"
                confidence = 0.5
            
            labeled.append({
                **section,
                'label': label,
                'confidence': confidence,
                'repetition_group': groups[i]
            })
        
        # Calculate average confidence
        confidences = [s['confidence'] for s in labeled]
        if np:
            avg_conf = np.mean(confidences)
        else:
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.5
        
        LOG.info(f"Labeled {len(labeled)} sections with average confidence {avg_conf:.2f}")
        return labeled


# Helper function for backend integration
def analyze_and_label_sections(audio_path: str, bpm: float, raw_sections: List[Dict]) -> List[Dict]:
    """Main entry point for section analysis"""
    try:
        analyzer = SectionAnalyzer(audio_path, bpm)
        
        # Add energy and spectral features
        analyzed_sections = analyzer.analyze_sections(raw_sections)
        
        # Apply intelligent labels
        labeled_sections = analyzer.label_sections(analyzed_sections)
        
        return labeled_sections
    except Exception as e:
        LOG.error(f"Section analysis failed: {e}")
        # Return raw sections as fallback
        return raw_sections
