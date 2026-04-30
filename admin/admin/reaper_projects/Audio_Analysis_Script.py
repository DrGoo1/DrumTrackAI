#!/usr/bin/env python3
"""
Audio Analysis Script for SD3 Output Files
Analyzes the rendered drum samples for levels, quality, and processing needs
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
import json
from datetime import datetime

def analyze_audio_file(file_path):
    """Analyze a single audio file for various metrics"""
    try:
        # Read the audio file
        sample_rate, audio_data = wavfile.read(file_path)
        
        # Convert to float and normalize to -1 to 1 range
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data.astype(np.float32) / 2147483648.0
        elif audio_data.dtype == np.int24:
            audio_data = audio_data.astype(np.float32) / 8388608.0
        
        # Handle stereo vs mono
        if len(audio_data.shape) > 1:
            # Stereo - analyze both channels
            left_channel = audio_data[:, 0]
            right_channel = audio_data[:, 1]
            # Use RMS of both channels for analysis
            audio_rms = np.sqrt((left_channel**2 + right_channel**2) / 2)
        else:
            # Mono
            audio_rms = np.abs(audio_data)
        
        # Calculate metrics
        analysis = {
            'file_name': os.path.basename(file_path),
            'file_size_mb': os.path.getsize(file_path) / (1024 * 1024),
            'duration_seconds': len(audio_data) / sample_rate,
            'sample_rate': sample_rate,
            'channels': 2 if len(audio_data.shape) > 1 else 1,
            'bit_depth': str(audio_data.dtype),
            
            # Level Analysis
            'peak_level_db': 20 * np.log10(np.max(np.abs(audio_data))) if np.max(np.abs(audio_data)) > 0 else -np.inf,
            'rms_level_db': 20 * np.log10(np.sqrt(np.mean(audio_data**2))) if np.sqrt(np.mean(audio_data**2)) > 0 else -np.inf,
            'dynamic_range_db': 20 * np.log10(np.max(np.abs(audio_data))) - 20 * np.log10(np.sqrt(np.mean(audio_data**2))) if np.sqrt(np.mean(audio_data**2)) > 0 else 0,
            
            # Quality Metrics
            'clipping_detected': np.any(np.abs(audio_data) >= 0.99),
            'silence_percentage': (np.sum(np.abs(audio_data) < 0.001) / len(audio_data)) * 100,
            'signal_start_time': None,
            'signal_end_time': None,
        }
        
        # Find signal start and end times (above threshold)
        threshold = 0.01  # 1% of full scale
        signal_indices = np.where(np.abs(audio_data) > threshold)[0]
        
        if len(signal_indices) > 0:
            analysis['signal_start_time'] = signal_indices[0] / sample_rate
            analysis['signal_end_time'] = signal_indices[-1] / sample_rate
            analysis['signal_duration'] = analysis['signal_end_time'] - analysis['signal_start_time']
        
        return analysis
        
    except Exception as e:
        return {
            'file_name': os.path.basename(file_path),
            'error': str(e)
        }

def analyze_all_files(directory):
    """Analyze all WAV files in the directory"""
    print(f"=== Audio Analysis for {directory} ===")
    
    wav_files = [f for f in os.listdir(directory) if f.endswith('.wav')]
    
    if not wav_files:
        print("No WAV files found in directory")
        return []
    
    print(f"Found {len(wav_files)} WAV files to analyze")
    
    analyses = []
    
    for wav_file in wav_files:
        file_path = os.path.join(directory, wav_file)
        print(f"Analyzing: {wav_file}")
        
        analysis = analyze_audio_file(file_path)
        analyses.append(analysis)
        
        # Print key metrics
        if 'error' not in analysis:
            print(f"  Peak Level: {analysis['peak_level_db']:.1f} dB")
            print(f"  RMS Level: {analysis['rms_level_db']:.1f} dB")
            print(f"  Dynamic Range: {analysis['dynamic_range_db']:.1f} dB")
            print(f"  Duration: {analysis['duration_seconds']:.2f}s")
            print(f"  Signal Start: {analysis['signal_start_time']:.3f}s" if analysis['signal_start_time'] else "  No signal detected")
            print(f"  Clipping: {'YES' if analysis['clipping_detected'] else 'NO'}")
            print(f"  Silence: {analysis['silence_percentage']:.1f}%")
        else:
            print(f"  ERROR: {analysis['error']}")
        print()
    
    return analyses

def generate_recommendations(analyses):
    """Generate processing recommendations based on analysis"""
    print("=== PROCESSING RECOMMENDATIONS ===")
    
    if not analyses or all('error' in a for a in analyses):
        print("No valid audio files to analyze")
        return
    
    valid_analyses = [a for a in analyses if 'error' not in a]
    
    # Calculate statistics
    peak_levels = [a['peak_level_db'] for a in valid_analyses if a['peak_level_db'] != -np.inf]
    rms_levels = [a['rms_level_db'] for a in valid_analyses if a['rms_level_db'] != -np.inf]
    dynamic_ranges = [a['dynamic_range_db'] for a in valid_analyses]
    
    print(f"Peak Level Range: {min(peak_levels):.1f} to {max(peak_levels):.1f} dB")
    print(f"RMS Level Range: {min(rms_levels):.1f} to {max(rms_levels):.1f} dB")
    print(f"Dynamic Range: {min(dynamic_ranges):.1f} to {max(dynamic_ranges):.1f} dB")
    print()
    
    # Check for issues and recommendations
    recommendations = []
    
    # Level recommendations
    avg_peak = np.mean(peak_levels)
    avg_rms = np.mean(rms_levels)
    
    if avg_peak > -1.0:
        recommendations.append("WARNING  LEVELS TOO HIGH: Average peak level is too close to 0 dB. Risk of clipping.")
        recommendations.append("   SOLUTION: Add -3 dB to -6 dB headroom in render settings")
    elif avg_peak < -12.0:
        recommendations.append("WARNING  LEVELS TOO LOW: Average peak level is very low. May need normalization.")
        recommendations.append("   SOLUTION: Increase gain or normalize to -3 dB peak")
    else:
        recommendations.append("SUCCESS LEVELS GOOD: Peak levels are in acceptable range")
    
    # Check for clipping
    clipped_files = [a for a in valid_analyses if a['clipping_detected']]
    if clipped_files:
        recommendations.append(f"WARNING  CLIPPING DETECTED in {len(clipped_files)} files")
        recommendations.append("   SOLUTION: Reduce Superior Drummer 3 output level or add limiter")
    else:
        recommendations.append("SUCCESS NO CLIPPING: All files are clean")
    
    # Check signal timing
    signal_starts = [a['signal_start_time'] for a in valid_analyses if a['signal_start_time'] is not None]
    if signal_starts:
        avg_start = np.mean(signal_starts)
        if avg_start > 1.5:  # Expected around 1.3s
            recommendations.append(f"WARNING  SIGNAL TIMING: Average signal start at {avg_start:.2f}s (expected ~1.3s)")
            recommendations.append("   SOLUTION: Adjust MIDI positioning in batch script")
        else:
            recommendations.append("SUCCESS SIGNAL TIMING: Drum hits are properly positioned")
    
    # Check for excessive silence
    avg_silence = np.mean([a['silence_percentage'] for a in valid_analyses])
    if avg_silence > 80:
        recommendations.append(f"WARNING  EXCESSIVE SILENCE: {avg_silence:.1f}% silence detected")
        recommendations.append("   SOLUTION: Trim silence or adjust time selection")
    else:
        recommendations.append("SUCCESS SILENCE LEVELS: Appropriate amount of silence")
    
    # Print recommendations
    for rec in recommendations:
        print(rec)
    
    print()
    print("=== BATCH PROCESSING READINESS ===")
    
    critical_issues = [r for r in recommendations if r.startswith("WARNING")]
    if not critical_issues:
        print("COMPLETE READY FOR FULL BATCH PROCESSING!")
        print("   All quality metrics are within acceptable ranges")
        print("   No additional processing required")
    else:
        print("WARNING  ISSUES DETECTED - RECOMMEND FIXES BEFORE FULL BATCH:")
        for issue in critical_issues:
            if not issue.startswith("   "):
                print(f"   • {issue[4:]}")  # Remove warning emoji and spaces
    
    return recommendations

def main():
    """Main analysis function"""
    print("=== SD3 Output File Analysis ===")
    print(f"Analysis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Analyze local output directory
    local_dir = r"D:\DrumTracKAI_v1.1.7\admin\sd3_extracted_samples"
    
    if os.path.exists(local_dir):
        analyses = analyze_all_files(local_dir)
        
        # Generate recommendations
        recommendations = generate_recommendations(analyses)
        
        # Save analysis results
        output_file = os.path.join(local_dir, "audio_analysis_results.json")
        with open(output_file, 'w') as f:
            json.dump({
                'analysis_date': datetime.now().isoformat(),
                'directory': local_dir,
                'file_analyses': analyses,
                'recommendations': recommendations
            }, f, indent=2)
        
        print(f"Analysis results saved to: {output_file}")
        
    else:
        print(f"Directory not found: {local_dir}")

if __name__ == "__main__":
    main()
