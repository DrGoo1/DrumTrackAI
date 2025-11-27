import { AudioEngine } from "./AudioEngine";
import { EuclideanPatternEvent } from "../euclidean/euclidean";

/**
 * Simple Euclidean preview player using click sounds via AudioEngine.
 * This avoids pulling in Tone.js and reuses the existing Web Audio wrapper.
 */
export class EuclideanClickPlayer {
  private engine: AudioEngine;

  constructor(engine: AudioEngine) {
    this.engine = engine;
  }

  async playPattern(events: EuclideanPatternEvent[], tempo: number) {
    await this.engine.init();
    const ctx = this.engine.getContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    const secPerBeat = 60 / Math.max(tempo, 1);

    for (const ev of events) {
      const t = now + ev.timeBeats * secPerBeat;
      const freq = ev.isAccent ? 1500 : 900;
      this.engine.scheduleClick(t, freq, 0.03);
    }
  }
}
