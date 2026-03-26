// MIDI Scheduler using Tone.js for DrumTracKAI Open Source WebDAW
// Handles sample-accurate MIDI playback synchronized with audio timeline

import * as Tone from 'tone'
import { MidiTrack, MidiNote, TempoPt } from './types'
import { ticksToSeconds } from './tempo'

export interface MidiInstrument {
  // Extended interface for MIDI-specific instruments
  triggerAttackRelease: (frequency: any, duration: number, time: number, velocity: number) => void
  dispose: () => void
}

export class MidiScheduler {
  private parts: Record<string, Tone.Part> = {}
  private instruments: Record<string, MidiInstrument> = {}
  private ppq: number
  
  constructor(
    private getTempoMap: () => TempoPt[],
    ppq = 480
  ) {
    this.ppq = ppq
  }
  
  /**
   * Set up or update a MIDI track for playback
   * @param track MIDI track data
   * @param instrument Tone.js instrument for playback
   */
  setTrack(track: MidiTrack, instrument: MidiInstrument) {
    // Dispose existing part if it exists
    this.parts[track.id]?.dispose()
    
    // Store instrument reference
    this.instruments[track.id] = instrument
    
    // Create events array from all clips in track
    const events: { time: number; note: MidiNote; trackId: string }[] = []
    
    track.clips.forEach(clip => {
      clip.notes.forEach(note => {
        const startTime = ticksToSeconds(this.getTempoMap(), note.t0, this.ppq)
        events.push({ 
          time: startTime, 
          note, 
          trackId: track.id 
        })
      })
    })
    
    // Create Tone.Part for scheduling
    const part = new Tone.Part((time, event: any) => {
      const { note, trackId } = event
      const duration = ticksToSeconds(
        this.getTempoMap(), 
        note.t1 - note.t0, 
        this.ppq
      )
      
      // Skip if track is muted
      if (track.muted) return
      
      // Skip if another track is soloed and this isn't it
      const soloTracks = Object.values(this.parts).some(p => 
        this.getTrackById(trackId)?.solo
      )
      if (soloTracks && !track.solo) return
      
      // Trigger note on instrument
      this.triggerNote(instrument, note, duration, time)
      
    }, events).start(0)
    
    this.parts[track.id] = part
  }
  
  /**
   * Remove a track from scheduling
   * @param trackId Track ID to remove
   */
  removeTrack(trackId: string) {
    this.parts[trackId]?.dispose()
    delete this.parts[trackId]
    
    this.instruments[trackId]?.dispose()
    delete this.instruments[trackId]
  }
  
  /**
   * Update mute/solo state for a track
   * @param trackId Track ID
   * @param muted Mute state
   * @param solo Solo state
   */
  updateTrackState(trackId: string, muted: boolean, solo: boolean) {
    // Mute/solo is handled in the part callback
    // No need to recreate the part, just update the track data
  }
  
  /**
   * Trigger a MIDI note on an instrument
   * @param instrument Tone.js instrument
   * @param note MIDI note data
   * @param duration Note duration in seconds
   * @param time Scheduled time
   */
  private triggerNote(
    instrument: MidiInstrument, 
    note: MidiNote, 
    duration: number, 
    time: number
  ) {
    try {
      // Convert MIDI note number to frequency
      const frequency = Tone.Frequency(note.pitch, 'midi')
      
      // Convert velocity (0-127) to gain (0-1)
      const velocity = note.vel / 127
      
      // Trigger note with proper timing
      instrument.triggerAttackRelease(
        frequency, 
        Math.max(duration, 0.01), // Minimum duration
        time, 
        velocity
      )
    } catch (error) {
      console.warn('Failed to trigger MIDI note:', error)
    }
  }
  
  /**
   * Get track by ID (helper for solo checking)
   */
  private getTrackById(trackId: string): MidiTrack | undefined {
    // This would need to be injected or accessed from store
    // For now, return undefined to avoid errors
    return undefined
  }
  
  /**
   * Start all MIDI parts
   */
  start() {
    Object.values(this.parts).forEach(part => {
      if (part.state === 'stopped') {
        part.start()
      }
    })
  }
  
  /**
   * Stop all MIDI parts
   */
  stop() {
    Object.values(this.parts).forEach(part => {
      part.stop()
    })
  }
  
  /**
   * Pause all MIDI parts
   */
  pause() {
    // Tone.js doesn't have explicit pause, use stop
    this.stop()
  }
  
  /**
   * Seek to a specific time
   * @param seconds Time in seconds
   */
  seek(seconds: number) {
    // Stop all parts and restart from new position
    Object.values(this.parts).forEach(part => {
      part.stop()
      part.start(seconds)
    })
  }
  
  /**
   * Set loop region for all parts
   * @param startSeconds Loop start in seconds
   * @param endSeconds Loop end in seconds
   */
  setLoop(startSeconds: number, endSeconds: number) {
    Object.values(this.parts).forEach(part => {
      part.loopStart = startSeconds
      part.loopEnd = endSeconds
      part.loop = true
    })
  }
  
  /**
   * Disable looping for all parts
   */
  disableLoop() {
    Object.values(this.parts).forEach(part => {
      part.loop = false
    })
  }
  
  /**
   * Dispose all resources
   */
  dispose() {
    Object.values(this.parts).forEach(part => part.dispose())
    Object.values(this.instruments).forEach(inst => inst.dispose())
    this.parts = {}
    this.instruments = {}
  }
  
  /**
   * Get current playback state
   */
  getState() {
    const partStates = Object.values(this.parts).map(part => part.state)
    if (partStates.every(state => state === 'started')) return 'playing'
    if (partStates.every(state => state === 'stopped')) return 'stopped'
    return 'mixed'
  }
  
  /**
   * Update tempo map (called when audio analysis changes)
   */
  updateTempoMap() {
    // Recreate all parts with new tempo map
    const trackIds = Object.keys(this.parts)
    // Would need track data to recreate - this is a placeholder
    console.log('Tempo map updated, need to recreate parts for tracks:', trackIds)
  }
}
