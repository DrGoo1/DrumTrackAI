// MIDI Import/Export using @tonejs/midi for Standard MIDI Files
// Handles conversion between SMF format and our internal MIDI data model

import { Midi } from '@tonejs/midi'
import { useMidi } from './midiStore'
import { MidiSong, MidiTrack, MidiNote, MidiTrackKind } from './types'

/**
 * Import Standard MIDI File from ArrayBuffer
 * @param arrayBuffer SMF file data
 * @param preserveAudioTempo Whether to keep existing audio tempo map
 */
export async function importSMF(arrayBuffer: ArrayBuffer, preserveAudioTempo = true): Promise<void> {
  try {
    const midi = new Midi(arrayBuffer)
    const midiStore = useMidi.getState()
    
    console.log('Importing MIDI file:', {
      tracks: midi.tracks.length,
      duration: midi.duration,
      ppq: midi.header.ppq,
      tempos: midi.header.tempos.length
    })
    
    // Import tempo map if not preserving audio tempo
    if (!preserveAudioTempo && midi.header.tempos.length > 0) {
      const tempoMap = midi.header.tempos.map(tempo => ({
        tSec: tempo.time,
        bpm: tempo.bpm
      }))
      midiStore.setTempoMap(tempoMap)
      console.log('Imported tempo map:', tempoMap.length, 'points')
    }
    
    // Import time signature
    if (midi.header.timeSignatures.length > 0) {
      const timeSig = midi.header.timeSignatures[0]
      // @tonejs/midi uses different property names
      const numerator = (timeSig as any).numerator || 4
      const denominator = (timeSig as any).denominator || 4
      midiStore.setTimeSig(numerator, denominator)
      console.log('Imported time signature:', numerator, '/', denominator)
    }
    
    // Import tracks
    midi.tracks.forEach((track, index) => {
      if (track.notes.length === 0) return // Skip empty tracks
      
      // Determine track kind based on channel and content
      const trackKind: MidiTrackKind = determineTrackKind(track, index)
      
      // Create track in store
      const trackId = midiStore.addTrack({
        name: track.name || `MIDI Track ${index + 1}`,
        kind: trackKind,
        chan: track.channel || 1
      })
      
      // Convert notes to our format
      const notes: MidiNote[] = track.notes.map(note => ({
        id: crypto.randomUUID(),
        t0: Math.round(note.ticks),
        t1: Math.round(note.ticks + note.durationTicks),
        pitch: note.midi,
        vel: Math.round(note.velocity * 127),
        chan: track.channel || 1
      }))
      
      // Create clip with all notes
      const clipStartTick = Math.min(...notes.map(n => n.t0))
      const clipEndTick = Math.max(...notes.map(n => n.t1))
      
      midiStore.addClip(trackId, {
        name: `${track.name || 'MIDI'} Clip`,
        startTick: clipStartTick,
        endTick: clipEndTick,
        notes
      })
      
      console.log(`Imported track "${track.name}":`, notes.length, 'notes')
    })
    
    console.log('MIDI import completed successfully')
    
  } catch (error) {
    console.error('Failed to import MIDI file:', error)
    throw new Error(`MIDI import failed: ${error.message}`)
  }
}

/**
 * Export current MIDI song to Standard MIDI File
 * @returns ArrayBuffer containing SMF data
 */
export function exportSMF(): ArrayBuffer {
  try {
    const { song } = useMidi.getState()
    const midi = new Midi()
    
    console.log('Exporting MIDI file:', {
      tracks: song.tracks.length,
      ppq: song.ppq,
      tempoPoints: song.tempoMap.length
    })
    
    // Set PPQ (use constructor or create new Midi with PPQ)
    // Note: @tonejs/midi may not allow direct PPQ modification after creation
    
    // Export tempo map - use any type to handle @tonejs/midi API differences
    song.tempoMap.forEach((tempoPoint, index) => {
      const tempoEvent = {
        time: index === 0 ? 0 : tempoPoint.tSec,
        bpm: tempoPoint.bpm,
        ticks: 0 // Add required ticks property
      }
      
      if (index === 0) {
        // Initialize tempo array if needed
        if (!midi.header.tempos) {
          (midi.header as any).tempos = []
        }
        (midi.header as any).tempos.push(tempoEvent)
      } else {
        (midi.header as any).tempos.push(tempoEvent)
      }
    })
    
    // Export time signature
    const [numerator, denominator] = song.timeSig
    // Use any type to bypass TypeScript restrictions for @tonejs/midi API differences
    if (!(midi.header as any).timeSignatures) {
      (midi.header as any).timeSignatures = []
    }
    (midi.header as any).timeSignatures.push({
      ticks: 0,
      numerator,
      denominator,
      metronome: 24,
      thirtyseconds: 8
    })
    
    // Export tracks
    song.tracks.forEach(track => {
      if (track.clips.length === 0) return // Skip empty tracks
      
      const midiTrack = midi.addTrack()
      midiTrack.name = track.name
      midiTrack.channel = track.chan
      
      // Add all notes from all clips
      track.clips.forEach(clip => {
        clip.notes.forEach(note => {
          midiTrack.addNote({
            midi: note.pitch,
            ticks: note.t0,
            durationTicks: note.t1 - note.t0,
            velocity: note.vel / 127
          })
        })
      })
      
      console.log(`Exported track "${track.name}":`, midiTrack.notes.length, 'notes')
    })
    
    const uint8Array = midi.toArray()
    // Convert Uint8Array to ArrayBuffer for compatibility
    const arrayBuffer = uint8Array.buffer.slice(uint8Array.byteOffset, uint8Array.byteOffset + uint8Array.byteLength) as ArrayBuffer
    console.log('MIDI export completed, size:', arrayBuffer.byteLength, 'bytes')
    
    return arrayBuffer
    
  } catch (error) {
    console.error('Failed to export MIDI file:', error)
    throw new Error(`MIDI export failed: ${error.message}`)
  }
}

/**
 * Save MIDI file to disk
 * @param filename Filename for the MIDI file
 */
export function saveMidiFile(filename = 'drumtrackai-song.mid'): void {
  try {
    const arrayBuffer = exportSMF()
    const blob = new Blob([arrayBuffer], { type: 'audio/midi' })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(url)
    console.log('MIDI file saved:', filename)
    
  } catch (error) {
    console.error('Failed to save MIDI file:', error)
    throw error
  }
}

/**
 * Load MIDI file from file input
 * @param file File object from input
 * @param preserveAudioTempo Whether to keep existing audio tempo
 */
export async function loadMidiFile(file: File, preserveAudioTempo = true): Promise<void> {
  try {
    const arrayBuffer = await file.arrayBuffer()
    await importSMF(arrayBuffer, preserveAudioTempo)
    console.log('MIDI file loaded:', file.name)
    
  } catch (error) {
    console.error('Failed to load MIDI file:', error)
    throw error
  }
}

/**
 * Determine track kind based on MIDI track content
 * @param track Tone.js MIDI track
 * @param index Track index
 * @returns Appropriate track kind
 */
function determineTrackKind(track: any, index: number): MidiTrackKind {
  // Channel 10 (9 in 0-based) is typically drums in General MIDI
  if (track.channel === 9) {
    return 'drums'
  }
  
  // First track is often drums in our context
  if (index === 0) {
    return 'drums'
  }
  
  // Check note range to guess instrument type
  const pitches = track.notes.map((note: any) => note.midi)
  const minPitch = Math.min(...pitches)
  const maxPitch = Math.max(...pitches)
  
  // Low notes suggest bass
  if (maxPitch < 60 && minPitch < 45) {
    return 'bass'
  }
  
  // Default to melodic
  return 'melodic'
}

/**
 * Create a template MIDI song for new projects
 * @param bpm Default BPM
 * @returns Template MIDI song
 */
export function createTemplateMidiSong(bpm = 120): MidiSong {
  return {
    ppq: 480,
    tempoMap: [{ tSec: 0, bpm }],
    timeSig: [4, 4],
    sections: [],
    tracks: []
  }
}

/**
 * Validate MIDI file before import
 * @param arrayBuffer SMF file data
 * @returns Validation result
 */
export function validateMidiFile(arrayBuffer: ArrayBuffer): { valid: boolean; error?: string; info?: any } {
  try {
    const midi = new Midi(arrayBuffer)
    
    return {
      valid: true,
      info: {
        tracks: midi.tracks.length,
        duration: midi.duration,
        ppq: midi.header.ppq,
        hasNotes: midi.tracks.some(track => track.notes.length > 0)
      }
    }
    
  } catch (error) {
    return {
      valid: false,
      error: error.message
    }
  }
}
