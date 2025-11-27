import React from "react";
import { useLimbStore, LimbId } from "../state/limbStore";

const LIMB_LABELS: Record<LimbId, string> = {
  RH: "Right Hand",
  LH: "Left Hand",
  RF: "Right Foot",
  LF: "Left Foot",
};

export const KitLimbsPanel: React.FC = () => {
  const { kit, mapping, setHandedness, setLimbInstruments } = useLimbStore();

  return (
    <div className="space-y-2 p-3 bg-neutral-900 rounded border border-neutral-800 text-[12px] leading-snug">
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-cyan-300 text-sm tracking-wide">Kit &amp; Limbs</span>
      </div>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-neutral-300">Handedness</span>
        <select
          className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1 text-[11px]"
          value={mapping.handedness}
          onChange={(e) => setHandedness(e.target.value as any)}
        >
          <option value="right">Right-handed</option>
          <option value="left">Left-handed</option>
        </select>
      </div>
      <div className="text-[10px] text-neutral-500">
        Configure which kit pieces each limb primarily controls. This guides generation and the limb view.
      </div>
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {(Object.keys(LIMB_LABELS) as LimbId[]).map((limb) => {
          const selected = new Set(mapping.limbToInstrumentIds[limb] || []);
          return (
            <div key={limb} className="border border-neutral-800 rounded p-2 bg-neutral-950/60">
              <div className="text-[11px] text-neutral-200 mb-1">{LIMB_LABELS[limb]}</div>
              <div className="flex flex-wrap gap-1">
                {kit.instruments.map((inst) => {
                  const active = selected.has(inst.id);
                  return (
                    <button
                      key={inst.id}
                      type="button"
                      className={
                        "px-1.5 py-0.5 rounded text-[10px] border " +
                        (active
                          ? "bg-emerald-600/80 border-emerald-400 text-white"
                          : "bg-neutral-900 border-neutral-700 text-neutral-300 hover:border-emerald-500")
                      }
                      onClick={() => {
                        const next = active
                          ? Array.from(selected).filter((id) => id !== inst.id)
                          : [...Array.from(selected), inst.id];
                        setLimbInstruments(limb, next);
                      }}
                    >
                      {inst.label}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
