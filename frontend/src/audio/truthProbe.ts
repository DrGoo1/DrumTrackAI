export type TruthProbeConfig = {
  getBpm: () => number
  getTimeSignature: () => [number, number]
  getBeatTimes?: () => number[] | null | undefined
  scheduleClick: (ctxTime: number, freq: number, dur: number) => void
  report?: (stats: { scheduled: number; windowStartSec: number; windowEndSec: number }) => void
}

type ScheduleWindowArgs = {
  ctxNow: number
  playbackNowSec: number
  windowStartSec: number
  windowEndSec: number
}

export type BeatTimeAnomaly = {
  index: number
  tSec: number
  dtPrevSec: number
  medianDtSec: number
  ratioToMedian: number
  bar: number
  beatInBar: number
  isBarBoundary: boolean
}

function median(values: number[]): number {
  if (!values.length) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  if (sorted.length % 2 === 1) return sorted[mid] ?? 0
  const a = sorted[mid - 1] ?? 0
  const b = sorted[mid] ?? 0
  return (a + b) / 2
}

export function detectBeatTimeAnomalies(args: {
  beatTimes: number[]
  beatsPerBar: number
  maxAnomalies?: number
  // Ratios outside [minRatio, maxRatio] are flagged.
  minRatio?: number
  maxRatio?: number
}): BeatTimeAnomaly[] {
  const beatTimes = Array.isArray(args.beatTimes) ? args.beatTimes : []
  if (beatTimes.length < 3) return []
  const beatsPerBar = Math.max(1, Math.floor(Number(args.beatsPerBar) || 4))
  const maxAnomalies = Math.max(1, Math.min(50, Math.floor(args.maxAnomalies ?? 12)))
  const minRatio = Number.isFinite(args.minRatio as any) ? Number(args.minRatio) : 0.55
  const maxRatio = Number.isFinite(args.maxRatio as any) ? Number(args.maxRatio) : 1.65

  const dts: number[] = []
  for (let i = 1; i < beatTimes.length; i++) {
    const t0 = beatTimes[i - 1] ?? 0
    const t1 = beatTimes[i] ?? 0
    const dt = t1 - t0
    if (Number.isFinite(dt) && dt > 0) dts.push(dt)
  }
  const med = median(dts)
  if (!(med > 0)) return []

  const out: BeatTimeAnomaly[] = []
  for (let i = 1; i < beatTimes.length; i++) {
    const tPrev = beatTimes[i - 1] ?? 0
    const t = beatTimes[i] ?? 0
    const dt = t - tPrev
    if (!Number.isFinite(t) || !Number.isFinite(dt) || !(dt > 0)) continue
    const ratio = dt / med
    if (ratio < minRatio || ratio > maxRatio) {
      const bar = Math.floor(i / beatsPerBar) + 1
      const beatInBar = (i % beatsPerBar) + 1
      const isBarBoundary = beatInBar === 1
      out.push({
        index: i,
        tSec: t,
        dtPrevSec: dt,
        medianDtSec: med,
        ratioToMedian: ratio,
        bar,
        beatInBar,
        isBarBoundary,
      })
      if (out.length >= maxAnomalies) break
    }
  }
  return out
}

export function getWorstBeatTimeAnomaly(args: {
  beatTimes: number[]
  beatsPerBar: number
  minRatio?: number
  maxRatio?: number
}): BeatTimeAnomaly | null {
  const anomalies = detectBeatTimeAnomalies({
    beatTimes: args.beatTimes,
    beatsPerBar: args.beatsPerBar,
    maxAnomalies: 50,
    minRatio: args.minRatio,
    maxRatio: args.maxRatio,
  })
  if (!anomalies.length) return null
  let best = anomalies[0]
  let bestScore = Math.abs((best.ratioToMedian || 1) - 1)
  for (let i = 1; i < anomalies.length; i++) {
    const a = anomalies[i]
    const score = Math.abs((a.ratioToMedian || 1) - 1)
    if (score > bestScore) {
      best = a
      bestScore = score
    }
  }
  return best
}

export class TruthProbe {
  private enabled = false
  private lastScheduledUntilSec = -Infinity
  private getBpm: () => number
  private getTimeSignature: () => [number, number]
  private getBeatTimes?: () => number[] | null | undefined
  private scheduleClick: (ctxTime: number, freq: number, dur: number) => void
  private report?: (stats: { scheduled: number; windowStartSec: number; windowEndSec: number }) => void

  constructor(cfg: TruthProbeConfig) {
    this.getBpm = cfg.getBpm
    this.getTimeSignature = cfg.getTimeSignature
    this.getBeatTimes = cfg.getBeatTimes
    this.scheduleClick = cfg.scheduleClick
    this.report = cfg.report
  }

  private scheduleFromBeatTimes(args: ScheduleWindowArgs, beatTimes: number[], beatsPerBar: number) {
    const startSec = Math.max(args.windowStartSec, this.lastScheduledUntilSec)
    const endSec = args.windowEndSec
    if (!(endSec > startSec)) return

    // Find beat indices in [startSec, endSec)
    let lo = 0
    let hi = beatTimes.length - 1
    while (lo < hi) {
      const mid = Math.floor((lo + hi) / 2)
      if ((beatTimes[mid] ?? 0) < startSec) lo = mid + 1
      else hi = mid
    }
    let idx = Math.max(0, lo)
    while (idx > 0 && (beatTimes[idx - 1] ?? 0) >= startSec) idx -= 1

    let scheduled = 0
    for (let i = idx; i < beatTimes.length; i++) {
      const tSec = beatTimes[i] ?? 0
      if (!Number.isFinite(tSec)) continue
      if (tSec < startSec) continue
      if (tSec >= endSec) break

      const isDownbeat = beatsPerBar > 0 ? (i % beatsPerBar === 0) : false
      const freq = isDownbeat ? 1600 : 1000
      const ctxTime = args.ctxNow + (tSec - args.playbackNowSec)
      this.scheduleClick(ctxTime, freq, 0.03)
      scheduled += 1
    }

    this.report?.({ scheduled, windowStartSec: startSec, windowEndSec: endSec })
    this.lastScheduledUntilSec = endSec
  }

  setEnabled(v: boolean) {
    this.enabled = v
    if (!v) this.lastScheduledUntilSec = -Infinity
  }

  reset() {
    this.lastScheduledUntilSec = -Infinity
  }

  scheduleWindow(args: ScheduleWindowArgs) {
    if (!this.enabled) return

    const [tsNum] = this.getTimeSignature() || [4, 4]
    const beatsPerBar = Math.max(1, Number(tsNum) || 4)

    const beatTimes = this.getBeatTimes?.()
    if (Array.isArray(beatTimes) && beatTimes.length >= 2) {
      this.scheduleFromBeatTimes(args, beatTimes, beatsPerBar)
      return
    }

    const bpm = Math.max(1, Number(this.getBpm()) || 120)
    const [num, den] = this.getTimeSignature() || [4, 4]

    const secPerBeat = (60 / bpm) * (4 / (den || 4))
    const secPerBar = secPerBeat * (num || 4)

    const startSec = Math.max(args.windowStartSec, this.lastScheduledUntilSec)
    const endSec = args.windowEndSec
    if (!(endSec > startSec)) return

    const firstBeatIdx = Math.ceil(startSec / secPerBeat)
    const lastBeatIdx = Math.floor(endSec / secPerBeat)

    let scheduled = 0
    for (let i = firstBeatIdx; i <= lastBeatIdx; i++) {
      const tSec = i * secPerBeat
      const isDownbeat = Math.abs(tSec % secPerBar) < secPerBeat * 0.001
      const freq = isDownbeat ? 1600 : 1000
      const ctxTime = args.ctxNow + (tSec - args.playbackNowSec)
      this.scheduleClick(ctxTime, freq, 0.03)
      scheduled += 1
    }

    this.report?.({ scheduled, windowStartSec: startSec, windowEndSec: endSec })

    this.lastScheduledUntilSec = endSec
  }
}

export function isTruthProbeEnabled(): boolean {
  try {
    return window.localStorage.getItem('dtk_truth_probe') === '1'
  } catch {
    return false
  }
}

export function isTruthProbeLoggingEnabled(): boolean {
  try {
    return window.localStorage.getItem('dtk_truth_probe_log') === '1'
  } catch {
    return false
  }
}
