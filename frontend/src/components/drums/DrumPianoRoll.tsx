// frontend/src/components/drums/DrumPianoRoll.tsx

import React, { useMemo, useCallback, useEffect, useState, useRef } from "react";
import {
  DrumTrackForDCSM,
  DrumNoteEvent,
  NoteAspect,
  DrumInstrumentId,
} from "../../types/drumTrack";
import type { DrumPlayerChannelId, DrumPlayerEngine } from "../../audio/drumPlayerEngine";
import { getMidiPitchForInstrument } from "../../utils/drumTrackUtils";
import {
  GridResolution,
  getSubdivisionsPerBar,
  getTicksPerSubdivision,
} from "../../utils/pianoRollGrid";
import { GrooveWeightMap } from "../../types/grooveWeight";
import { LIMB_CONFIG, inferLimbFromInstrument, type LimbId } from "../../constants/limbs";
import { BAR_GRID_THEME } from "../../constants/barGrid";
import { getInstrumentForMidiPitch } from "../../utils/drumTrackUtils";

const SUPPORTED_LIMBS: readonly LimbId[] = ["RH", "LH", "RF", "LF"];

export type DrumSectionRegion = {
  id: string;
  label: string;
  startBar: number;
  endBar: number;
  color?: string;
};

interface DrumPianoRollProps {
  drumTrack: DrumTrackForDCSM | null;
  timeSignature: [number, number];
  bpm?: number;
  playheadSeconds?: number;
  playing?: boolean;
  gridResolution: GridResolution;
  currentAspect: NoteAspect | "all";
  grooveWeights?: GrooveWeightMap;
  onNoteChange?: (notes: DrumNoteEvent[]) => void;
  onNoteSelect?: (noteIds: string[]) => void;
  selectedNoteIds?: string[];
  scrollContainerRef?: React.RefObject<HTMLDivElement>;
  pixelsPerBeat: number;
  visibleStartMeasure?: number;
  visibleMeasureCount?: number;
  totalSongBars?: number;
  drumEngine?: DrumPlayerEngine | null;
  sectionRegions?: DrumSectionRegion[];
}

function getSectionOverlayColor(label?: string | null): string {
  const v = (label || "").toLowerCase();
  if (v.includes("verse")) return "#3b82f6";
  if (v.includes("chorus")) return "#22c55e";
  if (v.includes("bridge")) return "#a855f7";
  if (v.includes("intro")) return "#f97316";
  if (v.includes("outro")) return "#ef4444";
  return "#64748b";
}

function mapInstrumentToChannel(instId: DrumInstrumentId): DrumPlayerChannelId | null {
  switch (instId) {
    case "kick":
      return "kick";
    case "snare_center":
    case "snare_ghost":
    case "snare_rim":
      return "snare_top";
    case "hihat_closed":
    case "hihat_open":
    case "hihat_pedal":
      return "hat";
    case "ride_bow":
    case "ride_bell":
    case "ride_edge":
      return "ride";
    case "tom_high":
      return "tom1";
    case "tom_mid":
      return "tom3";
    case "tom_floor":
      return "tom5";
    case "crash_1":
    case "crash_2":
      return "crash";
    default:
      return null;
  }
}

const instrumentOrder: DrumInstrumentId[] = [
  "kick",
  "snare_center",
  "snare_ghost",
  "snare_rim",
  "hihat_closed",
  "hihat_open",
  "hihat_pedal",
  "ride_bow",
  "ride_bell",
  "ride_edge",
  "tom_high",
  "tom_mid",
  "tom_floor",
  "crash_1",
  "crash_2",
];

const limbLaneOrder: readonly LimbId[] = ["RH", "LH", "RF", "LF"] as const;

const DEFAULT_LIMB_INSTRUMENT: Record<(typeof limbLaneOrder)[number], DrumInstrumentId> = {
  RH: "hihat_closed",
  LH: "snare_center",
  RF: "kick",
  LF: "hihat_pedal",
};

const inferLimbFromMidiPitch = (pitch?: number | null): LimbId | null => {
  if (typeof pitch !== "number" || !Number.isFinite(pitch)) {
    return null;
  }
  const p = Math.round(pitch);
  // Common GM drum pitches
  if (p === 36 || p === 35) return "RF"; // kick
  if (p === 38 || p === 40 || p === 37) return "LH"; // snare / rim
  if (p === 44) return "LF"; // pedal hat
  if (p === 42 || p === 46 || p === 45) return "RH"; // hats
  if (p === 49 || p === 57 || p === 51 || p === 59 || p === 55 || p === 52) return "RH"; // cymbals
  if (p === 41 || p === 43 || p === 47 || p === 48 || p === 50) return "LH"; // toms
  return null;
};

export const DrumPianoRoll: React.FC<DrumPianoRollProps> = ({
  drumTrack,
  timeSignature,
  bpm,
  playheadSeconds,
  playing,
  gridResolution,
  currentAspect,
  grooveWeights,
  onNoteChange,
  onNoteSelect,
  selectedNoteIds = [],
  scrollContainerRef,
  pixelsPerBeat,
  visibleStartMeasure,
  visibleMeasureCount,
  totalSongBars,
  drumEngine,
  sectionRegions,
}) => {
  if (!drumTrack) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs text-slate-500">
        No drum track generated yet.
      </div>
    );
  }

  const headerScrollRef = useRef<HTMLDivElement | null>(null);
  const laneScrollRef = useRef<HTMLDivElement | null>(null);

  const [laneChannelState, setLaneChannelState] = useState<
    Record<string, { mute: boolean; solo: boolean }>
  >({});

  useEffect(() => {
    if (!drumEngine) {
      setLaneChannelState({});
      return;
    }

    const update = () => {
      try {
        const next: Record<string, { mute: boolean; solo: boolean }> = {};
        for (const instId of instrumentOrder) {
          const channelId = mapInstrumentToChannel(instId);
          if (!channelId) continue;
          const p = drumEngine.getChannelParams(channelId);
          next[instId] = { mute: Boolean(p.mute), solo: Boolean(p.solo) };
        }
        setLaneChannelState(next);
      } catch {
        setLaneChannelState({});
      }
    };

    update();
    const interval = window.setInterval(update, 200);
    return () => window.clearInterval(interval);
  }, [drumEngine]);

  const { resolution_ppq, notes } = drumTrack;

  const trackBarCount = useMemo(
    () => (notes.length ? 1 + Math.max(...notes.map((n) => n.barIndex ?? 0)) : 0),
    [notes]
  );

  const subdivisionsPerBar = getSubdivisionsPerBar(gridResolution);
  const ticksPerSubdivision = getTicksPerSubdivision(
    resolution_ppq,
    timeSignature,
    gridResolution
  );
  const beatsPerBar = timeSignature[0];
  const ticksPerBar = resolution_ppq * beatsPerBar;
  const barWidthPx = pixelsPerBeat * beatsPerBar;

  const [scrollLeft, setScrollLeft] = useState(0);

  const totalBarsSpan = totalSongBars ?? Math.max(trackBarCount || 1, 1);
  const totalWidth = Math.max(1, totalBarsSpan * barWidthPx);

  const normalizedSectionRegions = useMemo(() => {
    const regions = Array.isArray(sectionRegions) ? sectionRegions : [];
    return regions
      .map((r) => {
        const startBar = Math.max(0, Math.min(totalBarsSpan - 1, Math.floor(r.startBar ?? 0)));
        const endBar = Math.max(startBar, Math.min(totalBarsSpan - 1, Math.floor(r.endBar ?? startBar)));
        const label = (r.label || "Section").toString();
        const color = (r.color || getSectionOverlayColor(label)).toString();
        return {
          id: (r.id || `${label}-${startBar}-${endBar}`).toString(),
          label,
          startBar,
          endBar,
          color,
        };
      })
      .filter((r) => Number.isFinite(r.startBar) && Number.isFinite(r.endBar) && r.endBar >= r.startBar);
  }, [sectionRegions, totalBarsSpan]);

  const playheadX = useMemo(() => {
    const playSec = typeof playheadSeconds === "number" && Number.isFinite(playheadSeconds) ? playheadSeconds : null;
    const tempo = typeof bpm === "number" && Number.isFinite(bpm) && bpm > 0 ? bpm : null;
    if (playSec === null || tempo === null) return null;
    const beats = (playSec * tempo) / 60;
    if (!Number.isFinite(beats) || beats < 0) return null;
    return beats * pixelsPerBeat;
  }, [bpm, pixelsPerBeat, playheadSeconds]);

  const clampedPlayheadX = useMemo(() => {
    if (playheadX === null) return null;
    const maxX = Math.max(0, totalWidth - 2);
    return Math.max(0, Math.min(maxX, playheadX));
  }, [playheadX, totalWidth]);

  useEffect(() => {
    if (!playing) return;
    if (clampedPlayheadX === null) return;
    const laneEl = laneScrollRef.current;
    if (!laneEl) return;

    const viewLeft = laneEl.scrollLeft;
    const viewRight = viewLeft + laneEl.clientWidth;
    const margin = Math.max(32, laneEl.clientWidth * 0.2);

    if (clampedPlayheadX < viewLeft + margin || clampedPlayheadX > viewRight - margin) {
      const target = Math.max(0, clampedPlayheadX - laneEl.clientWidth * 0.35);
      laneEl.scrollLeft = target;
    }
  }, [clampedPlayheadX, playing]);

  const fallbackStartBar = Math.max(0, visibleStartMeasure ?? 0);
  const viewStartBar = useMemo(() => {
    const derived = barWidthPx > 0 ? Math.floor(scrollLeft / barWidthPx) : 0;
    return Math.max(0, Number.isFinite(derived) ? derived : fallbackStartBar);
  }, [barWidthPx, fallbackStartBar, scrollLeft]);

  const viewBarCount = useMemo(() => {
    const viewportPx = laneScrollRef.current?.clientWidth ?? 0;
    if (!Number.isFinite(viewportPx) || viewportPx <= 0 || !Number.isFinite(barWidthPx) || barWidthPx <= 0) {
      const available = Math.max(1, trackBarCount - fallbackStartBar);
      return Math.max(1, visibleMeasureCount ?? available);
    }
    const barsInView = Math.ceil(viewportPx / barWidthPx) + 2;
    const desired = Math.max(1, barsInView);
    return Number.isFinite(visibleMeasureCount) ? Math.max(desired, visibleMeasureCount!) : desired;
  }, [barWidthPx, fallbackStartBar, trackBarCount, visibleMeasureCount]);

  const windowStartBar = viewStartBar;
  const renderStartBar = Math.max(0, windowStartBar - 1);
  const renderEndBar = windowStartBar + viewBarCount + 1;

  const filteredNotes = useMemo(() => {
    if (currentAspect === "all") return notes;
    return notes.filter((n) => n.aspect === currentAspect);
  }, [notes, currentAspect]);

  const handleNoteClick = useCallback(
    (note: DrumNoteEvent, ev: React.MouseEvent) => {
      ev.stopPropagation();
      if (!onNoteSelect) return;
      if (ev.shiftKey) {
        onNoteSelect([...selectedNoteIds, note.id]);
      } else {
        onNoteSelect([note.id]);
      }
    },
    [onNoteSelect, selectedNoteIds]
  );

  const laneHeight = 20;
  const limbLaneHeight = 18;
  const limbAccentForInstrument = useCallback((instrumentId: string): { limb: LimbId | null; accent?: string } => {
    const limb = inferLimbFromInstrument(instrumentId);
    return {
      limb,
      accent: limb ? LIMB_CONFIG[limb].accentColor : undefined,
    };
  }, []);

  const supportedLimb = useCallback((raw?: DrumNoteEvent["limbId"] | null): LimbId | null => {
    if (!raw) return null;
    const v = String(raw);
    if (v === "LS") return "LH";
    if (v === "RS") return "RH";
    return SUPPORTED_LIMBS.includes(v as LimbId) ? (v as LimbId) : null;
  }, []);

  const limbAccentForNote = useCallback((note: DrumNoteEvent): { limb: LimbId | null; accent?: string } => {
    const direct = supportedLimb(note.limbId);
    const pitchFallback = inferLimbFromMidiPitch(note.midiPitch);
    const inferredInstrument = note.instrumentId
      ? note.instrumentId
      : typeof note.midiPitch === "number"
        ? getInstrumentForMidiPitch(note.midiPitch)
        : null;
    const fallback = inferredInstrument ? inferLimbFromInstrument(inferredInstrument) : null;
    const limb = direct ?? fallback ?? pitchFallback;
    return {
      limb,
      accent: limb ? LIMB_CONFIG[limb].accentColor : undefined,
    };
  }, [supportedLimb]);

  const limbForNote = useCallback(
    (note: DrumNoteEvent): LimbId | null => {
      const direct = supportedLimb(note.limbId);
      if (direct) return direct;

      const pitchFallback = inferLimbFromMidiPitch(note.midiPitch);
      if (pitchFallback && limbLaneOrder.includes(pitchFallback)) {
        return pitchFallback;
      }

      const inferredInstrument = note.instrumentId
        ? note.instrumentId
        : typeof note.midiPitch === "number"
          ? getInstrumentForMidiPitch(note.midiPitch)
          : null;
      if (inferredInstrument) {
        const inferred = inferLimbFromInstrument(inferredInstrument);
        if (inferred && limbLaneOrder.includes(inferred)) {
          return inferred;
        }
      }
      return null;
    },
    [supportedLimb],
  );

  const limbNotesByLimb: Record<LimbId, DrumNoteEvent[]> = useMemo(() => {
    const map: Record<string, DrumNoteEvent[]> = {};
    for (const limb of limbLaneOrder) {
      map[limb] = [];
    }
    for (const n of filteredNotes) {
      const limb = limbForNote(n);
      if (!limb || !limbLaneOrder.includes(limb)) {
        continue;
      }
      map[limb].push(n);
    }
    return map as Record<LimbId, DrumNoteEvent[]>;
  }, [filteredNotes, limbForNote]);

  const toggleLimbHit = useCallback(
    (limb: LimbId, ev: React.MouseEvent) => {
      if (!onNoteChange) return;
      const laneEl = laneScrollRef.current;
      if (!laneEl) return;

      const rect = laneEl.getBoundingClientRect();
      const xPx = ev.clientX - rect.left + laneEl.scrollLeft;
      if (!Number.isFinite(xPx) || xPx < 0) return;

      const barIndex = Math.max(0, Math.floor(xPx / Math.max(1, barWidthPx)));
      const inBarPx = xPx - barIndex * barWidthPx;
      const cellPx = barWidthPx / Math.max(1, subdivisionsPerBar);
      const subIdx = Math.max(0, Math.min(subdivisionsPerBar - 1, Math.floor(inBarPx / Math.max(1, cellPx))));
      const tickInBar = Math.max(0, Math.round(subIdx * ticksPerSubdivision));
      const tickTolerance = Math.max(1, Math.floor(ticksPerSubdivision / 2));

      const existingIdx = notes.findIndex((n) => {
        const nLimb = limbForNote(n);
        if (nLimb !== limb) return false;
        if ((n.barIndex ?? 0) !== barIndex) return false;
        return Math.abs((n.tickInBar ?? 0) - tickInBar) <= tickTolerance;
      });

      if (existingIdx >= 0) {
        const next = notes.filter((_, idx) => idx !== existingIdx);
        onNoteChange(next);
        return;
      }

      const instrumentId = DEFAULT_LIMB_INSTRUMENT[limb] ?? "snare_center";
      const midiPitch = getMidiPitchForInstrument(instrumentId);
      const id = `limb-${limb}-${barIndex}-${tickInBar}-${Math.random().toString(36).slice(2, 7)}`;
      const velocity = 100;
      const aspect = currentAspect === "all" ? "groove" : (currentAspect as NoteAspect);

      const newNote: DrumNoteEvent = {
        id,
        barIndex,
        tickInBar,
        tickLength: Math.max(1, Math.round(ticksPerSubdivision * 0.95)),
        channel: 9,
        midiPitch,
        velocity,
        instrumentId,
        aspect,
        limbId: limb,
        isGhost: false,
        isAccent: false,
        isFlam: false,
        isDrag: false,
      };

      onNoteChange([...notes, newNote]);
      if (onNoteSelect) {
        onNoteSelect([id]);
      }
    },
    [
      barWidthPx,
      currentAspect,
      limbForNote,
      notes,
      onNoteChange,
      onNoteSelect,
      subdivisionsPerBar,
      supportedLimb,
      ticksPerSubdivision,
    ],
  );

  const notesByInstrument: Record<DrumInstrumentId, DrumNoteEvent[]> = useMemo(
    () => {
      const map: Record<string, DrumNoteEvent[]> = {};
      for (const id of instrumentOrder) map[id] = [];
      for (const n of filteredNotes) {
        const instrumentIdRaw = (n.instrumentId || "").toString();
        const hasLane = instrumentOrder.includes(instrumentIdRaw as DrumInstrumentId);
        const inferred =
          hasLane && instrumentIdRaw !== "other"
            ? (instrumentIdRaw as DrumInstrumentId)
            : typeof n.midiPitch === "number"
              ? getInstrumentForMidiPitch(n.midiPitch)
              : "other";
        const key = (inferred || "other") as DrumInstrumentId;
        const arr = map[key] || (map[key] = []);
        arr.push(n);
      }
      return map as Record<DrumInstrumentId, DrumNoteEvent[]>;
    },
    [filteredNotes]
  );

  React.useEffect(() => {
    const headerEl = headerScrollRef.current;
    const laneEl = laneScrollRef.current;
    if (!laneEl || !headerEl) {
      return;
    }
    const syncHeader = () => {
      headerEl.scrollLeft = laneEl.scrollLeft;
    };
    laneEl.addEventListener("scroll", syncHeader, { passive: true });
    return () => {
      laneEl.removeEventListener("scroll", syncHeader);
    };
  }, [totalBarsSpan]);

  useEffect(() => {
    const laneEl = laneScrollRef.current;
    if (!laneEl) return;
    const update = () => setScrollLeft(laneEl.scrollLeft);
    update();
    laneEl.addEventListener("scroll", update, { passive: true });
    return () => laneEl.removeEventListener("scroll", update);
  }, [drumTrack?.track_id, barWidthPx]);

  React.useEffect(() => {
    if (scrollContainerRef) {
      scrollContainerRef.current = laneScrollRef.current;
    }
    return () => {
      if (scrollContainerRef && scrollContainerRef.current === laneScrollRef.current) {
        scrollContainerRef.current = null;
      }
    };
  }, [scrollContainerRef, drumTrack?.track_id]);

  return (
    <div className="flex-1 min-w-0 flex flex-col bg-slate-900 text-xs overflow-hidden">
      {/* Header row */}
      <div className="flex flex-row border-b border-slate-700 min-w-0">
        <div className="w-36 flex-shrink-0 border-r border-slate-700 bg-slate-950 px-2 py-1 text-slate-400">
          Instrument
        </div>
        <div className="flex-1 min-w-0 relative overflow-x-auto" ref={headerScrollRef}>
          <div
            className="relative"
            style={{ width: `${totalWidth}px`, height: 24 }}
          >
            {normalizedSectionRegions.map((r) => {
              const left = r.startBar * barWidthPx;
              const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
              return (
                <div
                  key={`section-hdr-${r.id}`}
                  className="absolute top-0 bottom-0"
                  style={{
                    left,
                    width,
                    background: r.color,
                    opacity: 0.10,
                    pointerEvents: "none",
                    zIndex: 1,
                  }}
                />
              );
            })}
            {/* Bar labels */}
            {Array.from({ length: totalBarsSpan }).map((_, barIdx) => (
              <div
                key={`bar-label-${barIdx}`}
                className="absolute top-0 h-full flex items-center text-[10px]"
                style={{
                  left: barIdx * barWidthPx,
                  width: barWidthPx,
                  paddingLeft: 4,
                  borderRight: `1px solid ${BAR_GRID_THEME.bar}`,
                  color: BAR_GRID_THEME.label,
                }}
              >
                {barIdx + 1}
              </div>
            ))}

            {normalizedSectionRegions.map((r) => {
              const left = r.startBar * barWidthPx;
              const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
              return (
                <div
                  key={`section-label-${r.id}`}
                  className="absolute top-0 h-full flex items-center"
                  style={{
                    left: left + 18,
                    width: Math.max(1, width - 24),
                    color: r.color,
                    opacity: 0.95,
                    pointerEvents: "none",
                    zIndex: 3,
                    fontSize: 10,
                    fontWeight: 700,
                    textShadow: "0 1px 0 rgba(0,0,0,0.6)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {r.label}
                </div>
              );
            })}

            {/* Subdivision grid + groove weights */}
            {Array.from({ length: totalBarsSpan }).map((_, barIdx) =>
              Array.from({ length: subdivisionsPerBar }).map((__, subIdx) => {
                const left =
                  barIdx * barWidthPx +
                  (barWidthPx * subIdx) / subdivisionsPerBar;

                const weight =
                  grooveWeights?.[barIdx]?.[subIdx]?.weight ?? "neutral";
                let color = BAR_GRID_THEME.subdivision;
                if (subIdx % (subdivisionsPerBar / 4 || 1) === 0) {
                  color = BAR_GRID_THEME.beat;
                }
                if (weight === "heavy") {
                  color = BAR_GRID_THEME.bar;
                } else if (weight === "syncopated") {
                  color = BAR_GRID_THEME.accent;
                }

                return (
                  <div
                    key={`${barIdx}-${subIdx}`}
                    className="absolute top-0 bottom-0"
                    style={{
                      left,
                      borderLeft: `1px solid ${color}`,
                      opacity: 0.8,
                    }}
                  />
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-row flex-1 overflow-hidden min-w-0">
        {/* Instrument labels */}
        <div className="w-36 flex-shrink-0 bg-slate-950 border-r border-slate-700">
          {instrumentOrder.map((instId) => {
            const { accent } = limbAccentForInstrument(instId);
            const channelId = mapInstrumentToChannel(instId);
            const chState = laneChannelState[instId] || { mute: false, solo: false };
            return (
              <div
                key={instId}
                className="h-5 flex items-center justify-between gap-2 px-2 text-[11px] font-semibold border-b border-transparent"
                style={{
                  color: accent || "#e2e8f0",
                  backgroundColor: accent ? `${accent}1a` : undefined,
                  borderColor: accent ? `${accent}66` : undefined,
                }}
              >
                <span className="min-w-0 flex-1 truncate">{instId.replace("_", " ")}</span>
                {drumEngine && channelId && (
                  <span className="flex items-center gap-1">
                    <button
                      type="button"
                      className={
                        "w-5 h-4 rounded border text-[9px] leading-none " +
                        (chState.solo
                          ? "bg-yellow-500/80 border-yellow-300 text-black"
                          : "bg-slate-900 border-slate-700 text-slate-300")
                      }
                      onClick={() => {
                        const next = !chState.solo;
                        drumEngine.setChannelParams(channelId, { solo: next });
                        setLaneChannelState((prev) => ({
                          ...prev,
                          [instId]: { ...chState, solo: next },
                        }));
                      }}
                      title="Solo"
                    >
                      S
                    </button>
                    <button
                      type="button"
                      className={
                        "w-5 h-4 rounded border text-[9px] leading-none " +
                        (chState.mute
                          ? "bg-red-600/80 border-red-300 text-white"
                          : "bg-slate-900 border-slate-700 text-slate-300")
                      }
                      onClick={() => {
                        const next = !chState.mute;
                        drumEngine.setChannelParams(channelId, { mute: next });
                        setLaneChannelState((prev) => ({
                          ...prev,
                          [instId]: { ...chState, mute: next },
                        }));
                      }}
                      title="Mute"
                    >
                      M
                    </button>
                  </span>
                )}
              </div>
            );
          })}

          <div className="h-1" />
          {limbLaneOrder.map((limb) => (
            <div
              key={`limb-label-${limb}`}
              className="flex items-center px-2 text-[11px] font-semibold border-t border-slate-800"
              style={{ height: limbLaneHeight, color: LIMB_CONFIG[limb].accentColor }}
            >
              {LIMB_CONFIG[limb].label}
            </div>
          ))}
        </div>

        {/* Note lanes */}
        <div
          className="flex-1 min-w-0 relative overflow-x-auto overflow-y-hidden"
          ref={laneScrollRef}
        >
          <div
            className="relative"
            style={{
              width: `${totalWidth}px`,
              height: instrumentOrder.length * laneHeight + limbLaneOrder.length * limbLaneHeight,
            }}
          >
            {normalizedSectionRegions.map((r) => {
              const left = r.startBar * barWidthPx;
              const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
              return (
                <div
                  key={`section-lane-${r.id}`}
                  className="absolute top-0 bottom-0"
                  style={{
                    left,
                    width,
                    background: r.color,
                    opacity: 0.08,
                    pointerEvents: "none",
                    zIndex: 0,
                  }}
                />
              );
            })}
            {clampedPlayheadX !== null && (
              <div
                className="absolute top-0 bottom-0"
                style={{
                  left: clampedPlayheadX,
                  width: 2,
                  background: "rgba(34, 211, 238, 0.8)",
                  boxShadow: "0 0 8px rgba(34, 211, 238, 0.6)",
                  pointerEvents: "none",
                  zIndex: 20,
                }}
              />
            )}
            {Array.from({ length: totalBarsSpan + 1 }).map((_, barIdx) => (
              <div
                key={`lane-grid-bar-${barIdx}`}
                className="absolute top-0 bottom-0"
                style={{
                  left: barIdx * barWidthPx,
                  borderLeft: `1px solid ${BAR_GRID_THEME.bar}`,
                  opacity: 0.7,
                  pointerEvents: "none",
                }}
              />
            ))}
            {Array.from({ length: totalBarsSpan }).flatMap((_, barIdx) =>
              Array.from({ length: subdivisionsPerBar }).map((__, subIdx) => {
                const left = barIdx * barWidthPx + (barWidthPx * subIdx) / subdivisionsPerBar;
                const isBeat = subIdx % (subdivisionsPerBar / 4 || 1) === 0;
                const color = isBeat ? BAR_GRID_THEME.beat : BAR_GRID_THEME.subdivision;
                return (
                  <div
                    key={`lane-grid-sub-${barIdx}-${subIdx}`}
                    className="absolute top-0 bottom-0"
                    style={{
                      left,
                      borderLeft: `1px solid ${color}`,
                      opacity: 0.35,
                      pointerEvents: "none",
                    }}
                  />
                );
              }),
            )}

            {/* Horizontal lines */}
            {instrumentOrder.map((instId, laneIdx) => (
              <div
                key={instId}
                className="absolute left-0 right-0 border-b border-slate-800"
                style={{ top: laneIdx * laneHeight, height: laneHeight }}
              />
            ))}

            {limbLaneOrder.map((limb, idx) => (
              <div
                key={`limb-row-${limb}`}
                className="absolute left-0 right-0 border-t border-slate-800"
                style={{
                  top: instrumentOrder.length * laneHeight + idx * limbLaneHeight,
                  height: limbLaneHeight,
                }}
              />
            ))}

            {/* Notes */}
            {instrumentOrder.map((instId, laneIdx) => {
              const laneNotes = notesByInstrument[instId] || [];
              return laneNotes.map((n) => {
                const noteBar = n.barIndex ?? 0;
                if (noteBar < renderStartBar || noteBar > renderEndBar) {
                  return null;
                }

                const fracInBar = (n.tickInBar ?? 0) / ticksPerBar;
                const x = noteBar * barWidthPx + fracInBar * barWidthPx;
                const w = Math.max(
                  4,
                  barWidthPx * ((n.tickLength ?? ticksPerSubdivision) / ticksPerBar)
                );
                const y = laneIdx * laneHeight + 2;
                const h = laneHeight - 4;

                const selected = selectedNoteIds.includes(n.id);
                const { accent, limb } = limbAccentForNote(n);
                let backgroundColor = accent ? `${accent}d0` : "#64748b";
                if (n.isGhost) backgroundColor = accent ? `${accent}66` : "#94a3b8";
                else if (n.isAccent) backgroundColor = accent ? `${accent}ff` : "#fbbf24";
                else if (n.aspect === "fill") backgroundColor = accent ? `${accent}b3` : "#a855f7";
                const borderColor = accent ? `${accent}a0` : "transparent";
                const limbLabel = limb ? LIMB_CONFIG[limb].label : "Unassigned";
                return (
                  <div
                    key={n.id}
                    className={`absolute rounded-sm cursor-pointer border ${
                      selected ? "outline outline-1 outline-white" : ""
                    } ${n.locked ? "ring-2 ring-emerald-400/80" : ""}`}
                    style={{
                      left: x,
                      top: y,
                      width: w,
                      height: h,
                      backgroundColor,
                      borderColor,
                      color: accent ? "#0f172a" : undefined,
                    }}
                    onClick={(ev) => handleNoteClick(n, ev)}
                    title={`${instId} · ${limbLabel} @ bar ${noteBar + 1}`}
                  />
                );
              });
            })}

            {limbLaneOrder.map((limb, limbIdx) => {
              const laneNotes = limbNotesByLimb[limb] || [];
              const y = 1;
              const h = limbLaneHeight - 2;
              const accent = LIMB_CONFIG[limb].accentColor;
              return (
                <div
                  key={`limb-lane-${limb}`}
                  className="absolute left-0 right-0"
                  style={{
                    top: instrumentOrder.length * laneHeight + limbIdx * limbLaneHeight,
                    height: limbLaneHeight,
                  }}
                  onClick={(ev) => toggleLimbHit(limb, ev)}
                >
                  {laneNotes.map((n) => {
                    const noteBar = n.barIndex ?? 0;
                    if (noteBar < renderStartBar || noteBar > renderEndBar) {
                      return null;
                    }
                    const fracInBar = (n.tickInBar ?? 0) / ticksPerBar;
                    const x = noteBar * barWidthPx + fracInBar * barWidthPx;
                    const w = Math.max(4, barWidthPx * ((n.tickLength ?? ticksPerSubdivision) / ticksPerBar));
                    const selected = selectedNoteIds.includes(n.id);
                    return (
                      <div
                        key={`limb-hit-${n.id}`}
                        className={`absolute rounded-sm border ${selected ? "outline outline-1 outline-white" : ""}`}
                        style={{
                          left: x,
                          top: y,
                          width: w,
                          height: h,
                          backgroundColor: `${accent}cc`,
                          borderColor: `${accent}aa`,
                          pointerEvents: "none",
                        }}
                      />
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
