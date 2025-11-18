"""
Prepare Training Data for GrooVAE
Extracts features from 91,074 MIDI patterns and creates train/val/test splits
"""

import sqlite3
import numpy as np
import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple
import mido

class TrainingDataPreparator:
    def __init__(self, db_path: str = "f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db"):
        self.db_path = db_path
        self.patterns = []
        
    def load_patterns_from_db(self):
        """Load all patterns from database"""
        print("📊 Loading patterns from database...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path, tempo_bpm, time_signature, duration_bars,
                   style, complexity, density,
                   kick_pattern, snare_pattern, hihat_pattern,
                   kick_count, snare_count, hihat_count
            FROM drum_patterns
            WHERE tempo_bpm > 0 AND duration_bars > 0
        """)
        
        rows = cursor.fetchall()
        print(f"✓ Loaded {len(rows):,} patterns")
        
        for row in rows:
            pattern = {
                'file_path': row[0],
                'tempo': row[1],
                'time_sig': row[2],
                'duration': row[3],
                'style': row[4] or 'unknown',
                'complexity': row[5] or 0.5,
                'density': row[6] or 1.0,
                'kick_pattern': json.loads(row[7]) if row[7] else [],
                'snare_pattern': json.loads(row[8]) if row[8] else [],
                'hihat_pattern': json.loads(row[9]) if row[9] else [],
                'kick_count': row[10],
                'snare_count': row[11],
                'hihat_count': row[12]
            }
            self.patterns.append(pattern)
        
        conn.close()
        return self.patterns
    
    def extract_midi_features(self, file_path: str) -> np.ndarray:
        """Extract detailed MIDI features as a piano roll"""
        try:
            mid = mido.MidiFile(file_path)
            
            # Create piano roll: 8 drum lanes x 128 time steps (32 bars @ 1/16 notes)
            # Lanes: 0=kick, 1=snare, 2=hihat_closed, 3=hihat_open, 4=ride, 5=toms, 6=crash, 7=other
            piano_roll = np.zeros((8, 128), dtype=np.float32)
            
            # Calculate ticks per 16th note
            ticks_per_beat = mid.ticks_per_beat
            ticks_per_16th = ticks_per_beat // 4
            
            # Extract notes
            time = 0
            for track in mid.tracks:
                for msg in track:
                    time += msg.time
                    if msg.type == 'note_on' and msg.velocity > 0:
                        # Calculate position in 16th notes
                        position = int(time / ticks_per_16th)
                        if position >= 128:
                            continue
                        
                        # Map to drum lane
                        lane = self._midi_note_to_lane(msg.note)
                        if lane is not None:
                            piano_roll[lane, position] = msg.velocity / 127.0
            
            return piano_roll
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return np.zeros((8, 128), dtype=np.float32)
    
    def _midi_note_to_lane(self, note: int) -> int:
        """Map MIDI note to drum lane"""
        # GM drum mapping
        if note == 36:  # Kick
            return 0
        elif note == 38:  # Snare
            return 1
        elif note in [42, 44]:  # Closed hi-hat
            return 2
        elif note == 46:  # Open hi-hat
            return 3
        elif note == 51:  # Ride
            return 4
        elif note in [41, 43, 45, 47, 48, 50]:  # Toms
            return 5
        elif note in [49, 55, 57]:  # Crash
            return 6
        else:
            return 7  # Other
    
    def create_feature_vectors(self):
        """Create normalized feature vectors for all patterns"""
        print("\n🔧 Creating feature vectors...")
        
        features = []
        labels = []
        
        for idx, pattern in enumerate(self.patterns):
            if idx % 1000 == 0:
                print(f"  Processed {idx:,}/{len(self.patterns):,}...")
            
            # Extract piano roll from MIDI
            piano_roll = self.extract_midi_features(pattern['file_path'])
            
            # Flatten to 1D vector (8 * 128 = 1024 dimensions)
            feature_vector = piano_roll.flatten()
            
            # Add metadata features
            meta_features = np.array([
                pattern['tempo'] / 200.0,  # Normalize to 0-1
                pattern['complexity'],
                pattern['density'] / 10.0,
                pattern['kick_count'] / 100.0,
                pattern['snare_count'] / 100.0,
                pattern['hihat_count'] / 200.0
            ], dtype=np.float32)
            
            # Combine
            full_feature = np.concatenate([feature_vector, meta_features])
            
            features.append(full_feature)
            
            # Label (style)
            labels.append(pattern['style'])
        
        print(f"✓ Created {len(features):,} feature vectors")
        print(f"  Feature dimension: {features[0].shape[0]}")
        
        return np.array(features), labels
    
    def split_data(self, features: np.ndarray, labels: List[str], 
                   train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
        """Split data into train/val/test sets"""
        print("\n📊 Splitting data...")
        
        n_samples = len(features)
        indices = np.random.permutation(n_samples)
        
        train_end = int(n_samples * train_ratio)
        val_end = int(n_samples * (train_ratio + val_ratio))
        
        train_idx = indices[:train_end]
        val_idx = indices[train_end:val_end]
        test_idx = indices[val_end:]
        
        splits = {
            'train': {
                'features': features[train_idx],
                'labels': [labels[i] for i in train_idx],
                'patterns': [self.patterns[i] for i in train_idx]
            },
            'val': {
                'features': features[val_idx],
                'labels': [labels[i] for i in val_idx],
                'patterns': [self.patterns[i] for i in val_idx]
            },
            'test': {
                'features': features[test_idx],
                'labels': [labels[i] for i in test_idx],
                'patterns': [self.patterns[i] for i in test_idx]
            }
        }
        
        print(f"✓ Train: {len(train_idx):,} samples")
        print(f"✓ Val:   {len(val_idx):,} samples")
        print(f"✓ Test:  {len(test_idx):,} samples")
        
        return splits
    
    def save_prepared_data(self, splits: Dict, output_dir: str = "E:/DrumTracKAI_Master/03_Training_Data/preprocessed"):
        """Save prepared data to disk"""
        print(f"\n💾 Saving prepared data to {output_dir}...")
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for split_name, split_data in splits.items():
            # Save features (numpy array)
            features_file = f"{output_dir}/{split_name}_features.npy"
            np.save(features_file, split_data['features'])
            
            # Save metadata (pickle)
            meta_file = f"{output_dir}/{split_name}_metadata.pkl"
            with open(meta_file, 'wb') as f:
                pickle.dump({
                    'labels': split_data['labels'],
                    'patterns': split_data['patterns']
                }, f)
            
            print(f"  ✓ {split_name}: {features_file}")
        
        # Save normalization statistics
        all_features = np.concatenate([
            splits['train']['features'],
            splits['val']['features'],
            splits['test']['features']
        ])
        
        stats = {
            'mean': np.mean(all_features, axis=0),
            'std': np.std(all_features, axis=0),
            'min': np.min(all_features, axis=0),
            'max': np.max(all_features, axis=0)
        }
        
        stats_file = f"{output_dir}/normalization_stats.pkl"
        with open(stats_file, 'wb') as f:
            pickle.dump(stats, f)
        
        print(f"  ✓ Stats: {stats_file}")
        print("\n✅ Data preparation complete!")
    
    def prepare_all(self):
        """Complete data preparation pipeline"""
        print("🎯 AI Training Data Preparation Pipeline")
        print("="*70)
        
        # Load patterns
        self.load_patterns_from_db()
        
        # Create features
        features, labels = self.create_feature_vectors()
        
        # Split data
        splits = self.split_data(features, labels)
        
        # Save
        self.save_prepared_data(splits)
        
        print("\n🎯 Next Step: Train GrooVAE model")
        print("   Run: python train_groove_vae.py")

if __name__ == "__main__":
    preparator = TrainingDataPreparator()
    preparator.prepare_all()
