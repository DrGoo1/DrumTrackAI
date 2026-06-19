export type MeterEvent = {
  barIndex: number;
  num: number;
  denom: 2 | 4 | 8 | 16;
};

export type TempoEventBB = {
  barIndex: number;
  beatInBar: number;
  bpm: number;
  rampTo?: { bpm: number; bars: number };
};

export type BeatGrid = {
  beatTimesSec: number[];
  barStartBeatIndex: number[];
  totalBars: number;
};

export type BarBeat = {
  barIndex: number;
  beatInBar: number;
};

function clampInt(v: number, lo: number, hi: number): number {
  const n = Math.floor(Number.isFinite(v) ? v : 0);
  return Math.max(lo, Math.min(hi, n));
}

function normalizeMeterMap(meterMap: MeterEvent[]): MeterEvent[] {
  const out = (Array.isArray(meterMap) ? meterMap : [])
    .map((m) => ({
      barIndex: clampInt(Number((m as any)?.barIndex), 0, Number.MAX_SAFE_INTEGER),
      num: clampInt(Number((m as any)?.num), 1, 64),
      denom: (Number((m as any)?.denom) || 4) as any,
    }))
    .filter((m) => Number.isFinite(m.barIndex) && Number.isFinite(m.num) && Number.isFinite(m.denom))
    .sort((a, b) => a.barIndex - b.barIndex);

  // Ensure barIndex 0 exists.
  if (!out.length || out[0].barIndex !== 0) {
    out.unshift({ barIndex: 0, num: 4, denom: 4 });
  }

  // De-dupe by barIndex (last wins).
  const dedup: MeterEvent[] = [];
  for (const ev of out) {
    const prev = dedup[dedup.length - 1];
    if (prev && prev.barIndex === ev.barIndex) {
      dedup[dedup.length - 1] = ev;
    } else {
      dedup.push(ev);
    }
  }

  return dedup.map((m) => ({
    barIndex: m.barIndex,
    num: m.num,
    denom: (m.denom === 2 || m.denom === 4 || m.denom === 8 || m.denom === 16 ? m.denom : 4) as any,
  }));
}

function normalizeTempoMapBB(tempoMap: TempoEventBB[], meterMap: MeterEvent[]): TempoEventBB[] {
  const meter = normalizeMeterMap(meterMap);

  const out = (Array.isArray(tempoMap) ? tempoMap : [])
    .map((t) => {
      const barIndex = clampInt(Number((t as any)?.barIndex), 0, Number.MAX_SAFE_INTEGER);
      const beatsPerBar = beatsPerBarAt(meter, barIndex);
      const beatInBar = clampInt(Number((t as any)?.beatInBar), 0, Math.max(0, beatsPerBar - 1));
      const bpm = Number((t as any)?.bpm) || 0;
      const rampTo = (t as any)?.rampTo;
      const rampNorm = rampTo
        ? {
            bpm: Number(rampTo?.bpm) || 0,
            bars: clampInt(Number(rampTo?.bars), 1, 1024),
          }
        : undefined;
      return { barIndex, beatInBar, bpm, rampTo: rampNorm } as TempoEventBB;
    })
    .filter((t) => Number.isFinite(t.barIndex) && Number.isFinite(t.beatInBar) && Number.isFinite(t.bpm) && t.bpm > 0)
    .sort((a, b) => (a.barIndex - b.barIndex) || (a.beatInBar - b.beatInBar));

  if (!out.length || out[0].barIndex !== 0 || out[0].beatInBar !== 0) {
    out.unshift({ barIndex: 0, beatInBar: 0, bpm: 120 });
  }

  // De-dupe (barIndex, beatInBar) last wins.
  const dedup: TempoEventBB[] = [];
  for (const ev of out) {
    const prev = dedup[dedup.length - 1];
    if (prev && prev.barIndex === ev.barIndex && prev.beatInBar === ev.beatInBar) {
      dedup[dedup.length - 1] = ev;
    } else {
      dedup.push(ev);
    }
  }

  return dedup;
}

function beatsPerBarAt(meter: MeterEvent[], barIndex: number): number {
  let cur = meter[0];
  for (let i = 0; i < meter.length; i++) {
    if (meter[i].barIndex <= barIndex) cur = meter[i];
    else break;
  }
  return Math.max(1, Number(cur.num) || 4);
}

export function barBeatToBeatFloat(meterMap: MeterEvent[], bb: BarBeat): number {
  const meter = normalizeMeterMap(meterMap);
  const barIndex = clampInt(Number((bb as any)?.barIndex), 0, Number.MAX_SAFE_INTEGER);
  const beatInBarRaw = Number((bb as any)?.beatInBar);

  let beats = 0;
  for (let b = 0; b < barIndex; b++) {
    beats += beatsPerBarAt(meter, b);
    if (beats > 1e9) break;
  }

  const bpb = beatsPerBarAt(meter, barIndex);
  const beatInBar = Math.max(0, Math.min(bpb, Number.isFinite(beatInBarRaw) ? beatInBarRaw : 0));
  return beats + beatInBar;
}

export function beatFloatToBarBeat(meterMap: MeterEvent[], beatFloat: number): BarBeat {
  const meter = normalizeMeterMap(meterMap);
  const b = Math.max(0, Number.isFinite(beatFloat) ? beatFloat : 0);
  const wholeBeats = Math.floor(b);
  const frac = b - wholeBeats;

  let barIndex = 0;
  let remaining = wholeBeats;
  while (barIndex < 100000) {
    const bpb = beatsPerBarAt(meter, barIndex);
    if (remaining < bpb) break;
    remaining -= bpb;
    barIndex += 1;
  }

  return { barIndex, beatInBar: remaining + frac };
}

export function deriveBeatGridFromMaps(args: {
  durationSec: number;
  meterMap: MeterEvent[];
  tempoMapBB: TempoEventBB[];
  startOffsetSec?: number;
  maxBars?: number;
}): BeatGrid {
  const durationSec = Math.max(0, Number(args.durationSec) || 0);
  const startOffsetSec = Number.isFinite(args.startOffsetSec) ? Number(args.startOffsetSec) : 0;
  const maxBars = clampInt(Number(args.maxBars ?? 4096), 1, 100000);

  const meter = normalizeMeterMap(args.meterMap);
  const tempo = normalizeTempoMapBB(args.tempoMapBB, meter);

  // Main generation loop.
  const beatTimesSec: number[] = [];
  const barStartBeatIndex: number[] = [];

  let t = startOffsetSec;
  let barIndex = 0;
  let beatInBar = 0;
  let bpm = tempo[0].bpm;
  let tempoIdx = 0;

  const pushBarStartIfNeeded = () => {
    if (barStartBeatIndex.length === 0) barStartBeatIndex.push(0);
  };

  pushBarStartIfNeeded();
  beatTimesSec.push(t);

  while (barIndex < maxBars) {
    // Apply any tempo changes at this bar/beat.
    while (tempoIdx + 1 < tempo.length) {
      const next = tempo[tempoIdx + 1];
      if (next.barIndex < barIndex) {
        tempoIdx += 1;
        bpm = tempo[tempoIdx].bpm;
        continue;
      }
      if (next.barIndex === barIndex && next.beatInBar <= beatInBar) {
        tempoIdx += 1;
        bpm = tempo[tempoIdx].bpm;
        continue;
      }
      break;
    }

    const secPerBeat = 60 / Math.max(1e-6, bpm);
    t += secPerBeat;
    beatTimesSec.push(t);

    if (durationSec > 0 && t >= startOffsetSec + durationSec) {
      break;
    }

    const bpb = beatsPerBarAt(meter, barIndex);
    beatInBar += 1;
    if (beatInBar >= bpb) {
      beatInBar = 0;
      barIndex += 1;
      barStartBeatIndex.push(beatTimesSec.length - 1);
    }
  }

  // Ensure we have at least two beats.
  if (beatTimesSec.length < 2) {
    beatTimesSec.push(startOffsetSec + 0.5);
  }

  return {
    beatTimesSec,
    barStartBeatIndex,
    totalBars: Math.max(1, barStartBeatIndex.length),
  };
}

export function timeSecToBeatFloat(beatTimesSec: number[], tSec: number): number {
  if (!Array.isArray(beatTimesSec) || beatTimesSec.length < 2) return 0;
  const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);
  if (t <= beatTimesSec[0]) return 0;

  let lo = 0;
  let hi = beatTimesSec.length - 1;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (beatTimesSec[mid] < t) lo = mid + 1;
    else hi = mid;
  }

  const idx = lo;
  if (idx <= 0) return 0;
  if (idx >= beatTimesSec.length) return beatTimesSec.length - 1;

  const prev = idx - 1;
  const t0 = beatTimesSec[prev];
  const t1 = beatTimesSec[idx];
  if (!Number.isFinite(t0) || !Number.isFinite(t1) || t1 <= t0) return prev;
  const frac = Math.max(0, Math.min(1, (t - t0) / (t1 - t0)));
  return prev + frac;
}

export function beatFloatToTimeSec(beatTimesSec: number[], beatsIn: number): number {
  if (!Array.isArray(beatTimesSec) || beatTimesSec.length < 2) return 0;
  const maxIdx = beatTimesSec.length - 1;
  const b = Math.max(0, Number.isFinite(beatsIn) ? beatsIn : 0);
  const idx0 = Math.max(0, Math.min(maxIdx, Math.floor(b)));
  const idx1 = Math.max(0, Math.min(maxIdx, idx0 + 1));
  const t0 = Number(beatTimesSec[idx0] ?? 0);
  const t1 = Number(beatTimesSec[idx1] ?? t0);
  const frac = Math.max(0, Math.min(1, b - idx0));
  if (idx0 === idx1) return Number.isFinite(t0) ? t0 : 0;
  if (!Number.isFinite(t0) || !Number.isFinite(t1)) return Number.isFinite(t0) ? t0 : 0;
  return t0 + (t1 - t0) * frac;
}
