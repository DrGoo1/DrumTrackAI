"""
AI Pattern Generator - Production Integration
Combines SQL pattern matching + VAE AI generation + Drummer styling
"""

import torch
import numpy as np
import sqlite3
import json
from typing import List, Dict, Optional
from pathlib import Path
from groove_vae_model import GrooVAE
from drummer_mapping_service import get_drummer_service
from drummer_categories import get_category_service
import mido
from datetime import datetime

class AIPatternGenerator:
    """
    Ultimate AI-Powered Drum Pattern Generator
    
    Pipeline:
    1. SQL pattern matching (fast, deterministic)
    2. VAE encoding to latent space
    3. Intelligent blending/interpolation
    4. VAE decoding to new pattern
    5. Drummer profile styling
    6. Humanization
    7. MIDI export
    """
    
    def __init__(self, 
                 model_path: str = "E:/DrumTracKAI_Master/04_Models/current/groove_vae_best.pth",
                 db_path: str = "f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db",
                 device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        
        print("🚀 Initializing AI Pattern Generator...")
        self.device = device
        self.db_path = db_path
        
        # Load VAE model
        print(f"  Loading GrooVAE model ({device})...")
        self.model = GrooVAE(latent_dim=64, hidden_dim=512).to(device)
        checkpoint = torch.load(model_path, map_location=device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        print(f"  ✓ Model loaded (val_loss: {checkpoint['val_loss']:.4f})")
        
        # Database connection
        self.db = sqlite3.connect(db_path)
        self.cursor = self.db.cursor()
        print(f"  ✓ Database connected")
        
        # Drummer mapping service
        self.drummer_service = get_drummer_service()
        self.category_service = get_category_service()
        print(f"  ✓ Drummer mapping & category services loaded")
        
        print("✅ AI Pattern Generator ready!")
    
    def find_similar_patterns(self, 
                              tempo: float,
                              style: str,
                              section: str = 'verse',
                              complexity: float = 0.5,
                              n_results: int = 5) -> List[Dict]:
        """
        Step 1: Find similar patterns from database using SQL
        
        Args:
            tempo: Target tempo (BPM)
            style: Musical style (rock, funk, jazz, etc.)
            section: Song section (verse, chorus, bridge)
            complexity: Pattern complexity (0-1)
            n_results: Number of patterns to return
        
        Returns:
            List of matching patterns with metadata
        """
        print(f"\n🔍 Finding similar patterns...")
        print(f"  Tempo: {tempo} BPM, Style: {style}, Section: {section}")
        
        # SQL query with tolerance
        tempo_min = tempo * 0.9
        tempo_max = tempo * 1.1
        complexity_min = max(0, complexity - 0.2)
        complexity_max = min(1, complexity + 0.2)
        
        query = """
            SELECT file_path, tempo_bpm, style, complexity, density,
                   kick_pattern, snare_pattern, hihat_pattern,
                   kick_count, snare_count, hihat_count
            FROM drum_patterns
            WHERE tempo_bpm BETWEEN ? AND ?
              AND style LIKE ?
              AND complexity BETWEEN ? AND ?
              AND duration_bars >= 1
            ORDER BY ABS(tempo_bpm - ?) ASC
            LIMIT ?
        """
        
        self.cursor.execute(query, (
            tempo_min, tempo_max,
            f'%{style}%',
            complexity_min, complexity_max,
            tempo,
            n_results
        ))
        
        rows = self.cursor.fetchall()
        
        patterns = []
        for row in rows:
            patterns.append({
                'file_path': row[0],
                'tempo': row[1],
                'style': row[2],
                'complexity': row[3],
                'density': row[4],
                'kick_pattern': json.loads(row[5]) if row[5] else [],
                'snare_pattern': json.loads(row[6]) if row[6] else [],
                'hihat_pattern': json.loads(row[7]) if row[7] else [],
                'kick_count': row[8],
                'snare_count': row[9],
                'hihat_count': row[10]
            })
        
        print(f"  ✓ Found {len(patterns)} matching patterns")
        return patterns
    
    def extract_features_from_midi(self, midi_path: str) -> np.ndarray:
        """Extract feature vector from MIDI file"""
        try:
            mid = mido.MidiFile(midi_path)
            
            # Create piano roll
            piano_roll = np.zeros((8, 128), dtype=np.float32)
            
            ticks_per_beat = mid.ticks_per_beat
            ticks_per_16th = ticks_per_beat // 4
            
            time = 0
            for track in mid.tracks:
                for msg in track:
                    time += msg.time
                    if msg.type == 'note_on' and msg.velocity > 0:
                        position = int(time / ticks_per_16th)
                        if position >= 128:
                            continue
                        
                        lane = self._midi_note_to_lane(msg.note)
                        if lane is not None:
                            piano_roll[lane, position] = msg.velocity / 127.0
            
            # Flatten and add metadata (zeros for now - would come from analysis)
            feature_vector = np.concatenate([
                piano_roll.flatten(),
                np.zeros(6, dtype=np.float32)  # Metadata placeholder
            ])
            
            return feature_vector
        
        except Exception as e:
            print(f"  ⚠️  Error loading MIDI: {e}")
            return np.zeros(1030, dtype=np.float32)
    
    def _midi_note_to_lane(self, note: int) -> Optional[int]:
        """Map MIDI note to drum lane"""
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
    
    def generate_ai_pattern(self,
                           tempo: float,
                           style: str,
                           section: str = 'verse',
                           complexity: float = 0.5,
                           creativity: float = 0.3,
                           drummer_profile: Optional[str] = None) -> Dict:
        """
        Complete AI generation pipeline
        
        Args:
            tempo: Target tempo (BPM)
            style: Musical style
            section: Song section
            complexity: Pattern complexity (0-1)
            creativity: How different from references (0-1)
            drummer_profile: Drummer style to apply
        
        Returns:
            Generated pattern as dict with MIDI data
        """
        print("\n" + "="*70)
        print(f"🎵 GENERATING AI DRUM PATTERN")
        print("="*70)
        
        # Step 1: Find similar patterns from database
        reference_patterns = self.find_similar_patterns(
            tempo=tempo,
            style=style,
            section=section,
            complexity=complexity,
            n_results=5
        )
        
        if len(reference_patterns) == 0:
            print("  ⚠️  No reference patterns found, generating from scratch")
            return self._generate_from_scratch(tempo, style)
        
        # Step 2: Extract features from reference patterns
        print(f"\n🔧 Extracting features from {len(reference_patterns)} patterns...")
        feature_vectors = []
        
        for pattern in reference_patterns:
            features = self.extract_features_from_midi(pattern['file_path'])
            feature_vectors.append(features)
        
        # Convert to tensors
        features_tensor = torch.FloatTensor(np.array(feature_vectors)).to(self.device)
        
        # Step 3: Encode to latent space
        print(f"\n🧠 Encoding to latent space...")
        with torch.no_grad():
            latent_vectors = []
            for features in features_tensor:
                mu, logvar = self.model.encode(features.unsqueeze(0))
                latent_vectors.append(mu)
            
            latent_vectors = torch.cat(latent_vectors, dim=0)
        
        # Step 4: Blend in latent space
        print(f"\n🎨 Blending patterns (creativity: {creativity})...")
        
        if creativity < 0.5:
            # Low creativity: weighted average of references
            blended_latent = torch.mean(latent_vectors, dim=0, keepdim=True)
        else:
            # High creativity: add random variation
            blended_latent = torch.mean(latent_vectors, dim=0, keepdim=True)
            noise = torch.randn_like(blended_latent) * creativity * 0.5
            blended_latent = blended_latent + noise
        
        # Step 5: Decode to pattern
        print(f"\n🎹 Decoding to drum pattern...")
        with torch.no_grad():
            generated_piano_roll = self.model.decode(blended_latent)
            generated_piano_roll = generated_piano_roll.cpu().numpy()[0].reshape(8, 128)
        
        # Step 6: Apply drummer profile (if specified)
        if drummer_profile:
            print(f"\n👤 Applying {drummer_profile} drummer profile...")
            generated_piano_roll = self._apply_drummer_profile(
                generated_piano_roll,
                drummer_profile
            )
        
        # Step 7: Humanization
        print(f"\n🎭 Applying humanization...")
        generated_piano_roll = self._humanize_pattern(generated_piano_roll)
        
        # Step 8: Convert to MIDI
        print(f"\n💾 Converting to MIDI...")
        midi_data = self._pattern_to_midi(generated_piano_roll, tempo)
        
        # Step 9: Calculate statistics
        stats = self._calculate_pattern_stats(generated_piano_roll)
        
        result = {
            'piano_roll': generated_piano_roll.tolist(),
            'midi_base64': midi_data,
            'tempo': tempo,
            'style': style,
            'section': section,
            'stats': stats,
            'reference_count': len(reference_patterns),
            'creativity': creativity,
            'drummer_profile': drummer_profile,
            'timestamp': datetime.now().isoformat()
        }
        
        print("\n✅ Pattern generation complete!")
        print(f"  Kick: {stats['kick_count']}, Snare: {stats['snare_count']}, HiHat: {stats['hihat_count']}")
        
        return result
    
    def _generate_from_scratch(self, tempo: float, style: str) -> Dict:
        """Generate pattern from random latent vector"""
        print("  Generating from random latent space...")
        
        with torch.no_grad():
            generated_piano_roll = self.model.generate(num_samples=1)
            generated_piano_roll = generated_piano_roll.cpu().numpy()[0].reshape(8, 128)
        
        midi_data = self._pattern_to_midi(generated_piano_roll, tempo)
        stats = self._calculate_pattern_stats(generated_piano_roll)
        
        return {
            'piano_roll': generated_piano_roll.tolist(),
            'midi_base64': midi_data,
            'tempo': tempo,
            'style': style,
            'stats': stats,
            'reference_count': 0,
            'creativity': 1.0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _apply_drummer_profile(self, piano_roll: np.ndarray, profile: str) -> np.ndarray:
        """
        Apply drummer-specific characteristics using quantified style vectors
        Supports category-based numbered drummers (pure individual characteristics)
        """
        # Map category drummer ID to source drummer ID
        source_drummer_id = self.category_service.get_source_drummer_id(profile)
        
        if not source_drummer_id:
            # Fallback: try as direct source drummer ID
            source_drummer_id = profile
        
        # Get quantified characteristics from drummer mapping service
        characteristics = self.drummer_service.get_drummer_characteristics(source_drummer_id)
        
        if not characteristics:
            print(f"  Warning: No characteristics found for {profile}, using default")
            return piano_roll
        
        # Extract quantified values (0.0 to 1.0)
        ghost_density = characteristics.get('ghost_note_density', 0.5)
        ride_pref = characteristics.get('ride_preference', 0.5)
        kick_syncopation = characteristics.get('kick_syncopation', 0.5)
        dynamics_range = characteristics.get('dynamics_range', 0.7)
        
        # Apply ride preference (lane 4 = ride, lane 2 = hihat)
        if ride_pref > 0.7:  # Ride-heavy drummer
            piano_roll[4] *= (1.0 + (ride_pref - 0.5))  # Boost ride
            piano_roll[2] *= (1.0 - (ride_pref - 0.5) * 0.3)  # Reduce hihat
        
        # Apply ghost notes on snare (lane 1)
        if ghost_density > 0.6:
            # Soften low-velocity snare hits (ghost notes)
            piano_roll[1] = np.where(
                piano_roll[1] < 0.4,
                piano_roll[1] * (1.0 - ghost_density * 0.3),
                piano_roll[1]
            )
        
        # Apply bass drum syncopation (lane 0)
        if kick_syncopation > 0.7:
            # Add emphasis to syncopated kicks
            for i in range(0, 128, 4):
                if i + 2 < 128 and piano_roll[0, i + 2] > 0.3:
                    piano_roll[0, i + 2] = min(1.0, piano_roll[0, i + 2] * 1.2)
        
        # Apply dynamic range
        if dynamics_range > 0.8:
            # Wider dynamic range (more variation)
            piano_roll = piano_roll * (0.7 + np.random.random(piano_roll.shape) * 0.6 * dynamics_range)
        elif dynamics_range < 0.4:
            # Narrower dynamic range (more consistent)
            piano_roll = piano_roll * (0.8 + np.random.random(piano_roll.shape) * 0.4)
        
        # Clip to valid range
        piano_roll = np.clip(piano_roll, 0, 1)
        
        return piano_roll
    
    def _humanize_pattern(self, piano_roll: np.ndarray) -> np.ndarray:
        """Apply subtle humanization"""
        # Velocity variation
        piano_roll = piano_roll * (0.9 + np.random.random(piano_roll.shape) * 0.2)
        
        # Clip to valid range
        piano_roll = np.clip(piano_roll, 0, 1)
        
        return piano_roll
    
    def _pattern_to_midi(self, piano_roll: np.ndarray, tempo: float) -> str:
        """Convert piano roll to base64 MIDI"""
        import base64
        from io import BytesIO
        
        mid = mido.MidiFile()
        mid.ticks_per_beat = 480
        
        # Create 8 tracks (one per drum lane)
        track_names = ['Kick', 'Snare', 'HiHat Closed', 'HiHat Open', 
                      'Ride', 'Toms', 'Crash', 'Other']
        
        for lane in range(8):
            track = mido.MidiTrack()
            track.append(mido.MetaMessage('track_name', name=track_names[lane], time=0))
            track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo), time=0))
            
            # Add notes
            for pos in range(128):
                if piano_roll[lane, pos] > 0.3:  # Threshold
                    note = self._lane_to_midi_note(lane)
                    velocity = int(piano_roll[lane, pos] * 100) + 20
                    velocity = min(127, velocity)
                    
                    track.append(mido.Message('note_on', note=note, velocity=velocity, time=pos * 120))
                    track.append(mido.Message('note_off', note=note, velocity=0, time=20))
            
            mid.tracks.append(track)
        
        # Save to bytes
        buffer = BytesIO()
        mid.save(file=buffer)
        midi_bytes = buffer.getvalue()
        
        # Encode to base64
        midi_base64 = base64.b64encode(midi_bytes).decode('utf-8')
        
        return midi_base64
    
    def _lane_to_midi_note(self, lane: int) -> int:
        """Map drum lane to GM MIDI note"""
        mapping = {
            0: 36,  # Kick
            1: 38,  # Snare
            2: 42,  # Hi-hat closed
            3: 46,  # Hi-hat open
            4: 51,  # Ride
            5: 45,  # Tom
            6: 49,  # Crash
            7: 37   # Other
        }
        return mapping.get(lane, 37)
    
    def _calculate_pattern_stats(self, piano_roll: np.ndarray) -> Dict:
        """Calculate pattern statistics"""
        return {
            'kick_count': int(np.sum(piano_roll[0] > 0.3)),
            'snare_count': int(np.sum(piano_roll[1] > 0.3)),
            'hihat_count': int(np.sum(piano_roll[2] > 0.3) + np.sum(piano_roll[3] > 0.3)),
            'total_notes': int(np.sum(piano_roll > 0.3)),
            'density': float(np.mean(piano_roll > 0.3))
        }
    
    def close(self):
        """Clean up resources"""
        self.db.close()


# Example usage
if __name__ == "__main__":
    print("🎵 AI Pattern Generator - Test")
    print("="*70)
    
    # Initialize
    generator = AIPatternGenerator()
    
    # Generate a pattern with Studio Groove Master (Jeff Porcaro characteristics)
    result = generator.generate_ai_pattern(
        tempo=156.0,
        style='rock',
        section='verse',
        complexity=0.6,
        creativity=0.5,
        drummer_profile='studio_groove_master'  # DrumTracKAI fictional name
    )
    
    print("\n📊 Generated Pattern:")
    print(json.dumps(result['stats'], indent=2))
    
    # Save MIDI
    import base64
    midi_bytes = base64.b64decode(result['midi_base64'])
    with open('ai_generated_test.mid', 'wb') as f:
        f.write(midi_bytes)
    print("\n💾 Saved: ai_generated_test.mid")
    
    generator.close()
    print("\n✅ Test complete!")
