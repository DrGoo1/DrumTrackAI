"""
Dataset Builder for LLM Training
Builds training datasets from extracted features
"""

import json
import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from sklearn.model_selection import train_test_split
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TrainingDataset:
    """Training dataset container"""
    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    feature_names: List[str]
    metadata: Dict


class DrumDatasetBuilder:
    """Build training datasets from extracted features"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use absolute path relative to this module's location
            module_dir = Path(__file__).parent.parent
            db_path = module_dir / "data" / "drum_training.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Dataset Builder initialized: {self.db_path}")
    
    def load_all_features(self) -> List[Dict]:
        """Load all humanization features from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM humanization_features')
        rows = cursor.fetchall()
        conn.close()
        
        features = []
        for row in rows:
            features.append({
                'id': row[0],
                'source': row[1],
                'drummer_name': row[2],
                'style': row[3],
                'tempo': row[4],
                'features_json': json.loads(row[5]),
                'created_at': row[6]
            })
        
        logger.info(f"Loaded {len(features)} feature records")
        return features
    
    def build_humanization_dataset(self,
                                   min_samples: int = 50,
                                   test_size: float = 0.2,
                                   val_size: float = 0.1) -> TrainingDataset:
        """
        Build dataset for humanization model training
        
        Returns dataset with:
        - X: Input features (pattern info, tempo, style)
        - y: Target features (humanization parameters)
        """
        features = self.load_all_features()
        
        if len(features) < min_samples:
            raise ValueError(f"Not enough samples: {len(features)} < {min_samples}")
        
        # Convert to feature matrices
        X, y, feature_names = self._features_to_arrays(features)
        
        # Split dataset
        # First split: train+val and test
        X_trainval, X_test, y_trainval, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Second split: train and val
        val_ratio = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_trainval, y_trainval, test_size=val_ratio, random_state=42
        )
        
        logger.info(f"Dataset split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")
        
        return TrainingDataset(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            y_test=y_test,
            feature_names=feature_names,
            metadata={
                'total_samples': len(features),
                'feature_count': X.shape[1],
                'target_count': y.shape[1]
            }
        )
    
    def _features_to_arrays(self, features: List[Dict]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Convert feature dicts to numpy arrays"""
        X_list = []
        y_list = []
        
        for feat in features:
            feat_json = feat['features_json']
            
            # Input features (what we know about the pattern)
            x = [
                feat['tempo'] or 120.0,
                self._style_to_int(feat['style']),
                feat_json.get('pattern_complexity', 0.7),
            ]
            
            # Target features (humanization parameters to learn)
            y = [
                feat_json.get('timing_variance', 0.0),
                feat_json.get('timing_drift', 0.0),
                feat_json.get('groove_consistency', 0.8),
                feat_json.get('swing_factor', 0.0),
                feat_json.get('velocity_variance', 0.15),
                feat_json.get('ghost_note_frequency', 0.15),
                feat_json.get('velocity_humanization', 0.12),
                feat_json.get('hihat_variation', 0.3),
                feat_json.get('kick_snare_relationship', 0.75),
            ]
            
            X_list.append(x)
            y_list.append(y)
        
        feature_names = [
            'tempo', 'style', 'pattern_complexity',
            # Targets
            'timing_variance', 'timing_drift', 'groove_consistency', 
            'swing_factor', 'velocity_variance', 'ghost_note_frequency',
            'velocity_humanization', 'hihat_variation', 'kick_snare_relationship'
        ]
        
        return np.array(X_list), np.array(y_list), feature_names
    
    def _style_to_int(self, style: Optional[str]) -> int:
        """Convert style string to integer"""
        style_map = {
            'rock': 0,
            'funk': 1,
            'jazz': 2,
            'latin': 3,
            'metal': 4,
            'pop': 5,
            'live_recording': 6
        }
        return style_map.get(style, 0)
    
    def export_dataset(self, dataset: TrainingDataset, output_dir: Path):
        """Export dataset to files for training"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save numpy arrays
        np.save(output_dir / 'X_train.npy', dataset.X_train)
        np.save(output_dir / 'y_train.npy', dataset.y_train)
        np.save(output_dir / 'X_val.npy', dataset.X_val)
        np.save(output_dir / 'y_val.npy', dataset.y_val)
        np.save(output_dir / 'X_test.npy', dataset.X_test)
        np.save(output_dir / 'y_test.npy', dataset.y_test)
        
        # Save metadata
        metadata = {
            'feature_names': dataset.feature_names,
            'metadata': dataset.metadata,
            'created_at': str(Path().cwd())
        }
        
        with open(output_dir / 'dataset_info.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Dataset exported to {output_dir}")
    
    def get_dataset_stats(self) -> Dict:
        """Get statistics about available data"""
        features = self.load_all_features()
        
        stats = {
            'total_samples': len(features),
            'drummers': {},
            'styles': {},
            'sources': {}
        }
        
        for feat in features:
            # Count by drummer
            drummer = feat['drummer_name'] or 'unknown'
            stats['drummers'][drummer] = stats['drummers'].get(drummer, 0) + 1
            
            # Count by style
            style = feat['style'] or 'unknown'
            stats['styles'][style] = stats['styles'].get(style, 0) + 1
            
            # Count by source type
            source_type = 'commercial' if 'wav' in feat['source'] or 'mp3' in feat['source'] else 'sensor'
            stats['sources'][source_type] = stats['sources'].get(source_type, 0) + 1
        
        return stats


class HumanizationDataset:
    """PyTorch-compatible dataset for humanization training"""
    
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = X
        self.y = y
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]
    
    def batch(self, batch_size: int):
        """Generator for batches"""
        for i in range(0, len(self), batch_size):
            yield self.X[i:i+batch_size], self.y[i:i+batch_size]


def test_dataset_builder():
    """Test the dataset builder"""
    print("🧪 Testing Dataset Builder")
    print("=" * 60)
    
    builder = DrumDatasetBuilder()
    
    # Get stats
    print("\n📊 Dataset Statistics:")
    try:
        stats = builder.get_dataset_stats()
        print(f"   Total samples: {stats['total_samples']}")
        print(f"   Drummers: {stats['drummers']}")
        print(f"   Styles: {stats['styles']}")
        print(f"   Sources: {stats['sources']}")
        
        # Try building dataset if we have enough data
        if stats['total_samples'] >= 10:
            print("\n🔨 Building dataset...")
            dataset = builder.build_humanization_dataset(min_samples=10)
            print(f"   Train: {len(dataset.X_train)}")
            print(f"   Val: {len(dataset.X_val)}")
            print(f"   Test: {len(dataset.X_test)}")
            print(f"   Features: {len(dataset.feature_names)}")
            print("   ✅ Dataset built successfully")
        else:
            print(f"\n⚠️ Not enough data yet ({stats['total_samples']} samples)")
            print("   Run data extraction first to gather training data")
            
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
        print("   This is expected if no data has been extracted yet")
    
    print("\n✅ Dataset builder test complete")


if __name__ == "__main__":
    test_dataset_builder()
