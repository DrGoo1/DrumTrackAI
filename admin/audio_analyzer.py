#!/usr/bin/env python3
"""
Audio Analyzer - Verify Extracted Audio Files
=============================================

Analyzes the extracted audio files to ensure they are correct:
- File size and duration
- Audio content verification
- Waveform analysis
- Quality checks

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import wave
import struct
from pathlib import Path
import os

def analyze_wav_file(wav_path):
    """Analyze a WAV file for correctness"""
    print(f"\nINSPECTING ANALYZING: {wav_path.name}")
    print("=" * 50)
    
    if not wav_path.exists():
        print(f"ERROR File not found: {wav_path}")
        return False
    
    file_size = wav_path.stat().st_size
    print(f"FOLDER File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    
    if file_size == 0:
        print("ERROR File is empty!")
        return False
    
    try:
        # Open and analyze WAV file
        with wave.open(str(wav_path), 'rb') as wav_file:
            # Get basic properties
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            duration = frames / sample_rate
            
            print(f"AUDIO Audio Properties:")
            print(f"   Sample Rate: {sample_rate} Hz")
            print(f"   Channels: {channels} ({'Stereo' if channels == 2 else 'Mono'})")
            print(f"   Bit Depth: {sample_width * 8} bit")
            print(f"   Duration: {duration:.3f} seconds")
            print(f"   Total Frames: {frames:,}")
            
            # Check if duration is reasonable (should be around 1 second for our render)
            if duration < 0.1:
                print("WARNING  WARNING: Very short duration - may be incomplete")
            elif duration > 5.0:
                print("WARNING  WARNING: Very long duration - may include extra content")
            else:
                print("SUCCESS Duration looks reasonable")
            
            # Read some audio data to check for content
            wav_file.setpos(0)
            sample_data = wav_file.readframes(min(frames, sample_rate))  # Read up to 1 second
            
            if sample_data:
                # Convert to numbers for analysis
                if sample_width == 1:
                    samples = struct.unpack(f'{len(sample_data)}B', sample_data)
                elif sample_width == 2:
                    samples = struct.unpack(f'{len(sample_data)//2}h', sample_data)
                elif sample_width == 4:
                    samples = struct.unpack(f'{len(sample_data)//4}i', sample_data)
                else:
                    print(f"WARNING  Unsupported sample width: {sample_width}")
                    return True
                
                # Check for silence (all zeros)
                non_zero_samples = sum(1 for s in samples if s != 0)
                silence_ratio = 1.0 - (non_zero_samples / len(samples))
                
                print(f"VOLUME Audio Content:")
                print(f"   Non-zero samples: {non_zero_samples:,} / {len(samples):,}")
                print(f"   Silence ratio: {silence_ratio:.1%}")
                
                if silence_ratio > 0.95:
                    print("ERROR File appears to be mostly silent!")
                    return False
                elif silence_ratio > 0.8:
                    print("WARNING  WARNING: File has a lot of silence")
                else:
                    print("SUCCESS File contains audio content")
                
                # Check peak levels
                max_sample = max(abs(s) for s in samples)
                if sample_width == 2:
                    max_possible = 32767
                elif sample_width == 4:
                    max_possible = 2147483647
                else:
                    max_possible = 255
                
                peak_ratio = max_sample / max_possible
                peak_db = 20 * (peak_ratio ** 0.5) if peak_ratio > 0 else -100
                
                print(f"   Peak level: {peak_ratio:.1%} ({peak_db:.1f} dB)")
                
                if peak_ratio < 0.01:
                    print("WARNING  WARNING: Very low audio levels")
                elif peak_ratio > 0.95:
                    print("WARNING  WARNING: Audio may be clipping")
                else:
                    print("SUCCESS Audio levels look good")
                
            else:
                print("ERROR No audio data found!")
                return False
            
        print("SUCCESS WAV file analysis complete")
        return True
        
    except wave.Error as e:
        print(f"ERROR WAV file error: {e}")
        return False
    except Exception as e:
        print(f"ERROR Analysis error: {e}")
        return False

def find_and_analyze_output_files():
    """Find and analyze all output audio files"""
    print("AUDIO AUDIO FILE ANALYSIS")
    print("=" * 60)
    print("Analyzing extracted audio files for correctness")
    print("=" * 60)
    
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    
    if not output_dir.exists():
        print(f"ERROR Output directory not found: {output_dir}")
        return
    
    print(f"DIRECTORY Searching in: {output_dir}")
    
    # Find all WAV files recursively
    wav_files = []
    for item in output_dir.rglob("*.wav"):
        if item.is_file():
            wav_files.append(item)
    
    if not wav_files:
        print("ERROR No WAV files found!")
        return
    
    print(f"FOLDER Found {len(wav_files)} WAV file(s):")
    for wav_file in wav_files:
        rel_path = wav_file.relative_to(output_dir)
        size = wav_file.stat().st_size
        print(f"   {rel_path} ({size:,} bytes)")
    
    # Analyze each file
    success_count = 0
    for wav_file in wav_files:
        if analyze_wav_file(wav_file):
            success_count += 1
    
    print(f"\nANALYSIS ANALYSIS SUMMARY")
    print("=" * 30)
    print(f"Files analyzed: {len(wav_files)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(wav_files) - success_count}")
    
    if success_count == len(wav_files):
        print("COMPLETE All audio files are valid!")
    elif success_count > 0:
        print("WARNING  Some audio files have issues")
    else:
        print("ERROR All audio files failed analysis")
    
    # Check for expected output
    expected_file = output_dir / "china_china_hard.wav"
    if expected_file.exists():
        print(f"\nSUCCESS Expected output file found: {expected_file.name}")
    else:
        print(f"\nERROR Expected output file missing: china_china_hard.wav")
        
        # Look for similar files
        similar_files = list(output_dir.rglob("*china*"))
        if similar_files:
            print("INSPECTING Found similar files:")
            for f in similar_files:
                print(f"   {f.relative_to(output_dir)}")

def main():
    """Main audio analysis"""
    find_and_analyze_output_files()

if __name__ == "__main__":
    main()
