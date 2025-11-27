import React from "react";

export interface SectionRow {
  id: string;
  start: number;
  end: number;
  density: number;
  fillIn: boolean;
  fillOut: boolean;
  label?: string;
}

interface SectionsPanelProps {
  sections: SectionRow[];
  onChange: (next: SectionRow[]) => void;
  onAutoSectionize?: () => void;
}

export const SectionsPanel: React.FC<SectionsPanelProps> = ({ sections, onChange, onAutoSectionize }) => {
  function update(idx: number, patch: Partial<SectionRow>) {
    const next = sections.map((s, i) => (i === idx ? { ...s, ...patch } : s));
    onChange(next);
  }

  return (
    <div className="space-y-2 p-2 bg-neutral-900 rounded border border-neutral-800">
      <div className="flex items-center justify-between text-xs font-semibold text-neutral-200">
        <span>Arrangement Sections</span>
        {onAutoSectionize && (
          <button
            className="px-2 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-[11px]"
            onClick={onAutoSectionize}
          >
            Auto Sectionize
          </button>
        )}
      </div>
      <div className="space-y-1 max-h-52 overflow-y-auto text-[11px]">
        {sections.length === 0 && (
          <div className="text-neutral-500">No sections yet. Auto-sectionize to begin.</div>
        )}
        {sections.map((s, idx) => (
          <div
            key={s.id}
            className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto_auto_auto] gap-1 items-center bg-neutral-950/70 px-2 py-1 rounded"
          >
            <div>
              <div className="text-neutral-400">Start</div>
              <input
                type="number"
                className="w-full bg-neutral-900 border border-neutral-700 rounded px-1 py-0.5"
                value={s.start}
                step={0.01}
                onChange={(e) => update(idx, { start: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div>
              <div className="text-neutral-400">End</div>
              <input
                type="number"
                className="w-full bg-neutral-900 border border-neutral-700 rounded px-1 py-0.5"
                value={s.end}
                step={0.01}
                onChange={(e) => update(idx, { end: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="px-1">
              <div className="text-neutral-400">Density</div>
              <input
                type="number"
                className="w-16 bg-neutral-900 border border-neutral-700 rounded px-1 py-0.5"
                value={s.density}
                min={0}
                max={1}
                step={0.05}
                onChange={(e) => update(idx, { density: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <label className="flex items-center gap-1 px-1">
              <input
                type="checkbox"
                checked={s.fillIn}
                onChange={(e) => update(idx, { fillIn: e.target.checked })}
              />
              <span>Fill In</span>
            </label>
            <label className="flex items-center gap-1 px-1">
              <input
                type="checkbox"
                checked={s.fillOut}
                onChange={(e) => update(idx, { fillOut: e.target.checked })}
              />
              <span>Fill Out</span>
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}
