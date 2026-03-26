import React, { useRef, useEffect, useState } from 'react';
import { useRudimentBlockStore } from '../state/useRudimentBlockStore';
import { BAR_GRID_THEME } from '../constants/barGrid';

type SectionStyle = { fill: string; stroke: string; title: string };

const SECTION_STYLES: Record<string, SectionStyle> = {
  intro: { fill: 'rgba(249, 115, 22, 0.5)', stroke: '#f97316', title: 'INTRO' },
  verse: { fill: 'rgba(59, 130, 246, 0.5)', stroke: '#3b82f6', title: 'VERSE' },
  prechorus: { fill: 'rgba(14, 165, 233, 0.5)', stroke: '#0ea5e9', title: 'PRE-CHORUS' },
  chorus: { fill: 'rgba(34, 197, 94, 0.5)', stroke: '#22c55e', title: 'CHORUS' },
  postchorus: { fill: 'rgba(34, 197, 94, 0.42)', stroke: '#22c55e', title: 'POST-CHORUS' },
  bridge: { fill: 'rgba(168, 85, 247, 0.5)', stroke: '#a855f7', title: 'BRIDGE' },
  breakdown: { fill: 'rgba(236, 72, 153, 0.45)', stroke: '#ec4899', title: 'BREAKDOWN' },
  interlude: { fill: 'rgba(99, 102, 241, 0.45)', stroke: '#6366f1', title: 'INTERLUDE' },
  solo: { fill: 'rgba(234, 179, 8, 0.45)', stroke: '#eab308', title: 'SOLO' },
  outro: { fill: 'rgba(239, 68, 68, 0.5)', stroke: '#ef4444', title: 'OUTRO' },
  ending: { fill: 'rgba(239, 68, 68, 0.42)', stroke: '#ef4444', title: 'ENDING' },
  tag: { fill: 'rgba(148, 163, 184, 0.45)', stroke: '#94a3b8', title: 'TAG' },
  default: { fill: 'rgba(100, 116, 139, 0.5)', stroke: '#64748b', title: 'SECTION' },
};

function sectionStyleFor(label?: string): SectionStyle {
  const key = (label || '').trim().toLowerCase();
  return SECTION_STYLES[key] || SECTION_STYLES.default;
}

export type UploadedTrack = {
  key: string;
  peaks: number[];
  sr: number;
  seconds: number;
  color: string;
  name: string;
  peaksL?: number[];
  peaksR?: number[];
  waveformExtents?: WaveformExtent[];
  waveformExtentsL?: WaveformExtent[];
  waveformExtentsR?: WaveformExtent[];
};

type WaveformExtent = {
  min: number;
  max: number;
};

export type Section = {
  id: string;
  start: number;
  end: number;
  density: number;
  fillIn: boolean;
  fillOut: boolean;
  label?: string;
  confidence?: number;
  tempo?: number;                  // Per-section micro tempo
  energy?: number;                 // Section energy/loudness
  spectral_centroid?: number;      // Section brightness
};

interface TimelineProps {
  bpm: number;
  tempoMap?: Array<{ tSec: number; bpm: number }>;
  beatTimes?: number[];
  beatZeroOffsetSec?: number;
  tracks: UploadedTrack[];
  sections: Section[];
  onSectionsChange: (sections: Section[]) => void;
  playhead: number;
  setPlayhead: (time: number) => void;
  playing: boolean;
  onDropFiles: (files: FileList) => void;
  loop: { enabled: boolean; start: number; end: number };
  setLoop: (loop: { enabled: boolean; start: number; end: number }) => void;
  gridSec: number;
  onAutoSectionize?: (trackKey: string) => void;
  selectedSectionIds?: Set<string>;
  onSelectSection?: (sectionId: string, multi: boolean) => void;
  onSectionContextMenu?: (sectionId: string) => void;
  pixelsPerBeat: number;
  timeSignature?: [number, number];
  scrollSyncRef?: React.RefObject<HTMLDivElement | null>;
}

const resolvePeakMagnitude = (value: any): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.abs(value);
  }
  if (Array.isArray(value)) {
    return value.reduce((max, sample) => Math.max(max, resolvePeakMagnitude(sample)), 0);
  }
  if (value && typeof value === 'object') {
    const max = typeof value.max === 'number' ? Math.abs(value.max) : 0;
    const min = typeof value.min === 'number' ? Math.abs(value.min) : 0;
    const rms = typeof value.rms === 'number' ? Math.abs(value.rms) : 0;
    return Math.max(max, min, rms);
  }
  return 0;
};

const sampleSeriesValue = (series: any[] | undefined, column: number, totalColumns: number): number => {
  if (!series?.length || totalColumns <= 0) {
    return 0;
  }
  if (series.length === 1) {
    return resolvePeakMagnitude(series[0]);
  }
  const clampedColumn = Math.max(0, Math.min(totalColumns - 1, column));
  const normalized = totalColumns === 1 ? 0 : clampedColumn / (totalColumns - 1);
  const rawIndex = normalized * (series.length - 1);
  const floorIndex = Math.floor(rawIndex);
  const ceilIndex = Math.min(series.length - 1, floorIndex + 1);
  const t = rawIndex - floorIndex;
  const start = resolvePeakMagnitude(series[floorIndex]);
  const end = resolvePeakMagnitude(series[ceilIndex]);
  return start + (end - start) * t;
};

const clampSigned = (value: number): number => {
  if (!Number.isFinite(value)) return 0;
  if (value > 1) return 1;
  if (value < -1) return -1;
  return value;
};

type TempoPoint = { tSec: number; bpm: number };

function normalizeTempoMap(tempoMap?: Array<{ tSec: number; bpm: number }>): TempoPoint[] {
  const pts = Array.isArray(tempoMap)
    ? tempoMap
        .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
        .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
        .sort((a, b) => a.tSec - b.tSec)
    : [];
  return pts;
}

function makeTimeBeatMapper(tempoPts: TempoPoint[], fallbackBpm: number) {
  const bpm0 = Number.isFinite(fallbackBpm) && fallbackBpm > 0 ? fallbackBpm : 120;
  const pts = tempoPts.length ? tempoPts : [{ tSec: 0, bpm: bpm0 }];

  const beatsAtPoint: number[] = new Array(pts.length);
  beatsAtPoint[0] = 0;
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1];
    const cur = pts[i];
    const dt = Math.max(0, cur.tSec - prev.tSec);
    beatsAtPoint[i] = beatsAtPoint[i - 1] + (dt * prev.bpm) / 60;
  }

  const beatsAtTime = (tSec: number): number => {
    const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);
    if (pts.length === 1) {
      return (t * pts[0].bpm) / 60;
    }
    for (let i = 1; i < pts.length; i++) {
      const cur = pts[i];
      if (t <= cur.tSec) {
        const prev = pts[i - 1];
        const dt = Math.max(0, t - prev.tSec);
        return beatsAtPoint[i - 1] + (dt * prev.bpm) / 60;
      }
    }
    const last = pts[pts.length - 1];
    const dt = Math.max(0, t - last.tSec);
    return beatsAtPoint[beatsAtPoint.length - 1] + (dt * last.bpm) / 60;
  };

  const timeAtBeats = (beatsIn: number): number => {
    const beats = Math.max(0, Number.isFinite(beatsIn) ? beatsIn : 0);
    if (pts.length === 1) {
      return (beats * 60) / pts[0].bpm;
    }
    for (let i = 1; i < pts.length; i++) {
      const prev = pts[i - 1];
      const b0 = beatsAtPoint[i - 1];
      const b1 = beatsAtPoint[i];
      if (beats <= b1) {
        const db = Math.max(0, beats - b0);
        return prev.tSec + (db * 60) / prev.bpm;
      }
    }
    const last = pts[pts.length - 1];
    const bLast = beatsAtPoint[beatsAtPoint.length - 1];
    const db = Math.max(0, beats - bLast);
    return last.tSec + (db * 60) / last.bpm;
  };

  return { beatsAtTime, timeAtBeats };
}

function normalizeBeatTimes(beatTimes?: number[]): number[] {
  if (!Array.isArray(beatTimes) || beatTimes.length < 2) return [];
  const out = beatTimes
    .map((t) => Number(t))
    .filter((t) => Number.isFinite(t))
    .sort((a, b) => a - b);
  return out.length >= 2 ? out : [];
}

function makeTimeBeatMapperFromBeatTimes(beatTimes: number[]) {
  const bt = normalizeBeatTimes(beatTimes);
  const beatsAtTime = (tSec: number): number => {
    const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);
    if (bt.length < 2) return 0;
    let lo = 0;
    let hi = bt.length - 1;
    while (lo < hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (bt[mid] < t) lo = mid + 1;
      else hi = mid;
    }
    const idx = lo;
    if (idx <= 0) return 0;
    if (idx >= bt.length) return bt.length - 1;
    const prev = idx - 1;
    const t0 = bt[prev];
    const t1 = bt[idx];
    if (!Number.isFinite(t0) || !Number.isFinite(t1) || t1 <= t0) return prev;
    const frac = Math.max(0, Math.min(1, (t - t0) / (t1 - t0)));
    return prev + frac;
  };

  const timeAtBeats = (beatsIn: number): number => {
    const beats = Math.max(0, Number.isFinite(beatsIn) ? beatsIn : 0);
    if (bt.length < 2) return 0;
    const maxIdx = bt.length - 1;
    const idx0 = Math.max(0, Math.min(maxIdx, Math.floor(beats)));
    const idx1 = Math.max(0, Math.min(maxIdx, idx0 + 1));
    const t0 = bt[idx0] ?? 0;
    const t1 = bt[idx1] ?? t0;
    const frac = Math.max(0, Math.min(1, beats - idx0));
    if (idx0 === idx1) return Number.isFinite(t0) ? t0 : 0;
    if (!Number.isFinite(t0) || !Number.isFinite(t1)) return Number.isFinite(t0) ? t0 : 0;
    return t0 + (t1 - t0) * frac;
  };

  return { beatsAtTime, timeAtBeats };
}

type WaveformChannelSource = {
  extents?: WaveformExtent[];
  magnitudes?: any[];
};

const sampleWaveformPoint = (
  source: WaveformChannelSource,
  column: number,
  totalColumns: number
): WaveformExtent => {
  const { extents, magnitudes } = source;
  if (extents?.length) {
    if (extents.length === 1) {
      return extents[0];
    }
    const clampedColumn = Math.max(0, Math.min(totalColumns - 1, column));
    const normalized = totalColumns === 1 ? 0 : clampedColumn / (totalColumns - 1);
    const rawIndex = normalized * (extents.length - 1);
    const floorIndex = Math.floor(rawIndex);
    const ceilIndex = Math.min(extents.length - 1, floorIndex + 1);
    const t = rawIndex - floorIndex;
    const start = extents[floorIndex];
    const end = extents[ceilIndex];
    return {
      min: start.min + (end.min - start.min) * t,
      max: start.max + (end.max - start.max) * t,
    };
  }

  const magnitude = sampleSeriesValue(magnitudes, column, totalColumns);
  return { min: -magnitude, max: magnitude };
};

const drawWaveformChannel = (
  ctx: CanvasRenderingContext2D,
  source: WaveformChannelSource,
  width: number,
  centerY: number,
  amplitude: number,
  color: string,
  timeAtBeat: (beat: number) => number,
  trackDurationSec: number,
  pixelsPerBeat: number
) => {
  if ((!source.extents || !source.extents.length) && (!source.magnitudes || !source.magnitudes.length)) {
    return;
  }
  if (width <= 0 || amplitude <= 0) {
    return;
  }

  const durationSec = Math.max(1e-6, Number.isFinite(trackDurationSec) ? trackDurationSec : 0);

  const sampleAtNormalized = (norm: number): WaveformExtent => {
    const clamped = Math.max(0, Math.min(1, Number.isFinite(norm) ? norm : 0));
    const { extents, magnitudes } = source;
    if (extents?.length) {
      if (extents.length === 1) return extents[0];
      const rawIndex = clamped * (extents.length - 1);
      const floorIndex = Math.floor(rawIndex);
      const ceilIndex = Math.min(extents.length - 1, floorIndex + 1);
      const t = rawIndex - floorIndex;
      const start = extents[floorIndex];
      const end = extents[ceilIndex];
      return {
        min: start.min + (end.min - start.min) * t,
        max: start.max + (end.max - start.max) * t,
      };
    }
    if (magnitudes?.length) {
      const idx = Math.max(0, Math.min(magnitudes.length - 1, Math.round(clamped * (magnitudes.length - 1))));
      const magnitude = resolvePeakMagnitude(magnitudes[idx]);
      return { min: -magnitude, max: magnitude };
    }
    return { min: 0, max: 0 };
  };

  const topY: number[] = new Array(width);
  const bottomY: number[] = new Array(width);

  for (let x = 0; x < width; x++) {
    const beat = pixelsPerBeat > 0 ? x / pixelsPerBeat : 0;
    const tSec = timeAtBeat(beat);
    const norm = tSec / durationSec;
    const { min, max } = sampleAtNormalized(norm);
    topY[x] = centerY - clampSigned(max) * amplitude;
    bottomY[x] = centerY - clampSigned(min) * amplitude;
  }

  // Fill first for better perceived density, then outline.
  ctx.save();
  ctx.globalAlpha = 0.7;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(0, topY[0]);
  for (let x = 1; x < width; x++) {
    ctx.lineTo(x, topY[x]);
  }
  for (let x = width - 1; x >= 0; x--) {
    ctx.lineTo(x, bottomY[x]);
  }
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  ctx.strokeStyle = color;
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(0, topY[0]);
  for (let x = 1; x < width; x++) {
    ctx.lineTo(x, topY[x]);
  }
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(0, bottomY[0]);
  for (let x = 1; x < width; x++) {
    ctx.lineTo(x, bottomY[x]);
  }
  ctx.stroke();
};

const Timeline: React.FC<TimelineProps> = ({
  bpm,
  tempoMap,
  beatTimes,
  tracks,
  sections,
  onSectionsChange,
  playhead,
  setPlayhead,
  playing,
  onDropFiles,
  loop,
  setLoop,
  gridSec,
  onAutoSectionize,
  selectedSectionIds = new Set(),
  onSelectSection,
  onSectionContextMenu,
  pixelsPerBeat,
  timeSignature = [4, 4],
  scrollSyncRef,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const contentWidthRef = useRef<number>(0);
  const timelineDurationRef = useRef<number>(0);
  const lastTimelineDebugRef = useRef<string>('');
  const blocksBySection = useRudimentBlockStore((state) => state.blocksBySection);
  const [viewportWidth, setViewportWidth] = useState(0);

  useEffect(() => {
    if (!scrollSyncRef) return;
    (scrollSyncRef as React.MutableRefObject<HTMLDivElement | null>).current = scrollContainerRef.current;
    return () => {
      if ((scrollSyncRef as React.MutableRefObject<HTMLDivElement | null>).current === scrollContainerRef.current) {
        (scrollSyncRef as React.MutableRefObject<HTMLDivElement | null>).current = null;
      }
    };
  }, [scrollSyncRef]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const updateWidth = () => {
      const width = viewportRef.current?.clientWidth ?? canvasRef.current?.parentElement?.clientWidth ?? 0;
      setViewportWidth(width);
    };
    updateWidth();
    const observer = typeof ResizeObserver !== 'undefined' && viewportRef.current
      ? new ResizeObserver(updateWidth)
      : null;
    if (observer && viewportRef.current) {
      observer.observe(viewportRef.current);
    }
    window.addEventListener('resize', updateWidth);
    return () => {
      window.removeEventListener('resize', updateWidth);
      observer?.disconnect();
    };
  }, []);

  // Draw timeline and waveforms
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const tempoPts = normalizeTempoMap(tempoMap);
    const normalizedBeatTimes = normalizeBeatTimes(beatTimes);
    const mapper = normalizedBeatTimes.length ? makeTimeBeatMapperFromBeatTimes(normalizedBeatTimes) : makeTimeBeatMapper(tempoPts, bpm);
    const trackDurations = tracks.length ? tracks.map((t) => Number(t.seconds) || 0) : [0];
    const waveformDurationSec = Math.max(...trackDurations, 0);
    const sectionDurationSec = sections.length ? Math.max(...sections.map((s) => Number(s.end) || 0)) : 0;
    const loopExtentSec = loop?.end ?? 0;
    const timelineDurationSec = Math.max(10, waveformDurationSec, sectionDurationSec, loopExtentSec);
    timelineDurationRef.current = timelineDurationSec;

    const timelineBeats = Math.max(1, mapper.beatsAtTime(timelineDurationSec));

    const parentWidth = viewportWidth
      || viewportRef.current?.clientWidth
      || canvas.parentElement?.clientWidth
      || 800;
    const displayWidth = Math.max(parentWidth, Math.ceil(timelineBeats * Math.max(1, pixelsPerBeat)));
    contentWidthRef.current = displayWidth;

    const displayHeight = Math.max(180, Math.max(1, tracks.length) * 55);
    const dpr = window.devicePixelRatio || 1;
    const targetWidth = Math.round(displayWidth * dpr);
    const targetHeight = Math.round(displayHeight * dpr);
    if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
      canvas.width = targetWidth;
      canvas.height = targetHeight;
    }
    canvas.style.width = `${displayWidth}px`;
    canvas.style.height = `${displayHeight}px`;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const width = displayWidth;
    const height = displayHeight;
    const headerHeight = 32;
    const contentHeight = height - headerHeight;
    const beatsPerBar = timeSignature?.[0] ?? 4;
    const pxPerBeatLocal = Math.max(1, pixelsPerBeat);
    const pxForBeat = (beat: number) => Math.max(0, beat * pxPerBeatLocal);
    const totalBeats = Math.ceil(timelineBeats);
    const totalBars = Math.ceil(totalBeats / Math.max(1, beatsPerBar));
    const barWidthPx = pxPerBeatLocal * beatsPerBar;

    const drawBarGrid = () => {
      ctx.save();
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.35;
      for (let beat = 0; beat <= totalBeats; beat += 1) {
        if (beat % beatsPerBar === 0) {
          continue;
        }
        const x = pxForBeat(beat);
        if (x > width + 1) {
          break;
        }
        ctx.strokeStyle = BAR_GRID_THEME.beat;
        ctx.beginPath();
        ctx.moveTo(x, headerHeight);
        ctx.lineTo(x, height);
        ctx.stroke();
      }

      ctx.globalAlpha = 0.55;
      for (let bar = 0; bar <= totalBars; bar += 1) {
        const x = pxForBeat(bar * beatsPerBar);
        if (x > width + 1) {
          break;
        }
        ctx.strokeStyle = BAR_GRID_THEME.bar;
        ctx.lineWidth = bar % 4 === 0 ? 2 : 1;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      ctx.restore();
    };

    const timelineDebugKey = `${sections.length}|${bpm}|${pixelsPerBeat}|${timeSignature?.[0] ?? 4}/${timeSignature?.[1] ?? 4}|beats=${timelineBeats.toFixed(2)}|sec=${timelineDurationSec.toFixed(3)}`;
    if (sections.length > 0 && lastTimelineDebugRef.current !== timelineDebugKey) {
      lastTimelineDebugRef.current = timelineDebugKey;
      console.log(`🎨 Timeline rendering ${sections.length} sections at ${pxPerBeatLocal.toFixed(1)}px/beat (tempo-map aware)`);
    }

    drawBarGrid();

    // Draw tracks below header
    const trackHeight = Math.max(48, contentHeight / Math.max(1, tracks.length));
    tracks.forEach((track, i) => {
      const y = headerHeight + i * trackHeight;
      const waveformColor = track.color || '#38bdf8';
      const trackDuration = Math.max(0.1, track.seconds || timelineDurationSec);
      const waveformBeats = Math.max(0.1, mapper.beatsAtTime(trackDuration));
      const waveformWidth = Math.min(width, Math.max(1, Math.round(pxForBeat(waveformBeats))));
      const bgColor = `${waveformColor}20`;

      ctx.fillStyle = bgColor;
      ctx.fillRect(0, y, waveformWidth, trackHeight - 2);
      if (waveformWidth < width) {
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(waveformWidth, y, width - waveformWidth, trackHeight - 2);
      }

      ctx.save();
      ctx.beginPath();
      ctx.rect(0, y, waveformWidth, trackHeight - 2);
      ctx.clip();

      const peaksL = (track as any).peaksL;
      const peaksR = (track as any).peaksR;
      const extentsMono = (track as any).waveformExtents as WaveformExtent[] | undefined;
      const extentsL = (track as any).waveformExtentsL as WaveformExtent[] | undefined;
      const extentsR = (track as any).waveformExtentsR as WaveformExtent[] | undefined;
      const monoPeaks = track.peaks && track.peaks.length
        ? track.peaks
        : Array.isArray(peaksL) && peaksL.length
          ? peaksL
          : Array.isArray(peaksR) && peaksR.length
            ? peaksR
            : [];
      const hasStereoPeaks = !!(peaksL && peaksR && Array.isArray(peaksL) && Array.isArray(peaksR));

      if (hasStereoPeaks) {
        const channelGap = 6;
        const halfHeight = (trackHeight - channelGap) / 2;
        const channelHeight = Math.max(12, halfHeight - 4);
        const channelAmplitude = Math.max(4, channelHeight / 2);
        const leftCenter = y + channelHeight / 2 + 2;
        const rightCenter = y + halfHeight + channelHeight / 2 + 2;

        drawWaveformChannel(
          ctx,
          { extents: extentsL, magnitudes: peaksL },
          waveformWidth,
          leftCenter,
          channelAmplitude,
          waveformColor,
          mapper.timeAtBeats,
          trackDuration,
          pxPerBeatLocal,
        );
        drawWaveformChannel(
          ctx,
          { extents: extentsR, magnitudes: peaksR },
          waveformWidth,
          rightCenter,
          channelAmplitude,
          waveformColor,
          mapper.timeAtBeats,
          trackDuration,
          pxPerBeatLocal,
        );

        const dividerY = y + halfHeight;
        ctx.strokeStyle = '#ffffff30';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(0, dividerY);
        ctx.lineTo(width, dividerY);
        ctx.stroke();
      } else if (monoPeaks.length) {
        const usableHeight = Math.max(24, trackHeight - 12);
        const amplitude = usableHeight / 2;
        const centerY = y + trackHeight / 2;
        drawWaveformChannel(
          ctx,
          { extents: extentsMono, magnitudes: monoPeaks },
          waveformWidth,
          centerY,
          amplitude,
          waveformColor,
          mapper.timeAtBeats,
          trackDuration,
          pxPerBeatLocal,
        );
      } else {
        ctx.fillStyle = '#475569';
        ctx.font = '12px sans-serif';
        ctx.fillText('No waveform data yet', 12, y + trackHeight / 2);
      }

      ctx.restore();

      ctx.fillStyle = '#ffffff';
      ctx.font = '12px sans-serif';
      ctx.fillText(track.name + (hasStereoPeaks ? ' (Stereo)' : ''), 8, y + 20);
    });

    ctx.fillStyle = BAR_GRID_THEME.background;
    ctx.fillRect(0, 0, width, headerHeight);

    // Tempo curve overlay (if available)
    if (tempoMap && tempoMap.length >= 2) {
      const pts = tempoMap
        .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
        .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
        .sort((a, b) => a.tSec - b.tSec);

      if (pts.length >= 2) {
        let minBpm = Infinity;
        let maxBpm = -Infinity;
        for (const p of pts) {
          if (p.bpm < minBpm) minBpm = p.bpm;
          if (p.bpm > maxBpm) maxBpm = p.bpm;
        }
        const range = Math.max(0, maxBpm - minBpm);
        const stable = range <= 1.5;
        const pad = Math.max(0.25, range * 0.15);
        const lo = minBpm - pad;
        const hi = maxBpm + pad;
        const denom = Math.max(1e-6, hi - lo);

        const yTop = 3;
        const yBottom = headerHeight - 3;

        ctx.save();
        ctx.globalAlpha = 0.95;
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = stable ? 'rgba(16, 185, 129, 0.9)' : 'rgba(245, 158, 11, 0.95)';
        ctx.shadowColor = stable ? 'rgba(16, 185, 129, 0.35)' : 'rgba(245, 158, 11, 0.35)';
        ctx.shadowBlur = 6;

        ctx.beginPath();
        pts.forEach((p, idx) => {
          const x = pxForBeat(mapper.beatsAtTime(p.tSec));
          const norm = (p.bpm - lo) / denom;
          const y = yBottom - norm * (yBottom - yTop);
          if (idx === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Subtle baseline
        ctx.shadowBlur = 0;
        ctx.globalAlpha = 0.35;
        ctx.strokeStyle = '#334155';
        ctx.beginPath();
        ctx.moveTo(0, yBottom);
        ctx.lineTo(width, yBottom);
        ctx.stroke();

        // Label
        ctx.globalAlpha = 0.8;
        ctx.fillStyle = stable ? '#34d399' : '#fbbf24';
        ctx.font = '10px sans-serif';
        ctx.fillText(`tempo curve (range ${range.toFixed(1)} bpm)`, 8, headerHeight - 6);
        ctx.restore();
      }
    }

    sections.forEach((section, idx) => {
      const startX = pxForBeat(mapper.beatsAtTime(section.start));
      const endX = pxForBeat(mapper.beatsAtTime(section.end));

      if (idx === 0 && lastTimelineDebugRef.current === timelineDebugKey) {
        console.log(`🎯 First section ${section.label} spans ${endX - startX}px`);
      }

      const style = sectionStyleFor(section.label);
      const isSelected = selectedSectionIds.has(section.id);

      ctx.fillStyle = style.fill;
      ctx.fillRect(startX, 0, endX - startX, headerHeight);

      if (isSelected) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.fillRect(startX, 0, endX - startX, headerHeight);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.strokeRect(startX, 0, endX - startX, headerHeight);
      }

      ctx.lineWidth = 2;
      ctx.strokeRect(startX, 0, endX - startX, headerHeight);

      ctx.save();
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = style.stroke;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(startX, headerHeight);
      ctx.lineTo(startX, height);
      ctx.stroke();
      ctx.restore();

      if (section.label && endX - startX > 60) {
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px sans-serif';
        const labelText = (style.title || section.label.toUpperCase()).toUpperCase();
        const textWidth = ctx.measureText(labelText).width;
        const textX = startX + (endX - startX - textWidth) / 2;
        ctx.fillText(labelText, textX, 12);

        const microTempo = section.tempo || bpm;
        ctx.font = 'bold 10px monospace';
        ctx.fillStyle = '#fbbf24';
        const tempoText = `♩=${Math.round(microTempo)}`;
        const tempoTextWidth = ctx.measureText(tempoText).width;
        const tempoTextX = startX + (endX - startX - tempoTextWidth) / 2;
        ctx.fillText(tempoText, tempoTextX, 22);

        const startB = mapper.beatsAtTime(section.start);
        const endB = mapper.beatsAtTime(section.end);
        const beatsSpan = Math.max(0, endB - startB);
        const bars = Math.max(1, Math.round(beatsSpan / Math.max(1, beatsPerBar)));
        ctx.font = '9px sans-serif';
        ctx.fillStyle = '#cbd5e1';
        const barText = `${bars}`;
        const barTextWidth = ctx.measureText(barText).width;
        const barTextX = startX + (endX - startX - barTextWidth) / 2;
        ctx.fillText(barText, barTextX, 30);
      }

      const sectionBlocks = blocksBySection[section.id] || [];
      if (sectionBlocks.length) {
        const sectionStartBeat = mapper.beatsAtTime(section.start);
        sectionBlocks.forEach((block) => {
          if (!block.lengthBars || block.lengthBars <= 0) {
            return;
          }

          const blockStartBeat = sectionStartBeat + Math.max(0, block.startBar) * Math.max(1, beatsPerBar);
          const rawEndBeat = blockStartBeat + block.lengthBars * Math.max(1, beatsPerBar);
          const blockStartSec = mapper.timeAtBeats(blockStartBeat);
          const rawEndSec = mapper.timeAtBeats(rawEndBeat);
          const clampedStart = Math.max(section.start, blockStartSec);
          const clampedEnd = Math.min(section.end, rawEndSec);
          if (clampedEnd <= clampedStart) {
            return;
          }

          const blockStartX = pxForBeat(mapper.beatsAtTime(clampedStart));
          const blockEndX = pxForBeat(mapper.beatsAtTime(clampedEnd));
          const blockWidth = Math.max(4, blockEndX - blockStartX);

          ctx.fillStyle = 'rgba(147, 51, 234, 0.6)';
          ctx.fillRect(blockStartX, 4, blockWidth, 8);
          ctx.strokeStyle = '#f0abfc';
          ctx.lineWidth = 1;
          ctx.strokeRect(blockStartX, 4, blockWidth, 8);

          if (blockWidth > 32) {
            const label = block.rudimentId || block.families?.[0] || 'rudiment';
            ctx.fillStyle = '#fdf4ff';
            ctx.font = '8px sans-serif';
            const labelWidth = ctx.measureText(label).width;
            const labelX = blockStartX + (blockWidth - labelWidth) / 2;
            ctx.fillText(label, labelX, 12);
          }
        });
      }
    });

    ctx.save();
    ctx.globalAlpha = 0.9;
    ctx.fillStyle = BAR_GRID_THEME.label;
    ctx.font = '10px sans-serif';
    for (let bar = 0; bar < totalBars; bar += 1) {
      const startX = pxForBeat(bar * beatsPerBar);
      const nextX = pxForBeat((bar + 1) * beatsPerBar);
      if (nextX - startX < 36) {
        continue;
      }
      ctx.fillText(`${bar + 1}`, startX + 6, 12);
    }
    ctx.restore();

    const playheadX = pxForBeat(mapper.beatsAtTime(playhead));
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playheadX, 0);
    ctx.lineTo(playheadX, height);
    ctx.stroke();
  }, [tracks, playhead, sections, bpm, tempoMap, beatTimes, blocksBySection, viewportWidth, pixelsPerBeat, loop, timeSignature]);

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const durationSec = timelineDurationRef.current || Math.max(...tracks.map((t) => t.seconds), 10);
    const tempoPts = normalizeTempoMap(tempoMap);
    const normalizedBeatTimes = normalizeBeatTimes(beatTimes);
    const mapper = normalizedBeatTimes.length
      ? makeTimeBeatMapperFromBeatTimes(normalizedBeatTimes)
      : makeTimeBeatMapper(tempoPts, bpm);
    const totalBeats = Math.max(1, mapper.beatsAtTime(durationSec));
    const canvasWidth = canvas.clientWidth || contentWidthRef.current || 1;
    const clickBeat = (x / canvasWidth) * totalBeats;
    const clickTime = mapper.timeAtBeats(clickBeat);

    const headerHeight = 32;

    if (y <= headerHeight && onSelectSection) {
      for (const section of sections) {
        const startB = mapper.beatsAtTime(section.start);
        const endB = mapper.beatsAtTime(section.end);
        const startX = (startB / totalBeats) * canvasWidth;
        const endX = (endB / totalBeats) * canvasWidth;
        if (x >= startX && x <= endX) {
          const isMulti = event.ctrlKey || event.metaKey;
          onSelectSection(section.id, isMulti);
          return;
        }
      }
      onSelectSection('', false);
      return;
    }

    setPlayhead(clickTime);
  };

  const handleCanvasContextMenu = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onSectionContextMenu) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const headerHeight = 32;
    if (y > headerHeight) return;

    const durationSec = timelineDurationRef.current || Math.max(...tracks.map((t) => t.seconds), 10);
    const tempoPts = normalizeTempoMap(tempoMap);
    const normalizedBeatTimes = normalizeBeatTimes(beatTimes);
    const mapper = normalizedBeatTimes.length
      ? makeTimeBeatMapperFromBeatTimes(normalizedBeatTimes)
      : makeTimeBeatMapper(tempoPts, bpm);
    const totalBeats = Math.max(1, mapper.beatsAtTime(durationSec));
    const canvasWidth = canvas.clientWidth || contentWidthRef.current || 1;

    for (const section of sections) {
      const startB = mapper.beatsAtTime(section.start);
      const endB = mapper.beatsAtTime(section.end);
      const startX = (startB / totalBeats) * canvasWidth;
      const endX = (endB / totalBeats) * canvasWidth;
      if (x >= startX && x <= endX) {
        event.preventDefault();
        onSectionContextMenu(section.id);
        return;
      }
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      onDropFiles(files);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  const addSection = () => {
    const newSection: Section = {
      id: `section-${Date.now()}`,
      start: playhead,
      end: playhead + 4,
      density: 0.5,
      fillIn: false,
      fillOut: false,
    };
    onSectionsChange([...sections, newSection]);
  };

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-100">Timeline</h3>
        <div className="flex gap-2">
          {tracks.length > 0 && onAutoSectionize && (
            <button
              onClick={() => onAutoSectionize(tracks[0].key)}
              className="px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              Auto-Detect Sections
            </button>
          )}
          <button
            onClick={addSection}
            className="px-3 py-1 bg-emerald-600 text-white rounded hover:bg-emerald-700"
          >
            Add Section
          </button>
        </div>
      </div>

      <div
        ref={viewportRef}
        className="relative"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <div className="flex min-w-0">
          <div className="w-36 flex-shrink-0" />
          <div
            ref={scrollContainerRef}
            className="flex-1 min-w-0 overflow-x-auto rounded bg-slate-900"
          >
            <canvas
              ref={canvasRef}
              className="w-full cursor-pointer"
              onClick={handleCanvasClick}
              onContextMenu={handleCanvasContextMenu}
            />
          </div>
        </div>
      </div>

      {/* Sections list removed - now shown in collapsible "Musical Arrangement" below */}
    </div>
  );
};

export default Timeline;
