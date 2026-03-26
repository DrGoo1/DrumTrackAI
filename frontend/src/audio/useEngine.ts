import { useRef, useEffect } from 'react'

import { getSharedAudioContext } from './sharedAudioContext'

interface AudioEngine {
  setLaneGainDb?: (id: string, gainDb: number) => void;
  setLanePan?: (id: string, pan: number) => void;
  setLaneMuted?: (id: string, muted: boolean) => void;
  attachAnalyser?: (id: string) => AnalyserNode | null;
  setTempoRatio?: (ratio: number) => void;
  play?: () => void;
  stop?: () => void;
}

// Mock engine implementation for Phase 3.5
class MockAudioEngine implements AudioEngine {
  private trackNodes: { [id: string]: { gain: GainNode; pan: StereoPannerNode; analyser?: AnalyserNode } } = {}
  private context: AudioContext

  constructor() {
    this.context = getSharedAudioContext({ latencyHint: 'interactive' })
  }

  setLaneGainDb(id: string, gainDb: number) {
    console.log(`Set gain ${gainDb}dB for track ${id}`)
    if (this.trackNodes[id]?.gain) {
      this.trackNodes[id].gain.gain.value = Math.pow(10, gainDb / 20)
    }
  }

  setLanePan(id: string, pan: number) {
    console.log(`Set pan ${pan} for track ${id}`)
    if (this.trackNodes[id]?.pan) {
      this.trackNodes[id].pan.pan.value = pan
    }
  }

  setLaneMuted(id: string, muted: boolean) {
    console.log(`Set muted ${muted} for track ${id}`)
    if (this.trackNodes[id]?.gain) {
      this.trackNodes[id].gain.gain.value = muted ? 0 : 1
    }
  }

  attachAnalyser(id: string): AnalyserNode | null {
    if (!this.trackNodes[id]) {
      // Create mock track nodes
      const gain = this.context.createGain()
      const pan = this.context.createStereoPanner()
      gain.connect(pan)
      pan.connect(this.context.destination)
      this.trackNodes[id] = { gain, pan }
    }

    if (!this.trackNodes[id].analyser) {
      const analyser = this.context.createAnalyser()
      analyser.fftSize = 2048
      this.trackNodes[id].gain.connect(analyser)
      this.trackNodes[id].analyser = analyser
    }

    return this.trackNodes[id].analyser || null
  }

  setTempoRatio(ratio: number) {
    console.log(`Set tempo ratio ${ratio}`)
    // Mock implementation - in real engine would adjust playback rate
  }

  play() {
    console.log('Engine play')
  }

  stop() {
    console.log('Engine stop')
  }
}

export function useEngine(): AudioEngine {
  const engineRef = useRef<MockAudioEngine | null>(null)

  useEffect(() => {
    if (!engineRef.current) {
      engineRef.current = new MockAudioEngine()
    }
  }, [])

  return engineRef.current || new MockAudioEngine()
}
