"""
Database Bootstrapper for Training System
Quickly builds robust drum knowledge base from existing databases:
- E-GMD (E-Groove MIDI Dataset)
- Snare Rudiments
- SoundsTracks Loops

This gives instant access to thousands of training examples!
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Check for MIDI parsing
try:
    import mido
    MIDI_AVAILABLE = True
except ImportError:
    logger.warning("mido not available - install with: pip install mido")
    MIDI_AVAILABLE = False

try:
    import librosa
    import soundfile as sf
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    logger.warning("librosa/soundfile not available")
    AUDIO_LIBS_AVAILABLE = False

from .data_extraction import HumanizationFeatures, CommercialSongAnalyzer


class EGMDExtractor:
    """
    Extract training data from E-GMD (E-Groove MIDI Dataset)
    
    E-GMD contains thousands of MIDI drum grooves with:
    - Precise timing information
    - Velocity data
    - Style annotations
    - Drummer information (sometimes)
    
    Perfect for learning timing variance and patterns!
    """
    
    def __init__(self, egmd_dir: Path, db_path: Path = Path("admin/data/drum_training.db")):
        self.egmd_dir = Path(egmd_dir)
        self.db_path = db_path
        
        if not MIDI_AVAILABLE:
            raise ImportError("mido not installed. Run: pip install mido")
        
        logger.info(f"E-GMD Extractor initialized: {self.egmd_dir}")
    
    def extract_from_midi(self, midi_file: Path, style: str = None) -> Optional[HumanizationFeatures]:
        """
        Extract humanization features from E-GMD MIDI file
        
        Args:
            midi_file: Path to MIDI file
            style: Genre/style (from filename or metadata)
        
        Returns:
            HumanizationFeatures or None
        """
        try:
            mid = mido.MidiFile(str(midi_file))
            
            # Extract drum notes (channel 9 is drums in GM)
            notes = []
            current_time = 0
            
            for track in mid.tracks:
                for msg in track:
                    current_time += msg.time
                    
                    if msg.type == 'note_on' and msg.channel == 9 and msg.velocity > 0:
                        notes.append({
                            'time': mido.tick2second(current_time, mid.ticks_per_beat, 500000),  # Default tempo
                            'note': msg.note,
                            'velocity': msg.velocity
                        })
            
            if len(notes) < 8:  # Need minimum notes
                return None
            
            # Calculate timing features
            times = np.array([n['time'] for n in notes])
            velocities = np.array([n['velocity'] for n in notes])
            
            # Inter-onset intervals
            intervals = np.diff(times)
            
            # Timing variance (how much timing varies)
            timing_variance = float(np.std(intervals)) if len(intervals) > 0 else 0.0
            
            # Timing drift (systematic early/late)
            if len(intervals) > 0:
                median_interval = np.median(intervals)
                timing_drift = float(np.mean(intervals - median_interval))
            else:
                timing_drift = 0.0
            
            # Velocity variance
            velocity_variance = float(np.std(velocities) / 127.0)
            
            # Ghost notes (velocity < 40)
            ghost_notes = np.sum(velocities < 40)
            ghost_note_frequency = float(ghost_notes / len(velocities))
            
            # Estimate tempo
            if len(intervals) > 0:
                # Assume intervals are 16th notes
                tempo = 60.0 / (np.median(intervals) * 4)
                tempo = np.clip(tempo, 60, 200)
            else:
                tempo = 120.0
            
            # Extract style from filename if not provided
            if not style:
                style = self._extract_style_from_filename(midi_file.name)
            
            features = HumanizationFeatures(
                timing_variance=timing_variance,
                timing_drift=timing_drift,
                groove_consistency=0.8,  # MIDI is generally consistent
                swing_factor=0.0,  # TODO: Detect swing
                velocity_variance=velocity_variance,
                accent_pattern=[1.0, 0.7, 0.9, 0.7] * 4,  # Default
                ghost_note_frequency=ghost_note_frequency,
                velocity_humanization=velocity_variance,
                pattern_complexity=0.7,
                fill_frequency=0.2,
                transition_smoothness=0.8,
                hihat_variation=0.3,
                kick_snare_relationship=0.75,
                ride_vs_hihat_ratio=0.2,
                section_awareness=0.7,
                energy_curve=[0.7, 0.8, 0.9, 0.85, 0.7],
                drummer_name="E-GMD",
                style=style,
                tempo=float(tempo),
                time_signature=(4, 4)
            )
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting from {midi_file}: {e}")
            return None
    
    def _extract_style_from_filename(self, filename: str) -> str:
        """Extract style from filename"""
        filename_lower = filename.lower()
        
        styles = ['rock', 'jazz', 'funk', 'latin', 'blues', 'metal', 'pop', 'country']
        for style in styles:
            if style in filename_lower:
                return style
        
        return 'unknown'
    
    def batch_extract(self, limit: int = None) -> int:
        """
        Extract features from all E-GMD MIDI files
        
        Args:
            limit: Maximum files to process
        
        Returns:
            Number of files processed
        """
        if not self.egmd_dir.exists():
            logger.error(f"E-GMD directory not found: {self.egmd_dir}")
            return 0
        
        # Find all MIDI files
        midi_files = list(self.egmd_dir.rglob('*.mid')) + list(self.egmd_dir.rglob('*.midi'))
        
        if limit:
            midi_files = midi_files[:limit]
        
        logger.info(f"Found {len(midi_files)} MIDI files in E-GMD")
        
        count = 0
        for i, midi_file in enumerate(midi_files, 1):
            if i % 100 == 0:
                logger.info(f"Processing {i}/{len(midi_files)}...")
            
            features = self.extract_from_midi(midi_file)
            if features:
                self._save_features(features, str(midi_file))
                count += 1
        
        logger.info(f"Extracted features from {count} E-GMD files")
        return count
    
    def _save_features(self, features: HumanizationFeatures, source: str):
        """Save features to database"""
        import sqlite3
        from dataclasses import asdict
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO humanization_features (source, drummer_name, style, tempo, features_json)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            source,
            features.drummer_name,
            features.style,
            features.tempo,
            json.dumps(asdict(features))
        ))
        
        conn.commit()
        conn.close()


class RudimentsExtractor:
    """
    Extract training data from Snare Rudiments
    
    Rudiments teach fundamental patterns:
    - Single stroke roll
    - Double stroke roll
    - Paradiddles
    - Flams
    - Drags
    - Ruffs
    
    These are building blocks of all drumming!
    """
    
    def __init__(self, rudiments_dir: Path = None, db_path: Path = Path("admin/data/drum_training.db")):
        self.rudiments_dir = Path(rudiments_dir) if rudiments_dir else None
        self.db_path = db_path
        
        # Define standard rudiments programmatically
        self.standard_rudiments = self._define_standard_rudiments()
        
        logger.info("Rudiments Extractor initialized")
    
    def _define_standard_rudiments(self) -> Dict:
        """
        Define standard 40 PAS rudiments
        
        Each rudiment has:
        - Sticking pattern (R/L)
        - Timing pattern
        - Typical tempos
        - Style usage
        """
        return {
            'single_stroke_roll': {
                'sticking': 'RLRLRLRL',
                'description': 'Alternating single strokes',
                'typical_tempo': (120, 180),
                'velocity_pattern': [1.0, 0.9, 1.0, 0.9],  # Slight accent on downbeats
                'styles': ['rock', 'jazz', 'all']
            },
            'double_stroke_roll': {
                'sticking': 'RRLLRRLL',
                'description': 'Two strokes per hand',
                'typical_tempo': (100, 160),
                'velocity_pattern': [1.0, 0.8, 1.0, 0.8],
                'styles': ['rock', 'jazz', 'all']
            },
            'paradiddle': {
                'sticking': 'RLRRLRLL',
                'description': 'Single-single-double pattern',
                'typical_tempo': (80, 140),
                'velocity_pattern': [1.0, 0.8, 0.9, 1.0, 0.9, 0.8, 0.9, 1.0],
                'styles': ['rock', 'jazz', 'all']
            },
            'flam': {
                'sticking': 'lRrL',  # lowercase = grace note
                'description': 'Grace note before main stroke',
                'typical_tempo': (60, 120),
                'velocity_pattern': [0.3, 1.0, 0.3, 1.0],  # Grace notes quiet
                'styles': ['rock', 'jazz', 'funk']
            },
            'drag': {
                'sticking': 'llR-rrL',
                'description': 'Two grace notes before main stroke',
                'typical_tempo': (60, 120),
                'velocity_pattern': [0.3, 0.3, 1.0, 0.3, 0.3, 1.0],
                'styles': ['jazz', 'funk']
            },
            'flam_tap': {
                'sticking': 'lRRrLL',
                'description': 'Flam followed by tap',
                'typical_tempo': (70, 130),
                'velocity_pattern': [0.3, 1.0, 0.8, 0.3, 1.0, 0.8],
                'styles': ['rock', 'jazz']
            },
            'single_paradiddle': {
                'sticking': 'RLRRLRLL',
                'description': 'Basic paradiddle pattern',
                'typical_tempo': (80, 140),
                'velocity_pattern': [1.0, 0.8, 0.9, 1.0, 0.9, 0.8, 0.9, 1.0],
                'styles': ['rock', 'jazz', 'all']
            },
            'double_paradiddle': {
                'sticking': 'RLRLRRLRLRLL',
                'description': 'Extended paradiddle',
                'typical_tempo': (70, 120),
                'velocity_pattern': [1.0, 0.8, 0.9, 0.8, 0.9, 1.0] * 2,
                'styles': ['jazz', 'fusion']
            },
            'ratamacue': {
                'sticking': 'lRlRLrLR',
                'description': 'Drag-tap-tap pattern',
                'typical_tempo': (60, 110),
                'velocity_pattern': [0.3, 1.0, 0.3, 1.0, 0.9, 0.3, 1.0, 0.9],
                'styles': ['jazz', 'orchestral']
            },
            'five_stroke_roll': {
                'sticking': 'RRLLL',
                'description': 'Five stroke roll',
                'typical_tempo': (80, 140),
                'velocity_pattern': [1.0, 0.9, 0.9, 0.9, 1.0],
                'styles': ['rock', 'jazz', 'all']
            },
            'seven_stroke_roll': {
                'sticking': 'RRLLRRL',
                'description': 'Seven stroke roll',
                'typical_tempo': (80, 140),
                'velocity_pattern': [1.0, 0.9, 0.9, 0.9, 0.9, 0.9, 1.0],
                'styles': ['rock', 'jazz']
            },
            'nine_stroke_roll': {
                'sticking': 'RRLLRRLLR',
                'description': 'Nine stroke roll',
                'typical_tempo': (70, 130),
                'velocity_pattern': [1.0, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 1.0],
                'styles': ['rock', 'orchestral']
            },
            'thirteen_stroke_roll': {
                'sticking': 'RRLLRRLLRRLLR',
                'description': 'Thirteen stroke roll',
                'typical_tempo': (60, 120),
                'velocity_pattern': [1.0, 0.9] * 6 + [1.0],
                'styles': ['orchestral', 'jazz']
            },
            'triple_stroke_roll': {
                'sticking': 'RRRLLLRRRLLL',
                'description': 'Three strokes per hand',
                'typical_tempo': (90, 150),
                'velocity_pattern': [1.0, 0.85, 0.85, 1.0, 0.85, 0.85] * 2,
                'styles': ['jazz', 'fusion']
            },
            'swiss_triplet': {
                'sticking': 'lRRlLL',
                'description': 'Drag with triplet feel',
                'typical_tempo': (70, 130),
                'velocity_pattern': [0.3, 1.0, 0.8, 0.3, 1.0, 0.8],
                'styles': ['jazz', 'funk']
            }
        }
    
    def extract_rudiment_features(self, rudiment_name: str) -> HumanizationFeatures:
        """
        Create humanization features from rudiment
        
        Rudiments teach:
        - Accent patterns
        - Ghost note usage
        - Timing consistency
        - Hand coordination
        """
        if rudiment_name not in self.standard_rudiments:
            return None
        
        rudiment = self.standard_rudiments[rudiment_name]
        
        # Rudiments are very consistent (that's the point!)
        # But they teach accent patterns and ghost notes
        
        features = HumanizationFeatures(
            timing_variance=0.01,  # Very consistent
            timing_drift=0.0,
            groove_consistency=0.95,  # Very consistent
            swing_factor=0.0,
            velocity_variance=0.2,  # Good dynamics
            accent_pattern=rudiment['velocity_pattern'],
            ghost_note_frequency=0.3,  # Rudiments have lots of ghost notes
            velocity_humanization=0.1,
            pattern_complexity=0.6,
            fill_frequency=0.0,  # Rudiments aren't fills
            transition_smoothness=0.9,
            hihat_variation=0.0,  # Just snare
            kick_snare_relationship=0.0,
            ride_vs_hihat_ratio=0.0,
            section_awareness=0.0,
            energy_curve=[0.8] * 5,
            drummer_name="Rudiments",
            style="all",
            tempo=float(np.mean(rudiment['typical_tempo'])),
            time_signature=(4, 4)
        )
        
        return features
    
    def batch_extract_rudiments(self) -> int:
        """Extract all standard rudiments"""
        count = 0
        
        for rudiment_name in self.standard_rudiments.keys():
            features = self.extract_rudiment_features(rudiment_name)
            if features:
                self._save_features(features, f"rudiment_{rudiment_name}")
                count += 1
        
        logger.info(f"Extracted {count} rudiment patterns")
        return count
    
    def _save_features(self, features: HumanizationFeatures, source: str):
        """Save features to database"""
        import sqlite3
        from dataclasses import asdict
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO humanization_features (source, drummer_name, style, tempo, features_json)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            source,
            features.drummer_name,
            features.style,
            features.tempo,
            json.dumps(asdict(features))
        ))
        
        conn.commit()
        conn.close()


class SoundsTracksLoopsExtractor:
    """
    Extract training data from SoundsTracks drum loops
    
    These are professionally recorded drum loops:
    - High quality audio
    - Various styles
    - Real performances
    - Mastered sound
    
    Perfect for learning real-world humanization!
    """
    
    def __init__(self, loops_dir: Path, db_path: Path = Path("admin/data/drum_training.db")):
        self.loops_dir = Path(loops_dir)
        self.db_path = db_path
        
        if not AUDIO_LIBS_AVAILABLE:
            raise ImportError("librosa/soundfile not available")
        
        # Use existing analyzer
        self.analyzer = CommercialSongAnalyzer()
        
        logger.info(f"SoundsTracks Loops Extractor initialized: {self.loops_dir}")
    
    def extract_from_loop(self, audio_file: Path, style: str = None) -> Optional[HumanizationFeatures]:
        """
        Extract features from drum loop
        
        Uses the same analysis as commercial songs
        """
        # Extract style from filename if not provided
        if not style:
            style = self._extract_style_from_filename(audio_file.name)
        
        # Extract drummer from filename (if present)
        drummer_name = self._extract_drummer_from_filename(audio_file.name)
        
        # Use commercial song analyzer
        features = self.analyzer.analyze_song(audio_file, drummer_name, style)
        
        return features
    
    def _extract_style_from_filename(self, filename: str) -> str:
        """Extract style from filename"""
        filename_lower = filename.lower()
        
        styles = ['rock', 'jazz', 'funk', 'latin', 'blues', 'metal', 'pop', 'country', 'hip-hop', 'r&b']
        for style in styles:
            if style in filename_lower or style.replace('&', '') in filename_lower:
                return style
        
        return 'unknown'
    
    def _extract_drummer_from_filename(self, filename: str) -> str:
        """Extract drummer name from filename if present"""
        # Many loop libraries include drummer names
        filename_lower = filename.lower()
        
        if 'style' in filename_lower or 'groove' in filename_lower:
            return "Loop Library"
        
        return "Professional Drummer"
    
    def batch_extract(self, limit: int = None) -> int:
        """
        Extract features from all loop files
        
        Args:
            limit: Maximum files to process
        
        Returns:
            Number of files processed
        """
        if not self.loops_dir.exists():
            logger.error(f"Loops directory not found: {self.loops_dir}")
            return 0
        
        # Find all audio files
        audio_files = (
            list(self.loops_dir.rglob('*.wav')) +
            list(self.loops_dir.rglob('*.aif')) +
            list(self.loops_dir.rglob('*.aiff')) +
            list(self.loops_dir.rglob('*.mp3'))
        )
        
        if limit:
            audio_files = audio_files[:limit]
        
        logger.info(f"Found {len(audio_files)} loop files")
        
        count = 0
        for i, audio_file in enumerate(audio_files, 1):
            if i % 10 == 0:
                logger.info(f"Processing {i}/{len(audio_files)}...")
            
            try:
                features = self.extract_from_loop(audio_file)
                if features:
                    count += 1
            except Exception as e:
                logger.error(f"Error processing {audio_file}: {e}")
        
        logger.info(f"Extracted features from {count} loop files")
        return count


def bootstrap_knowledge_base(
    egmd_dir: Path = None,
    rudiments: bool = True,
    loops_dir: Path = None,
    egmd_limit: int = 500,
    loops_limit: int = 100
) -> Dict[str, int]:
    """
    Bootstrap training system with all available databases
    
    Args:
        egmd_dir: Path to E-GMD dataset
        rudiments: Whether to extract rudiments
        loops_dir: Path to SoundsTracks loops
        egmd_limit: Max E-GMD files
        loops_limit: Max loop files
    
    Returns:
        Dictionary with extraction counts
    """
    results = {}
    
    print("=" * 70)
    print("🚀 Bootstrapping Drum Knowledge Base")
    print("=" * 70)
    
    # 1. E-GMD
    if egmd_dir and Path(egmd_dir).exists():
        print("\n1️⃣ Extracting from E-GMD MIDI Dataset...")
        try:
            extractor = EGMDExtractor(egmd_dir)
            count = extractor.batch_extract(limit=egmd_limit)
            results['egmd'] = count
            print(f"   ✅ Extracted {count} E-GMD grooves")
        except Exception as e:
            print(f"   ⚠️ E-GMD extraction failed: {e}")
            results['egmd'] = 0
    else:
        print("\n1️⃣ E-GMD: Skipped (directory not specified or not found)")
        results['egmd'] = 0
    
    # 2. Rudiments
    if rudiments:
        print("\n2️⃣ Extracting Standard Rudiments...")
        try:
            extractor = RudimentsExtractor()
            count = extractor.batch_extract_rudiments()
            results['rudiments'] = count
            print(f"   ✅ Extracted {count} rudiment patterns")
        except Exception as e:
            print(f"   ⚠️ Rudiments extraction failed: {e}")
            results['rudiments'] = 0
    else:
        results['rudiments'] = 0
    
    # 3. SoundsTracks Loops
    if loops_dir and Path(loops_dir).exists():
        print("\n3️⃣ Extracting from SoundsTracks Loops...")
        try:
            extractor = SoundsTracksLoopsExtractor(loops_dir)
            count = extractor.batch_extract(limit=loops_limit)
            results['loops'] = count
            print(f"   ✅ Extracted {count} drum loops")
        except Exception as e:
            print(f"   ⚠️ Loops extraction failed: {e}")
            results['loops'] = 0
    else:
        print("\n3️⃣ SoundsTracks Loops: Skipped (directory not specified or not found)")
        results['loops'] = 0
    
    # Summary
    total = sum(results.values())
    
    print("\n" + "=" * 70)
    print(f"✅ Knowledge Base Bootstrap Complete!")
    print("=" * 70)
    print(f"\nTotal training samples added: {total}")
    print(f"  - E-GMD MIDI grooves: {results.get('egmd', 0)}")
    print(f"  - Rudiment patterns: {results.get('rudiments', 0)}")
    print(f"  - Drum loops: {results.get('loops', 0)}")
    
    if total >= 100:
        print(f"\n🎉 Excellent! You have {total} training samples")
        print("   Ready to train a robust model!")
    elif total >= 50:
        print(f"\n✅ Good! You have {total} training samples")
        print("   Enough for initial training")
    else:
        print(f"\n⚠️ Only {total} samples")
        print("   Add more databases or download from YouTube")
    
    return results


def test_bootstrapper():
    """Test the bootstrapper"""
    print("🧪 Testing Database Bootstrapper")
    print("=" * 60)
    
    # Test rudiments (doesn't need external data)
    print("\n📝 Testing Rudiments Extractor...")
    try:
        extractor = RudimentsExtractor()
        print(f"   Available rudiments: {len(extractor.standard_rudiments)}")
        
        # Test extracting one rudiment
        features = extractor.extract_rudiment_features('single_stroke_roll')
        if features:
            print(f"   ✅ Extracted single stroke roll features")
            print(f"      Timing variance: {features.timing_variance:.4f}")
            print(f"      Ghost note frequency: {features.ghost_note_frequency:.2f}")
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
    
    print("\n✅ Bootstrapper test complete")
    print("\nTo use:")
    print("  bootstrap_knowledge_base(")
    print("      egmd_dir=Path('path/to/egmd'),")
    print("      rudiments=True,")
    print("      loops_dir=Path('path/to/loops')")
    print("  )")


if __name__ == "__main__":
    test_bootstrapper()
