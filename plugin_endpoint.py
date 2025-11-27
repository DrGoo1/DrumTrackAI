"""
Plugin API Endpoint - Handles requests from DrumTracKAI Connector Plugin
Integrates with existing backend for drum generation
"""

import base64
import io
import tempfile
from pathlib import Path
from aiohttp import web
import soundfile as sf
import mido
import logging

logger = logging.getLogger(__name__)


class PluginAPIHandler:
    """Handles API requests from the VST/AU plugin"""
    
    def __init__(self, audio_analyzer, drum_generator):
        """
        Args:
            audio_analyzer: Your existing audio analysis module
            drum_generator: Your existing drum generation module
        """
        self.audio_analyzer = audio_analyzer
        self.drum_generator = drum_generator
    
    async def handle_generate_request(self, request):
        """
        Main endpoint: POST /api/generate
        
        Accepts JSON with:
        {
            "api_key": "optional",
            "mode": "audio" or "midi",
            "bpm": 120.0,
            "time_sig": "4/4",
            "style_id": "default",
            "guide_enabled": true,
            "guide_instrument": "bass",  // "mix", "bass", "guitar", "keys", "vocal", "other"
            "audio_wav_base64": "..." (if mode == "audio"),
            "midi_smf_base64": "..." (if mode == "midi")
        }
        
        Returns:
        {
            "ok": true,
            "status_message": "success",
            "midi_smf_base64": "..."
        }
        """
        try:
            data = await request.json()
            
            # Validate request
            mode = data.get('mode', 'audio')
            bpm = float(data.get('bpm', 120.0))
            time_sig = data.get('time_sig', '4/4')
            api_key = data.get('api_key', '')
            style_id = data.get('style_id', 'default')
            
            # Guide track parameters
            guide_enabled = bool(data.get('guide_enabled', False))
            guide_instrument = data.get('guide_instrument', 'mix')
            
            logger.info(f"Plugin request: mode={mode}, bpm={bpm}, time_sig={time_sig}, "
                       f"guide={guide_instrument if guide_enabled else 'disabled'}")
            
            # Process based on mode
            if mode == 'audio':
                drum_midi = await self._process_audio_mode(data, bpm, time_sig, style_id, 
                                                          guide_enabled, guide_instrument)
            elif mode == 'midi':
                drum_midi = await self._process_midi_mode(data, bpm, time_sig, style_id,
                                                         guide_enabled, guide_instrument)
            else:
                return web.json_response({
                    'ok': False,
                    'status_message': f'Invalid mode: {mode}'
                }, status=400)
            
            if drum_midi is None:
                return web.json_response({
                    'ok': False,
                    'status_message': 'Failed to generate drums'
                }, status=500)
            
            # Convert MIDI to base64
            midi_b64 = base64.b64encode(drum_midi).decode('utf-8')
            
            return web.json_response({
                'ok': True,
                'status_message': 'success',
                'midi_smf_base64': midi_b64
            })
            
        except Exception as e:
            logger.error(f"Plugin API error: {e}", exc_info=True)
            return web.json_response({
                'ok': False,
                'status_message': str(e)
            }, status=500)
    
    async def _process_audio_mode(self, data, bpm, time_sig, style_id, guide_enabled, guide_instrument):
        """Process audio input and generate drums"""
        try:
            # Decode base64 WAV
            audio_b64 = data.get('audio_wav_base64', '')
            if not audio_b64:
                raise ValueError("No audio data provided")
            
            audio_bytes = base64.b64decode(audio_b64)
            
            # Save to temp file for analysis
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            try:
                # Analyze audio (use your existing analysis)
                analysis = await self._analyze_audio(tmp_path, bpm, guide_enabled, guide_instrument)
                
                # Add metadata to analysis
                analysis['style_id'] = style_id
                analysis['guide_enabled'] = guide_enabled
                analysis['guide_instrument'] = guide_instrument
                
                # Generate drum track
                drum_midi = await self._generate_drums_from_analysis(
                    analysis, bpm, time_sig
                )
                
                return drum_midi
                
            finally:
                # Cleanup
                Path(tmp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return None
    
    async def _process_midi_mode(self, data, bpm, time_sig, style_id, guide_enabled, guide_instrument):
        """Process MIDI input and generate enhanced drums"""
        try:
            # Decode base64 MIDI
            midi_b64 = data.get('midi_smf_base64', '')
            if not midi_b64:
                raise ValueError("No MIDI data provided")
            
            midi_bytes = base64.b64decode(midi_b64)
            
            # Parse MIDI
            with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
                tmp.write(midi_bytes)
                tmp_path = tmp.name
            
            try:
                # Analyze MIDI pattern
                analysis = await self._analyze_midi(tmp_path, bpm, guide_enabled, guide_instrument)
                
                # Add metadata to analysis
                analysis['style_id'] = style_id
                analysis['guide_enabled'] = guide_enabled
                analysis['guide_instrument'] = guide_instrument
                
                # Generate enhanced drum track
                drum_midi = await self._generate_drums_from_analysis(
                    analysis, bpm, time_sig
                )
                
                return drum_midi
                
            finally:
                Path(tmp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"MIDI processing failed: {e}")
            return None
    
    async def _analyze_audio(self, audio_path, bpm, guide_enabled, guide_instrument):
        """
        Analyze audio using your existing system
        Returns dict with tempo, sections, energy, etc.
        
        If guide_enabled and guide_instrument == "bass":
            - Emphasize low-frequency transients
            - Focus on bass fundamental tracking
            - Align kick patterns to bass
        
        If guide_enabled and guide_instrument == "guitar" or "keys":
            - Emphasize harmonic rhythm / chord hits
            - Use for drum accents
        """
        # TODO: Use your actual audio analyzer with guide-aware processing
        # Example:
        # if guide_enabled and guide_instrument == 'bass':
        #     analysis = self.audio_analyzer.analyze_bass_guide(audio_path)
        # else:
        #     analysis = self.audio_analyzer.analyze(audio_path)
        
        # Placeholder - replace with actual analysis
        analysis = {
            'tempo': bpm,
            'time_signature': '4/4',
            'sections': [
                {'type': 'verse', 'start': 0, 'end': 8},
                {'type': 'chorus', 'start': 8, 'end': 16}
            ],
            'energy_curve': [0.7] * 16,
            'style': 'rock',
            'guide_enabled': guide_enabled,
            'guide_instrument': guide_instrument
        }
        
        return analysis
    
    async def _analyze_midi(self, midi_path, bpm, guide_enabled, guide_instrument):
        """
        Analyze MIDI pattern
        Returns dict with pattern info
        """
        try:
            mid = mido.MidiFile(midi_path)
            
            # Extract basic info
            analysis = {
                'tempo': bpm,
                'time_signature': '4/4',
                'length_bars': 4,
                'complexity': 0.5,
                'style': 'rock',
                'guide_enabled': guide_enabled,
                'guide_instrument': guide_instrument
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"MIDI analysis failed: {e}")
            return {
                'tempo': bpm,
                'style': 'rock',
                'guide_enabled': guide_enabled,
                'guide_instrument': guide_instrument
            }
    
    async def _generate_drums_from_analysis(self, analysis, bpm, time_sig):
        """
        Generate drum MIDI from analysis
        Returns MIDI file bytes
        
        Use guide_enabled and guide_instrument from analysis:
        - If guide_enabled and guide_instrument == 'bass':
            * Align kick patterns to bass hits
            * Lock groove to bass timing
        - If guide_enabled and guide_instrument == 'guitar' or 'keys':
            * Use chord hits for accent patterns
            * Align snare to rhythm guitar strums
        """
        # TODO: Use your actual drum generator with guide-aware logic
        # Example:
        # guide_enabled = analysis.get('guide_enabled', False)
        # guide_instrument = analysis.get('guide_instrument', 'mix')
        # 
        # if guide_enabled and guide_instrument == 'bass':
        #     drum_track = self.drum_generator.generate_bass_locked(analysis)
        # elif guide_enabled and guide_instrument == 'guitar':
        #     drum_track = self.drum_generator.generate_chord_accents(analysis)
        # else:
        #     drum_track = self.drum_generator.generate(analysis)
        
        # Placeholder - generate simple drum pattern
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        mid.tracks.append(track)
        
        # Set tempo
        tempo_us = mido.bpm2tempo(bpm)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo_us))
        track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))
        
        # Generate basic pattern (kick on 1 and 3, snare on 2 and 4, hihats on 8ths)
        ticks_per_beat = 480
        ticks_per_bar = ticks_per_beat * 4
        
        for bar in range(4):  # 4 bars
            bar_start = bar * ticks_per_bar
            
            # Kick (note 36) on beats 1 and 3
            track.append(mido.Message('note_on', note=36, velocity=100, time=bar_start if bar == 0 else 0))
            track.append(mido.Message('note_off', note=36, velocity=0, time=100))
            track.append(mido.Message('note_on', note=36, velocity=100, time=ticks_per_beat * 2 - 100))
            track.append(mido.Message('note_off', note=36, velocity=0, time=100))
            
            # Snare (note 38) on beats 2 and 4
            track.append(mido.Message('note_on', note=38, velocity=100, time=ticks_per_beat - 100))
            track.append(mido.Message('note_off', note=38, velocity=0, time=100))
            track.append(mido.Message('note_on', note=38, velocity=100, time=ticks_per_beat - 100))
            track.append(mido.Message('note_off', note=38, velocity=0, time=100))
            
            # Hihat (note 42) on 8th notes
            for eighth in range(8):
                if eighth > 0 or bar > 0:  # Skip first note as it's at time 0
                    track.append(mido.Message('note_on', note=42, velocity=80, time=ticks_per_beat // 2 - 50 if eighth > 0 else 0))
                else:
                    track.append(mido.Message('note_on', note=42, velocity=80, time=0))
                track.append(mido.Message('note_off', note=42, velocity=0, time=50))
        
        # End of track
        track.append(mido.MetaMessage('end_of_track', time=0))
        
        # Convert to bytes
        with io.BytesIO() as bio:
            mid.save(file=bio)
            midi_bytes = bio.getvalue()
        
        return midi_bytes


def setup_plugin_routes(app, audio_analyzer=None, drum_generator=None):
    """
    Add plugin API routes to your aiohttp app
    
    Usage:
        app = web.Application()
        setup_plugin_routes(app, your_audio_analyzer, your_drum_generator)
    """
    handler = PluginAPIHandler(audio_analyzer, drum_generator)
    
    app.router.add_post('/api/generate', handler.handle_generate_request)
    
    logger.info("Plugin API endpoint registered: POST /api/generate")
    
    return handler


# Standalone test server
if __name__ == '__main__':
    import asyncio
    from aiohttp import web
    
    logging.basicConfig(level=logging.INFO)
    
    app = web.Application()
    setup_plugin_routes(app)
    
    print("=" * 80)
    print("DrumTracKAI Plugin API Test Server")
    print("=" * 80)
    print("Running on http://localhost:8000")
    print("Endpoint: POST /api/generate")
    print()
    print("This is a test server with placeholder drum generation.")
    print("Integrate with your actual backend for real functionality.")
    print("=" * 80)
    
    web.run_app(app, host='localhost', port=8000)
