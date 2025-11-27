export type TimeSig = { num: number; den: number };
export type TempoSegment = {
  startTime: number; // seconds
  bpm: number;
  timeSig: TimeSig;
};

export class TempoMap {
  private segments: TempoSegment[] = [];

  constructor(segments: TempoSegment[] = [{ startTime: 0, bpm: 120, timeSig: { num: 4, den: 4 } }]) {
    this.segments = [...segments].sort((a, b) => a.startTime - b.startTime);
  }

  getSegments() { return this.segments; }

  timeToBeats(t: number): number {
    let beats = 0;
    for (let i = 0; i < this.segments.length; i++) {
      const cur = this.segments[i];
      const next = this.segments[i + 1];
      const end = next ? next.startTime : Number.POSITIVE_INFINITY;
      const clamp = Math.max(0, Math.min(t, end) - cur.startTime);
      if (clamp > 0) {
        beats += (clamp / 60) * cur.bpm;
      }
      if (t < end) break;
    }
    return beats;
  }

  beatsToTime(b: number): number {
    let remaining = b;
    for (let i = 0; i < this.segments.length; i++) {
      const cur = this.segments[i];
      const next = this.segments[i + 1];
      const span = next ? next.startTime - cur.startTime : Number.POSITIVE_INFINITY;
      const segBeats = (span / 60) * cur.bpm;
      if (remaining <= segBeats) {
        return cur.startTime + (remaining * 60) / cur.bpm;
      }
      remaining -= segBeats;
    }
    return this.segments[this.segments.length - 1].startTime + (remaining * 60) / this.segments[this.segments.length - 1].bpm;
  }

  nextDownbeatAfter(t: number): number {
    const beats = this.timeToBeats(t);
    const nextBarBeat = Math.ceil(beats / 4) * 4; // assume 4/4; TODO: handle variable time sig
    return this.beatsToTime(nextBarBeat);
  }
}
