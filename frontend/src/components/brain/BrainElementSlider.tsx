import React from "react";
import { BrainElementDefinition } from "../../types/brain";
import { Tooltip } from "../Tooltip";

interface BrainElementSliderProps {
  definition: BrainElementDefinition;
  value: number;
  frozen: boolean;
  disabled: boolean;
  locked?: boolean;
  onChange: (value: number) => void;
  onReset: () => void;
  onToggleFreeze?: () => void;
  onToggleDisable?: () => void;
}

export const BrainElementSlider: React.FC<BrainElementSliderProps> = ({
  definition,
  value,
  frozen,
  disabled,
  locked = false,
  onChange,
  onReset,
  onToggleFreeze,
  onToggleDisable,
}) => {
  const sliderId = `brain-element-${definition.id}`;
  const range = definition.maxValue - definition.minValue || 1;
  const percent = ((value - definition.minValue) / range) * 100;
  const step = Math.max(range / 100, 0.01);
  const isInteractable = !locked && !disabled;

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Tooltip content={definition.description} placement="top" maxWidthClassName="w-72">
            <p className="text-sm font-semibold text-white">
              {definition.label}
            </p>
          </Tooltip>
          <p className="text-xs text-slate-400">{definition.description}</p>
        </div>
        <div className="flex flex-wrap gap-1 text-[0.6rem] font-semibold uppercase text-slate-300">
          {frozen && <span className="rounded bg-blue-900/60 px-2 py-0.5 text-blue-200">Frozen</span>}
          {disabled && <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-200">Disabled</span>}
          {locked && <span className="rounded bg-amber-900/60 px-2 py-0.5 text-amber-200">Locked</span>}
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <div className="h-1.5 w-full rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"
            style={{ width: `${percent}%` }}
          />
        </div>
        <input
          id={sliderId}
          type="range"
          min={definition.minValue}
          max={definition.maxValue}
          step={step}
          value={value}
          disabled={!isInteractable}
          onChange={(event) => onChange(Number(event.target.value))}
          className="w-full cursor-pointer accent-indigo-500"
        />
        <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
          <span>
            {value.toFixed(2)} <span className="text-slate-500">(default {definition.defaultValue.toFixed(2)})</span>
          </span>
          <button
            type="button"
            onClick={onReset}
            className="text-amber-300 hover:text-amber-100"
            disabled={locked}
          >
            Reset
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        {definition.supportsFreeze && (
          <button
            type="button"
            onClick={onToggleFreeze}
            className={`rounded-full border px-3 py-1 transition-colors ${
              frozen
                ? "border-blue-400 bg-blue-900/50 text-blue-100"
                : "border-slate-600 text-slate-300 hover:border-blue-400 hover:text-blue-200"
            }`}
            disabled={locked}
          >
            {frozen ? "Unfreeze" : "Freeze"}
          </button>
        )}
        {definition.supportsDisable && (
          <button
            type="button"
            onClick={onToggleDisable}
            className={`rounded-full border px-3 py-1 transition-colors ${
              disabled
                ? "border-slate-400 bg-slate-800 text-slate-100"
                : "border-slate-600 text-slate-300 hover:border-pink-400 hover:text-pink-200"
            }`}
            disabled={locked}
          >
            {disabled ? "Enable" : "Disable"}
          </button>
        )}
      </div>
    </div>
  );
};

export default BrainElementSlider;
