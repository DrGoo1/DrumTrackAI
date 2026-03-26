// MIDI Scheduler using Tone.js for DrumTracKAI Open Source WebDAW
// Handles sample-accurate MIDI playback synchronized with audio timeline

import * as Tone from 'tone'
import { MidiTrack, MidiNote, TempoPt } from './types'
import { getBpmAtTime, ticksToSeconds } from './tempo'

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
    const events: { time: number; note: MidiNote; trackId: string; disableGrooveShaping?: boolean }[] = []
    
    track.clips.forEach(clip => {
      clip.notes.forEach(note => {
        const startTime = ticksToSeconds(this.getTempoMap(), note.t0, this.ppq)
        events.push({ 
          time: startTime, 
          note, 
          trackId: track.id,
          disableGrooveShaping: clip.disableGrooveShaping,
        })
      })
    })
    
    // Create Tone.Part for scheduling
    const part = new Tone.Part((time, event: any) => {
      const { note, trackId, disableGrooveShaping } = event
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
      this.triggerNote(instrument, note, duration, time, Boolean(disableGrooveShaping))
      
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
    time: number,
    disableGrooveShaping: boolean
  ) {
    try {
      // Convert MIDI note number to frequency
      const frequency = Tone.Frequency(note.pitch, 'midi')
      
      // Convert velocity (0-127) to gain (0-1)
      const baseVelocity = Math.max(1, Math.min(127, note.vel)) / 127

      if (disableGrooveShaping) {
        const velocity = Math.max(0, Math.min(1, baseVelocity))
        instrument.triggerAttackRelease(
          frequency,
          Math.max(duration, 0.01),
          time,
          velocity,
        )
        return
      }

      // ---------------------------------------------------------------------
      // Groove-based playback shaping (NO randomness)
      // ---------------------------------------------------------------------
      // Goal: avoid "random" humanization; only apply musically motivated feel.
      // - hats: subtle swing + deterministic accent pattern
      // - snare: slightly laid-back
      // - kick: slightly ahead
      const role = this.drumRoleForPitch(note.pitch)

      const tempoMap = this.getTempoMap()
      const noteSec = ticksToSeconds(tempoMap, note.t0, this.ppq)
      const bpm = getBpmAtTime(tempoMap, noteSec)

      // Position helpers (assume 4/4-ish grid for feel shaping; still works generically)
      const ticksInQuarter = this.ppq
      const ticksInEighth = this.ppq / 2
      const ticksInSixteenth = this.ppq / 4
      const posInBeat = ((note.t0 % ticksInQuarter) + ticksInQuarter) % ticksInQuarter

      // A gentle swing feel by delaying the "and" (eighth offbeat) for hats/cymbals.
      const isEighthOffbeat = posInBeat >= ticksInEighth - ticksInSixteenth * 0.25 && posInBeat <= ticksInEighth + ticksInSixteenth * 0.25
      const swingMs = 10 // fixed, musical (not random)

      // Intentional microtiming offsets
      let timingOffsetMs = 0
      if ((role === 'hihat' || role === 'cymbal') && isEighthOffbeat) timingOffsetMs += swingMs
      if (role === 'snare') timingOffsetMs += 6
      if (role === 'kick') timingOffsetMs -= 3

      const when = time + timingOffsetMs / 1000

      // Deterministic velocity shaping
      let velocityMul = 1

      // Hi-hat accent pattern: stronger on downbeats / weaker on off subdivisions
      if (role === 'hihat') {
        const sixteenthIndex = Math.floor((((note.t0 % (ticksInQuarter * 4)) + (ticksInQuarter * 4)) % (ticksInQuarter * 4)) / ticksInSixteenth)
        const inBeatSixteenth = Math.floor(posInBeat / ticksInSixteenth)
        // Common feel: 1 e + a (accent 1 and 3, lighter e/a)
        if (inBeatSixteenth === 0) velocityMul *= 1.06
        else if (inBeatSixteenth === 2) velocityMul *= 0.96
        else velocityMul *= 0.92
        // Slightly stronger on beat 1/3 within bar
        if (sixteenthIndex === 0 || sixteenthIndex === 8) velocityMul *= 1.03
      }

      // Backbeat emphasis (helps groove without randomness)
      if (role === 'snare') {
        const beatInBar = Math.floor((((note.t0 % (ticksInQuarter * 4)) + (ticksInQuarter * 4)) % (ticksInQuarter * 4)) / ticksInQuarter)
        if (beatInBar === 1 || beatInBar === 3) velocityMul *= 1.05
      }

      // Convert resulting velocity, clamp
      const velocity = Math.max(0, Math.min(1, baseVelocity * velocityMul))
      
      // Trigger note with proper timing
      instrument.triggerAttackRelease(
        frequency, 
        Math.max(duration, 0.01), // Minimum duration
        when, 
        velocity
      )
    } catch (error) {
      console.warn('Failed to trigger MIDI note:', error)
    }
  }

  private drumRoleForPitch(pitch: number): 'kick' | 'snare' | 'hihat' | 'cymbal' | 'tom' | 'other' {
    // GM-ish pitch buckets for feel.
    if (pitch === 36 || pitch === 35) return 'kick'
    if (pitch === 38 || pitch === 40 || pitch === 37) return 'snare'
    if (pitch === 42 || pitch === 44 || pitch === 46) return 'hihat'
    if (pitch === 49 || pitch === 57 || pitch === 55 || pitch === 52 || pitch === 51 || pitch === 59) return 'cymbal'
    if (pitch === 41 || pitch === 43 || pitch === 45 || pitch === 47 || pitch === 48 || pitch === 50) return 'tom'
    return 'other'
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
