#!/usr/bin/env python3
"""
Monitor Audio Quality - Real-time Batch Processing Verification
==============================================================

Monitors the batch extraction process and randomly samples output
audio files to verify quality, duration, and correctness.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import wave
import random
import time
import os
from pathlib import Path
import subprocess
import threading

class AudioQualityMonitor:
    def __init__(self):
        self.output_dir = Path(__file__).parent / "sd3_extracted_samples"
        self.monitored_files = set()
        self.quality_stats = {
            'total_checked': 0,
            'good_quality': 0,
            'poor_quality': 0,
            'errors': 0,
            'avg_duration': 0,
            'avg_file_size': 0
        }
        self.running = True
        
    def analyze_wav_file(self, wav_path):
        """Analyze a WAV file for quality metrics"""
        try:
            with wave.open(str(wav_path), 'rb') as wav_file:
                # Get basic properties
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                duration = frames / sample_rate
                
                # Read audio data for analysis
                audio_data = wav_file.readframes(frames)
                
                # Calculate file size
                file_size = wav_path.stat().st_size
                
                # Basic quality checks
                quality_score = 0
                issues = []
                
                # Check duration (should be ~0.5 seconds)
                if 0.4 <= duration <= 0.6:
                    quality_score += 25
                else:
                    issues.append(f"Duration: {duration:.3f}s (expected ~0.5s)")
                
                # Check sample rate (should be 44.1kHz)
                if sample_rate == 44100:
                    quality_score += 25
                else:
                    issues.append(f"Sample rate: {sample_rate}Hz (expected 44100Hz)")
                
                # Check channels (should be stereo)
                if channels == 2:
                    quality_score += 25
                else:
                    issues.append(f"Channels: {channels} (expected 2)")
                
                # Check file size (should be substantial for 0.5s of audio)
                expected_size = sample_rate * channels * sample_width * duration
                if file_size >= expected_size * 0.8:  # Allow 20% compression
                    quality_score += 25
                else:
                    issues.append(f"File size: {file_size} bytes (expected ~{int(expected_size)})")
                
                return {
                    'path': wav_path,
                    'duration': duration,
                    'sample_rate': sample_rate,
                    'channels': channels,
                    'sample_width': sample_width,
                    'file_size': file_size,
                    'quality_score': quality_score,
                    'issues': issues,
                    'is_good': quality_score >= 75
                }
                
        except Exception as e:
            return {
                'path': wav_path,
                'error': str(e),
                'is_good': False,
                'quality_score': 0
            }
    
    def get_new_wav_files(self):
        """Get newly created WAV files that haven't been monitored yet"""
        if not self.output_dir.exists():
            return []
        
        current_files = set()
        for wav_file in self.output_dir.glob("*.wav"):
            if wav_file.is_file():
                current_files.add(wav_file)
        
        new_files = current_files - self.monitored_files
        self.monitored_files.update(new_files)
        
        return list(new_files)
    
    def play_audio_sample(self, wav_path):
        """Play a short audio sample (if possible)"""
        try:
            # Try to play with Windows default player
            subprocess.run(['start', str(wav_path)], shell=True, check=False)
            return True
        except:
            return False
    
    def monitor_batch_quality(self, sample_rate=0.1, play_samples=False):
        """Monitor batch processing and randomly sample files for quality"""
        print("AUDIO REAL-TIME AUDIO QUALITY MONITORING")
        print("=" * 60)
        print(f"Monitoring directory: {self.output_dir}")
        print(f"Sample rate: {sample_rate*100:.1f}% of new files")
        print(f"Play samples: {'Yes' if play_samples else 'No'}")
        print("=" * 60)
        
        last_file_count = 0
        
        while self.running:
            try:
                # Get new files
                new_files = self.get_new_wav_files()
                
                if new_files:
                    total_files = len(self.monitored_files)
                    print(f"\nPROGRESS NEW FILES DETECTED: +{len(new_files)} files (total: {total_files})")
                    
                    # Randomly sample files for quality check
                    files_to_check = []
                    for file in new_files:
                        if random.random() < sample_rate:
                            files_to_check.append(file)
                    
                    # Always check at least one file if we have new files
                    if not files_to_check and new_files:
                        files_to_check = [random.choice(new_files)]
                    
                    # Analyze selected files
                    for wav_file in files_to_check:
                        self.analyze_and_report_file(wav_file, play_samples)
                    
                    # Update progress
                    if total_files % 50 == 0 and total_files > last_file_count:
                        self.print_quality_summary()
                        last_file_count = total_files
                
                time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                print("\n⏹ Monitoring stopped by user")
                break
            except Exception as e:
                print(f"ERROR Monitoring error: {e}")
                time.sleep(10)
    
    def analyze_and_report_file(self, wav_file, play_sample=False):
        """Analyze a single file and report results"""
        print(f"\nINSPECTING ANALYZING: {wav_file.name}")
        print("-" * 40)
        
        analysis = self.analyze_wav_file(wav_file)
        
        if 'error' in analysis:
            print(f"ERROR ERROR: {analysis['error']}")
            self.quality_stats['errors'] += 1
        else:
            # Update statistics
            self.quality_stats['total_checked'] += 1
            if analysis['is_good']:
                self.quality_stats['good_quality'] += 1
                print(f"SUCCESS QUALITY: GOOD ({analysis['quality_score']}/100)")
            else:
                self.quality_stats['poor_quality'] += 1
                print(f"WARNING  QUALITY: POOR ({analysis['quality_score']}/100)")
            
            # Update averages
            self.quality_stats['avg_duration'] = (
                (self.quality_stats['avg_duration'] * (self.quality_stats['total_checked'] - 1) + 
                 analysis['duration']) / self.quality_stats['total_checked']
            )
            self.quality_stats['avg_file_size'] = (
                (self.quality_stats['avg_file_size'] * (self.quality_stats['total_checked'] - 1) + 
                 analysis['file_size']) / self.quality_stats['total_checked']
            )
            
            # Show details
            print(f"ANALYSIS Duration: {analysis['duration']:.3f}s")
            print(f"ANALYSIS Sample Rate: {analysis['sample_rate']:,}Hz")
            print(f"ANALYSIS Channels: {analysis['channels']}")
            print(f"ANALYSIS File Size: {analysis['file_size']:,} bytes ({analysis['file_size']/1024:.1f} KB)")
            
            # Show issues if any
            if analysis['issues']:
                print(f"WARNING  Issues found:")
                for issue in analysis['issues']:
                    print(f"   • {issue}")
            
            # Play sample if requested
            if play_sample and analysis['is_good']:
                print(f"VOLUME Playing audio sample...")
                self.play_audio_sample(wav_file)
    
    def print_quality_summary(self):
        """Print current quality statistics summary"""
        stats = self.quality_stats
        total = stats['total_checked']
        
        if total == 0:
            return
        
        print(f"\nANALYSIS QUALITY SUMMARY ({total} files checked)")
        print("=" * 50)
        print(f"Good Quality: {stats['good_quality']} ({stats['good_quality']/total*100:.1f}%)")
        print(f"Poor Quality: {stats['poor_quality']} ({stats['poor_quality']/total*100:.1f}%)")
        print(f"Errors: {stats['errors']}")
        print(f"Avg Duration: {stats['avg_duration']:.3f}s")
        print(f"Avg File Size: {stats['avg_file_size']/1024:.1f} KB")
        
        # Quality assessment
        good_rate = stats['good_quality'] / total
        if good_rate >= 0.9:
            print(f"COMPLETE EXCELLENT quality rate!")
        elif good_rate >= 0.7:
            print(f"SUCCESS GOOD quality rate")
        elif good_rate >= 0.5:
            print(f"WARNING  MODERATE quality rate - check settings")
        else:
            print(f"ERROR LOW quality rate - investigate issues")
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.running = False

def main():
    """Main monitoring execution"""
    print("AUDIO SUPERIOR DRUMMER AUDIO QUALITY MONITOR")
    print("=" * 70)
    print("Real-time verification of batch extraction quality")
    print("=" * 70)
    
    monitor = AudioQualityMonitor()
    
    print(f"\nTARGET MONITORING OPTIONS:")
    print(f"1. Sample rate: How often to check files (10% = check 1 in 10 files)")
    print(f"2. Play samples: Whether to play audio samples for verification")
    
    try:
        sample_rate_input = input("Sample rate (0.1 for 10%, 0.2 for 20%, etc.): ").strip()
        sample_rate = float(sample_rate_input) if sample_rate_input else 0.1
        sample_rate = max(0.01, min(1.0, sample_rate))  # Clamp between 1% and 100%
    except:
        sample_rate = 0.1
    
    play_samples = input("Play audio samples? (y/n): ").lower().startswith('y')
    
    print(f"\nLAUNCH STARTING QUALITY MONITORING")
    print(f"Sample rate: {sample_rate*100:.1f}%")
    print(f"Play samples: {'Yes' if play_samples else 'No'}")
    print(f"Press Ctrl+C to stop monitoring")
    
    try:
        monitor.monitor_batch_quality(sample_rate, play_samples)
    except KeyboardInterrupt:
        print(f"\n⏹ Monitoring stopped")
    finally:
        monitor.print_quality_summary()
        print(f"\n Final monitoring report complete")

if __name__ == "__main__":
    main()
