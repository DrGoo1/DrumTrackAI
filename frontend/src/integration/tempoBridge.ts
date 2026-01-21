// Transport Bridge - Synchronizes audio timeline with MIDI system
// Ensures single source of truth for tempo, cursor, and playback state

import { MidiScheduler } from '../midi/scheduler'
import { useMidi } from '../midi/midiStore'

export class TransportBridge {
  private midiScheduler: MidiScheduler
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

    this.isInitialized = true
  }
  
  /**
   * Dispose of all resources and unsubscribe from stores
   */
  dispose() {
    this.midiScheduler.dispose()
    this.isInitialized = false
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
    // disabled
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
