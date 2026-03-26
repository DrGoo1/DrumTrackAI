import React from "react";
import { BrainPanelMode } from "../../types/brain";

interface BrainPresetBarProps {
  mode: BrainPanelMode;
  locked?: boolean;
  clipboardAvailable: boolean;
  onModeChange: (mode: BrainPanelMode) => void;
  onRandomize: () => void;
  onResetAll: () => void;
  onCopy: () => void;
  onPaste: () => void;
}

const MODES: Array<{ label: string; value: BrainPanelMode; helper: string }> = [
  { label: "EASY", value: "easy", helper: "Quick tweaks" },
  { label: "NORMAL", value: "normal", helper: "Core controls" },
  { label: "PRO", value: "pro", helper: "All elements" },
];

export const BrainPresetBar: React.FC<BrainPresetBarProps> = ({
  mode,
  locked = false,
  clipboardAvailable,
  onModeChange,
  onRandomize,
  onResetAll,
  onCopy,
  onPaste,
}) => {
  return (
    <div className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
      <div className="flex flex-wrap items-center gap-2">
        {MODES.map((preset) => (
          <button
            key={preset.value}
            type="button"
            disabled={locked}
            onClick={() => onModeChange(preset.value)}
            className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-colors ${
              mode === preset.value
                ? "bg-gradient-to-r from-indigo-500 to-purple-500 text-white"
                : "bg-slate-800/80 text-slate-300 hover:bg-slate-700/80"
            }`}
          >
            {preset.label}
            <span className="ml-1 text-[0.6rem] font-normal uppercase text-slate-300">
              {preset.helper}
            </span>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 text-xs font-semibold">
        <button
          type="button"
          onClick={onRandomize}
          disabled={locked}
          className="flex items-center gap-1 rounded-full border border-blue-500/60 px-3 py-1 text-blue-200 hover:border-blue-400"
        >
          🎲 Randomize
        </button>
        <button
          type="button"
          onClick={onResetAll}
          disabled={locked}
          className="flex items-center gap-1 rounded-full border border-amber-500/60 px-3 py-1 text-amber-200 hover:border-amber-400"
        >
          ♻ Reset All
        </button>
        <button
          type="button"
          onClick={onCopy}
          disabled={locked}
          className="flex items-center gap-1 rounded-full border border-slate-600 px-3 py-1 text-slate-200 hover:border-slate-400"
        >
          📋 Copy
        </button>
        <button
          type="button"
          onClick={onPaste}
          disabled={locked || !clipboardAvailable}
          className={`flex items-center gap-1 rounded-full border px-3 py-1 ${
            clipboardAvailable && !locked
              ? "border-emerald-500/60 text-emerald-200 hover:border-emerald-400"
              : "border-slate-700 text-slate-500"
          }`}
        >
          📥 Paste
        </button>
      </div>
    </div>
  );
};

export default BrainPresetBar;
