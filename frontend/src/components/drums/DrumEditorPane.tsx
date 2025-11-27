// frontend/src/components/drums/DrumEditorPane.tsx

import React, { useState } from "react";
import {
  DrumTrackForDCSM,
  DrumNoteEvent,
  NoteAspect,
} from "../../types/drumTrack";
import { DrumPianoRoll } from "./DrumPianoRoll";
import { NoteInspector } from "./NoteInspector";
import { GridResolution } from "../../utils/pianoRollGrid";
import { GrooveWeightMap } from "../../types/grooveWeight";

interface DrumEditorPaneProps {
  drumTrack: DrumTrackForDCSM | null;
  timeSignature: [number, number];
  grooveWeights?: GrooveWeightMap;
  onUpdateTrack?: (track: DrumTrackForDCSM) => void;
}

export const DrumEditorPane: React.FC<DrumEditorPaneProps> = ({
  drumTrack,
  timeSignature,
  grooveWeights,
  onUpdateTrack,
}) => {
  const [gridResolution, setGridResolution] =
    useState<GridResolution>("16th");
  const [currentAspect, setCurrentAspect] =
    useState<NoteAspect | "all">("all");
  const [selectedNoteIds, setSelectedNoteIds] = useState<string[]>([]);

  const selectedNotes: DrumNoteEvent[] =
    drumTrack?.notes.filter((n) => selectedNoteIds.includes(n.id)) ?? [];

  const handleNoteChange = (patch: Partial<DrumNoteEvent>) => {
    if (!drumTrack || !onUpdateTrack || selectedNoteIds.length === 0) return;
    const newNotes = drumTrack.notes.map((n) =>
      selectedNoteIds.includes(n.id) && !n.locked ? { ...n, ...patch } : n
    );
    onUpdateTrack({ ...drumTrack, notes: newNotes });
  };

  return (
    <div className="flex flex-row h-full">
      <div className="flex-1 flex flex-col">
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
                onClick={() => setGridResolution(res)}
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
          gridResolution={gridResolution}
          currentAspect={currentAspect}
          grooveWeights={grooveWeights}
          selectedNoteIds={selectedNoteIds}
          onNoteSelect={setSelectedNoteIds}
          onNoteChange={(notes) => {
            if (!drumTrack || !onUpdateTrack) return;
            onUpdateTrack({ ...drumTrack, notes });
          }}
        />
      </div>

      {/* Note inspector */}
      <NoteInspector
        selectedNotes={selectedNotes}
        onUpdateNotes={handleNoteChange}
      />
    </div>
  );
};
