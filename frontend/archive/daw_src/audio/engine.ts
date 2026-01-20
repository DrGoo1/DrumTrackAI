import * as Tone from 'tone'

// Simple per-lane sampler wired to Tone.Player for audio samples
export type KitMap = Record<string,string>

export class DrumEngine {
  context = Tone.getContext().rawContext
  players: Record<string, Tone.Player> = {}
  master = new Tone.Gain(0.9).toDestination()
  meter = new Tone.Meter()
  analyser = new Tone.Analyser('waveform', 256)

  constructor(public kit: KitMap) {
    Object.entries(kit).forEach(([lane, url]) => {
      const p = new Tone.Player({ url, autostart: false }).connect(this.master)
      this.players[lane] = p
    })
    this.master.connect(this.meter)
    this.master.connect(this.analyser)
  }

  async trigger(lane: string, time: number, velocity = 1) {
    const p = this.players[lane]
    if (!p) return
    const t = Tone.now() + Math.max(0, time - this.getTransportSec())
    p.volume.value = 20 * Math.log10(Math.max(0.001, velocity))
    p.start(t)
  }

  getTransportSec() {
    return Tone.Transport.seconds
  }

  getLevels() {
    return this.meter.getValue() // [-Infinity..]
  }

  getWaveform() {
    return this.analyser.getValue() as Float32Array
  }
}
