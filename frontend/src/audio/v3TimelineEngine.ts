import { getSharedAudioContext, resumeSharedAudioContext } from './sharedAudioContext'

export class V3TimelineEngine {
  private ctx: AudioContext
  private buffer: AudioBuffer | null = null
  private source: AudioBufferSourceNode | null = null
  private startCtxTime = 0
  private offsetAtStart = 0
  private playing = false

  constructor() {
    this.ctx = getSharedAudioContext({ latencyHint: 'interactive' })
  }

  get audioContext() {
    return this.ctx
  }

  async loadUrl(url: string) {
    await resumeSharedAudioContext()
    const res = await fetch(url)
    if (!res.ok) throw new Error(`Failed to load audio (${res.status} ${res.statusText})`)
    const arr = await res.arrayBuffer()
    this.buffer = await this.ctx.decodeAudioData(arr)
    this.stop()
  }

  isReady() {
    return Boolean(this.buffer)
  }

  getDurationSeconds(): number | null {
    return this.buffer ? this.buffer.duration : null
  }

  play(startAtSeconds = 0) {
    if (!this.buffer) return
    this.stopSourceOnly()

    this.source = this.ctx.createBufferSource()
    this.source.buffer = this.buffer
    this.source.connect(this.ctx.destination)

    this.offsetAtStart = Math.max(0, startAtSeconds)
    this.startCtxTime = this.ctx.currentTime

    try {
      this.source.start(0, this.offsetAtStart)
      this.playing = true
    } catch {
      this.playing = false
    }
  }

  pause() {
    if (!this.playing) return
    const t = this.getCurrentTimeSeconds()
    this.stopSourceOnly()
    this.offsetAtStart = t
    this.playing = false
  }

  stop() {
    this.stopSourceOnly()
    this.offsetAtStart = 0
    this.playing = false
  }

  private stopSourceOnly() {
    if (this.source) {
      try {
        this.source.stop()
      } catch {
        // ignore
      }
      try {
        this.source.disconnect()
      } catch {
        // ignore
      }
      this.source = null
    }
  }

  getCurrentTimeSeconds(): number {
    if (!this.playing) return this.offsetAtStart
    return this.offsetAtStart + Math.max(0, this.ctx.currentTime - this.startCtxTime)
  }

  // Convert playback timeline seconds to AudioContext time for sample-accurate scheduling.
  getContextTimeForPlaybackTime(playbackSec: number): number {
    const t = Math.max(0, Number(playbackSec) || 0)
    // Current mapping is valid while playing; when paused/stopped, schedule relative to now.
    if (!this.playing) return this.ctx.currentTime + 0.01
    return this.startCtxTime + Math.max(0, t - this.offsetAtStart)
  }
}

let singleton: V3TimelineEngine | null = null
export function getV3TimelineEngine(): V3TimelineEngine {
  if (!singleton) singleton = new V3TimelineEngine()
  return singleton
}
