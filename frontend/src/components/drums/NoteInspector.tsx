// frontend/src/components/drums/NoteInspector.tsx

import React from "react";
import { DrumNoteEvent, LimbId, HitStyle } from "../../types/drumTrack";

interface NoteInspectorProps {
  selectedNotes: DrumNoteEvent[];
  onUpdateNotes?: (patch: Partial<DrumNoteEvent>) => void;
}

export const NoteInspector: React.FC<NoteInspectorProps> = ({
  selectedNotes,
  onUpdateNotes,
}) => {
  if (selectedNotes.length === 0) {
    return (
      <div className="w-64 border-l border-slate-700 bg-slate-950 p-4 text-xs text-slate-500 flex items-center justify-center">
        No notes selected
      </div>
    );
  }

  const firstNote = selectedNotes[0];
  const multiSelect = selectedNotes.length > 1;

  // Check if all selected notes have the same value for a property
  const allSame = <K extends keyof DrumNoteEvent>(key: K): boolean => {
    if (selectedNotes.length === 0) return false;
    const first = selectedNotes[0][key];
    return selectedNotes.every((n) => n[key] === first);
  };

  const handleChange = (patch: Partial<DrumNoteEvent>) => {
    if (onUpdateNotes) {
      onUpdateNotes(patch);
    }
  };

  return (
    <div className="w-64 border-l border-slate-700 bg-slate-950 flex flex-col overflow-y-auto">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <div className="text-xs font-semibold text-slate-200">
          Note Inspector
        </div>
        <div className="text-[10px] text-slate-500 mt-0.5">
          {multiSelect
            ? `${selectedNotes.length} notes selected`
            : `${firstNote.instrumentId} @ bar ${firstNote.barIndex + 1}`}
        </div>
      </div>

      {/* Velocity */}
      <div className="px-4 py-3 border-b border-slate-800">
        <label className="text-[10px] uppercase tracking-wide text-slate-400 block mb-1.5">
          Velocity
        </label>
        <input
          type="range"
          min="1"
          max="127"
          value={firstNote.velocity}
          onChange={(e) =>
            handleChange({ velocity: parseInt(e.target.value, 10) })
          }
          className="w-full"
        />
        <div className="flex justify-between items-center mt-1">
          <span className="text-[10px] text-slate-500">1</span>
          <span className="text-xs text-slate-200 font-mono">
            {firstNote.velocity}
          </span>
          <span className="text-[10px] text-slate-500">127</span>
        </div>
      </div>

      {/* Priority */}
      <div className="px-4 py-3 border-b border-slate-800">
        <label className="text-[10px] uppercase tracking-wide text-slate-400 block mb-1.5">
          Priority
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={firstNote.priority ?? 0.5}
          onChange={(e) =>
            handleChange({ priority: parseFloat(e.target.value) })
          }
          className="w-full"
        />
        <div className="flex justify-between items-center mt-1">
          <span className="text-[10px] text-slate-500">Low</span>
          <span className="text-xs text-slate-200 font-mono">
            {((firstNote.priority ?? 0.5) * 100).toFixed(0)}%
          </span>
          <span className="text-[10px] text-slate-500">High</span>
        </div>
      </div>

      {/* Timing Offset */}
      <div className="px-4 py-3 border-b border-slate-800">
        <label className="text-[10px] uppercase tracking-wide text-slate-400 block mb-1.5">
          Timing Offset (ms)
        </label>
        <input
          type="range"
          min="-50"
          max="50"
          step="0.1"
          value={firstNote.timingOffsetMs ?? 0}
          onChange={(e) =>
            handleChange({ timingOffsetMs: parseFloat(e.target.value) })
          }
          className="w-full"
        />
        <div className="flex justify-between items-center mt-1">
          <span className="text-[10px] text-slate-500">-50</span>
          <span className="text-xs text-slate-200 font-mono">
            {(firstNote.timingOffsetMs ?? 0).toFixed(1)}
          </span>
          <span className="text-[10px] text-slate-500">+50</span>
        </div>
      </div>

      {/* Hat Open Level (only for hi-hats) */}
      {firstNote.instrumentId.startsWith("hihat") && (
        <div className="px-4 py-3 border-b border-slate-800">
          <label className="text-[10px] uppercase tracking-wide text-slate-400 block mb-1.5">
            Hat Open Level
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={firstNote.hatOpenLevel ?? 0}
            onChange={(e) =>
              handleChange({ hatOpenLevel: parseFloat(e.target.value) })
            }
            className="w-full"
          />
          <div className="flex justify-between items-center mt-1">
            <span className="text-[10px] text-slate-500">Closed</span>
            <span className="text-xs text-slate-200 font-mono">
              {((firstNote.hatOpenLevel ?? 0) * 100).toFixed(0)}%
            </span>
            <span className="text-[10px] text-slate-500">Open</span>
          </div>
        </div>
      )}

      {/* Limb */}
      <div className="px-4 py-3 border-b border-slate-800">
        <label className="text-[10px] uppercase tracking-wide text-slate-400 block mb-1.5">
          Limb
        </label>
        <select
          value={firstNote.limbId ?? "other"}
          onChange={(e) => handleChange({ limbId: e.target.value as LimbId })}
          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
        >
          <option value="LH">LH (Left Hand)</option>
          <option value="RH">RH (Right Hand)</option>
          <option value="LF">LF (Left Foot)</option>
          <option value="RF">RF (Right Foot)</option>
          <option value="LS">LS (Left Stick)</option>
          <option value="RS">RS (Right Stick)</option>
          <option value="other">Other</option>
        </select>
      </div>

      {/* Hit Style */}
      <div className="px-4 py-3 border-b border-slate-800">
        <label className="text-[10px] uppercase tracking-wide text-slate-400 block mb-2">
          Hit Style
        </label>
        <div className="flex flex-col gap-1.5">
          {(["single", "double", "bounce"] as HitStyle[]).map((style) => (
            <label
              key={style}
              className="flex items-center gap-2 cursor-pointer"
            >
              <input
                type="radio"
                name="hitStyle"
                checked={firstNote.hitStyle === style}
                onChange={() => handleChange({ hitStyle: style })}
                className="text-slate-200"
              />
              <span className="text-xs text-slate-200 capitalize">{style}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Locked */}
      <div className="px-4 py-3 border-b border-slate-800">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={firstNote.locked ?? false}
            onChange={(e) => handleChange({ locked: e.target.checked })}
            className="text-emerald-500"
          />
          <span className="text-xs text-slate-200">Lock Note</span>
        </label>
        <div className="text-[10px] text-slate-500 mt-1">
          Locked notes cannot be overwritten by regeneration
        </div>
      </div>

      {/* Flags */}
      <div className="px-4 py-3 border-b border-slate-800">
        <div className="text-[10px] uppercase tracking-wide text-slate-400 mb-2">
          Flags
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={firstNote.isGhost ?? false}
              onChange={(e) => handleChange({ isGhost: e.target.checked })}
            />
            <span className="text-xs text-slate-200">Ghost</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={firstNote.isAccent ?? false}
              onChange={(e) => handleChange({ isAccent: e.target.checked })}
            />
            <span className="text-xs text-slate-200">Accent</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={firstNote.isFlam ?? false}
              onChange={(e) => handleChange({ isFlam: e.target.checked })}
            />
            <span className="text-xs text-slate-200">Flam</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={firstNote.isDrag ?? false}
              onChange={(e) => handleChange({ isDrag: e.target.checked })}
            />
            <span className="text-xs text-slate-200">Drag</span>
          </label>
        </div>
      </div>

      {/* Info */}
      {!multiSelect && (
        <div className="px-4 py-3 text-[10px] text-slate-500 space-y-1">
          <div>ID: {firstNote.id.slice(0, 8)}...</div>
          <div>
            Position: Bar {firstNote.barIndex + 1}, Tick {firstNote.tickInBar}
          </div>
          <div>MIDI: Ch {firstNote.channel}, Note {firstNote.midiPitch}</div>
          {firstNote.microTimingMs && (
            <div>Micro-timing: {firstNote.microTimingMs.toFixed(2)}ms</div>
          )}
        </div>
      )}
    </div>
  );
};
