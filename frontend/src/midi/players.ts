// Default MIDI Players using Tone.js for DrumTracKAI Open Source WebDAW
// Provides basic instruments for drums, bass, and melodic tracks

import * as Tone from 'tone'
import { MidiTrackKind } from './types'
import { wireToneInstrument } from '../audio/graph'

// Drum sample mappings - fixed to use actual sample files
const DRUM_SAMPLES = {
  'C1': 'kick.wav',
  'C#1': 'kick.wav', 
  'D1': 'snare.wav',
  'D#1': 'snare.wav',
  'E1': 'snare.wav',
  'F1': 'kick.wav',
  'F#1': 'hihat.wav',
  'G1': 'hihat.wav',
  'G#1': 'hihat.wav',
  'A1': 'crash.wav',
  'A#1': 'crash.wav',
  'B1': 'crash.wav'
}

export interface DrumKit {
  kick: Tone.Player
  snare: Tone.Player
  hihat: Tone.Player
  openhat: Tone.Player
  crash: Tone.Player
  ride: Tone.Player
  tom1: Tone.Player
  tom2: Tone.Player
  tom3: Tone.Player
}

/**
 * Create a drum sampler with basic kit sounds
 * Uses our existing drum samples from public/samples/drums/
 */
export function createDrumPlayer(trackId: string): Tone.Sampler {
  const sampler = new Tone.Sampler({
    urls: DRUM_SAMPLES,
    baseUrl: '/samples/drums/',
    onload: () => {
      console.log('Drum kit loaded successfully')
    }
  }).toDestination()
  
  wireToneInstrument(trackId, sampler)
  return sampler
}

/**
 * Create a bass synthesizer
 */
export function createBassPlayer(trackId: string): Tone.Synth {
  const synth = new Tone.Synth({
    oscillator: {
      type: 'sawtooth'
    },
    envelope: {
      attack: 0.01,
      decay: 0.1,
      sustain: 0.6,
      release: 0.2
    }
  }).toDestination()
  
  wireToneInstrument(trackId, synth)
  return synth
}

/**
 * Create a melodic polyphonic synthesizer
 */
export function createMelodicPlayer(trackId: string): Tone.PolySynth {
  const synth = new Tone.PolySynth(Tone.Synth, {
    oscillator: {
      type: 'triangle'
    },
    envelope: {
      attack: 0.02,
      decay: 0.1,
      sustain: 0.8,
      release: 0.5
    }
  }).toDestination()
  
  wireToneInstrument(trackId, synth)
  return synth
}

/**
 * Get default player for a track kind
 * @param trackKind Type of MIDI track
 * @param trackId Track identifier for audio graph wiring
 * @returns Configured Tone.js instrument
 */
export function getDefaultPlayer(trackKind: MidiTrackKind, trackId: string): any {
  switch (trackKind) {
    case 'drums':
      return createDrumPlayer(trackId)
    case 'bass':
      return createBassPlayer(trackId)
    case 'melodic':
      return createMelodicPlayer(trackId)
    default:
      return createMelodicPlayer(trackId)
  }
}

/**
 * Create a player with custom samples
 * @param sampleMap Map of MIDI notes to sample URLs
 * @param baseUrl Base URL for samples
 * @returns Configured sampler
 */
export function createCustomPlayer(
  sampleMap: Record<string, string>,
  baseUrl = '/samples/'
): Tone.Sampler {
  return new Tone.Sampler({
    urls: sampleMap,
    baseUrl,
    onload: () => {
      console.log('Custom samples loaded successfully')
    },
    onerror: (error) => {
      console.warn('Failed to load custom samples:', error)
    }
  }).toDestination()
}

/**
 * Standard GM drum map (General MIDI)
 */
export const GM_DRUM_MAP = {
  kick: 36,        // C1
  snare: 38,       // D1
  hihat: 42,       // F#1
  openhat: 46,     // A#1
  crash: 49,       // C#2
  ride: 51,        // D#2
  tom1: 50,        // D2 - High tom
  tom2: 47,        // B1 - Mid tom
  tom3: 41,        // F1 - Floor tom
  clap: 40,        // E1
  cowbell: 56,     // G#2
  tambourine: 54   // F#2
}

/**
 * Create effects chain for drum processing
 */
export function createDrumEffects(): Tone.Channel {
  const channel = new Tone.Channel({
    volume: 0,
    pan: 0
  })
  
  // Add compression for punch
  const compressor = new Tone.Compressor({
    threshold: -12,
    ratio: 4,
    attack: 0.003,
    release: 0.1
  })
  
  // Add EQ for shaping
  const eq = new Tone.EQ3({
    low: 0,
    mid: 0,
    high: 0
  })
  
  // Connect effects chain
  channel.chain(compressor, eq, Tone.Destination)
  
  return channel
}

/**
 * Create effects chain for bass processing
 */
export function createBassEffects(): Tone.Channel {
  const channel = new Tone.Channel({
    volume: 0,
    pan: 0
  })
  
  // Add compression for consistency
  const compressor = new Tone.Compressor({
    threshold: -18,
    ratio: 6,
    attack: 0.01,
    release: 0.1
  })
  
  // Add saturation for warmth
  const distortion = new Tone.Distortion({
    distortion: 0.1,
    oversample: '2x'
  })
  
  // Connect effects chain
  channel.chain(compressor, distortion, Tone.Destination)
  
  return channel
}
