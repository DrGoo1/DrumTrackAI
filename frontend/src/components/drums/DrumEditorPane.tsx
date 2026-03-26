// frontend/src/components/drums/DrumEditorPane.tsx

import React, { useEffect, useState } from "react";
import {
  DrumTrackForDCSM,
  DrumNoteEvent,
  NoteAspect,
} from "../../types/drumTrack";
import { DrumPianoRoll, type DrumSectionRegion } from "./DrumPianoRoll";
import { NoteInspector } from "./NoteInspector";
import { GridResolution } from "../../utils/pianoRollGrid";
import { GrooveWeightMap } from "../../types/grooveWeight";
import type { DrumPlayerEngine } from "../../audio/drumPlayerEngine";

interface DrumEditorPaneProps {
  drumTrack: DrumTrackForDCSM | null;
  timeSignature: [number, number];
  grooveWeights?: GrooveWeightMap;
  gridResolution: GridResolution;
  onGridResolutionChange: (resolution: GridResolution) => void;
  onUpdateTrack?: (track: DrumTrackForDCSM) => void;
  pianoRollScrollRef?: React.RefObject<HTMLDivElement>;
  pixelsPerBeat: number;
  bpm?: number;
  tempoMap?: Array<{ tSec: number; bpm: number }>;
  beatTimes?: number[];
  playheadSeconds?: number;
  playing?: boolean;
  selectedBarIndex?: number | null;
  onBarSelect?: (barIndex: number | null) => void;
  visibleStartMeasure?: number;
  visibleMeasureCount?: number;
  totalSongBars?: number;
  barDirectives?: Record<number, { forceFill?: boolean; suppressFill?: boolean }>;
  drumEngine?: DrumPlayerEngine | null;
  sectionRegions?: DrumSectionRegion[];
  selectedSectionIds?: Set<string> | string[];
  onSectionSelect?: (sectionId: string) => void;
}

export const DrumEditorPane: React.FC<DrumEditorPaneProps> = ({
  drumTrack,
  timeSignature,
  grooveWeights,
  gridResolution,
  onGridResolutionChange,
  onUpdateTrack,
  pianoRollScrollRef,
  pixelsPerBeat,
  bpm,
  tempoMap,
  beatTimes,
  playheadSeconds,
  playing,
  selectedBarIndex,
  onBarSelect,
  visibleStartMeasure,
  visibleMeasureCount,
  totalSongBars,
  barDirectives,
  drumEngine,
  sectionRegions,
  selectedSectionIds,
  onSectionSelect,
}) => {
  const [currentAspect, setCurrentAspect] =
    useState<NoteAspect | "all">("all");
  const [selectedNoteIds, setSelectedNoteIds] = useState<string[]>([]);

  const selectedNotes: DrumNoteEvent[] =
    drumTrack?.notes.filter((n) => selectedNoteIds.includes(n.id)) ?? [];

  useEffect(() => {
    setSelectedNoteIds([]);
  }, [drumTrack?.track_id]);

  const handleNoteChange = (patch: Partial<DrumNoteEvent>) => {
    if (!drumTrack || !onUpdateTrack || selectedNoteIds.length === 0) return;
    const newNotes = drumTrack.notes.map((n) =>
      selectedNoteIds.includes(n.id) && !n.locked ? { ...n, ...patch } : n
    );
    onUpdateTrack({ ...drumTrack, notes: newNotes });
  };

  return (
    <div className="relative flex flex-col h-full min-w-0 overflow-hidden">
        {/* Aspect + Grid controls */}
        <div className="flex items-center justify-between px-2 py-1 bg-slate-950 border-b border-slate-800 text-[11px] text-slate-200">
          <div className="flex items-center gap-2">
            <span className="uppercase text-[10px] tracking-wide text-slate-400">
              View
            </span>
            {(["all", "groove", "accent", "fill"] as const).map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setCurrentAspect(opt)}
                className={`px-2 py-0.5 rounded border ${
                  currentAspect === opt
                    ? "bg-slate-700 border-slate-500"
                    : "bg-slate-900 border-slate-800 text-slate-400"
                }`}
              >
                {opt.toUpperCase()}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="uppercase text-[10px] tracking-wide text-slate-400">
              Grid
            </span>
            {(["16th", "32nd", "64th"] as GridResolution[]).map((res) => (
              <button
                key={res}
                type="button"
                onClick={() => onGridResolutionChange(res)}
                className={`px-2 py-0.5 rounded border ${
                  gridResolution === res
                    ? "bg-slate-700 border-slate-500"
                    : "bg-slate-900 border-slate-800 text-slate-400"
                }`}
              >
                {res}
              </button>
            ))}
          </div>
        </div>

        <DrumPianoRoll
          drumTrack={drumTrack}
          timeSignature={timeSignature}
          bpm={bpm}
          tempoMap={tempoMap}
          beatTimes={beatTimes}
          playheadSeconds={playheadSeconds}
          playing={playing}
          gridResolution={gridResolution}
          currentAspect={currentAspect}
          grooveWeights={grooveWeights}
          selectedBarIndex={selectedBarIndex}
          onBarSelect={onBarSelect}
          barDirectives={barDirectives}
          selectedNoteIds={selectedNoteIds}
          onNoteSelect={setSelectedNoteIds}
          onNoteChange={(notes) => {
            if (!drumTrack || !onUpdateTrack) return;
            onUpdateTrack({ ...drumTrack, notes });
          }}
          scrollContainerRef={pianoRollScrollRef}
          pixelsPerBeat={pixelsPerBeat}
          visibleStartMeasure={visibleStartMeasure}
          visibleMeasureCount={visibleMeasureCount}
          totalSongBars={totalSongBars}
          drumEngine={drumEngine}
          sectionRegions={sectionRegions}
          selectedSectionIds={selectedSectionIds}
          onSectionSelect={onSectionSelect}
        />

      {selectedNotes.length > 0 && (
        <div className="absolute right-2 top-12 bottom-2 w-64 z-50 shadow-lg">
          <NoteInspector
            selectedNotes={selectedNotes}
            onUpdateNotes={handleNoteChange}
            onClose={() => setSelectedNoteIds([])}
          />
        </div>
      )}
    </div>
  );
};
