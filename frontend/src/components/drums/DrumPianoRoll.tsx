// frontend/src/components/drums/DrumPianoRoll.tsx

import React, { useMemo, useCallback } from "react";
import {
  DrumTrackForDCSM,
  DrumNoteEvent,
  NoteAspect,
  DrumInstrumentId,
} from "../../types/drumTrack";
import {
  GridResolution,
  getSubdivisionsPerBar,
  getTicksPerSubdivision,
} from "../../utils/pianoRollGrid";
import { GrooveWeightMap } from "../../types/grooveWeight";

interface DrumPianoRollProps {
  drumTrack: DrumTrackForDCSM | null;
  timeSignature: [number, number];
  gridResolution: GridResolution;
  currentAspect: NoteAspect | "all";
  grooveWeights?: GrooveWeightMap;
  onNoteChange?: (notes: DrumNoteEvent[]) => void;
  onNoteSelect?: (noteIds: string[]) => void;
  selectedNoteIds?: string[];
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

export const DrumPianoRoll: React.FC<DrumPianoRollProps> = ({
  drumTrack,
  timeSignature,
  gridResolution,
  currentAspect,
  grooveWeights,
  onNoteChange,
  onNoteSelect,
  selectedNoteIds = [],
}) => {
  if (!drumTrack) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs text-slate-500">
        No drum track generated yet.
      </div>
    );
  }

  const { resolution_ppq, notes } = drumTrack;

  const barCount = useMemo(
    () => (notes.length ? 1 + Math.max(...notes.map((n) => n.barIndex)) : 0),
    [notes]
  );

  const subdivisionsPerBar = getSubdivisionsPerBar(gridResolution);
  const ticksPerSubdivision = getTicksPerSubdivision(
    resolution_ppq,
    timeSignature,
    gridResolution
  );

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
  const barWidthPx = 320; // you can make this zoomable
  const totalWidth = barCount * barWidthPx;

  const notesByInstrument: Record<DrumInstrumentId, DrumNoteEvent[]> = useMemo(
    () => {
      const map: Record<string, DrumNoteEvent[]> = {};
      for (const id of instrumentOrder) map[id] = [];
      for (const n of filteredNotes) {
        const arr = map[n.instrumentId] || (map[n.instrumentId] = []);
        arr.push(n);
      }
      return map as Record<DrumInstrumentId, DrumNoteEvent[]>;
    },
    [filteredNotes]
  );

  return (
    <div className="flex-1 flex flex-col bg-slate-900 text-xs overflow-hidden">
      {/* Header row */}
      <div className="flex flex-row border-b border-slate-700">
        <div className="w-36 flex-shrink-0 border-r border-slate-700 bg-slate-950 px-2 py-1 text-slate-400">
          Instrument
        </div>
        <div className="flex-1 relative overflow-x-auto">
          <div
            className="relative"
            style={{ width: `${totalWidth}px`, height: 24 }}
          >
            {/* Bar labels */}
            {Array.from({ length: barCount }).map((_, barIdx) => (
              <div
                key={barIdx}
                className="absolute top-0 h-full border-r border-slate-700 text-[10px] text-slate-400 flex items-center"
                style={{
                  left: barIdx * barWidthPx,
                  width: barWidthPx,
                  paddingLeft: 4,
                }}
              >
                Bar {barIdx + 1}
              </div>
            ))}

            {/* Subdivision grid + groove weights */}
            {Array.from({ length: barCount }).map((_, barIdx) =>
              Array.from({ length: subdivisionsPerBar }).map((__, subIdx) => {
                const left =
                  barIdx * barWidthPx +
                  (barWidthPx * subIdx) / subdivisionsPerBar;

                const weight =
                  grooveWeights?.[barIdx]?.[subIdx]?.weight ?? "neutral";

                let lineClass = "border-slate-800";
                if (subIdx % (subdivisionsPerBar / 4) === 0) {
                  lineClass = "border-slate-600";
                }
                if (weight === "heavy") {
                  lineClass = "border-slate-400";
                } else if (weight === "syncopated") {
                  lineClass = "border-amber-500/80";
                }

                return (
                  <div
                    key={`${barIdx}-${subIdx}`}
                    className={`absolute top-0 bottom-0 border-l ${lineClass}`}
                    style={{ left }}
                  />
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-row flex-1 overflow-hidden">
        {/* Instrument labels */}
        <div className="w-36 flex-shrink-0 bg-slate-950 border-r border-slate-700">
          {instrumentOrder.map((instId) => (
            <div
              key={instId}
              className="h-5 flex items-center px-2 text-[11px] text-slate-200 border-b border-slate-800"
            >
              {instId.replace("_", " ")}
            </div>
          ))}
        </div>

        {/* Note lanes */}
        <div className="flex-1 relative overflow-x-auto overflow-y-hidden">
          <div
            className="relative"
            style={{
              width: `${totalWidth}px`,
              height: instrumentOrder.length * laneHeight,
            }}
          >
            {/* Horizontal lines */}
            {instrumentOrder.map((instId, laneIdx) => (
              <div
                key={instId}
                className="absolute left-0 right-0 border-b border-slate-800"
                style={{ top: laneIdx * laneHeight, height: laneHeight }}
              />
            ))}

            {/* Notes */}
            {instrumentOrder.map((instId, laneIdx) => {
              const laneNotes = notesByInstrument[instId] || [];
              return laneNotes.map((n) => {
                const barX = n.barIndex * barWidthPx;
                const fracInBar =
                  n.tickInBar / (resolution_ppq * timeSignature[0]);
                const x = barX + fracInBar * barWidthPx;
                const w = Math.max(
                  4,
                  (barWidthPx * (n.tickLength / (resolution_ppq * timeSignature[0])))
                );
                const y = laneIdx * laneHeight + 2;
                const h = laneHeight - 4;

                const selected = selectedNoteIds.includes(n.id);

                let bgClass = "bg-slate-500";
                if (n.isGhost) bgClass = "bg-slate-500/70";
                if (n.isAccent) bgClass = "bg-amber-500";
                if (n.aspect === "fill") bgClass = "bg-purple-500";
                if (n.locked) bgClass += " ring-2 ring-emerald-400/80";

                return (
                  <div
                    key={n.id}
                    className={`absolute rounded-sm cursor-pointer ${bgClass} ${
                      selected ? "outline outline-1 outline-white" : ""
                    }`}
                    style={{ left: x, top: y, width: w, height: h }}
                    onClick={(ev) => handleNoteClick(n, ev)}
                    title={`${instId} @ bar ${n.barIndex + 1}`}
                  />
                );
              });
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
