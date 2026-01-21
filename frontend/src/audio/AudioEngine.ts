// AudioEngine: Web Audio wrapper for playback and scheduling
// Minimal scaffold: create AudioContext, basic load/play helpers. Scheduler will be added separately.

import { getSharedAudioContext } from "./sharedAudioContext";

export class AudioEngine {
  private context: AudioContext | null = null;
  private trackBuffer: AudioBuffer | null = null;
  private trackSource: AudioBufferSourceNode | null = null;
  private clickGain: GainNode | null = null;
  private startTime = 0;
  private offsetAtStart = 0;
  private playing = false;

  async init() {
    if (!this.context) {
      this.context = getSharedAudioContext({ latencyHint: "interactive" });
      this.clickGain = this.context.createGain();
      this.clickGain.gain.value = 0.2;
      this.clickGain.connect(this.context.destination);
    }
  }

  async loadTrack(file: File) {
    if (!this.context) await this.init();
    const arrayBuf = await file.arrayBuffer();
    this.trackBuffer = await this.context!.decodeAudioData(arrayBuf);
  }

  play(startAtSeconds = 0) {
    if (!this.context || !this.trackBuffer) return;
    this.stop();
    this.trackSource = this.context.createBufferSource();
    this.trackSource.buffer = this.trackBuffer;
    this.trackSource.connect(this.context.destination);
    this.offsetAtStart = startAtSeconds;
    this.startTime = this.context.currentTime;
    this.trackSource.start(0, startAtSeconds);
    this.playing = true;
  }

  stop() {
    if (this.trackSource) {
      try { this.trackSource.stop(); } catch (e) { /* source may already be stopped */ }
      this.trackSource.disconnect();
      this.trackSource = null;
    }
    this.playing = false;
  }

  getCurrentTimeSeconds(): number {
    if (!this.context) return 0;
    if (!this.playing) return this.offsetAtStart;
    return this.offsetAtStart + (this.context.currentTime - this.startTime);
  }

  getBuffer(): AudioBuffer | null {
    return this.trackBuffer;
  }

  getContext(): AudioContext | null {
    return this.context;
  }

  // Schedule a short click (oscillator) at AudioContext time 'when'
  scheduleClick(when: number, freq = 1200, dur = 0.03) {
    if (!this.context || !this.clickGain) return;
    const osc = this.context.createOscillator();
    const env = this.context.createGain();
    osc.frequency.value = freq;
    osc.connect(env);
    env.connect(this.clickGain);
    const now = this.context.currentTime;
    const t0 = Math.max(when, now);
    env.gain.setValueAtTime(0.001, t0);
    env.gain.exponentialRampToValueAtTime(1.0, t0 + 0.001);
    env.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    osc.start(t0);
    osc.stop(t0 + dur + 0.01);
  }
}
