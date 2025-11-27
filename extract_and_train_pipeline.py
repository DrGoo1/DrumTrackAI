#!/usr/bin/env python3
"""
Complete E-GMD Pipeline: Extract → Build Dataset → Train Models
================================================================
Fully automated from extraction to trained models
"""
import sqlite3
import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("E-GMD COMPLETE PIPELINE - AUTOMATED")
print("=" * 70)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================================================
# PHASE 1: EXTRACTION
# ============================================================================

print("\n" + "=" * 70)
print("PHASE 1: FEATURE EXTRACTION")
print("=" * 70)

db_path = Path("admin/data/drum_training.db")

# Drop old table
conn = sqlite3.connect(db_path)
cur = conn.cursor()
print("\n🗑️  Dropping old table...")
cur.execute("DROP TABLE IF EXISTS egmd_midi_features")
conn.commit()
conn.close()
print("   ✅ Old table dropped")

print("\n🚀 Extracting all 91,074 E-GMD MIDI files...")
print("   Estimated time: ~90 minutes\n")

from admin.training.egmd_midi_extractor import EGMDMIDIExtractor

egmd_path = Path("E:\\E-GMD Dataset")
extractor = EGMDMIDIExtractor()

def extraction_progress(current, total, stats):
    if current % 500 == 0 or current == total:
        elapsed = stats.get('elapsed_time', 0)
        files_per_sec = stats.get('files_per_second', 0)
        remaining = (total - current) / files_per_sec if files_per_sec > 0 else 0
        
        print(f"[{current:6,}/{total:,}] "
              f"Success: {stats['successful']:6,} | "
              f"Failed: {stats['failed']:4} | "
              f"Speed: {files_per_sec:5.1f}/sec | "
              f"ETA: {remaining/60:.0f}m")
    return True

extraction_results = extractor.batch_extract(
    egmd_path=egmd_path,
    max_files=None,
    progress_callback=extraction_progress
)

print("\n✅ PHASE 1 COMPLETE!")
print(f"   Extracted: {extraction_results['successful']:,} files")
print(f"   Time: {extraction_results['elapsed_time']/60:.1f} minutes")

# ============================================================================
# PHASE 2: BUILD TRAINING DATASET
# ============================================================================

print("\n" + "=" * 70)
print("PHASE 2: BUILD TRAINING DATASET")
print("=" * 70)

print("\n📊 Loading extracted features from database...")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get all features
cur.execute("""
    SELECT 
        total_hits, duration, tempo, time_signature,
        drum_counts_json, velocity_stats_json, 
        timing_features_json, pattern_density,
        ghost_notes, accents, sequential_patterns_json,
        hihat_articulations_json, fill_segments_json,
        velocity_curve_json, swing_amount, style_hints_json
    FROM egmd_midi_features
""")

all_data = cur.fetchall()
conn.close()

print(f"   Loaded {len(all_data):,} feature sets")

print("\n🔧 Converting to training format...")

# Build feature vectors
X = []  # Input features
y_style = []  # Style labels
y_humanization = []  # Humanization targets

for row in all_data:
    (total_hits, duration, tempo, time_sig,
     drum_counts_json, velocity_stats_json, timing_json, density,
     ghost_notes, accents, seq_patterns_json,
     hihat_json, fills_json, velocity_curve_json, swing, style_hints_json) = row
    
    # Parse JSON fields
    drum_counts = json.loads(drum_counts_json) if drum_counts_json else {}
    velocity_stats = json.loads(velocity_stats_json) if velocity_stats_json else {}
    style_hints = json.loads(style_hints_json) if style_hints_json else []
    velocity_curve = json.loads(velocity_curve_json) if velocity_curve_json else []
    
    # Build feature vector
    features = [
        total_hits,
        duration,
        tempo,
        density,
        ghost_notes,
        accents,
        swing,
        # Drum counts (normalized)
        drum_counts.get('kick', 0) / max(total_hits, 1),
        drum_counts.get('snare', 0) / max(total_hits, 1),
        drum_counts.get('hihat_closed', 0) / max(total_hits, 1),
        drum_counts.get('hihat_open', 0) / max(total_hits, 1),
        drum_counts.get('ride', 0) / max(total_hits, 1),
        drum_counts.get('crash', 0) / max(total_hits, 1),
        drum_counts.get('tom_low', 0) / max(total_hits, 1),
        drum_counts.get('tom_mid', 0) / max(total_hits, 1),
        drum_counts.get('tom_high', 0) / max(total_hits, 1),
    ]
    
    # Add velocity curve (pad to 10 if needed)
    vel_curve_padded = (velocity_curve + [0] * 10)[:10]
    features.extend(vel_curve_padded)
    
    X.append(features)
    
    # Style classification targets
    style_vector = [
        1 if 'hihat_heavy' in style_hints else 0,
        1 if 'ride_heavy' in style_hints else 0,
        1 if 'kick_heavy' in style_hints else 0,
        1 if 'ghost_note_heavy' in style_hints else 0,
        1 if 'accent_heavy' in style_hints else 0,
        1 if 'high_dynamics' in style_hints else 0,
        1 if 'low_dynamics' in style_hints else 0,
    ]
    y_style.append(style_vector)
    
    # Humanization targets (timing variance, velocity variance, swing)
    humanization = [
        ghost_notes / max(total_hits, 1),  # Ghost note ratio
        accents / max(total_hits, 1),       # Accent ratio
        swing,                               # Swing amount
    ]
    y_humanization.append(humanization)

# Convert to numpy arrays
X = np.array(X, dtype=np.float32)
y_style = np.array(y_style, dtype=np.float32)
y_humanization = np.array(y_humanization, dtype=np.float32)

print(f"   Feature matrix shape: {X.shape}")
print(f"   Style labels shape: {y_style.shape}")
print(f"   Humanization labels shape: {y_humanization.shape}")

# Train/val/test split
print("\n📊 Creating train/val/test splits...")

from sklearn.model_selection import train_test_split

# 80% train, 10% val, 10% test
X_train, X_temp, y_style_train, y_style_temp, y_human_train, y_human_temp = train_test_split(
    X, y_style, y_humanization, test_size=0.2, random_state=42
)

X_val, X_test, y_style_val, y_style_test, y_human_val, y_human_test = train_test_split(
    X_temp, y_style_temp, y_human_temp, test_size=0.5, random_state=42
)

print(f"   Train: {len(X_train):,} samples")
print(f"   Val:   {len(X_val):,} samples")
print(f"   Test:  {len(X_test):,} samples")

# Save datasets
dataset_dir = Path("admin/models/egmd_datasets")
dataset_dir.mkdir(parents=True, exist_ok=True)

np.save(dataset_dir / "X_train.npy", X_train)
np.save(dataset_dir / "X_val.npy", X_val)
np.save(dataset_dir / "X_test.npy", X_test)
np.save(dataset_dir / "y_style_train.npy", y_style_train)
np.save(dataset_dir / "y_style_val.npy", y_style_val)
np.save(dataset_dir / "y_style_test.npy", y_style_test)
np.save(dataset_dir / "y_human_train.npy", y_human_train)
np.save(dataset_dir / "y_human_val.npy", y_human_val)
np.save(dataset_dir / "y_human_test.npy", y_human_test)

print(f"\n✅ PHASE 2 COMPLETE!")
print(f"   Datasets saved to: {dataset_dir}")

# ============================================================================
# PHASE 3: TRAIN STYLE CLASSIFIER
# ============================================================================

print("\n" + "=" * 70)
print("PHASE 3: TRAIN STYLE CLASSIFIER")
print("=" * 70)

print("\n🤖 Building style classifier model...")

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader
    
    TORCH_AVAILABLE = True
except ImportError:
    print("❌ PyTorch not available - skipping model training")
    TORCH_AVAILABLE = False

if TORCH_AVAILABLE:
    # Define model
    class StyleClassifier(nn.Module):
        def __init__(self, input_size, num_styles):
            super().__init__()
            self.model = nn.Sequential(
                nn.Linear(input_size, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(64, num_styles),
                nn.Sigmoid()
            )
        
        def forward(self, x):
            return self.model(x)
    
    input_size = X_train.shape[1]
    num_styles = y_style_train.shape[1]
    
    model = StyleClassifier(input_size, num_styles)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Create data loaders
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train),
        torch.FloatTensor(y_style_train)
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X_val),
        torch.FloatTensor(y_style_val)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32)
    
    print(f"   Model: {input_size} inputs → {num_styles} style outputs")
    print(f"   Training for 20 epochs...")
    
    # Train
    best_val_loss = float('inf')
    
    for epoch in range(20):
        # Train
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        # Validate
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                val_loss += loss.item()
        
        train_loss /= len(train_loader)
        val_loss /= len(val_loader)
        
        if (epoch + 1) % 5 == 0:
            print(f"   Epoch {epoch+1:2d}/20 | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), dataset_dir.parent / "style_classifier.pth")
    
    print(f"\n✅ PHASE 3 COMPLETE!")
    print(f"   Best val loss: {best_val_loss:.4f}")
    print(f"   Model saved: {dataset_dir.parent / 'style_classifier.pth'}")

# ============================================================================
# PHASE 4: TRAIN HUMANIZATION MODEL
# ============================================================================

print("\n" + "=" * 70)
print("PHASE 4: TRAIN HUMANIZATION MODEL")
print("=" * 70)

if TORCH_AVAILABLE:
    print("\n🤖 Building humanization model...")
    
    class HumanizationModel(nn.Module):
        def __init__(self, input_size, output_size):
            super().__init__()
            self.model = nn.Sequential(
                nn.Linear(input_size, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(64, output_size),
                nn.Sigmoid()
            )
        
        def forward(self, x):
            return self.model(x)
    
    output_size = y_human_train.shape[1]
    
    model = HumanizationModel(input_size, output_size)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Create data loaders
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train),
        torch.FloatTensor(y_human_train)
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X_val),
        torch.FloatTensor(y_human_val)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32)
    
    print(f"   Model: {input_size} inputs → {output_size} humanization outputs")
    print(f"   Training for 20 epochs...")
    
    best_val_loss = float('inf')
    
    for epoch in range(20):
        # Train
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        # Validate
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                val_loss += loss.item()
        
        train_loss /= len(train_loader)
        val_loss /= len(val_loader)
        
        if (epoch + 1) % 5 == 0:
            print(f"   Epoch {epoch+1:2d}/20 | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), dataset_dir.parent / "humanization_model.pth")
    
    print(f"\n✅ PHASE 4 COMPLETE!")
    print(f"   Best val loss: {best_val_loss:.4f}")
    print(f"   Model saved: {dataset_dir.parent / 'humanization_model.pth'}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("🎉 PIPELINE COMPLETE!")
print("=" * 70)

print(f"\n✅ Phase 1: Extracted {extraction_results['successful']:,} E-GMD files")
print(f"✅ Phase 2: Built training datasets ({len(X_train):,} train samples)")
if TORCH_AVAILABLE:
    print(f"✅ Phase 3: Trained style classifier")
    print(f"✅ Phase 4: Trained humanization model")

print(f"\n📁 Output Files:")
print(f"   Datasets: {dataset_dir}/")
if TORCH_AVAILABLE:
    print(f"   Models:   {dataset_dir.parent}/")
    print(f"      - style_classifier.pth")
    print(f"      - humanization_model.pth")

print(f"\n⏱️  Total Pipeline Time: {extraction_results['elapsed_time']/60:.1f} minutes")
print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

print("\n🚀 Your E-GMD models are trained and ready!")
print("=" * 70)
