#!/usr/bin/env python3
"""
Drummer Style Database Integration
Stores and retrieves quantified drummer style vectors for MIDI generation
"""

import sqlite3
import json
import pickle
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import numpy as np

from drummer_style_encoder import DrummerStyleVector, DrummerStyleEncoder

logger = logging.getLogger(__name__)

class DrummerStyleDatabase:
    """Database integration for drummer style vectors"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "drumtrackai.db"
        self.db_path = str(db_path)
        self._initialize_style_tables()
        logger.info(f"Drummer Style Database initialized: {self.db_path}")
    
    def _initialize_style_tables(self):
        """Initialize database tables for style vectors"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Main style vectors table
        c.execute('''CREATE TABLE IF NOT EXISTS drummer_style_vectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drummer_id TEXT NOT NULL,
            drummer_name TEXT NOT NULL,
            style_vector_json TEXT NOT NULL,
            style_vector_blob BLOB NOT NULL,
            confidence_score REAL NOT NULL,
            source_tracks TEXT NOT NULL,
            created_timestamp TEXT NOT NULL,
            updated_timestamp TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            UNIQUE(drummer_id, version)
        )''')
        
        # Individual drum characteristics table
        c.execute('''CREATE TABLE IF NOT EXISTS drum_characteristics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            style_vector_id INTEGER NOT NULL,
            drum_type TEXT NOT NULL,
            timing_precision REAL,
            pattern_complexity REAL,
            velocity_consistency REAL,
            rhythmic_role TEXT,
            characteristics_json TEXT,
            FOREIGN KEY (style_vector_id) REFERENCES drummer_style_vectors (id)
        )''')
        
        # Pattern complexity definitions table
        c.execute('''CREATE TABLE IF NOT EXISTS pattern_complexity_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drum_type TEXT NOT NULL UNIQUE,
            complexity_metric TEXT NOT NULL,
            scale_definition TEXT NOT NULL,
            calculation_method TEXT NOT NULL,
            examples_json TEXT,
            created_timestamp TEXT NOT NULL
        )''')
        
        # Style comparison metrics table
        c.execute('''CREATE TABLE IF NOT EXISTS style_comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drummer_a_id TEXT NOT NULL,
            drummer_b_id TEXT NOT NULL,
            similarity_score REAL NOT NULL,
            comparison_metrics TEXT NOT NULL,
            created_timestamp TEXT NOT NULL
        )''')
        
        # Initialize pattern complexity definitions if empty
        self._initialize_complexity_definitions(c)
        
        conn.commit()
        conn.close()
        logger.info("Style database tables initialized")
    
    def _initialize_complexity_definitions(self, cursor):
        """Initialize pattern complexity definitions for each drum type"""
        
        # Check if definitions already exist
        cursor.execute("SELECT COUNT(*) FROM pattern_complexity_definitions")
        if cursor.fetchone()[0] > 0:
            return  # Already initialized
        
        complexity_definitions = {
            'kick': {
                'complexity_metric': 'Pattern Entropy + Subdivision Density',
                'scale_definition': '0.0 = Simple on-beat pattern, 1.0 = Complex syncopated with varied subdivisions',
                'calculation_method': '''
                1. Calculate pattern entropy: -sum(p_i * log2(p_i)) where p_i is probability of each unique interval
                2. Calculate subdivision density: unique_subdivisions / max_possible_subdivisions
                3. Calculate syncopation ratio: off_beat_hits / total_hits
                4. Weighted sum: 0.4*entropy + 0.3*subdivision_density + 0.3*syncopation_ratio
                ''',
                'examples': {
                    '0.0-0.2': 'Simple 4/4 kick on beats 1 and 3',
                    '0.3-0.5': 'Basic variations with occasional syncopation',
                    '0.6-0.8': 'Complex patterns with ghost kicks and syncopation',
                    '0.9-1.0': 'Highly complex with varied subdivisions and polyrhythms'
                }
            },
            'snare': {
                'complexity_metric': 'Ghost Note Density + Accent Variation + Pattern Entropy',
                'scale_definition': '0.0 = Simple backbeat, 1.0 = Complex with extensive ghost notes and accents',
                'calculation_method': '''
                1. Calculate ghost note ratio: ghost_notes / total_hits
                2. Calculate accent variation: std_dev(velocities) / mean(velocities)
                3. Calculate pattern entropy: -sum(p_i * log2(p_i)) for timing intervals
                4. Calculate cross-stick/rim ratio: alternative_techniques / total_hits
                5. Weighted sum: 0.3*ghost_ratio + 0.3*accent_variation + 0.25*entropy + 0.15*technique_variety
                ''',
                'examples': {
                    '0.0-0.2': 'Simple backbeat on 2 and 4',
                    '0.3-0.5': 'Backbeat with occasional ghost notes',
                    '0.6-0.8': 'Extensive ghost notes with accent variations',
                    '0.9-1.0': 'Highly complex with linear patterns and technique variety'
                }
            },
            'hihat': {
                'complexity_metric': 'Subdivision Complexity + Open/Close Patterns + Velocity Dynamics',
                'scale_definition': '0.0 = Simple 8th note pattern, 1.0 = Complex with varied subdivisions and dynamics',
                'calculation_method': '''
                1. Calculate subdivision variety: unique_subdivisions / 16 (16th note grid)
                2. Calculate open/close complexity: pattern_entropy(open_close_sequence)
                3. Calculate velocity dynamics: coefficient_of_variation(velocities)
                4. Calculate foot splash ratio: foot_techniques / total_hits
                5. Weighted sum: 0.35*subdivision_variety + 0.25*open_close_complexity + 0.25*velocity_dynamics + 0.15*foot_techniques
                ''',
                'examples': {
                    '0.0-0.2': 'Simple 8th note closed hi-hat',
                    '0.3-0.5': '16th notes with basic open/close patterns',
                    '0.6-0.8': 'Complex subdivisions with dynamic control',
                    '0.9-1.0': 'Highly varied with foot techniques and polyrhythmic patterns'
                }
            },
            'toms': {
                'complexity_metric': 'Fill Complexity + Tom-to-Tom Movement + Rhythmic Sophistication',
                'scale_definition': '0.0 = Simple fills, 1.0 = Complex melodic and rhythmic tom work',
                'calculation_method': '''
                1. Calculate tom movement complexity: unique_tom_sequences / possible_sequences
                2. Calculate rhythmic sophistication: pattern_entropy + polyrhythm_detection
                3. Calculate melodic content: pitch_interval_variety / max_intervals
                4. Calculate fill integration: seamless_transitions / total_fills
                5. Weighted sum: 0.3*movement_complexity + 0.3*rhythmic_sophistication + 0.2*melodic_content + 0.2*fill_integration
                ''',
                'examples': {
                    '0.0-0.2': 'Simple tom fills, mostly single tom',
                    '0.3-0.5': 'Basic tom-to-tom movement in fills',
                    '0.6-0.8': 'Complex fills with melodic tom work',
                    '0.9-1.0': 'Highly sophisticated melodic and polyrhythmic tom playing'
                }
            },
            'crash': {
                'complexity_metric': 'Accent Placement + Crash Selection + Dynamic Integration',
                'scale_definition': '0.0 = Simple accent crashes, 1.0 = Complex orchestrated crash work',
                'calculation_method': '''
                1. Calculate accent sophistication: syncopated_accents / total_accents
                2. Calculate crash variety: unique_crash_types / available_crashes
                3. Calculate dynamic integration: crashes_supporting_song_dynamics / total_crashes
                4. Calculate choke technique usage: choked_crashes / total_crashes
                5. Weighted sum: 0.3*accent_sophistication + 0.25*crash_variety + 0.25*dynamic_integration + 0.2*choke_technique
                ''',
                'examples': {
                    '0.0-0.2': 'Basic crashes on strong beats',
                    '0.3-0.5': 'Crashes with some syncopated accents',
                    '0.6-0.8': 'Varied crash selection with dynamic awareness',
                    '0.9-1.0': 'Orchestrated crash work with advanced techniques'
                }
            },
            'ride': {
                'complexity_metric': 'Pattern Variation + Bell Usage + Rhythmic Sophistication',
                'scale_definition': '0.0 = Simple ride pattern, 1.0 = Complex jazz-level ride work',
                'calculation_method': '''
                1. Calculate pattern variation: unique_ride_patterns / total_measures
                2. Calculate bell integration: bell_hits / total_ride_hits
                3. Calculate swing/straight sophistication: timing_micro_variations_complexity
                4. Calculate cross-stick integration: edge_techniques / total_hits
                5. Weighted sum: 0.35*pattern_variation + 0.25*bell_integration + 0.25*timing_sophistication + 0.15*technique_variety
                ''',
                'examples': {
                    '0.0-0.2': 'Simple straight or swing ride pattern',
                    '0.3-0.5': 'Basic variations with occasional bell',
                    '0.6-0.8': 'Complex patterns with bell integration',
                    '0.9-1.0': 'Jazz-level sophistication with advanced techniques'
                }
            }
        }
        
        # Insert definitions
        for drum_type, definition in complexity_definitions.items():
            cursor.execute('''
                INSERT INTO pattern_complexity_definitions 
                (drum_type, complexity_metric, scale_definition, calculation_method, examples_json, created_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                drum_type,
                definition['complexity_metric'],
                definition['scale_definition'],
                definition['calculation_method'],
                json.dumps(definition['examples']),
                datetime.now().isoformat()
            ))
        
        logger.info("Pattern complexity definitions initialized")
    
    def store_drummer_style_vector(self, style_vector: DrummerStyleVector) -> int:
        """Store drummer style vector in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check if style vector already exists for this drummer
            c.execute('''
                SELECT id, version FROM drummer_style_vectors 
                WHERE drummer_id = ? 
                ORDER BY version DESC LIMIT 1
            ''', (style_vector.drummer_name.lower().replace(' ', '_'),))
            
            existing = c.fetchone()
            new_version = (existing[1] + 1) if existing else 1
            
            drummer_id = style_vector.drummer_name.lower().replace(' ', '_')
            
            # Store main style vector
            c.execute('''
                INSERT INTO drummer_style_vectors 
                (drummer_id, drummer_name, style_vector_json, style_vector_blob, 
                 confidence_score, source_tracks, created_timestamp, updated_timestamp, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                drummer_id,
                style_vector.drummer_name,
                json.dumps(style_vector.__dict__, default=str),
                pickle.dumps(style_vector),
                style_vector.confidence_score,
                json.dumps(style_vector.source_tracks),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                new_version
            ))
            
            style_vector_id = c.lastrowid
            
            # Store individual drum characteristics
            drum_chars = {
                'kick': style_vector.kick_characteristics,
                'snare': style_vector.snare_characteristics,
                'hihat': style_vector.hihat_characteristics
            }
            
            for drum_type, characteristics in drum_chars.items():
                if characteristics:  # Only store if characteristics exist
                    c.execute('''
                        INSERT INTO drum_characteristics 
                        (style_vector_id, drum_type, timing_precision, pattern_complexity, 
                         velocity_consistency, characteristics_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        style_vector_id,
                        drum_type,
                        characteristics.get('timing_precision', 0.0),
                        characteristics.get('pattern_complexity', 0.0),
                        characteristics.get('velocity_consistency', 0.0),
                        json.dumps(characteristics)
                    ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored style vector for {style_vector.drummer_name} (ID: {style_vector_id}, Version: {new_version})")
            return style_vector_id
            
        except Exception as e:
            logger.error(f"Error storing style vector: {e}")
            return -1
    
    def get_drummer_style_vector(self, drummer_name: str, version: int = None) -> Optional[DrummerStyleVector]:
        """Retrieve drummer style vector from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            drummer_id = drummer_name.lower().replace(' ', '_')
            
            if version:
                c.execute('''
                    SELECT style_vector_blob FROM drummer_style_vectors 
                    WHERE drummer_id = ? AND version = ?
                ''', (drummer_id, version))
            else:
                c.execute('''
                    SELECT style_vector_blob FROM drummer_style_vectors 
                    WHERE drummer_id = ? 
                    ORDER BY version DESC LIMIT 1
                ''', (drummer_id,))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                return pickle.loads(result[0])
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving style vector: {e}")
            return None
    
    def list_available_drummers(self) -> List[Dict]:
        """List all drummers with stored style vectors"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                SELECT drummer_name, drummer_id, confidence_score, source_tracks, 
                       created_timestamp, version
                FROM drummer_style_vectors 
                ORDER BY drummer_name, version DESC
            ''')
            
            results = []
            seen_drummers = set()
            
            for row in c.fetchall():
                drummer_name, drummer_id, confidence, source_tracks, created, version = row
                
                if drummer_name not in seen_drummers:
                    results.append({
                        'drummer_name': drummer_name,
                        'drummer_id': drummer_id,
                        'confidence_score': confidence,
                        'source_tracks': json.loads(source_tracks),
                        'created_timestamp': created,
                        'latest_version': version
                    })
                    seen_drummers.add(drummer_name)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error listing drummers: {e}")
            return []
    
    def get_pattern_complexity_definition(self, drum_type: str) -> Optional[Dict]:
        """Get pattern complexity definition for a drum type"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                SELECT complexity_metric, scale_definition, calculation_method, examples_json
                FROM pattern_complexity_definitions 
                WHERE drum_type = ?
            ''', (drum_type,))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                metric, scale_def, calc_method, examples_json = result
                return {
                    'complexity_metric': metric,
                    'scale_definition': scale_def,
                    'calculation_method': calc_method,
                    'examples': json.loads(examples_json)
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting complexity definition: {e}")
            return None
    
    def calculate_drummer_similarity(self, drummer_a: str, drummer_b: str) -> float:
        """Calculate similarity score between two drummers"""
        try:
            style_a = self.get_drummer_style_vector(drummer_a)
            style_b = self.get_drummer_style_vector(drummer_b)
            
            if not style_a or not style_b:
                return 0.0
            
            # Calculate similarity based on key metrics
            timing_sim = 1.0 - abs(style_a.timing_precision_mean - style_b.timing_precision_mean)
            groove_sim = 1.0 - abs(style_a.groove_score - style_b.groove_score)
            complexity_sim = 1.0 - abs(style_a.pattern_complexity_mean - style_b.pattern_complexity_mean)
            bass_sim = 1.0 - abs(style_a.bass_integration_score - style_b.bass_integration_score)
            syncopation_sim = 1.0 - abs(style_a.syncopation_tendency - style_b.syncopation_tendency)
            
            # Weighted similarity score
            similarity = (
                timing_sim * 0.25 +
                groove_sim * 0.25 +
                complexity_sim * 0.20 +
                bass_sim * 0.15 +
                syncopation_sim * 0.15
            )
            
            # Store comparison result
            self._store_similarity_result(drummer_a, drummer_b, similarity)
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def _store_similarity_result(self, drummer_a: str, drummer_b: str, similarity: float):
        """Store similarity calculation result"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            comparison_metrics = {
                'timing_weight': 0.25,
                'groove_weight': 0.25,
                'complexity_weight': 0.20,
                'bass_weight': 0.15,
                'syncopation_weight': 0.15
            }
            
            c.execute('''
                INSERT INTO style_comparisons 
                (drummer_a_id, drummer_b_id, similarity_score, comparison_metrics, created_timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                drummer_a.lower().replace(' ', '_'),
                drummer_b.lower().replace(' ', '_'),
                similarity,
                json.dumps(comparison_metrics),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing similarity result: {e}")
    
    def get_drummers_by_style_similarity(self, reference_drummer: str, threshold: float = 0.7) -> List[Dict]:
        """Get drummers similar to a reference drummer"""
        try:
            all_drummers = self.list_available_drummers()
            similar_drummers = []
            
            for drummer_info in all_drummers:
                if drummer_info['drummer_name'] == reference_drummer:
                    continue
                
                similarity = self.calculate_drummer_similarity(reference_drummer, drummer_info['drummer_name'])
                
                if similarity >= threshold:
                    drummer_info['similarity_score'] = similarity
                    similar_drummers.append(drummer_info)
            
            # Sort by similarity score descending
            similar_drummers.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return similar_drummers
            
        except Exception as e:
            logger.error(f"Error finding similar drummers: {e}")
            return []

class PatternComplexityCalculator:
    """Calculate pattern complexity scores for individual drums"""
    
    @staticmethod
    def calculate_kick_complexity(onsets: List[float], velocities: List[float], 
                                tempo: float, total_duration: float) -> float:
        """Calculate kick drum pattern complexity"""
        if not onsets or len(onsets) < 2:
            return 0.0
        
        # Calculate intervals between hits
        intervals = np.diff(onsets)
        
        # Pattern entropy
        unique_intervals, counts = np.unique(np.round(intervals, 2), return_counts=True)
        probabilities = counts / len(intervals)
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
        entropy_normalized = min(1.0, entropy / 3.0)  # Normalize to 0-1
        
        # Subdivision density
        beat_duration = 60.0 / tempo
        possible_subdivisions = 16  # 16th note grid
        unique_subdivisions = len(set(np.round(intervals / (beat_duration / 4), 0)))
        subdivision_density = min(1.0, unique_subdivisions / possible_subdivisions)
        
        # Syncopation ratio
        beats_per_measure = 4
        measure_duration = beat_duration * beats_per_measure
        on_beat_tolerance = beat_duration * 0.1  # 10% tolerance
        
        on_beat_hits = 0
        for onset in onsets:
            beat_position = (onset % measure_duration) / beat_duration
            if abs(beat_position - round(beat_position)) < (on_beat_tolerance / beat_duration):
                on_beat_hits += 1
        
        syncopation_ratio = 1.0 - (on_beat_hits / len(onsets))
        
        # Weighted complexity score
        complexity = (
            entropy_normalized * 0.4 +
            subdivision_density * 0.3 +
            syncopation_ratio * 0.3
        )
        
        return float(complexity)
    
    @staticmethod
    def calculate_snare_complexity(onsets: List[float], velocities: List[float], 
                                 tempo: float, total_duration: float) -> float:
        """Calculate snare drum pattern complexity"""
        if not onsets or not velocities:
            return 0.0
        
        velocities = np.array(velocities)
        
        # Ghost note ratio
        mean_velocity = np.mean(velocities)
        ghost_threshold = mean_velocity * 0.3
        ghost_notes = np.sum(velocities < ghost_threshold)
        ghost_ratio = ghost_notes / len(velocities)
        
        # Accent variation
        accent_variation = np.std(velocities) / (np.mean(velocities) + 1e-10)
        accent_variation_normalized = min(1.0, accent_variation)
        
        # Pattern entropy (timing intervals)
        if len(onsets) > 1:
            intervals = np.diff(onsets)
            unique_intervals, counts = np.unique(np.round(intervals, 2), return_counts=True)
            probabilities = counts / len(intervals)
            entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
            entropy_normalized = min(1.0, entropy / 3.0)
        else:
            entropy_normalized = 0.0
        
        # Technique variety (simplified - based on velocity clusters)
        velocity_clusters = len(set(np.round(velocities / 10) * 10))  # Group by 10s
        technique_variety = min(1.0, velocity_clusters / 8.0)  # Max 8 techniques
        
        # Weighted complexity score
        complexity = (
            ghost_ratio * 0.3 +
            accent_variation_normalized * 0.3 +
            entropy_normalized * 0.25 +
            technique_variety * 0.15
        )
        
        return float(complexity)
    
    @staticmethod
    def calculate_hihat_complexity(onsets: List[float], velocities: List[float], 
                                 tempo: float, total_duration: float) -> float:
        """Calculate hi-hat pattern complexity"""
        if not onsets:
            return 0.0
        
        beat_duration = 60.0 / tempo
        
        # Subdivision variety
        intervals = np.diff(onsets) if len(onsets) > 1 else [beat_duration]
        subdivision_grid = beat_duration / 16  # 16th note grid
        subdivisions = set(np.round(np.array(intervals) / subdivision_grid))
        subdivision_variety = min(1.0, len(subdivisions) / 16.0)
        
        # Open/close complexity (simplified - based on velocity patterns)
        if velocities:
            velocities = np.array(velocities)
            # Assume higher velocities = open hi-hat
            open_threshold = np.mean(velocities) + np.std(velocities) * 0.5
            open_pattern = velocities > open_threshold
            
            # Pattern entropy for open/close sequence
            if len(open_pattern) > 1:
                transitions = np.diff(open_pattern.astype(int))
                unique_transitions, counts = np.unique(transitions, return_counts=True)
                if len(unique_transitions) > 1:
                    probabilities = counts / len(transitions)
                    open_close_entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
                    open_close_complexity = min(1.0, open_close_entropy / 2.0)
                else:
                    open_close_complexity = 0.0
            else:
                open_close_complexity = 0.0
            
            # Velocity dynamics
            velocity_dynamics = np.std(velocities) / (np.mean(velocities) + 1e-10)
            velocity_dynamics = min(1.0, velocity_dynamics)
        else:
            open_close_complexity = 0.0
            velocity_dynamics = 0.0
        
        # Foot techniques (simplified - assume some percentage based on complexity)
        foot_techniques = min(0.3, subdivision_variety * 0.5)  # Estimate
        
        # Weighted complexity score
        complexity = (
            subdivision_variety * 0.35 +
            open_close_complexity * 0.25 +
            velocity_dynamics * 0.25 +
            foot_techniques * 0.15
        )
        
        return float(complexity)

# Integration function for main app
def integrate_style_vector_with_analysis(individual_analyses: Dict, collective_analysis: Dict,
                                       drummer_name: str, track_name: str) -> Optional[int]:
    """Integrate style vector creation and storage with existing analysis"""
    try:
        # Create style encoder
        encoder = DrummerStyleEncoder()
        
        # Generate style vector
        style_vector = encoder.encode_drummer_style(
            individual_analyses, collective_analysis, drummer_name, track_name
        )
        
        # Store in database
        db = DrummerStyleDatabase()
        style_vector_id = db.store_drummer_style_vector(style_vector)
        
        logger.info(f"Style vector integrated and stored for {drummer_name} (ID: {style_vector_id})")
        return style_vector_id
        
    except Exception as e:
        logger.error(f"Error integrating style vector: {e}")
        return None
