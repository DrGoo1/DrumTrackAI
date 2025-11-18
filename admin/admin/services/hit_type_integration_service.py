#!/usr/bin/env python3
"""
Hit-Type Integration Service for DrumTracKAI v1.1.7
==================================================

Integrates sophisticated hit-type analysis into the main DrumTracKAI workflow.
Provides seamless integration with existing analysis pipelines and admin UI.
"""

import numpy as np
import torch
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import asyncio

# Import our sophisticated analyzer
import sys
sys.path.append(str(Path(__file__).parent.parent))
from sophisticated_hit_type_analyzer import (
    SophisticatedHitTypeAnalyzer, 
    HitTypeClassification,
    HitTypeFeatures
)

# Import existing services
from central_database_service import CentralDatabaseService
from drumtrackai_complete_system import DrumTracKAI_Complete_System, DrumHit

logger = logging.getLogger(__name__)

@dataclass
class EnhancedDrumHit:
    """Enhanced drum hit with hit-type classification"""
    # Original drum hit data
    timestamp: float
    velocity: float
    drum_type: str
    frequency_content: np.ndarray
    attack_sharpness: float = 0.0
    spectral_evolution: List[float] = None
    micro_timing_deviation: float = 0.0
    bass_correlation: float = 0.0
    
    # Hit-type classification data
    hit_type: str = "unknown"
    hit_type_confidence: float = 0.0
    alternative_hit_types: Dict[str, float] = None
    hit_type_features: Dict = None
    
    # Analysis metadata
    analysis_version: str = "1.0"
    analyzed_at: str = None

class HitTypeIntegrationService:
    """Service to integrate hit-type analysis with DrumTracKAI workflow"""
    
    def __init__(self, sample_rate: int = 44100, use_gpu: bool = True):
        self.sample_rate = sample_rate
        self.use_gpu = use_gpu
        
        # Initialize components
        self.hit_type_analyzer = SophisticatedHitTypeAnalyzer(sample_rate, use_gpu)
        self.db_service = CentralDatabaseService()
        self.complete_system = DrumTracKAI_Complete_System(sample_rate, use_gpu)
        
        # Threading for async operations
        self._lock = threading.Lock()
        
        logger.info("Hit-Type Integration Service initialized")
    
    def analyze_with_hit_types(self, audio: np.ndarray, 
                              drummer_name: str = "unknown") -> Dict[str, Any]:
        """Complete analysis including hit-type classification"""
        
        logger.info(f"Starting complete analysis with hit-types for {drummer_name}")
        
        # Step 1: Run standard DrumTracKAI analysis
        standard_results = self.complete_system.analyze_complete_performance(audio)
        
        # Step 2: Extract drum onsets by type
        drum_onsets = self._extract_drum_onsets_by_type(standard_results)
        
        # Step 3: Run sophisticated hit-type analysis
        hit_type_results = self.hit_type_analyzer.analyze_drum_performance(audio, drum_onsets)
        
        # Step 4: Merge results into enhanced format
        enhanced_results = self._merge_analysis_results(standard_results, hit_type_results)
        
        # Step 5: Store in database
        analysis_id = self._store_enhanced_analysis(enhanced_results, drummer_name, audio)
        
        logger.info(f"Complete hit-type analysis finished (ID: {analysis_id})")
        
        return {
            'analysis_id': analysis_id,
            'drummer_name': drummer_name,
            'enhanced_results': enhanced_results,
            'hit_type_summary': self._generate_hit_type_summary(hit_type_results),
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _extract_drum_onsets_by_type(self, standard_results: Dict) -> Dict[str, np.ndarray]:
        """Extract drum onsets organized by drum type from standard analysis"""
        
        drum_onsets = {
            'snare': [],
            'hihat': [],
            'ride': [],
            'kick': [],
            'tom': []
        }
        
        # Extract from drum hits if available
        if 'drum_hits' in standard_results:
            for hit in standard_results['drum_hits']:
                if hasattr(hit, 'drum_type') and hasattr(hit, 'timestamp'):
                    drum_type = hit.drum_type.lower()
                    if drum_type in drum_onsets:
                        drum_onsets[drum_type].append(hit.timestamp)
        
        # Convert to numpy arrays
        for drum_type in drum_onsets:
            drum_onsets[drum_type] = np.array(sorted(drum_onsets[drum_type]))
        
        # Log onset counts
        for drum_type, onsets in drum_onsets.items():
            if len(onsets) > 0:
                logger.info(f"Found {len(onsets)} {drum_type} onsets")
        
        return drum_onsets
    
    def _merge_analysis_results(self, standard_results: Dict, 
                               hit_type_results: Dict[str, List[HitTypeClassification]]) -> Dict:
        """Merge standard analysis with hit-type classification results"""
        
        enhanced_results = standard_results.copy()
        enhanced_drum_hits = []
        
        # Process each drum type
        for drum_type, classifications in hit_type_results.items():
            for classification in classifications:
                # Find corresponding standard drum hit
                standard_hit = self._find_matching_standard_hit(
                    standard_results.get('drum_hits', []), 
                    classification.features.velocity * classification.features.attack_time,  # Use as timestamp proxy
                    drum_type
                )
                
                # Create enhanced drum hit
                enhanced_hit = EnhancedDrumHit(
                    timestamp=classification.features.velocity * classification.features.attack_time,
                    velocity=classification.features.velocity,
                    drum_type=drum_type,
                    frequency_content=np.array([classification.features.spectral_centroid]),
                    attack_sharpness=classification.features.attack_sharpness,
                    spectral_evolution=classification.features.spectral_evolution,
                    micro_timing_deviation=0.0,  # Could be enhanced
                    bass_correlation=0.0,  # Could be enhanced
                    hit_type=classification.primary_type,
                    hit_type_confidence=classification.confidence,
                    alternative_hit_types=classification.secondary_types,
                    hit_type_features=asdict(classification.features),
                    analysis_version="1.0",
                    analyzed_at=datetime.now().isoformat()
                )
                
                enhanced_drum_hits.append(enhanced_hit)
        
        enhanced_results['enhanced_drum_hits'] = enhanced_drum_hits
        enhanced_results['hit_type_analysis'] = hit_type_results
        
        return enhanced_results
    
    def _find_matching_standard_hit(self, standard_hits: List, timestamp: float, 
                                   drum_type: str) -> Optional[Any]:
        """Find matching standard drum hit for enhanced analysis"""
        
        # Simple matching by timestamp and drum type
        best_match = None
        min_time_diff = float('inf')
        
        for hit in standard_hits:
            if hasattr(hit, 'drum_type') and hasattr(hit, 'timestamp'):
                if hit.drum_type.lower() == drum_type.lower():
                    time_diff = abs(hit.timestamp - timestamp)
                    if time_diff < min_time_diff:
                        min_time_diff = time_diff
                        best_match = hit
        
        return best_match
    
    def _generate_hit_type_summary(self, hit_type_results: Dict[str, List[HitTypeClassification]]) -> Dict:
        """Generate summary statistics for hit-type analysis"""
        
        summary = {}
        
        for drum_type, classifications in hit_type_results.items():
            if not classifications:
                continue
            
            # Count hit types
            hit_type_counts = {}
            confidence_scores = []
            
            for classification in classifications:
                hit_type = classification.primary_type
                hit_type_counts[hit_type] = hit_type_counts.get(hit_type, 0) + 1
                confidence_scores.append(classification.confidence)
            
            # Calculate statistics
            total_hits = len(classifications)
            avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.0
            
            # Most common hit type
            most_common_hit_type = max(hit_type_counts.items(), key=lambda x: x[1]) if hit_type_counts else ("unknown", 0)
            
            summary[drum_type] = {
                'total_hits': total_hits,
                'hit_type_counts': hit_type_counts,
                'average_confidence': avg_confidence,
                'most_common_hit_type': most_common_hit_type[0],
                'hit_type_diversity': len(hit_type_counts)
            }
        
        return summary
    
    def _store_enhanced_analysis(self, enhanced_results: Dict, drummer_name: str, 
                                audio: np.ndarray) -> str:
        """Store enhanced analysis results in database"""
        
        analysis_id = f"enhanced_{drummer_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            with self._lock:
                # Store main analysis record
                self.db_service.execute_query("""
                    INSERT OR REPLACE INTO enhanced_analyses 
                    (analysis_id, drummer_name, analysis_data, created_at)
                    VALUES (?, ?, ?, ?)
                """, (analysis_id, drummer_name, json.dumps(enhanced_results, default=str), 
                     datetime.now().isoformat()))
                
                # Store individual hit-type classifications
                if 'enhanced_drum_hits' in enhanced_results:
                    for hit in enhanced_results['enhanced_drum_hits']:
                        self.db_service.execute_query("""
                            INSERT INTO hit_type_classifications
                            (analysis_id, timestamp, drum_type, hit_type, confidence, features_json, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (analysis_id, hit.timestamp, hit.drum_type, hit.hit_type,
                             hit.hit_type_confidence, json.dumps(hit.hit_type_features, default=str),
                             datetime.now().isoformat()))
                
                logger.info(f"Enhanced analysis stored with ID: {analysis_id}")
                
        except Exception as e:
            logger.error(f"Error storing enhanced analysis: {e}")
            # Create tables if they don't exist
            self._create_enhanced_analysis_tables()
            
        return analysis_id
    
    def _create_enhanced_analysis_tables(self):
        """Create database tables for enhanced analysis if they don't exist"""
        
        try:
            # Enhanced analyses table
            self.db_service.execute_query("""
                CREATE TABLE IF NOT EXISTS enhanced_analyses (
                    analysis_id TEXT PRIMARY KEY,
                    drummer_name TEXT NOT NULL,
                    analysis_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Hit-type classifications table
            self.db_service.execute_query("""
                CREATE TABLE IF NOT EXISTS hit_type_classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    drum_type TEXT NOT NULL,
                    hit_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    features_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES enhanced_analyses (analysis_id)
                )
            """)
            
            logger.info("Enhanced analysis tables created")
            
        except Exception as e:
            logger.error(f"Error creating enhanced analysis tables: {e}")
    
    def get_hit_type_statistics(self, drummer_name: str = None) -> Dict:
        """Get hit-type statistics from database"""
        
        try:
            if drummer_name:
                query = """
                    SELECT drum_type, hit_type, COUNT(*) as count, AVG(confidence) as avg_confidence
                    FROM hit_type_classifications htc
                    JOIN enhanced_analyses ea ON htc.analysis_id = ea.analysis_id
                    WHERE ea.drummer_name = ?
                    GROUP BY drum_type, hit_type
                    ORDER BY drum_type, count DESC
                """
                results = self.db_service.fetch_all(query, (drummer_name,))
            else:
                query = """
                    SELECT drum_type, hit_type, COUNT(*) as count, AVG(confidence) as avg_confidence
                    FROM hit_type_classifications
                    GROUP BY drum_type, hit_type
                    ORDER BY drum_type, count DESC
                """
                results = self.db_service.fetch_all(query)
            
            # Organize results
            statistics = {}
            for row in results:
                drum_type = row[0]
                hit_type = row[1]
                count = row[2]
                avg_confidence = row[3]
                
                if drum_type not in statistics:
                    statistics[drum_type] = {}
                
                statistics[drum_type][hit_type] = {
                    'count': count,
                    'average_confidence': avg_confidence
                }
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error getting hit-type statistics: {e}")
            return {}
    
    def export_hit_type_analysis(self, analysis_id: str, output_path: str):
        """Export detailed hit-type analysis to file"""
        
        try:
            # Get analysis data
            query = """
                SELECT analysis_data FROM enhanced_analyses WHERE analysis_id = ?
            """
            result = self.db_service.fetch_one(query, (analysis_id,))
            
            if result:
                analysis_data = json.loads(result[0])
                
                # Add hit-type classifications
                hit_classifications = self.db_service.fetch_all("""
                    SELECT timestamp, drum_type, hit_type, confidence, features_json
                    FROM hit_type_classifications
                    WHERE analysis_id = ?
                    ORDER BY timestamp
                """, (analysis_id,))
                
                export_data = {
                    'analysis_id': analysis_id,
                    'analysis_data': analysis_data,
                    'hit_classifications': [
                        {
                            'timestamp': row[0],
                            'drum_type': row[1],
                            'hit_type': row[2],
                            'confidence': row[3],
                            'features': json.loads(row[4]) if row[4] else None
                        }
                        for row in hit_classifications
                    ],
                    'export_timestamp': datetime.now().isoformat()
                }
                
                # Save to file
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                logger.info(f"Hit-type analysis exported to {output_path}")
                
            else:
                logger.warning(f"Analysis ID {analysis_id} not found")
                
        except Exception as e:
            logger.error(f"Error exporting hit-type analysis: {e}")
    
    def get_drummer_hit_type_profile(self, drummer_name: str) -> Dict:
        """Get comprehensive hit-type profile for a drummer"""
        
        try:
            # Get all analyses for this drummer
            analyses = self.db_service.fetch_all("""
                SELECT analysis_id, created_at FROM enhanced_analyses 
                WHERE drummer_name = ? ORDER BY created_at DESC
            """, (drummer_name,))
            
            if not analyses:
                return {'error': f'No analyses found for drummer {drummer_name}'}
            
            # Get hit-type statistics
            hit_type_stats = self.get_hit_type_statistics(drummer_name)
            
            # Calculate drummer characteristics
            profile = {
                'drummer_name': drummer_name,
                'total_analyses': len(analyses),
                'latest_analysis': analyses[0][1] if analyses else None,
                'hit_type_statistics': hit_type_stats,
                'drummer_characteristics': self._analyze_drummer_characteristics(hit_type_stats),
                'generated_at': datetime.now().isoformat()
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting drummer hit-type profile: {e}")
            return {'error': str(e)}
    
    def _analyze_drummer_characteristics(self, hit_type_stats: Dict) -> Dict:
        """Analyze drummer characteristics based on hit-type patterns"""
        
        characteristics = {}
        
        # Analyze snare characteristics
        if 'snare' in hit_type_stats:
            snare_stats = hit_type_stats['snare']
            total_snare_hits = sum(data['count'] for data in snare_stats.values())
            
            ghost_note_ratio = snare_stats.get('ghost_note', {}).get('count', 0) / total_snare_hits
            rim_shot_ratio = snare_stats.get('rim_shot', {}).get('count', 0) / total_snare_hits
            
            characteristics['snare_style'] = {
                'ghost_note_tendency': 'high' if ghost_note_ratio > 0.3 else 'medium' if ghost_note_ratio > 0.1 else 'low',
                'rim_shot_usage': 'frequent' if rim_shot_ratio > 0.2 else 'occasional' if rim_shot_ratio > 0.05 else 'rare',
                'dynamics_range': 'wide' if len(snare_stats) > 4 else 'moderate' if len(snare_stats) > 2 else 'narrow'
            }
        
        # Analyze hi-hat characteristics
        if 'hihat' in hit_type_stats:
            hihat_stats = hit_type_stats['hihat']
            total_hihat_hits = sum(data['count'] for data in hihat_stats.values())
            
            open_ratio = hihat_stats.get('open', {}).get('count', 0) / total_hihat_hits
            
            characteristics['hihat_style'] = {
                'openness_preference': 'open' if open_ratio > 0.6 else 'mixed' if open_ratio > 0.3 else 'closed',
                'articulation_variety': len(hihat_stats)
            }
        
        # Analyze ride characteristics
        if 'ride' in hit_type_stats:
            ride_stats = hit_type_stats['ride']
            total_ride_hits = sum(data['count'] for data in ride_stats.values())
            
            bell_ratio = ride_stats.get('bell_hit', {}).get('count', 0) / total_ride_hits
            
            characteristics['ride_style'] = {
                'bell_usage': 'frequent' if bell_ratio > 0.3 else 'occasional' if bell_ratio > 0.1 else 'rare',
                'technique_variety': len(ride_stats)
            }
        
        return characteristics

# Singleton instance for global access
_hit_type_integration_service = None

def get_hit_type_integration_service(sample_rate: int = 44100, use_gpu: bool = True) -> HitTypeIntegrationService:
    """Get singleton instance of hit-type integration service"""
    global _hit_type_integration_service
    
    if _hit_type_integration_service is None:
        _hit_type_integration_service = HitTypeIntegrationService(sample_rate, use_gpu)
    
    return _hit_type_integration_service

if __name__ == "__main__":
    # Test the integration service
    service = HitTypeIntegrationService()
    
    # Test with dummy audio
    duration = 5.0
    sample_rate = 44100
    t = np.linspace(0, duration, int(duration * sample_rate))
    audio = np.random.randn(len(t)) * 0.1  # Simple noise for testing
    
    # Run analysis
    results = service.analyze_with_hit_types(audio, "test_drummer")
    
    print("Hit-Type Integration Service test completed!")
    print(f"Analysis ID: {results['analysis_id']}")
    print(f"Hit-type summary: {results['hit_type_summary']}")
