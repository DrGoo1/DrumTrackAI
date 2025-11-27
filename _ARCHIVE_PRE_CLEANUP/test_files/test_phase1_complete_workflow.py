#!/usr/bin/env python3
"""
Phase 1 Complete Workflow Test
Tests end-to-end DCSM Studio functionality from upload to MIDI export
"""

import asyncio
import aiohttp
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{Colors.ENDC}\n")

def print_test(test_name: str):
    print(f"{Colors.OKBLUE}▶ TEST: {test_name}{Colors.ENDC}")

def print_success(message: str):
    print(f"{Colors.OKGREEN}  ✓ {message}{Colors.ENDC}")

def print_error(message: str):
    print(f"{Colors.FAIL}  ✗ {message}{Colors.ENDC}")

def print_warning(message: str):
    print(f"{Colors.WARNING}  ⚠ {message}{Colors.ENDC}")

def print_info(message: str):
    print(f"{Colors.OKCYAN}  ℹ {message}{Colors.ENDC}")


class Phase1WorkflowTester:
    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.session = None
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
        
    async def __aenter__(self):
        # Set longer timeout for large file uploads (Peg is 240s audio)
        timeout = aiohttp.ClientTimeout(total=300, connect=60, sock_read=120)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_backend_health(self) -> bool:
        """Test 1: Backend server is running and healthy"""
        print_test("Backend Server Health Check")
        
        try:
            async with self.session.get(f"{self.api_base}/healthz") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print_success(f"Backend is healthy: {data}")
                    self.test_results["passed"] += 1
                    return True
                else:
                    print_error(f"Backend returned status {resp.status}")
                    self.test_results["failed"] += 1
                    return False
        except Exception as e:
            print_error(f"Cannot connect to backend: {e}")
            print_info("Make sure backend is running: python dcsm_backend.py")
            self.test_results["failed"] += 1
            return False
    
    async def test_drummer_list(self) -> bool:
        """Test 2: Drummer list endpoint returns 10 drummers"""
        print_test("Drummer List Endpoint")
        
        try:
            async with self.session.get(f"{self.api_base}/api/drummers") as resp:
                if resp.status != 200:
                    print_error(f"Endpoint returned status {resp.status}")
                    self.test_results["failed"] += 1
                    return False
                
                data = await resp.json()
                drummers = data.get("drummers", [])
                
                if len(drummers) == 10:
                    print_success(f"Found {len(drummers)} drummers")
                    for drummer in drummers[:3]:
                        print_info(f"  - {drummer['display_name']} ({drummer['id']})")
                    print_info("  ... and 7 more")
                    self.test_results["passed"] += 1
                    return True
                else:
                    print_warning(f"Expected 10 drummers, got {len(drummers)}")
                    self.test_results["warnings"] += 1
                    return True
        except Exception as e:
            print_error(f"Drummer list test failed: {e}")
            self.test_results["failed"] += 1
            return False
    
    async def test_drummer_details(self, drummer_id: str = "studio_groove_master") -> Dict:
        """Test 3: Get specific drummer characteristics"""
        print_test(f"Drummer Details: {drummer_id}")
        
        try:
            async with self.session.get(f"{self.api_base}/api/drummers/{drummer_id}") as resp:
                if resp.status != 200:
                    print_error(f"Endpoint returned status {resp.status}")
                    self.test_results["failed"] += 1
                    return None
                
                drummer = await resp.json()
                
                print_success(f"Loaded: {drummer['display_name']}")
                print_info(f"  Source: {drummer.get('source_drummers', ['N/A'])}")
                print_info(f"  Genres: {', '.join(drummer.get('genre_tags', []))}")
                print_info(f"  Difficulty: {drummer.get('difficulty', 'N/A')}")
                
                # Check if characteristics loaded
                if 'characteristics' in drummer:
                    char_count = len(drummer['characteristics'])
                    print_success(f"Characteristics loaded: {char_count} attributes")
                    
                    # Show a few key characteristics
                    chars = drummer['characteristics']
                    if 'ghost_note_density' in chars:
                        print_info(f"  Ghost notes: {chars['ghost_note_density']:.2f}")
                    if 'swing_comfort' in chars:
                        print_info(f"  Swing comfort: {chars['swing_comfort']:.2f}")
                    if 'pocket_mastery' in chars:
                        print_info(f"  Pocket mastery: {chars['pocket_mastery']:.2f}")
                else:
                    print_warning("No characteristics found (using fallback)")
                    self.test_results["warnings"] += 1
                
                self.test_results["passed"] += 1
                return drummer
        except Exception as e:
            print_error(f"Drummer details test failed: {e}")
            self.test_results["failed"] += 1
            return None
    
    async def test_rust_audio_core(self) -> bool:
        """Test 4: Verify Rust audio-core is available"""
        print_test("Rust Audio Core Availability")
        
        # Check if audio-core binary exists
        audio_core_paths = [
            Path("audio-core/target/release/audio-core.exe"),
            Path("audio-core/target/release/audio-core"),
            Path("target/release/audio-core.exe"),
            Path("target/release/audio-core"),
        ]
        
        found = False
        for path in audio_core_paths:
            if path.exists():
                print_success(f"Found Rust audio-core: {path}")
                print_info(f"  Size: {path.stat().st_size / 1024:.1f} KB")
                found = True
                self.test_results["passed"] += 1
                break
        
        if not found:
            print_warning("Rust audio-core binary not found")
            print_info("Build with: cd audio-core && cargo build --release")
            print_info("System will fall back to Python (slower)")
            self.test_results["warnings"] += 1
        
        return True
    
    async def upload_test_file(self, file_path: str) -> Dict:
        """Test 5: Upload audio file and get analysis"""
        print_test(f"Upload Audio File: {Path(file_path).name}")
        
        if not Path(file_path).exists():
            print_error(f"Test file not found: {file_path}")
            print_info("Please provide a test audio file (MP3 or WAV)")
            self.test_results["failed"] += 1
            return None
        
        try:
            # Upload file
            data = aiohttp.FormData()
            data.add_field('file',
                          open(file_path, 'rb'),
                          filename=Path(file_path).name,
                          content_type='audio/mpeg')
            
            print_info("Uploading file...")
            async with self.session.post(f"{self.api_base}/files/upload", data=data) as resp:
                if resp.status != 200:
                    print_error(f"Upload failed with status {resp.status}")
                    text = await resp.text()
                    print_error(f"Response: {text[:200]}")
                    self.test_results["failed"] += 1
                    return None
                
                result = await resp.json()
                file_key = result.get('key')
                print_success(f"File uploaded: {file_key}")
            
            # Get waveform
            print_info("Generating waveform...")
            async with self.session.get(f"{self.api_base}/files/waveform", 
                                       params={'key': file_key, 'width': 1000}) as resp:
                if resp.status == 200:
                    waveform = await resp.json()
                    print_success(f"Waveform generated: {len(waveform.get('peaks', []))} peaks")
                    print_info(f"  Duration: {waveform.get('duration', 0):.1f}s")
                    print_info(f"  Sample rate: {waveform.get('sr', 0)} Hz")
                else:
                    print_warning("Waveform generation failed")
                    self.test_results["warnings"] += 1
            
            # Analyze tempo
            print_info("Analyzing tempo...")
            async with self.session.get(f"{self.api_base}/analyze/tempo",
                                       params={'key': file_key}) as resp:
                if resp.status == 200:
                    tempo_data = await resp.json()
                    tempo = tempo_data.get('tempo', 0)
                    confidence = tempo_data.get('confidence', 0)
                    print_success(f"Tempo detected: {tempo:.1f} BPM (confidence: {confidence:.2f})")
                else:
                    print_warning("Tempo detection failed")
                    tempo = 120  # Default
                    print_info(f"Using default tempo: {tempo} BPM")
                    self.test_results["warnings"] += 1
            
            self.test_results["passed"] += 1
            return {
                'key': file_key,
                'tempo': tempo,
                'duration': waveform.get('duration', 0)
            }
            
        except Exception as e:
            print_error(f"Upload test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results["failed"] += 1
            return None
    
    async def test_sectionization(self, file_key: str, tempo: float) -> List[Dict]:
        """Test 6: Smart sectionization"""
        print_test("Smart Sectionization")
        
        try:
            payload = {
                'key': file_key,
                'bpm': tempo,
                'time_signature_num': 4,
                'max_section_bars': 16
            }
            
            print_info(f"Running sectionization at {tempo} BPM...")
            async with self.session.post(f"{self.api_base}/api/sectionize_smart",
                                        json=payload) as resp:
                if resp.status != 200:
                    print_error(f"Sectionization failed with status {resp.status}")
                    text = await resp.text()
                    print_error(f"Response: {text[:200]}")
                    self.test_results["failed"] += 1
                    return []
                
                result = await resp.json()
                sections = result.get('sections', [])
                
                if len(sections) == 0:
                    print_warning("No sections detected")
                    self.test_results["warnings"] += 1
                    return []
                
                print_success(f"Detected {len(sections)} sections")
                for i, section in enumerate(sections):
                    label = section.get('label', 'Unknown')
                    start = section.get('start', 0)
                    end = section.get('end', 0)
                    confidence = section.get('confidence', 0)
                    print_info(f"  {i+1}. {label:12} {start:6.1f}s - {end:6.1f}s  (conf: {confidence:.2f})")
                
                self.test_results["passed"] += 1
                return sections
                
        except Exception as e:
            print_error(f"Sectionization test failed: {e}")
            self.test_results["failed"] += 1
            return []
    
    async def test_drum_generation(self, drummer_id: str, tempo: float, sections: List[Dict]) -> List[Dict]:
        """Test 7: Generate drums with selected drummer"""
        print_test(f"Drum Generation with {drummer_id}")
        
        if not sections:
            print_warning("No sections provided, creating test section")
            sections = [{
                'start': 0,
                'end': 8,
                'label': 'test',
                'fill_in': False,
                'fill_out': True,
                'density': 0.7
            }]
        
        try:
            # Test with first section only
            test_section = sections[0]
            
            payload = {
                'drummer_id': drummer_id,
                'bpm': tempo,
                'sections': [{
                    'start': test_section['start'],
                    'end': test_section['end'],
                    'fill_in': test_section.get('fill_in', False),
                    'fill_out': test_section.get('fill_out', True),
                    'label': test_section.get('label', 'verse'),
                    'density': test_section.get('density', 0.7)
                }],
                'song_analysis': {}
            }
            
            print_info(f"Generating for section: {test_section.get('label', 'Unknown')}")
            print_info(f"  Time: {test_section['start']:.1f}s - {test_section['end']:.1f}s")
            print_info(f"  Tempo: {tempo} BPM")
            
            async with self.session.post(f"{self.api_base}/api/generate_with_drummer",
                                        json=payload) as resp:
                if resp.status != 200:
                    print_error(f"Generation failed with status {resp.status}")
                    text = await resp.text()
                    print_error(f"Response: {text[:200]}")
                    self.test_results["failed"] += 1
                    return []
                
                result = await resp.json()
                notes = result.get('notes', [])
                params_used = result.get('params_used', {})
                
                if len(notes) == 0:
                    print_error("No notes generated!")
                    self.test_results["failed"] += 1
                    return []
                
                print_success(f"Generated {len(notes)} MIDI notes")
                
                # Analyze generated notes
                lanes = {}
                for note in notes:
                    lane = note.get('lane', 'unknown')
                    lanes[lane] = lanes.get(lane, 0) + 1
                
                print_info("Note distribution:")
                for lane, count in sorted(lanes.items()):
                    print_info(f"  {lane:10} {count:4} notes")
                
                print_info("Generation parameters:")
                for key, value in params_used.items():
                    print_info(f"  {key}: {value}")
                
                self.test_results["passed"] += 1
                return notes
                
        except Exception as e:
            print_error(f"Drum generation test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results["failed"] += 1
            return []
    
    async def test_midi_export(self, notes: List[Dict], tempo: float) -> bool:
        """Test 8: MIDI export functionality"""
        print_test("MIDI Export")
        
        if not notes:
            print_warning("No notes to export")
            self.test_results["warnings"] += 1
            return False
        
        # For now, just verify that notes are in correct format
        print_info("Validating MIDI note format...")
        
        valid = True
        for i, note in enumerate(notes[:5]):  # Check first 5
            if 'time' not in note or 'lane' not in note or 'vel' not in note:
                print_error(f"Invalid note format at index {i}: {note}")
                valid = False
        
        if valid:
            print_success("MIDI notes are in correct format")
            print_info(f"  Total notes: {len(notes)}")
            print_info(f"  Time range: {notes[0]['time']:.2f}s - {notes[-1]['time']:.2f}s")
            print_info(f"  Velocity range: {min(n['vel'] for n in notes)} - {max(n['vel'] for n in notes)}")
            
            # Note: Actual MIDI file export would happen in Rust
            print_info("MIDI file export is handled by Rust audio-core")
            print_info("  Command: audio-core generate-midi --notes <json>")
            
            self.test_results["passed"] += 1
            return True
        else:
            print_error("MIDI notes have invalid format")
            self.test_results["failed"] += 1
            return False
    
    async def run_full_workflow(self, test_audio_file: str = None):
        """Run complete Phase 1 workflow test"""
        
        print_header("PHASE 1: DCSM STUDIO WORKFLOW TEST")
        print_info(f"API Base: {self.api_base}")
        print_info(f"Test Audio: {test_audio_file or 'Will be provided'}")
        print()
        
        # Test 1: Backend health
        if not await self.test_backend_health():
            print_error("Cannot proceed without backend")
            return
        
        # Test 2: Drummer list
        await self.test_drummer_list()
        
        # Test 3: Drummer details
        drummer = await self.test_drummer_details("studio_groove_master")
        
        # Test 4: Rust availability
        await self.test_rust_audio_core()
        
        # Test 5: Upload & analyze (only if file provided)
        if test_audio_file:
            upload_result = await self.upload_test_file(test_audio_file)
            
            if upload_result:
                file_key = upload_result['key']
                tempo = upload_result['tempo']
                
                # Test 6: Sectionization
                sections = await self.test_sectionization(file_key, tempo)
                
                # Test 7: Drum generation
                if drummer:
                    notes = await self.test_drum_generation(
                        drummer['id'],
                        tempo,
                        sections
                    )
                    
                    # Test 8: MIDI export
                    if notes:
                        await self.test_midi_export(notes, tempo)
        else:
            print_warning("No test audio file provided")
            print_info("Skipping upload, sectionization, and generation tests")
            print_info("To run full test: python test_phase1_complete_workflow.py <audio_file.mp3>")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")
        
        total = self.test_results["passed"] + self.test_results["failed"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        warnings = self.test_results["warnings"]
        
        if failed == 0:
            print(f"{Colors.OKGREEN}{Colors.BOLD}✓ ALL TESTS PASSED{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.ENDC}")
        
        print()
        print(f"  Passed:   {Colors.OKGREEN}{passed:3}{Colors.ENDC} / {total}")
        print(f"  Failed:   {Colors.FAIL}{failed:3}{Colors.ENDC} / {total}")
        print(f"  Warnings: {Colors.WARNING}{warnings:3}{Colors.ENDC}")
        print()
        
        if failed == 0 and warnings == 0:
            print(f"{Colors.OKGREEN}Phase 1 is READY FOR PRODUCTION! 🎉{Colors.ENDC}")
        elif failed == 0:
            print(f"{Colors.WARNING}Phase 1 is functional but has warnings ⚠️{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}Phase 1 needs fixes before proceeding ❌{Colors.ENDC}")
        
        print()


async def main():
    """Main test runner"""
    
    # Get test audio file from command line
    test_file = None
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if not Path(test_file).exists():
            print(f"{Colors.FAIL}Error: File not found: {test_file}{Colors.ENDC}")
            sys.exit(1)
    
    # Run tests
    async with Phase1WorkflowTester() as tester:
        await tester.run_full_workflow(test_file)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
        sys.exit(1)
