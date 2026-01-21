import React, { useMemo, useState, useRef, useEffect } from "react";
import type { MidiNote } from "./PianoRoll";
import type { MeasureRange } from "./WebDAWApp";
import { getSubdivisionsPerBar, type GridResolution } from "../utils/pianoRollGrid";
import { LIMB_CONFIG, LIMB_ORDER, inferLimbFromLane, type LimbId } from "../constants/limbs";
import { BAR_GRID_THEME } from "../constants/barGrid";
import { getSharedAudioContext } from "../audio/sharedAudioContext";
const LIMB_FREQUENCY: Record<LimbId, number> = {
  RH: 1100,
  LH: 650,
  RF: 180,
  LF: 260,
};
const NOTE_ID_PREFIX = "limb-grid";

function makeNoteId(step: number, limb: LimbId) {
  return `${NOTE_ID_PREFIX}-${limb}-${step}-${Math.random().toString(36).slice(2, 7)}`;
}

function secondsPerMeasure(bpm: number, timeSig: [number, number]) {
  const beatsPerMeasure = timeSig[0];
  const secPerBeat = 60 / Math.max(1, bpm);
  return secPerBeat * beatsPerMeasure;
}

function getSectionAccentColor(label?: string | null): string {
  const v = (label || "").toLowerCase();
  if (v.includes("verse")) return "#3b82f6";
  if (v.includes("chorus")) return "#22c55e";
  if (v.includes("bridge")) return "#a855f7";
  if (v.includes("intro")) return "#f97316";
  if (v.includes("outro")) return "#ef4444";
  return "#64748b";
}

type LimbGridProps = {
  notes: MidiNote[];
  onChange: (notes: MidiNote[]) => void;
  bpm: number;
  timeSig: [number, number];
  selectedRange?: MeasureRange | null;
  gridResolution: GridResolution;
  sectionStartTime?: number;
  scrollContainerRef?: React.RefObject<HTMLDivElement>;
  pixelsPerBeat: number;
  totalSongBars?: number;
};

export const LimbGrid: React.FC<LimbGridProps> = ({
  notes,
  onChange,
  bpm,
  timeSig,
  selectedRange,
  gridResolution,
  sectionStartTime,
  scrollContainerRef,
  pixelsPerBeat,
  totalSongBars,
}) => {
  const [previewing, setPreviewing] = useState(false);
  const [scrollLeft, setScrollLeft] = useState(0);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);
  const effectiveTimeSig = timeSig;
  const tempoForGrid = selectedRange?.avgTempo ?? bpm;
  const secPerMeasure = secondsPerMeasure(tempoForGrid, effectiveTimeSig);
  const stepsPerMeasure = getSubdivisionsPerBar(gridResolution);

  const noteBounds = useMemo(() => {
    if (!notes.length) {
      return { min: 0, max: secPerMeasure };
    }
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    for (const note of notes) {
      const start = Number.isFinite(note.time) ? note.time : 0;
      const duration = Number.isFinite(note.duration) ? note.duration : 0;
      min = Math.min(min, start);
      max = Math.max(max, start + duration);
    }
    if (!Number.isFinite(min)) {
      min = 0;
    }
    if (!Number.isFinite(max) || max < min) {
      max = min + secPerMeasure;
    }
    return { min, max };
  }, [notes, secPerMeasure]);

  const rawStartMeasure = selectedRange?.startMeasure;
  const baseStartMeasure = Number.isFinite(rawStartMeasure) ? rawStartMeasure! : 0;

  const inferredMeasureCount = Math.ceil(
    (Math.max(0, noteBounds.max - noteBounds.min) + secPerMeasure) / secPerMeasure,
  );
  const measureCountCandidate = Number.isFinite(selectedRange?.measureCount)
    ? selectedRange!.measureCount
    : inferredMeasureCount;
  const selectionMeasures = Math.max(1, measureCountCandidate);

  const totalMeasuresSpan =
    selectedRange?.sectionId === "full-song" && Number.isFinite(totalSongBars)
      ? Math.max(1, totalSongBars!)
      : selectionMeasures;

  const totalSteps = Math.max(1, Math.round(totalMeasuresSpan * stepsPerMeasure));

  const beatsPerMeasure = effectiveTimeSig[0];
  const measureWidthPx = pixelsPerBeat * beatsPerMeasure;
  const rangeStartSecCandidate = sectionStartTime ?? selectedRange?.startTime ?? baseStartMeasure * secPerMeasure;
  const rangeStartSec = Number.isFinite(rangeStartSecCandidate)
    ? rangeStartSecCandidate
    : noteBounds.min;
  const rangeEndSecCandidate = selectedRange?.endTime ?? rangeStartSec + totalMeasuresSpan * secPerMeasure;
  const rangeEndSec = Number.isFinite(rangeEndSecCandidate) ? rangeEndSecCandidate : noteBounds.max;

  const stepDuration = secPerMeasure / stepsPerMeasure;
  const tolerance = stepDuration / 3;
  const totalWidth = Number.isFinite(totalMeasuresSpan * measureWidthPx) && totalMeasuresSpan * measureWidthPx > 0
    ? totalMeasuresSpan * measureWidthPx
    : totalSteps * Math.max(1, measureWidthPx / stepsPerMeasure);
  const cellWidth = Number.isFinite(totalWidth) && totalWidth > 0
    ? Math.max(1, totalWidth / totalSteps)
    : Math.max(1, measureWidthPx / stepsPerMeasure);

  const activeCells = useMemo(() => {
    const map = new Set<string>();
    const rangeEnd = rangeEndSec + tolerance;
    for (const note of notes) {
      const limb = note.limbId ?? inferLimbFromLane(note.lane);
      if (!limb) continue;
      if (note.time < rangeStartSec - tolerance || note.time > rangeEnd) continue;
      const stepFloat = (note.time - rangeStartSec) / stepDuration;
      const stepIndex = Math.round(stepFloat);
      const clamped = Math.max(0, Math.min(totalSteps - 1, stepIndex));
      map.add(`${limb}:${clamped}`);
    }
    return map;
  }, [notes, rangeStartSec, selectionMeasures, secPerMeasure, stepDuration, tolerance, totalSteps]);

  const previewNotes = useMemo(() => {
    const rangeEnd = rangeEndSec + tolerance;
    return notes.filter((note) => {
      const limb = note.limbId ?? inferLimbFromLane(note.lane);
      if (!limb) return false;
      if (note.time < rangeStartSec - tolerance || note.time > rangeEnd) return false;
      return true;
    });
  }, [notes, rangeStartSec, rangeEndSec, tolerance]);

  const stopPreview = () => {
    if (previewTimeoutRef.current) {
      window.clearTimeout(previewTimeoutRef.current);
      previewTimeoutRef.current = null;
    }
    setPreviewing(false);
  };

  const handlePreview = async () => {
    if (previewing) {
      stopPreview();
      return;
    }
    if (!previewNotes.length) {
      return;
    }
    const ctx = audioCtxRef.current || getSharedAudioContext({ latencyHint: "interactive" });
    audioCtxRef.current = ctx;
    await ctx.resume();
    const startTime = ctx.currentTime + 0.05;
    let finalTime = startTime;
    previewNotes.forEach((note) => {
      const limb = note.limbId ?? inferLimbFromLane(note.lane);
      if (!limb) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const rel = Math.max(0, note.time - rangeStartSec);
      const scheduled = startTime + rel;
      const freq = LIMB_FREQUENCY[limb] || 440;
      osc.type = limb === "RH" ? "triangle" : limb === "LH" ? "square" : "sine";
      osc.frequency.setValueAtTime(freq, scheduled);
      gain.gain.setValueAtTime(0.001, scheduled);
      gain.gain.linearRampToValueAtTime(0.5, scheduled + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.001, scheduled + 0.25);
      osc.connect(gain).connect(ctx.destination);
      osc.start(scheduled);
      osc.stop(scheduled + 0.3);
      finalTime = Math.max(finalTime, scheduled + 0.3);
    });
    setPreviewing(true);
    previewTimeoutRef.current = window.setTimeout(() => {
      stopPreview();
    }, Math.max(250, (finalTime - ctx.currentTime) * 1000));
  };

  const toggleCell = (limb: LimbId, stepIndex: number) => {
    const cellKey = `${limb}:${stepIndex}`;
    const time = rangeStartSec + stepIndex * stepDuration;
    const laneOptions = LIMB_CONFIG[limb].lanes;
    const defaultLane = laneOptions[0] ?? LIMB_CONFIG[limb].defaultLane;

    const hasNote = activeCells.has(cellKey);
    if (hasNote) {
      const next = notes.filter((note) => {
        const noteLimb = note.limbId ?? inferLimbFromLane(note.lane);
        if (noteLimb !== limb) return true;
        if (Math.abs(note.time - time) > tolerance) return true;
        return false;
      });
      onChange(next);
      return;
    }

    const newNote: MidiNote = {
      id: makeNoteId(stepIndex, limb),
      time,
      duration: stepDuration * 0.9,
      lane: defaultLane,
      vel: limb === "RH" ? 0.75 : limb === "LH" ? 0.85 : 0.9,
      limbId: limb,
    };

    onChange([...notes, newNote]);
  };

  const measureLabel = selectedRange
    ? `${selectedRange.sectionLabel || "Section"} · measures ${selectedRange.startMeasure + 1}-${selectedRange.endMeasure + 1}`
    : `First ${totalMeasuresSpan} measures`;

  const sectionAccent = getSectionAccentColor(selectedRange?.sectionLabel);
  const limbRowHeightPx = 44;

  const horizontalScrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (scrollContainerRef) {
      scrollContainerRef.current = horizontalScrollRef.current;
    }
    return () => {
      if (scrollContainerRef && scrollContainerRef.current === horizontalScrollRef.current) {
        scrollContainerRef.current = null;
      }
    };
  }, [scrollContainerRef, totalSteps]);

  useEffect(() => {
    const el = horizontalScrollRef.current;
    if (!el) return;
    const update = () => setScrollLeft(el.scrollLeft);
    update();
    el.addEventListener("scroll", update, { passive: true });
    return () => el.removeEventListener("scroll", update);
  }, [measureWidthPx, totalSteps]);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3 text-sm text-slate-200">
        <div>
          <div className="font-semibold flex items-center gap-2">
            <span>Four-Limb Grid</span>
            {selectedRange?.sectionLabel ? (
              <span
                className="px-2 py-0.5 rounded text-[11px] font-semibold text-slate-950"
                style={{ backgroundColor: sectionAccent }}
              >
                {selectedRange.sectionLabel}
              </span>
            ) : null}
          </div>
          <div className="text-xs text-slate-400">{measureLabel}</div>
        </div>
        <div className="flex items-center gap-3">
          <button
            className={`px-3 py-1.5 rounded text-xs font-semibold transition-colors ${
              previewing ? "bg-rose-600/80 text-white" : "bg-cyan-500/20 text-cyan-200 hover:bg-cyan-500/30"
            }`}
            onClick={handlePreview}
          >
            {previewing ? "⏹ Stop" : "▶︎ Play Grid"}
          </button>
        </div>
      </div>

      {!notes.length && !selectedRange && (
        <div className="text-xs text-slate-400 mb-3">
          No drum events yet. Generate drums or click cells to add hits per limb.
        </div>
      )}

      <div className="space-y-2">
        <div className="flex items-start gap-0 pr-2">
          <div className="w-36 flex-shrink-0 border-r border-slate-700">
            <div
              className="h-5 text-[10px] uppercase tracking-wide flex items-center"
              style={{ color: BAR_GRID_THEME.label }}
            >
              Bars
            </div>
            <div className="space-y-3 mt-3">
              {LIMB_ORDER.map((limb) => (
                <div
                  key={limb}
                  className="text-xs font-semibold uppercase tracking-wide flex items-center"
                  style={{ color: LIMB_CONFIG[limb].accentColor, height: limbRowHeightPx }}
                >
                  {LIMB_CONFIG[limb].label}
                </div>
              ))}
            </div>
          </div>

          <div ref={horizontalScrollRef} className="flex-1 min-w-0 overflow-x-auto hide-scrollbar">
            <div className="space-y-3" style={{ width: `${totalWidth}px` }}>
              <div className="relative" style={{ width: `${totalWidth}px`, height: 20 }}>
                {Array.from({ length: totalMeasuresSpan }).map((_, barIdx) => (
                  <div
                    key={`bar-label-${baseStartMeasure + barIdx}`}
                    className="absolute top-0 bottom-0 flex items-center text-[10px]"
                    style={{
                      left: barIdx * measureWidthPx,
                      width: measureWidthPx,
                      color: BAR_GRID_THEME.label,
                      borderLeft: `1px solid ${BAR_GRID_THEME.bar}`,
                      paddingLeft: 4,
                    }}
                  >
                    Bar {baseStartMeasure + barIdx + 1}
                  </div>
                ))}
              </div>

              {LIMB_ORDER.map((limb) => (
                <div key={limb} style={{ height: limbRowHeightPx }}>
                  <div
                    className="relative"
                    style={{
                      width: `${totalWidth}px`,
                      height: limbRowHeightPx,
                      borderRight: `1px solid ${BAR_GRID_THEME.bar}`,
                    }}
                  >
                    {Array.from({ length: totalMeasuresSpan }).map((_, barIdx) => (
                      <div
                        key={`grid-bar-${limb}-${barIdx}`}
                        className="absolute top-0 bottom-0"
                        style={{
                          left: barIdx * measureWidthPx,
                          borderLeft: `1px solid ${BAR_GRID_THEME.bar}`,
                          opacity: 0.9,
                        }}
                      />
                    ))}
                    {Array.from({ length: totalMeasuresSpan }).flatMap((_, barIdx) =>
                      Array.from({ length: stepsPerMeasure }).map((__, subIdx) => {
                        const left = barIdx * measureWidthPx + (measureWidthPx * subIdx) / stepsPerMeasure;
                        const isBeat = subIdx % (stepsPerMeasure / 4 || 1) === 0;
                        const color = isBeat ? BAR_GRID_THEME.beat : BAR_GRID_THEME.subdivision;
                        return (
                          <div
                            key={`grid-sub-${limb}-${barIdx}-${subIdx}`}
                            className="absolute top-0 bottom-0"
                            style={{
                              left,
                              borderLeft: `1px solid ${color}`,
                              opacity: 0.55,
                            }}
                          />
                        );
                      }),
                    )}

                    <div
                      className="grid gap-0 absolute inset-0"
                      style={{
                        gridTemplateColumns: `repeat(${totalSteps}, ${cellWidth}px)`,
                      }}
                    >
                      {Array.from({ length: totalSteps }).map((_, idx) => {
                        const key = `${limb}:${idx}`;
                        const isActive = activeCells.has(key);
                        const accent = LIMB_CONFIG[limb].accentColor;
                        const cellStyle: React.CSSProperties = isActive
                          ? {
                              backgroundColor: accent,
                              color: "#0f172a",
                              boxShadow: `inset 0 0 0 1px ${accent}80`,
                              borderColor: accent,
                            }
                          : {
                              borderColor: "transparent",
                            };
                        return (
                          <button
                            type="button"
                            key={key}
                            onClick={() => toggleCell(limb, idx)}
                            style={{ ...cellStyle, height: limbRowHeightPx }}
                            className={`border text-[10px] flex items-center justify-center select-none transition-colors duration-150 ${
                              isActive
                                ? "font-semibold"
                                : "bg-slate-900/20 border-transparent text-slate-500 hover:border-slate-500/40"
                            }`}
                          >
                            {isActive ? <span className="w-1.5 h-1.5 rounded-full bg-slate-900 block" /> : null}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
