#!/usr/bin/env python3
"""
TFR Integration Methods
Additional methods and utilities for TFR integration system
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

class TFRAnalysisValidator:
    """Validates TFR analysis results for authenticity"""
    
    @staticmethod
    def validate_tfr_results(tfr_results: Dict) -> Dict[str, Any]:
        """Validate TFR analysis results and flag any placeholder data"""
        
        validation_report = {
            'is_authentic': True,
            'issues': [],
            'confidence': 1.0,
            'validated_components': []
        }
        
        for stem_type, results in tfr_results.items():
            stem_validation = TFRAnalysisValidator._validate_stem_results(stem_type, results)
            validation_report['validated_components'].append(stem_validation)
            
            if not stem_validation['is_authentic']:
                validation_report['is_authentic'] = False
                validation_report['issues'].extend(stem_validation['issues'])
        
        # Calculate overall confidence
        if validation_report['validated_components']:
            confidences = [comp['confidence'] for comp in validation_report['validated_components']]
            validation_report['confidence'] = np.mean(confidences)
        
        return validation_report
    
    @staticmethod
    def _validate_stem_results(stem_type: str, results: Dict) -> Dict[str, Any]:
        """Validate results for a single stem"""
        
        validation = {
            'stem_type': stem_type,
            'is_authentic': True,
            'issues': [],
            'confidence': 1.0
        }
        
        # Check for enhanced hits
        enhanced_hits = results.get('enhanced_hits', [])
        if not enhanced_hits:
            validation['issues'].append(f"No enhanced hits found for {stem_type}")
            validation['is_authentic'] = False
            validation['confidence'] *= 0.5
        else:
            # Validate hit authenticity
            for i, hit in enumerate(enhanced_hits):
                hit_validation = TFRAnalysisValidator._validate_enhanced_hit(hit, i)
                if not hit_validation['is_authentic']:
                    validation['issues'].extend(hit_validation['issues'])
                    validation['confidence'] *= hit_validation['confidence']
        
        # Check TFR metrics
        tfr_metrics = results.get('tfr_metrics')
        if tfr_metrics:
            metrics_validation = TFRAnalysisValidator._validate_tfr_metrics(tfr_metrics)
            if not metrics_validation['is_authentic']:
                validation['issues'].extend(metrics_validation['issues'])
                validation['confidence'] *= metrics_validation['confidence']
        
        # Check groove signature
        groove_signature = results.get('groove_signature')
        if groove_signature is not None and len(groove_signature) == 0:
            validation['issues'].append(f"Empty groove signature for {stem_type}")
            validation['confidence'] *= 0.8
        
        return validation
    
    @staticmethod
    def _validate_enhanced_hit(hit, hit_index: int) -> Dict[str, Any]:
        """Validate a single enhanced hit"""
        
        validation = {
            'is_authentic': True,
            'issues': [],
            'confidence': 1.0
        }
        
        # Check for placeholder values
        if hit.attack_sharpness == 0.0 and hit.transient_strength == 0.0:
            validation['issues'].append(f"Hit {hit_index}: Zero attack sharpness and transient strength")
            validation['is_authentic'] = False
            validation['confidence'] *= 0.3
        
        # Check spectral evolution
        if not hit.spectral_evolution or len(hit.spectral_evolution) == 0:
            validation['issues'].append(f"Hit {hit_index}: Missing spectral evolution data")
            validation['confidence'] *= 0.7
        elif len(set(hit.spectral_evolution)) == 1:
            validation['issues'].append(f"Hit {hit_index}: Constant spectral evolution (likely placeholder)")
            validation['is_authentic'] = False
            validation['confidence'] *= 0.2
        
        # Check TFR analysis
        if not hit.tfr_analysis:
            validation['issues'].append(f"Hit {hit_index}: Missing TFR analysis")
            validation['confidence'] *= 0.5
        
        return validation
    
    @staticmethod
    def _validate_tfr_metrics(tfr_metrics) -> Dict[str, Any]:
        """Validate TFR metrics"""
        
        validation = {
            'is_authentic': True,
            'issues': [],
            'confidence': 1.0
        }
        
        # Check for suspicious patterns
        metrics_dict = tfr_metrics.__dict__ if hasattr(tfr_metrics, '__dict__') else tfr_metrics
        
        zero_count = sum(1 for value in metrics_dict.values() 
                        if isinstance(value, (int, float)) and value == 0.0)
        
        if zero_count > len(metrics_dict) * 0.5:
            validation['issues'].append("Too many zero values in TFR metrics")
            validation['is_authentic'] = False
            validation['confidence'] *= 0.4
        
        # Check groove signature
        if hasattr(tfr_metrics, 'groove_signature') and len(tfr_metrics.groove_signature) == 0:
            validation['issues'].append("Empty groove signature in TFR metrics")
            validation['confidence'] *= 0.6
        
        return validation

class TFRStyleVectorEncoder:
    """Encodes TFR analysis results into style vectors"""
    
    @staticmethod
    def encode_tfr_style_vector(tfr_results: Dict, drummer_name: str = "Unknown") -> Dict:
        """Encode TFR results into a comprehensive style vector"""
        
        logger.info(f"Encoding TFR style vector for {drummer_name}")
        
        style_vector = {
            'drummer_name': drummer_name,
            'analysis_type': 'TFR_Enhanced',
            'timestamp': np.datetime64('now').astype(str),
            'individual_drums': {},
            'collective_metrics': {},
            'groove_characteristics': {},
            'authenticity_validated': False
        }
        
        # Process each drum stem
        for stem_type, results in tfr_results.items():
            if stem_type == 'bass':
                continue
            
            drum_vector = TFRStyleVectorEncoder._encode_drum_specific_vector(stem_type, results)
            style_vector['individual_drums'][stem_type] = drum_vector
        
        # Calculate collective metrics
        style_vector['collective_metrics'] = TFRStyleVectorEncoder._calculate_collective_metrics(tfr_results)
        
        # Extract groove characteristics
        style_vector['groove_characteristics'] = TFRStyleVectorEncoder._extract_groove_characteristics(tfr_results)
        
        # Validate authenticity
        validation_report = TFRAnalysisValidator.validate_tfr_results(tfr_results)
        style_vector['authenticity_validated'] = validation_report['is_authentic']
        style_vector['validation_confidence'] = validation_report['confidence']
        style_vector['validation_issues'] = validation_report['issues']
        
        logger.info(f"TFR style vector encoded (authentic: {validation_report['is_authentic']}, "
                   f"confidence: {validation_report['confidence']:.3f})")
        
        return style_vector
    
    @staticmethod
    def _encode_drum_specific_vector(stem_type: str, results: Dict) -> Dict:
        """Encode style vector for a specific drum"""
        
        enhanced_hits = results.get('enhanced_hits', [])
        tfr_metrics = results.get('tfr_metrics')
        groove_signature = results.get('groove_signature', np.array([]))
        
        if not enhanced_hits:
            return {'error': 'No enhanced hits available'}
        
        # Attack characteristics
        attack_values = [hit.attack_sharpness for hit in enhanced_hits if hit.attack_sharpness > 0]
        attack_characteristics = {
            'mean_attack_sharpness': float(np.mean(attack_values)) if attack_values else 0.0,
            'attack_consistency': float(1.0 / (1.0 + np.std(attack_values))) if len(attack_values) > 1 else 0.0,
            'attack_range': float(np.max(attack_values) - np.min(attack_values)) if len(attack_values) > 1 else 0.0
        }
        
        # Transient characteristics
        transient_values = [hit.transient_strength for hit in enhanced_hits if hit.transient_strength > 0]
        transient_characteristics = {
            'mean_transient_strength': float(np.mean(transient_values)) if transient_values else 0.0,
            'transient_consistency': float(1.0 / (1.0 + np.std(transient_values))) if len(transient_values) > 1 else 0.0
        }
        
        # Spectral characteristics
        spectral_characteristics = TFRStyleVectorEncoder._analyze_spectral_characteristics(enhanced_hits)
        
        # Timing characteristics
        timing_characteristics = TFRStyleVectorEncoder._analyze_timing_characteristics(enhanced_hits)
        
        # Bass integration
        bass_correlations = [hit.bass_correlation for hit in enhanced_hits if hit.bass_correlation > 0]
        bass_integration = {
            'mean_bass_correlation': float(np.mean(bass_correlations)) if bass_correlations else 0.0,
            'bass_sync_consistency': float(1.0 / (1.0 + np.std(bass_correlations))) if len(bass_correlations) > 1 else 0.0
        }
        
        drum_vector = {
            'drum_type': stem_type,
            'hit_count': len(enhanced_hits),
            'attack_characteristics': attack_characteristics,
            'transient_characteristics': transient_characteristics,
            'spectral_characteristics': spectral_characteristics,
            'timing_characteristics': timing_characteristics,
            'bass_integration': bass_integration,
            'tfr_metrics': tfr_metrics.__dict__ if tfr_metrics and hasattr(tfr_metrics, '__dict__') else {},
            'groove_signature': groove_signature.tolist() if len(groove_signature) > 0 else []
        }
        
        return drum_vector
    
    @staticmethod
    def _analyze_spectral_characteristics(enhanced_hits: List) -> Dict:
        """Analyze spectral characteristics across hits"""
        
        spectral_evolutions = []
        frequency_modulations = []
        
        for hit in enhanced_hits:
            if hit.spectral_evolution and len(hit.spectral_evolution) > 0:
                spectral_evolutions.extend(hit.spectral_evolution)
            if hit.frequency_modulation > 0:
                frequency_modulations.append(hit.frequency_modulation)
        
        characteristics = {
            'spectral_complexity': float(np.std(spectral_evolutions)) if spectral_evolutions else 0.0,
            'mean_spectral_centroid': float(np.mean(spectral_evolutions)) if spectral_evolutions else 0.0,
            'mean_frequency_modulation': float(np.mean(frequency_modulations)) if frequency_modulations else 0.0,
            'spectral_consistency': float(1.0 / (1.0 + np.std(spectral_evolutions))) if len(spectral_evolutions) > 1 else 0.0
        }
        
        return characteristics
    
    @staticmethod
    def _analyze_timing_characteristics(enhanced_hits: List) -> Dict:
        """Analyze timing characteristics"""
        
        timestamps = [hit.timestamp for hit in enhanced_hits]
        intervals = np.diff(timestamps) if len(timestamps) > 1 else []
        
        timing_deviations = [hit.micro_timing_deviation for hit in enhanced_hits 
                           if hit.micro_timing_deviation != 0]
        
        characteristics = {
            'mean_interval': float(np.mean(intervals)) if intervals else 0.0,
            'interval_consistency': float(1.0 / (1.0 + np.std(intervals))) if len(intervals) > 1 else 0.0,
            'mean_timing_deviation': float(np.mean(timing_deviations)) if timing_deviations else 0.0,
            'timing_precision': float(1.0 / (1.0 + np.std(timing_deviations))) if len(timing_deviations) > 1 else 0.0
        }
        
        return characteristics
    
    @staticmethod
    def _calculate_collective_metrics(tfr_results: Dict) -> Dict:
        """Calculate metrics across all drums"""
        
        all_hits = []
        all_metrics = []
        
        for stem_type, results in tfr_results.items():
            if stem_type == 'bass':
                continue
            
            enhanced_hits = results.get('enhanced_hits', [])
            all_hits.extend(enhanced_hits)
            
            tfr_metrics = results.get('tfr_metrics')
            if tfr_metrics:
                all_metrics.append(tfr_metrics)
        
        if not all_hits:
            return {'error': 'No hits available for collective analysis'}
        
        # Cross-drum timing analysis
        timestamps = [hit.timestamp for hit in all_hits]
        timestamps.sort()
        
        collective_metrics = {
            'total_hits': len(all_hits),
            'overall_hit_density': len(all_hits) / (max(timestamps) - min(timestamps)) if len(timestamps) > 1 else 0.0,
            'cross_drum_timing_consistency': TFRStyleVectorEncoder._calculate_cross_drum_timing_consistency(all_hits),
            'overall_groove_depth': float(np.mean([m.groove_depth for m in all_metrics if hasattr(m, 'groove_depth')])) if all_metrics else 0.0,
            'overall_pattern_strength': float(np.mean([m.pattern_strength for m in all_metrics if hasattr(m, 'pattern_strength')])) if all_metrics else 0.0
        }
        
        return collective_metrics
    
    @staticmethod
    def _calculate_cross_drum_timing_consistency(all_hits: List) -> float:
        """Calculate timing consistency across all drums"""
        
        if len(all_hits) < 2:
            return 0.0
        
        # Group hits by approximate time (within 50ms)
        time_groups = []
        sorted_hits = sorted(all_hits, key=lambda h: h.timestamp)
        
        current_group = [sorted_hits[0]]
        
        for hit in sorted_hits[1:]:
            if hit.timestamp - current_group[-1].timestamp <= 0.05:  # 50ms window
                current_group.append(hit)
            else:
                if len(current_group) > 1:
                    time_groups.append(current_group)
                current_group = [hit]
        
        if len(current_group) > 1:
            time_groups.append(current_group)
        
        # Calculate timing consistency within groups
        consistencies = []
        for group in time_groups:
            timestamps = [hit.timestamp for hit in group]
            if len(timestamps) > 1:
                consistency = 1.0 / (1.0 + np.std(timestamps) * 1000)  # Scale by 1000 for ms
                consistencies.append(consistency)
        
        return float(np.mean(consistencies)) if consistencies else 0.0
    
    @staticmethod
    def _extract_groove_characteristics(tfr_results: Dict) -> Dict:
        """Extract overall groove characteristics"""
        
        all_signatures = []
        all_metrics = []
        
        for stem_type, results in tfr_results.items():
            if stem_type == 'bass':
                continue
            
            groove_signature = results.get('groove_signature', np.array([]))
            if len(groove_signature) > 0:
                all_signatures.append(groove_signature)
            
            tfr_metrics = results.get('tfr_metrics')
            if tfr_metrics:
                all_metrics.append(tfr_metrics)
        
        groove_characteristics = {
            'signature_complexity': float(np.mean([np.std(sig) for sig in all_signatures])) if all_signatures else 0.0,
            'overall_timbral_consistency': float(np.mean([m.timbral_consistency for m in all_metrics if hasattr(m, 'timbral_consistency')])) if all_metrics else 0.0,
            'overall_micro_timing_precision': float(np.mean([m.micro_timing_precision for m in all_metrics if hasattr(m, 'micro_timing_precision')])) if all_metrics else 0.0,
            'bass_integration_strength': float(np.mean([m.bass_drum_sync_precision for m in all_metrics if hasattr(m, 'bass_drum_sync_precision')])) if all_metrics else 0.0
        }
        
        return groove_characteristics

class TFRResultsExporter:
    """Exports TFR analysis results in various formats"""
    
    @staticmethod
    def export_to_json(tfr_results: Dict, style_vector: Dict, output_path: str) -> bool:
        """Export TFR results and style vector to JSON"""
        
        try:
            export_data = {
                'tfr_analysis_results': TFRResultsExporter._serialize_tfr_results(tfr_results),
                'style_vector': style_vector,
                'export_metadata': {
                    'export_time': np.datetime64('now').astype(str),
                    'analysis_type': 'TFR_Enhanced_DrumTracKAI',
                    'version': '1.1.7'
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=TFRResultsExporter._json_serializer)
            
            logger.info(f"TFR results exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export TFR results: {e}")
            return False
    
    @staticmethod
    def _serialize_tfr_results(tfr_results: Dict) -> Dict:
        """Serialize TFR results for JSON export"""
        
        serialized = {}
        
        for stem_type, results in tfr_results.items():
            serialized[stem_type] = {
                'enhanced_hits': [TFRResultsExporter._serialize_enhanced_hit(hit) 
                                for hit in results.get('enhanced_hits', [])],
                'tfr_metrics': TFRResultsExporter._serialize_tfr_metrics(results.get('tfr_metrics')),
                'groove_signature': results.get('groove_signature', np.array([])).tolist(),
                'refined_onsets': results.get('refined_onsets', np.array([])).tolist()
            }
        
        return serialized
    
    @staticmethod
    def _serialize_enhanced_hit(hit) -> Dict:
        """Serialize an enhanced hit for JSON export"""
        
        return {
            'timestamp': float(hit.timestamp),
            'velocity': float(hit.velocity),
            'drum_type': str(hit.drum_type),
            'precise_attack_time': float(hit.precise_attack_time),
            'attack_sharpness': float(hit.attack_sharpness),
            'spectral_evolution': hit.spectral_evolution if hit.spectral_evolution else [],
            'frequency_modulation': float(hit.frequency_modulation),
            'transient_strength': float(hit.transient_strength),
            'micro_timing_deviation': float(hit.micro_timing_deviation),
            'bass_correlation': float(hit.bass_correlation)
        }
    
    @staticmethod
    def _serialize_tfr_metrics(tfr_metrics) -> Dict:
        """Serialize TFR metrics for JSON export"""
        
        if not tfr_metrics:
            return {}
        
        if hasattr(tfr_metrics, '__dict__'):
            metrics_dict = tfr_metrics.__dict__.copy()
        else:
            metrics_dict = tfr_metrics
        
        # Convert numpy arrays to lists
        for key, value in metrics_dict.items():
            if isinstance(value, np.ndarray):
                metrics_dict[key] = value.tolist()
            elif isinstance(value, (np.integer, np.floating)):
                metrics_dict[key] = float(value)
        
        return metrics_dict
    
    @staticmethod
    def _json_serializer(obj):
        """Custom JSON serializer for numpy types"""
        
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Utility functions
def create_tfr_analysis_summary(tfr_results: Dict, style_vector: Dict) -> str:
    """Create a human-readable summary of TFR analysis"""
    
    summary_lines = [
        "=== TFR Enhanced DrumTracKAI Analysis Summary ===",
        f"Drummer: {style_vector.get('drummer_name', 'Unknown')}",
        f"Analysis Type: {style_vector.get('analysis_type', 'Unknown')}",
        f"Authenticity Validated: {style_vector.get('authenticity_validated', False)}",
        f"Validation Confidence: {style_vector.get('validation_confidence', 0.0):.3f}",
        ""
    ]
    
    # Individual drum analysis
    individual_drums = style_vector.get('individual_drums', {})
    for drum_type, drum_data in individual_drums.items():
        summary_lines.extend([
            f"--- {drum_type.upper()} ANALYSIS ---",
            f"Hit Count: {drum_data.get('hit_count', 0)}",
            f"Mean Attack Sharpness: {drum_data.get('attack_characteristics', {}).get('mean_attack_sharpness', 0.0):.3f}",
            f"Attack Consistency: {drum_data.get('attack_characteristics', {}).get('attack_consistency', 0.0):.3f}",
            f"Bass Integration: {drum_data.get('bass_integration', {}).get('mean_bass_correlation', 0.0):.3f}",
            ""
        ])
    
    # Collective metrics
    collective_metrics = style_vector.get('collective_metrics', {})
    if collective_metrics and 'error' not in collective_metrics:
        summary_lines.extend([
            "--- COLLECTIVE METRICS ---",
            f"Total Hits: {collective_metrics.get('total_hits', 0)}",
            f"Overall Hit Density: {collective_metrics.get('overall_hit_density', 0.0):.3f} hits/sec",
            f"Cross-Drum Timing Consistency: {collective_metrics.get('cross_drum_timing_consistency', 0.0):.3f}",
            f"Overall Groove Depth: {collective_metrics.get('overall_groove_depth', 0.0):.3f}",
            ""
        ])
    
    # Groove characteristics
    groove_chars = style_vector.get('groove_characteristics', {})
    if groove_chars:
        summary_lines.extend([
            "--- GROOVE CHARACTERISTICS ---",
            f"Signature Complexity: {groove_chars.get('signature_complexity', 0.0):.3f}",
            f"Timbral Consistency: {groove_chars.get('overall_timbral_consistency', 0.0):.3f}",
            f"Micro-Timing Precision: {groove_chars.get('overall_micro_timing_precision', 0.0):.3f}",
            f"Bass Integration Strength: {groove_chars.get('bass_integration_strength', 0.0):.3f}",
            ""
        ])
    
    # Validation issues
    validation_issues = style_vector.get('validation_issues', [])
    if validation_issues:
        summary_lines.extend([
            "--- VALIDATION ISSUES ---"
        ])
        for issue in validation_issues:
            summary_lines.append(f"• {issue}")
        summary_lines.append("")
    
    summary_lines.append("=== End Analysis Summary ===")
    
    return "\n".join(summary_lines)
