import { create } from 'zustand'
import { getSharedAudioContext } from './sharedAudioContext'

export type TrackChain = {
  id: string
  input?: any // Tone.ToneAudioNode | AudioNode
  gain: GainNode
  panner: StereoPannerNode
  analyser: AnalyserNode
  output: AudioNode
  muted: boolean
  solo: boolean
}

type GraphState = {
  chains: Record<string, TrackChain>
  ensure: (id: string) => TrackChain
  attachInput: (id: string, input: any) => void
  setVolumeDb: (id: string, db: number) => void
  setPan: (id: string, pan: number) => void
  toggleMute: (id: string) => void
  soloExclusive: (id: string) => void
  setPlaylistMaster: (node: AudioNode | null) => void
  playlistMaster?: AudioNode | null
}

export const useGraph = create<GraphState>((set, get) => ({
  chains: {},
  ensure: (id) => {
    const s = get()
    if (s.chains[id]) return s.chains[id]
    const ctx = getSharedAudioContext({ latencyHint: 'interactive' })
    const gain = ctx.createGain()
    const panner = ctx.createStereoPanner()
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 2048
    gain.connect(panner)
    panner.connect(analyser)
    analyser.connect(ctx.destination)
    const chain: TrackChain = { id, gain, panner, analyser, output: ctx.destination, muted: false, solo: false }
    set({ chains: { ...s.chains, [id]: chain } })
    return chain
  },
  attachInput: (id, input) => {
    const s = get(); const ch = s.ensure(id)
    try {
      // Tone nodes and WebAudio nodes both support connect; cast to any to appease TS
      (input as any).connect?.(ch.gain)
      ch.input = input
      set({ chains: { ...s.chains, [id]: ch } })
    } catch (e) { console.error('[graph] attachInput failed', e) }
  },
  setVolumeDb: (id, db) => {
    const s = get(); const ch = s.chains[id] || s.ensure(id)
    const lin = Math.pow(10, db / 20)
    ch.gain.gain.value = lin
    set({ chains: { ...s.chains, [id]: ch } })
  },
  setPan: (id, pan) => {
    const s = get(); const ch = s.chains[id] || s.ensure(id)
    ch.panner.pan.value = Math.max(-1, Math.min(1, pan))
    set({ chains: { ...s.chains, [id]: ch } })
  },
  toggleMute: (id) => {
    const s = get(); const ch = s.chains[id] || s.ensure(id)
    ch.muted = !ch.muted
    ch.gain.gain.value = ch.muted ? 0 : ch.gain.gain.value || 1
    set({ chains: { ...s.chains, [id]: ch } })
  },
  soloExclusive: (id) => {
    const s = get(); const out: Record<string, TrackChain> = {}
    Object.values(s.chains).forEach((ch: TrackChain) => {
      ch.solo = ch.id === id ? !ch.solo : false
      out[ch.id] = ch
    })
    // Implement basic solo: if any soloed, mute others
    const anySolo = Object.values(out).some(c => c.solo)
    Object.values(out).forEach(ch => {
      const lin = anySolo ? (ch.solo ? 1 : 0) : ch.muted ? 0 : 1
      ch.gain.gain.value = lin
    })
    set({ chains: out })
  },
  setPlaylistMaster: (node) => set({ playlistMaster: node })
}))

// helper to connect a Tone instrument or player
export function wireToneInstrument(trackId: string, inst: any) {
  const g = useGraph.getState(); const ch = g.ensure(trackId)
  // disconnect instrument's default destination, then route through chain
  try { (inst as any).disconnect?.() } catch (e) { console.debug('Disconnect failed:', e) }
  g.attachInput(trackId, inst)
}

export function meterNodeFor(trackId: string): AudioNode | undefined {
  const ch = useGraph.getState().chains[trackId]
  return ch?.analyser
}
