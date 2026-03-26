export type TimingEvent = {
  ctxNow: number;
  engineNow: number;
  safeWhen: number;
  clickCtxTime: number | null;
  deltaToClick: number | null;
};

class TimingDiagnostics {
  events: TimingEvent[] = [];
  maxEvents = 200;

  trimOffsets: Record<string, number> = {};
  peakTimes: Record<string, number> = {};
  peakAbs: Record<string, number> = {};

  sampleLoadCount = 0;
  lastSampleLoad: { channel: string; durationSec: number; sampleRate: number; url?: string } | null = null;

  record(evt: TimingEvent) {
    this.events.push(evt);
    if (this.events.length > this.maxEvents) {
      this.events.shift();
    }
  }

  setTrim(channel: string, offsetSec: number) {
    this.trimOffsets[String(channel)] = Number(offsetSec) || 0;
  }

  setPeakTime(channel: string, peakSec: number) {
    this.peakTimes[String(channel)] = Number(peakSec) || 0;
  }

  setPeakAbs(channel: string, peakAbs: number) {
    this.peakAbs[String(channel)] = Number(peakAbs) || 0;
  }

  recordSampleLoad(args: { channel: string; durationSec: number; sampleRate: number; url?: string }) {
    this.sampleLoadCount += 1;
    this.lastSampleLoad = {
      channel: String(args.channel),
      durationSec: Number(args.durationSec) || 0,
      sampleRate: Number(args.sampleRate) || 0,
      url: args.url ? String(args.url) : undefined,
    };
  }

  getStats() {
    const deltas = this.events
      .map((e) => e.deltaToClick)
      .filter((v): v is number => typeof v === 'number' && Number.isFinite(v));

    if (!deltas.length) return null;

    const avg = deltas.reduce((a, b) => a + b, 0) / deltas.length;
    const min = Math.min(...deltas);
    const max = Math.max(...deltas);

    return { avg, min, max, n: deltas.length };
  }
}

export const timingDiagnostics = new TimingDiagnostics();
