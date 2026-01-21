// Default MIDI Players using Tone.js for DrumTracKAI Open Source WebDAW
// Provides basic instruments for drums, bass, and melodic tracks

import { MidiTrackKind } from './types'
import { getSharedAudioContext, resumeSharedAudioContext } from '../audio/sharedAudioContext'

type WebAudioInstrument = {
  triggerAttackRelease: (note: any, duration: number, time: number, velocity: number) => void
  dispose: () => void
}

function midiToNoteName(midi: number): string {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  const n = Math.max(0, Math.min(127, Math.round(midi)))
  const name = names[n % 12]
  const oct = Math.floor(n / 12) - 1
  return `${name}${oct}`
}

function resolveNoteToSampleKey(note: any): string {
  // Accept MIDI number, note name string, or anything else.
  if (typeof note === 'number' && Number.isFinite(note)) return midiToNoteName(note)
  if (typeof note === 'string' && note.length) return note
  return 'C1'
}

function createSampleInstrument(trackId: string, sampleMap: Record<string, string>, baseUrl: string): WebAudioInstrument {
  const ctx = getSharedAudioContext({ latencyHint: 'interactive' })
  const buffers = new Map<string, AudioBuffer>()
  const inflight = new Map<string, Promise<AudioBuffer>>()

  const load = async (key: string): Promise<AudioBuffer> => {
    const existing = buffers.get(key)
    if (existing) return existing
    const inProg = inflight.get(key)
    if (inProg) return inProg

    const url = `${baseUrl}${sampleMap[key] || sampleMap['C1'] || 'kick.wav'}`
    const p = (async () => {
      await resumeSharedAudioContext()
      const res = await fetch(url)
      const arr = await res.arrayBuffer()
      const buf = await ctx.decodeAudioData(arr)
      buffers.set(key, buf)
      inflight.delete(key)
      return buf
    })()

    inflight.set(key, p)
    return p
  }

  return {
    triggerAttackRelease: (note: any, duration: number, time: number, velocity: number) => {
      const key = resolveNoteToSampleKey(note)
      void (async () => {
        const buf = await load(key)
        const src = ctx.createBufferSource()
        src.buffer = buf
        const gain = ctx.createGain()
        gain.gain.value = Math.max(0, Math.min(1, velocity))
        src.connect(gain)
        gain.connect(ctx.destination)

        const when = Math.max(ctx.currentTime, time)
        const dur = Math.max(0.01, Number.isFinite(duration) ? duration : 0.1)
        try {
          src.start(when)
          src.stop(when + dur)
        } catch {
          // ignore
        }
      })()
    },
    dispose: () => {
      void trackId
      buffers.clear()
      inflight.clear()
    },
  }
}

/**
 * Create a drum sampler with basic kit sounds
 * Uses our existing drum samples from public/samples/drums/
 */
export function createDrumPlayer(trackId: string): any {
  const DRUM_SAMPLES: Record<string, string> = {
    C1: 'kick.wav',
    'C#1': 'kick.wav',
    D1: 'snare.wav',
    'D#1': 'snare.wav',
    E1: 'snare.wav',
    F1: 'kick.wav',
    'F#1': 'hihat.wav',
    G1: 'hihat.wav',
    'G#1': 'hihat.wav',
    A1: 'crash.wav',
    'A#1': 'crash.wav',
    B1: 'crash.wav',
  }

  return createSampleInstrument(trackId, DRUM_SAMPLES, '/samples/drums/') as any
}

/**
 * Create a bass synthesizer
 */
export function createBassPlayer(trackId: string): any {
  // Legacy MIDI synth path removed; return a lightweight instrument that does nothing.
  // The main app playback should route through the WebAudio drum engine.
  return {
    triggerAttackRelease: () => {},
    dispose: () => {
      void trackId
    },
  } as any
}

/**
 * Create a melodic polyphonic synthesizer
 */
export function createMelodicPlayer(trackId: string): any {
  return {
    triggerAttackRelease: () => {},
    dispose: () => {
      void trackId
    },
  } as any
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
): any {
  return createSampleInstrument('custom', sampleMap, baseUrl)
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
export function createDrumEffects(): any {
  // Effects chain removed from Tone-based path.
  // Keep signature for compatibility.
  return {} as any
}

/**
 * Create effects chain for bass processing
 */
export function createBassEffects(): any {
  return {} as any
}
