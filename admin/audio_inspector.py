#!/usr/bin/env python3
"""
Audio Inspector - Comprehensive Audio File Analysis
===================================================

Inspects audio files with multiple methods to handle different formats
and provides detailed analysis of the extraction results.

Author: DrumTracKAI v1.1.7
Date: July 23, 2025
"""

import os
import struct
from pathlib import Path

def inspect_file_header(file_path):
    """Inspect the raw file header to determine format"""
    print(f"\nINSPECTING FILE HEADER: {file_path.name}")
    print("=" * 50)
    
    try:
        with open(file_path, 'rb') as f:
            header = f.read(44)  # Read first 44 bytes (standard WAV header)
            
        if len(header) < 12:
            print("ERROR File too small to analyze")
            return False
        
        # Check RIFF header
        riff_id = header[0:4]
        file_size = struct.unpack('<I', header[4:8])[0]
        wave_id = header[8:12]
        
        print(f"FOLDER File Header Analysis:")
        print(f"   RIFF ID: {riff_id}")
        print(f"   File Size: {file_size:,} bytes")
        print(f"   WAVE ID: {wave_id}")
        
        if riff_id == b'RIFF' and wave_id == b'WAVE':
            print("SUCCESS Valid RIFF/WAVE header detected")
            
            # Parse format chunk
            if len(header) >= 24:
                fmt_id = header[12:16]
                fmt_size = struct.unpack('<I', header[16:20])[0]
                
                print(f"   Format Chunk ID: {fmt_id}")
                print(f"   Format Chunk Size: {fmt_size}")
                
                if fmt_id == b'fmt ' and len(header) >= 24 + fmt_size:
                    audio_format = struct.unpack('<H', header[20:22])[0]
                    channels = struct.unpack('<H', header[22:24])[0]
                    sample_rate = struct.unpack('<I', header[24:28])[0]
                    byte_rate = struct.unpack('<I', header[28:32])[0]
                    block_align = struct.unpack('<H', header[32:34])[0]
                    bits_per_sample = struct.unpack('<H', header[34:36])[0]
                    
                    print(f"   Audio Format: {audio_format} ({'PCM' if audio_format == 1 else 'Compressed/Other'})")
                    print(f"   Channels: {channels}")
                    print(f"   Sample Rate: {sample_rate} Hz")
                    print(f"   Byte Rate: {byte_rate}")
                    print(f"   Block Align: {block_align}")
                    print(f"   Bits per Sample: {bits_per_sample}")
                    
                    if audio_format == 1:
                        print("SUCCESS Standard PCM format")
                        return True
                    elif audio_format == 3:
                        print("WARNING  IEEE Float format (32-bit float)")
                        return True
                    else:
                        print(f"WARNING  Compressed or unusual format: {audio_format}")
                        return True
            
        else:
            print("ERROR Not a valid WAV file")
            print(f"   Expected: RIFF...WAVE")
            print(f"   Found: {riff_id}...{wave_id}")
            return False
            
    except Exception as e:
        print(f"ERROR Error reading file header: {e}")
        return False

def check_file_playability(file_path):
    """Check if file can be played by common audio tools"""
    print(f"\nAUDIO PLAYABILITY CHECK: {file_path.name}")
    print("=" * 40)
    
    file_size = file_path.stat().st_size
    print(f"File size: {file_size:,} bytes")
    
    # Basic size checks
    if file_size < 1000:
        print("ERROR File too small to contain meaningful audio")
        return False
    elif file_size < 10000:
        print("WARNING  Very small file - may be very short audio")
    elif file_size > 100_000_000:
        print("WARNING  Very large file - may be uncompressed or very long")
    else:
        print("SUCCESS File size looks reasonable")
    
    # Try to estimate duration based on common formats
    # Assuming 44.1kHz, 16-bit, stereo: ~176KB per second
    estimated_duration = file_size / (44100 * 2 * 2)  # sample_rate * channels * bytes_per_sample
    print(f"Estimated duration (if 44.1kHz/16-bit/stereo): {estimated_duration:.2f} seconds")
    
    if 0.5 <= estimated_duration <= 2.0:
        print("SUCCESS Duration matches expected range (0.5-2.0 seconds)")
        return True
    elif estimated_duration < 0.1:
        print("WARNING  Very short duration")
        return False
    else:
        print("WARNING  Duration outside expected range")
        return True

def analyze_directory_structure():
    """Analyze the output directory structure"""
    print(f"\nDIRECTORY DIRECTORY STRUCTURE ANALYSIS")
    print("=" * 40)
    
    output_dir = Path(__file__).parent / "sd3_extracted_samples"
    
    if not output_dir.exists():
        print(f"ERROR Output directory not found: {output_dir}")
        return []
    
    print(f"Base directory: {output_dir}")
    
    all_files = []
    for root, dirs, files in os.walk(output_dir):
        root_path = Path(root)
        level = len(root_path.parts) - len(output_dir.parts)
        indent = "  " * level
        
        print(f"{indent}FOLDER {root_path.name}/")
        
        for file in files:
            file_path = root_path / file
            file_size = file_path.stat().st_size
            print(f"{indent}  FILE {file} ({file_size:,} bytes)")
            
            if file.lower().endswith(('.wav', '.mp3', '.flac', '.aiff')):
                all_files.append(file_path)
    
    return all_files

def comprehensive_audio_analysis():
    """Perform comprehensive analysis of all audio files"""
    print("AUDIO COMPREHENSIVE AUDIO ANALYSIS")
    print("=" * 60)
    print("Analyzing extracted audio files for correctness")
    print("=" * 60)
    
    # Analyze directory structure
    audio_files = analyze_directory_structure()
    
    if not audio_files:
        print("\nERROR No audio files found!")
        return
    
    print(f"\nANALYSIS Found {len(audio_files)} audio file(s)")
    
    # Analyze each file
    valid_files = 0
    playable_files = 0
    
    for audio_file in audio_files:
        print(f"\n{'='*70}")
        print(f"ANALYZING: {audio_file}")
        print(f"{'='*70}")
        
        # Header inspection
        if inspect_file_header(audio_file):
            valid_files += 1
        
        # Playability check
        if check_file_playability(audio_file):
            playable_files += 1
    
    # Summary
    print(f"\nANALYSIS ANALYSIS SUMMARY")
    print("=" * 30)
    print(f"Total files: {len(audio_files)}")
    print(f"Valid headers: {valid_files}")
    print(f"Playable files: {playable_files}")
    
    if valid_files == len(audio_files) and playable_files == len(audio_files):
        print("COMPLETE All audio files appear to be correct!")
    elif valid_files > 0 or playable_files > 0:
        print("WARNING  Some files may have issues, but extraction partially worked")
    else:
        print("ERROR All files failed analysis - extraction may have failed")
    
    # Check for expected output
    expected_files = [
        "china_china_hard.wav",
        "china_china_hard"
    ]
    
    print(f"\nTARGET EXPECTED OUTPUT CHECK:")
    for expected in expected_files:
        found_files = [f for f in audio_files if expected in str(f).lower()]
        if found_files:
            print(f"SUCCESS Found files matching '{expected}':")
            for f in found_files:
                rel_path = f.relative_to(Path(__file__).parent / "sd3_extracted_samples")
                print(f"   {rel_path}")
        else:
            print(f"ERROR No files found matching '{expected}'")

def main():
    """Main comprehensive analysis"""
    comprehensive_audio_analysis()

if __name__ == "__main__":
    main()
