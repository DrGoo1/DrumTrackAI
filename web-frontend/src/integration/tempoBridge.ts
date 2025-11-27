// Transport Bridge - Synchronizes audio timeline with MIDI system
// Ensures single source of truth for tempo, cursor, and playback state

import * as Tone from 'tone'
import { useDawStore } from '../state/dawStore'
import { useMidi } from '../midi/midiStore'
import { MidiScheduler } from '../midi/scheduler'
import { getDefaultPlayer } from '../midi/players'

export class TransportBridge {
  private midiScheduler: MidiScheduler
  private unsubscribers: (() => void)[] = []
  private isInitialized = false
  
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
      const tempoMap = state.project?.analytics?.tempoMap || []
      if (tempoMap.length > 0) {
        console.log('Syncing tempo map to MIDI:', tempoMap.length, 'points')
        useMidi.getState().setTempoMap(tempoMap)
        
        // Update Tone.js transport BPM (use first tempo point)
        if (tempoMap[0]) {
          Tone.Transport.bpm.value = tempoMap[0].bpm
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
          Tone.Transport.start()
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
      if (Math.abs(transportSeconds - cursorSec) > 0.1) {
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
    
    // Sync transport time back to DAW store
    const syncInterval = setInterval(() => {
      if (Tone.Transport.state === 'started') {
        const transportTime = Tone.Transport.seconds
        const dawTime = useDawStore.getState().cursorSec
        
        if (Math.abs(transportTime - dawTime) > 0.1) {
          useDawStore.getState().setCursor(transportTime)
        }
      }
    }, 100) // Update 10 times per second
    
    // Clean up interval on dispose
    this.unsubscribers.push(() => clearInterval(syncInterval))
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
