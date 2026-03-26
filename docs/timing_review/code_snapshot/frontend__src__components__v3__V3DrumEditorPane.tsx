import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DrumEditorPane } from "../drums/DrumEditorPane";
import { useV3Store } from "../../state/v3/store";
import { GridResolution } from "../../utils/pianoRollGrid";
import { renderPluginMidi } from "../../api/api";
import type { DrumPlayerEngine } from "../../audio/drumPlayerEngine";

function barIndexToSec(args: {
  barIndex: number;
  beatsPerBar: number;
  beatTimes?: number[];
  tempoMap?: Array<{ tSec: number; bpm: number }>;
  fallbackBpm: number;
}): number {
  const { barIndex, beatsPerBar, beatTimes, tempoMap, fallbackBpm } = args;
  const beats = Math.max(0, Math.floor(barIndex)) * Math.max(1, beatsPerBar);

  if (Array.isArray(beatTimes) && beatTimes.length >= 2) {
    const idx = Math.max(0, Math.min(beatTimes.length - 1, beats));
    const t = beatTimes[idx];
    if (Number.isFinite(t) && t >= 0) return t;
  }

  const pts = Array.isArray(tempoMap)
    ? tempoMap
        .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
        .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
        .sort((a, b) => a.tSec - b.tSec)
    : [];

  const bpm0 = Number.isFinite(fallbackBpm) && fallbackBpm > 0 ? fallbackBpm : 120;
  if (!pts.length) {
    return (beats * 60) / bpm0;
  }

  // Precompute beats at each tempo point.
  const beatsAtPoint: number[] = new Array(pts.length);
  beatsAtPoint[0] = 0;
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1];
    const cur = pts[i];
    const dt = Math.max(0, cur.tSec - prev.tSec);
    beatsAtPoint[i] = beatsAtPoint[i - 1] + (dt * prev.bpm) / 60;
  }

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
}

function beatsAtTimeFromBeatTimes(beatTimes: number[], tSec: number): number {
  if (!Array.isArray(beatTimes) || beatTimes.length < 2) return 0;
  const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);
  if (t <= beatTimes[0]) return 0;

  let lo = 0;
  let hi = beatTimes.length - 1;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (beatTimes[mid] < t) lo = mid + 1;
    else hi = mid;
  }
  const idx = lo;
  if (idx <= 0) return 0;
  if (idx >= beatTimes.length) return beatTimes.length - 1;
  const prev = idx - 1;
  const t0 = beatTimes[prev];
  const t1 = beatTimes[idx];
  if (!Number.isFinite(t0) || !Number.isFinite(t1) || t1 <= t0) return prev;
  const frac = Math.max(0, Math.min(1, (t - t0) / (t1 - t0)));
  return prev + frac;
}

function beatsAtTimeFromTempoMap(tempoMap: Array<{ tSec: number; bpm: number }>, fallbackBpm: number, tSec: number): number {
  const pts = Array.isArray(tempoMap)
    ? tempoMap
        .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
        .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
        .sort((a, b) => a.tSec - b.tSec)
    : [];

  const bpm0 = Number.isFinite(fallbackBpm) && fallbackBpm > 0 ? fallbackBpm : 120;
  const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);

  if (!pts.length) {
    return (t * bpm0) / 60;
  }
  if (pts.length === 1) {
    return (t * pts[0].bpm) / 60;
  }

  let beats = 0;
  let prevT = pts[0].tSec;
  let prevBpm = pts[0].bpm;
  if (t <= prevT) return 0;

  for (let i = 1; i < pts.length; i++) {
    const cur = pts[i];
    if (t <= cur.tSec) {
      beats += ((t - prevT) * prevBpm) / 60;
      return beats;
    }
    beats += ((cur.tSec - prevT) * prevBpm) / 60;
    prevT = cur.tSec;
    prevBpm = cur.bpm;
  }

  beats += ((t - prevT) * prevBpm) / 60;
  return beats;
}

function playheadToXPx(args: {
  tSec: number;
  pixelsPerBeat: number;
  beatTimes?: number[];
  tempoMap?: Array<{ tSec: number; bpm: number }>;
  fallbackBpm: number;
}): number {
  const pxPerBeat = Math.max(1, Number(args.pixelsPerBeat) || 0);
  const beats = Array.isArray(args.beatTimes) && args.beatTimes.length >= 2
    ? beatsAtTimeFromBeatTimes(args.beatTimes, args.tSec)
    : beatsAtTimeFromTempoMap(args.tempoMap || [], args.fallbackBpm, args.tSec);
  return Math.max(0, beats) * pxPerBeat;
}

function formatBBT(args: { tSec: number; timeSig: [number, number]; beatTimes?: number[]; tempoMap?: Array<{ tSec: number; bpm: number }>; fallbackBpm: number }): string {
  const beatsPerBar = Number(args.timeSig?.[0] || 4) || 4;
  const ppq = 960;
  let beats = 0;
  if (Array.isArray(args.beatTimes) && args.beatTimes.length >= 2) {
    beats = beatsAtTimeFromBeatTimes(args.beatTimes, args.tSec);
  } else {
    beats = beatsAtTimeFromTempoMap(args.tempoMap || [], args.fallbackBpm, args.tSec);
  }
  const b = Math.max(0, Number.isFinite(beats) ? beats : 0);
  const wholeBeats = Math.floor(b);
  const frac = Math.max(0, Math.min(0.999999, b - wholeBeats));
  const bar = Math.floor(wholeBeats / beatsPerBar) + 1;
  const beatInBar = (wholeBeats % beatsPerBar) + 1;
  const tick = Math.floor(frac * ppq);
  return `${bar}:${beatInBar}:${tick}`;
}

export function V3DrumEditorPane(props: {
  pianoRollScrollRef?: React.RefObject<HTMLDivElement | null>;
  pixelsPerBeat: number;
  drumEngine?: DrumPlayerEngine | null;
  playing?: boolean;
}) {
  const drumTrack = useV3Store((s) => s.generatedDrumTrack);
  const arrangement = useV3Store((s) => s.arrangement);
  const globalDefaults = useV3Store((s) => s.globalDefaults);
  const setGlobalDefaults = useV3Store((s) => s.setGlobalDefaults);
  const barEdits = useV3Store((s) => s.barEdits);
  const playheadSec = useV3Store((s) => s.playheadSec);
  const setPlayheadSec = useV3Store((s) => s.setPlayheadSec);
  const selectedSectionId = useV3Store((s) => s.selection.selectedSectionId);
  const setSelectedSectionId = useV3Store((s) => s.setSelectedSectionId);
  const selectedBarIndex = useV3Store((s) => s.selection.selectedBarIndex);
  const setSelectedBarIndex = useV3Store((s) => s.setSelectedBarIndex);

  const arrangementStripScrollRef = useRef<HTMLDivElement | null>(null);

  const [gridResolution, setGridResolution] = useState<GridResolution>("16th");

  const bpm = arrangement.tempoMap?.[0]?.bpm || 120;
  const timeSig = arrangement.timeSig;

  const [exportBusy, setExportBusy] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const sectionRegions = useMemo(() => {
    const beatsPerBar = Number(arrangement.timeSig?.[0] || 4) || 4;
    const secs = arrangement.sections || [];
    if (!secs.length) return [];

    return secs
      .map((s, idx) => {
        const startSec = Number((s as any)?.startSec ?? 0);
        const endSec = Number((s as any)?.endSec ?? 0);
        if (!Number.isFinite(startSec) || !Number.isFinite(endSec) || endSec <= startSec) return null;

        const startBeats = Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2
          ? beatsAtTimeFromBeatTimes(arrangement.beatTimes, startSec)
          : beatsAtTimeFromTempoMap(arrangement.tempoMap || [], bpm, startSec);

        const endBeats = Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2
          ? beatsAtTimeFromBeatTimes(arrangement.beatTimes, endSec)
          : beatsAtTimeFromTempoMap(arrangement.tempoMap || [], bpm, endSec);

        if (!Number.isFinite(startBeats) || !Number.isFinite(endBeats) || endBeats <= startBeats) return null;

        const startBar = Math.max(0, Math.floor(startBeats / Math.max(1, beatsPerBar)));
        const endBar = Math.max(startBar, Math.floor((Math.max(startBeats, endBeats - 1e-6)) / Math.max(1, beatsPerBar)));
        return {
          id: `v3-${idx}-${startSec.toFixed(3)}-${endSec.toFixed(3)}`,
          label: (s as any)?.label || `Section ${idx + 1}`,
          startBar,
          endBar,
        };
      })
      .filter(Boolean) as Array<{ id: string; label: string; startBar: number; endBar: number }>;
  }, [arrangement.beatTimes, arrangement.sections, arrangement.tempoMap, arrangement.timeSig, bpm]);

  const bbt = useMemo(() => {
    return formatBBT({
      tSec: playheadSec,
      timeSig: arrangement.timeSig,
      beatTimes: arrangement.beatTimes,
      tempoMap: arrangement.tempoMap,
      fallbackBpm: bpm,
    });
  }, [arrangement.beatTimes, arrangement.tempoMap, arrangement.timeSig, bpm, playheadSec]);

  const downloadMidiBase64 = useCallback((base64Midi: string, filenameBase: string) => {
    const binStr = window.atob(base64Midi);
    const bytes = new Uint8Array(binStr.length);
    for (let i = 0; i < binStr.length; i++) bytes[i] = binStr.charCodeAt(i);
    const blob = new Blob([bytes], { type: "audio/midi" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filenameBase}.mid`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }, []);

  const playheadXPx = useMemo(() => {
    return playheadToXPx({
      tSec: playheadSec,
      pixelsPerBeat: props.pixelsPerBeat,
      beatTimes: arrangement.beatTimes,
      tempoMap: arrangement.tempoMap,
      fallbackBpm: bpm,
    });
  }, [arrangement.beatTimes, arrangement.tempoMap, bpm, playheadSec, props.pixelsPerBeat]);

  const onExportMidi = useCallback(async () => {
    if (!drumTrack) return;
    setExportBusy(true);
    setExportError(null);
    try {
      const beatsPerBar = Number(arrangement.timeSig?.[0] || 4) || 4;
      const ppq = Number((drumTrack as any)?.resolution_ppq || 960) || 960;
      const ticksPerBar = ppq * beatsPerBar;

      const plugin = (globalDefaults.exportPlugin || "jamstix") as "jamstix" | "sd3" | "ssd5";
      const advancedArticulations = !!globalDefaults.advancedArticulations;

      const notes = (drumTrack.notes || [])
        .map((n: any) => {
          const barIndex = Number(n?.barIndex || 0);
          const tickInBar = Number(n?.tickInBar || 0);
          const tickLength = Number(n?.tickLength || 0);
          const t0 = barIndex * ticksPerBar + tickInBar;
          const t1 = Math.max(t0 + 1, t0 + Math.max(1, tickLength));
          return {
            t0,
            t1,
            pitch: Number(n?.midiPitch || 36),
            vel: Number(n?.velocity || 100),
            chan: Number(n?.channel ?? 9),
            articulationId: n?.articulationId ? String(n.articulationId) : undefined,
          };
        })
        .filter((x: any) => Number.isFinite(x.t0) && Number.isFinite(x.t1) && Number.isFinite(x.pitch));

      const res = await renderPluginMidi({ plugin, advancedArticulations, ppq, notes });

      const secId = selectedSectionId ? String(selectedSectionId) : "full";
      const filenameBase = `DrumTracKAI-${plugin}-${secId}`;
      downloadMidiBase64(res.midi_base64, filenameBase);
    } catch (e: any) {
      setExportError(e?.message || String(e));
    } finally {
      setExportBusy(false);
    }
  }, [arrangement.timeSig, downloadMidiBase64, drumTrack, globalDefaults.advancedArticulations, globalDefaults.exportPlugin, selectedSectionId]);

  const onBarSelect = useCallback(
    (barIdx: number | null) => {
      setSelectedBarIndex(barIdx);
      if (barIdx === null) return;
      const beatsPerBar = arrangement.timeSig?.[0] || 4;
      const t = barIndexToSec({
        barIndex: barIdx,
        beatsPerBar,
        beatTimes: arrangement.beatTimes,
        tempoMap: arrangement.tempoMap,
        fallbackBpm: bpm,
      });
      setPlayheadSec(t);
    },
    [arrangement.beatTimes, arrangement.tempoMap, arrangement.timeSig, bpm, setPlayheadSec, setSelectedBarIndex],
  );

  useEffect(() => {
    let rafId: number | null = null;
    let cleanup: null | (() => void) = null;

    const tryAttach = () => {
      const drumEl = props.pianoRollScrollRef?.current || null;
      const stripEl = arrangementStripScrollRef.current;
      if (!drumEl || !stripEl) {
        rafId = window.requestAnimationFrame(tryAttach);
        return;
      }

      // Initial sync
      stripEl.scrollLeft = drumEl.scrollLeft;

      let active: 'drum' | 'strip' | null = null;

      const onDrumScroll = () => {
        if (!props.pianoRollScrollRef?.current || !arrangementStripScrollRef.current) return;
        if (active === 'strip') return;
        active = 'drum';
        arrangementStripScrollRef.current.scrollLeft = props.pianoRollScrollRef.current.scrollLeft;
        window.requestAnimationFrame(() => {
          if (active === 'drum') active = null;
        });
      };

      const onStripScroll = () => {
        if (!props.pianoRollScrollRef?.current || !arrangementStripScrollRef.current) return;
        if (active === 'drum') return;
        active = 'strip';
        props.pianoRollScrollRef.current.scrollLeft = arrangementStripScrollRef.current.scrollLeft;
        window.requestAnimationFrame(() => {
          if (active === 'strip') active = null;
        });
      };

      drumEl.addEventListener('scroll', onDrumScroll, { passive: true });
      stripEl.addEventListener('scroll', onStripScroll, { passive: true });

      cleanup = () => {
        drumEl.removeEventListener('scroll', onDrumScroll);
        stripEl.removeEventListener('scroll', onStripScroll);
      };
    };

    tryAttach();
    return () => {
      if (rafId !== null) window.cancelAnimationFrame(rafId);
      cleanup?.();
    };
  }, [props.pianoRollScrollRef]);

  const totalSongBars = useMemo(() => {
    const beatsPerBar = Number(arrangement.timeSig?.[0] || 4) || 4;

    let maxBarFromArrangement = 0;
    const secs = arrangement.sections || [];
    for (const s of secs) {
      const endSec = Number((s as any)?.endSec ?? 0);
      if (!Number.isFinite(endSec) || endSec <= 0) continue;

      const endBeats = Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2
        ? beatsAtTimeFromBeatTimes(arrangement.beatTimes, endSec)
        : beatsAtTimeFromTempoMap(arrangement.tempoMap || [], bpm, endSec);

      if (!Number.isFinite(endBeats) || endBeats <= 0) continue;
      const bar = Math.max(0, Math.ceil(endBeats / Math.max(1, beatsPerBar)));
      if (bar > maxBarFromArrangement) maxBarFromArrangement = bar;
    }

    let maxBarFromNotes = 0;
    const notes = drumTrack?.notes || [];
    for (const n of notes) {
      const bi = Number((n as any)?.barIndex);
      if (Number.isFinite(bi) && bi > maxBarFromNotes) maxBarFromNotes = bi;
    }

    // `maxBarFromArrangement` is already a bar-count estimate; `maxBarFromNotes` is a 0-based index.
    const barsFromNotes = notes.length ? maxBarFromNotes + 1 : 0;
    return Math.max(1, maxBarFromArrangement, barsFromNotes);
  }, [arrangement.beatTimes, arrangement.sections, arrangement.tempoMap, arrangement.timeSig, bpm, drumTrack?.notes]);

  const beatsPerBar = Number(arrangement.timeSig?.[0] || 4) || 4;
  const barWidthPx = Math.max(1, props.pixelsPerBeat) * Math.max(1, beatsPerBar);
  const stripWidthPx = Math.max(1, totalSongBars) * barWidthPx;

  const sectionColorFor = (label: string): string => {
    const v = String(label || '').toLowerCase();
    if (v.includes('verse')) return 'rgba(59,130,246,0.35)';
    if (v.includes('chorus')) return 'rgba(34,197,94,0.35)';
    if (v.includes('bridge')) return 'rgba(168,85,247,0.35)';
    if (v.includes('intro')) return 'rgba(249,115,22,0.35)';
    if (v.includes('outro')) return 'rgba(239,68,68,0.35)';
    return 'rgba(148,163,184,0.22)';
  };

  const barDirectives = useMemo(() => {
    const secKey = selectedSectionId ? String(selectedSectionId) : "";
    if (!secKey) return {} as Record<number, { forceFill?: boolean; suppressFill?: boolean }>;
    const byBar = (barEdits as any)?.[secKey] || {};
    const out: Record<number, { forceFill?: boolean; suppressFill?: boolean }> = {};
    for (const k of Object.keys(byBar)) {
      const bi = Number(k);
      if (!Number.isFinite(bi)) continue;
      const st = byBar[bi] || {};
      if (st.forceFill || st.suppressFill) {
        out[bi] = { forceFill: !!st.forceFill, suppressFill: !!st.suppressFill };
      }
    }
    return out;
  }, [barEdits, selectedSectionId]);

  if (!drumTrack) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
        <div className="text-xs font-semibold text-slate-200 tracking-wide">Drum Performance Editor</div>
        <div className="mt-1 text-[11px] text-slate-500">
          Generate drums to populate the editor grid.
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden">
      <div className="px-3 py-1 border-b border-slate-800 bg-slate-950 text-[11px] text-slate-300 flex items-center justify-between gap-3">
        <div>
          Playhead: {playheadSec.toFixed(2)}s • {bbt}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-2 py-0.5 rounded border border-slate-800 bg-slate-950">
            <div className="text-[11px] text-slate-400">Export</div>
            <select
              className="bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-[11px]"
              value={(globalDefaults.exportPlugin || "jamstix") as any}
              onChange={(e) => setGlobalDefaults({ exportPlugin: e.target.value as any })}
              disabled={exportBusy}
            >
              <option value="jamstix">Jamstix</option>
              <option value="sd3">SD3</option>
              <option value="ssd5">SSD5</option>
            </select>
            <label className="flex items-center gap-1 text-[11px] text-slate-200">
              <input
                type="checkbox"
                checked={!!globalDefaults.advancedArticulations}
                onChange={(e) => setGlobalDefaults({ advancedArticulations: e.target.checked })}
                disabled={exportBusy}
              />
              Advanced
            </label>
            <button
              type="button"
              className="px-2 py-0.5 rounded bg-slate-800 text-slate-100 border border-slate-700 disabled:opacity-50"
              onClick={() => void onExportMidi()}
              disabled={exportBusy || !drumTrack}
            >
              {exportBusy ? "Exporting…" : "Export .mid"}
            </button>
          </div>
        </div>
      </div>

      {exportError && (
        <div className="px-3 py-1 border-b border-slate-800 bg-slate-950 text-[11px] text-rose-300">
          Export error: {exportError}
        </div>
      )}

      <div className="border-b border-slate-800 bg-slate-950">
        <div className="px-3 py-1 text-[11px] text-slate-400">Arrangement</div>
        <div className="overflow-x-auto" ref={arrangementStripScrollRef}>
          <div className="relative" style={{ width: stripWidthPx, height: 40 }}>
            <div
              className="absolute top-0 bottom-0"
              style={{
                left: playheadXPx,
                width: 2,
                background: 'rgba(34,197,94,0.75)',
                boxShadow: '0 0 10px rgba(34,197,94,0.25)',
                pointerEvents: 'none',
                zIndex: 20,
              }}
            />

            {Array.from({ length: Math.max(1, totalSongBars) }).map((_, barIdx) => (
              <div
                key={`arr-strip-bar-${barIdx}`}
                className="absolute top-0 bottom-0"
                style={{
                  left: barIdx * barWidthPx,
                  width: barWidthPx,
                  borderLeft: '1px solid rgba(148,163,184,0.22)',
                  pointerEvents: 'none',
                }}
              />
            ))}

            {sectionRegions.map((r) => {
              const left = r.startBar * barWidthPx;
              const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
              const selected = selectedSectionId && String(selectedSectionId) === String(r.id);
              return (
                <button
                  key={`arr-strip-sec-${r.id}`}
                  type="button"
                  className="absolute top-1 bottom-1 rounded-sm border text-[10px] font-semibold text-slate-100 px-2 overflow-hidden"
                  style={{
                    left,
                    width,
                    background: sectionColorFor(r.label),
                    borderColor: selected ? 'rgba(217,70,239,0.7)' : 'rgba(148,163,184,0.25)',
                  }}
                  onClick={() => {
                    setSelectedSectionId(String(r.id));
                    setSelectedBarIndex(r.startBar);
                    onBarSelect(r.startBar);
                  }}
                >
                  <span className="truncate block">{r.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="h-[820px]">
        <DrumEditorPane
          drumTrack={drumTrack}
          timeSignature={arrangement.timeSig}
          grooveWeights={undefined}
          gridResolution={gridResolution}
          onGridResolutionChange={setGridResolution}
          onUpdateTrack={undefined}
          bpm={bpm}
          tempoMap={arrangement.tempoMap}
          beatTimes={arrangement.beatTimes}
          playheadSeconds={playheadSec}
          playing={props.playing}
          pixelsPerBeat={props.pixelsPerBeat}
          pianoRollScrollRef={props.pianoRollScrollRef as any}
          drumEngine={props.drumEngine}
          selectedBarIndex={selectedBarIndex}
          onBarSelect={onBarSelect}
          totalSongBars={totalSongBars}
          barDirectives={barDirectives}
          sectionRegions={sectionRegions as any}
          selectedSectionIds={selectedSectionId ? new Set([selectedSectionId]) : new Set()}
          onSectionSelect={(sectionId) => {
            setSelectedSectionId(sectionId ? sectionId : null);
          }}
        />
      </div>
    </div>
  );
}
