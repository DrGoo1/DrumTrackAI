// Transport Bridge - Synchronizes audio timeline with MIDI system
// Ensures single source of truth for tempo, cursor, and playback state

import * as Tone from 'tone'
import { useDawStore } from '../state/dawStore'
import { useMidi } from '../midi/midiStore'
import { useV3Store } from '../state/v3/store'
import { MidiScheduler } from '../midi/scheduler'
import { getDefaultPlayer } from '../midi/players'

export class TransportBridge {
  private midiScheduler: MidiScheduler
  private unsubscribers: (() => void)[] = []
  private isInitialized = false

  private simplifyTempoMap(tempoMap: any[]): any[] {
    if (!Array.isArray(tempoMap) || tempoMap.length === 0) return []

    // If analysis provides a dense tempo map, small per-point jitter can feel like
    // random/non-musical tempo changes during drum playback. For MIDI playback we
    // prefer a stable tempo unless there's clear intentional tempo variation.
    if (tempoMap.length < 8) return tempoMap

    const bpms = tempoMap
      .map((p: any) => Number(p?.bpm))
      .filter((v: number) => Number.isFinite(v))
    if (bpms.length === 0) return tempoMap

    const sorted = [...bpms].sort((a, b) => a - b)
    const median = sorted[Math.floor(sorted.length / 2)]
    const min = sorted[0]
    const max = sorted[sorted.length - 1]
    const range = max - min

    // If overall variation is small, flatten to a single BPM.
    if (range <= 3.0) {
      const stable = Number.isFinite(median) ? median : bpms[0]
      const first = tempoMap[0]
      return [{ ...first, bpm: stable }]
    }

    return tempoMap
  }
  
  constructor() {
    this.midiScheduler = new MidiScheduler(
      () => useMidi.getState().song.tempoMap,
      480 // PPQ
    )
  }
  
  /**
   * Initialize the transport bridge
   * Sets up bidirectional sync between audio and MIDI systems
   */
  initialize() {
    if (this.isInitialized) return
    
    console.log('Initializing transport bridge...')
    
    // Sync tempo map from audio to MIDI
    this.syncTempoMap()
    
    // Sync arrangement sections from audio to MIDI
    this.syncArrangementSections()
    
    // Sync transport controls
    this.syncTransportControls()
    
    // Sync MIDI tracks with scheduler
    this.syncMidiTracks()
    
    // Set up Tone.js transport
    this.setupToneTransport()
    
    this.isInitialized = true
    console.log('Transport bridge initialized successfully')
  }
  
  /**
   * Dispose of all resources and unsubscribe from stores
   */
  dispose() {
    this.unsubscribers.forEach(unsub => unsub())
    this.unsubscribers = []
    this.midiScheduler.dispose()
    this.isInitialized = false
  }
  
  /**
   * Sync tempo map from audio analysis to MIDI store
   */
  private syncTempoMap() {
    const unsubscribe = useDawStore.subscribe((state) => {
      if (useV3Store.getState().ui.arrangementOwner === 'v3') return
      const tempoMap = state.project?.analytics?.tempoMap || []
      if (tempoMap.length > 0) {
        const stableTempoMap = this.simplifyTempoMap(tempoMap)
        console.log('Syncing tempo map to MIDI:', stableTempoMap.length, 'points')
        useMidi.getState().setTempoMap(stableTempoMap)
        
        // Update Tone.js transport BPM (use first tempo point)
        if (stableTempoMap[0]) {
          Tone.Transport.bpm.value = stableTempoMap[0].bpm
        }
      }
    })
    
    this.unsubscribers.push(unsubscribe)
  }
  
  /**
   * Sync arrangement sections from audio analysis to MIDI store
   */
  private syncArrangementSections() {
    const unsubscribe = useDawStore.subscribe((state) => {
      if (useV3Store.getState().ui.arrangementOwner === 'v3') return
      const sections = state.project?.analytics?.sections || []
      if (sections.length > 0) {
        console.log('Syncing arrangement sections to MIDI:', sections.length, 'sections')
        useMidi.getState().setSections(sections)
      }
    })
    
    this.unsubscribers.push(unsubscribe)
  }
  
  /**
   * Sync transport controls (play/pause/stop/seek)
   */
  private syncTransportControls() {
    // Sync DAW playing state to Tone.Transport
    const playingUnsub = useDawStore.subscribe((state) => {
      const playing = state.playing
      if (playing) {
        if (Tone.Transport.state !== 'started') {
          const startAt = Math.max(0, Number(state.cursorSec) || 0)
          Tone.Transport.start('+0', startAt)
          this.midiScheduler.start()
        }
      } else {
        if (Tone.Transport.state === 'started') {
          Tone.Transport.pause()
          this.midiScheduler.pause()
        }
      }
    })
    
    // Sync cursor position
    const cursorUnsub = useDawStore.subscribe((state) => {
      const cursorSec = state.cursorSec
      const transportSeconds = Tone.Transport.seconds
      const diff = Math.abs(transportSeconds - cursorSec)
      // While playing, avoid constantly forcing Tone.Transport to chase the waveform-playlist clock.
      // That feedback loop can cause audible jitter / worse sync. Only correct large drift.
      const threshold = state.playing ? 0.25 : 0.05
      if (diff > threshold) {
        Tone.Transport.seconds = cursorSec
        this.midiScheduler.seek(cursorSec)
      }
    })
    
    // Sync loop settings
    const loopUnsub = useDawStore.subscribe((state) => {
      const enabled = state.loopEnabled
      const start = state.loopStartSec
      const end = state.loopEndSec
      
      if (enabled && start < end) {
        Tone.Transport.loopStart = start
        Tone.Transport.loopEnd = end
        Tone.Transport.loop = true
        this.midiScheduler.setLoop(start, end)
      } else {
        Tone.Transport.loop = false
        this.midiScheduler.disableLoop()
      }
    })
    
    this.unsubscribers.push(playingUnsub, cursorUnsub, loopUnsub)
  }
  
  /**
   * Sync MIDI tracks with scheduler
   */
  private syncMidiTracks() {
    const unsubscribe = useMidi.subscribe((state) => {
      const tracks = state.song.tracks
      console.log('Syncing MIDI tracks with scheduler:', tracks.length, 'tracks')
      
      // Update scheduler for each track
      tracks.forEach(track => {
        const instrument = getDefaultPlayer(track.kind, track.id)
        this.midiScheduler.setTrack(track, instrument)
      })
    })
    
    this.unsubscribers.push(unsubscribe)
  }
  
  /**
   * Set up Tone.js transport configuration
   */
  private setupToneTransport() {
    // Set initial BPM
    const initialTempo = useMidi.getState().song.tempoMap[0]
    if (initialTempo) {
      Tone.Transport.bpm.value = initialTempo.bpm
    }
    
    // Set up transport callbacks
    Tone.Transport.on('start', () => {
      console.log('Tone.Transport started')
    })
    
    Tone.Transport.on('stop', () => {
      console.log('Tone.Transport stopped')
    })
    
    Tone.Transport.on('pause', () => {
      console.log('Tone.Transport paused')
    })
    
    // NOTE: Do not sync Tone.Transport time back into the DAW cursor.
    // waveform-playlist (audio timeline) is the master clock; Tone follows it.
  }
  
  /**
   * Get current MIDI scheduler instance
   */
  getMidiScheduler(): MidiScheduler {
    return this.midiScheduler
  }
  
  /**
   * Force sync all systems (useful for debugging)
   */
  forceSyncAll() {
    console.log('Force syncing all transport systems...')
    
    const dawState = useDawStore.getState()
    const midiState = useMidi.getState()
    
    // Sync tempo
    if (dawState.project?.analytics?.tempoMap) {
      midiState.setTempoMap(dawState.project.analytics.tempoMap)
    }
    
    // Sync sections
    if (dawState.project?.analytics?.sections) {
      midiState.setSections(dawState.project.analytics.sections)
    }
    
    // Sync transport state
    if (dawState.playing) {
      Tone.Transport.start()
      this.midiScheduler.start()
    } else {
      Tone.Transport.pause()
      this.midiScheduler.pause()
    }
    
    // Sync cursor
    Tone.Transport.seconds = dawState.cursorSec
    this.midiScheduler.seek(dawState.cursorSec)
    
    console.log('Force sync complete')
  }
}

// Global transport bridge instance
let transportBridge: TransportBridge | null = null

/**
 * Get or create the global transport bridge instance
 */
export function getTransportBridge(): TransportBridge {
  if (!transportBridge) {
    transportBridge = new TransportBridge()
  }
  return transportBridge
}

/**
 * Initialize the transport bridge (call once in app startup)
 */
export function initializeTransportBridge(): TransportBridge {
  const bridge = getTransportBridge()
  bridge.initialize()
  return bridge
}

/**
 * Dispose of the transport bridge (call on app shutdown)
 */
export function disposeTransportBridge() {
  if (transportBridge) {
    transportBridge.dispose()
    transportBridge = null
  }
}
