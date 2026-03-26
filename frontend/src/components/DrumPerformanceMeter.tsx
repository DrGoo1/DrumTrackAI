import React, { useMemo } from "react";
import type { MidiNote } from "./PianoRoll";
import type { MeasureRange } from "./WebDAWApp";

const CATEGORY_DEFS = [
  {
    id: "hats",
    label: "Hi-Hat Pulse",
    focus: "Closed & open hats",
    lanes: ["hihat", "openhat", "hat", "pedalhat"],
    accent: "from-cyan-500/30 to-cyan-400/10",
    icon: "✨",
  },
  {
    id: "ride",
    label: "Ride Articulation",
    focus: "Bell & bow clarity",
    lanes: ["ride", "ridebell"],
    accent: "from-amber-500/30 to-amber-400/10",
    icon: "🔔",
  },
  {
    id: "kick",
    label: "Low-End Drive",
    focus: "Kick + sub pulses",
    lanes: ["kick", "subkick", "bass"],
    accent: "from-emerald-500/30 to-emerald-400/10",
    icon: "💥",
  },
  {
    id: "snare",
    label: "Backbeat & Ghosts",
    focus: "Snare control",
    lanes: ["snare", "clap"],
    accent: "from-rose-500/20 to-rose-400/5",
    icon: "🥁",
  },
  {
    id: "cymbals",
    label: "Cymbal Texture",
    focus: "Crash & swells",
    lanes: ["crash", "china", "splash"],
    accent: "from-purple-500/20 to-purple-400/5",
    icon: "🌊",
  },
];

const clamp = (value: number, min = 0, max = 100) => Math.min(max, Math.max(min, value));

function describeIntensity(value: number) {
  if (value < 25) return "Sparse";
  if (value < 55) return "Balanced";
  if (value < 80) return "Driving";
  return "Explosive";
}

type DrumPerformanceMeterProps = {
  notes: MidiNote[];
  bpm: number;
  timeSig: [number, number];
  selectedRange?: MeasureRange | null;
};

export const DrumPerformanceMeter: React.FC<DrumPerformanceMeterProps> = ({
  notes,
  bpm,
  timeSig,
  selectedRange,
}) => {
  const analysisWindow = useMemo(() => {
    if (selectedRange?.startTime != null && selectedRange?.endTime != null) {
      return {
        start: selectedRange.startTime,
        end: selectedRange.endTime,
        label: `${selectedRange.sectionLabel ?? "Section"} · ${selectedRange.measureCount} bars`,
      };
    }
    const earliest = Math.min(0, ...notes.map((n) => n.time));
    const latest = Math.max(0, ...notes.map((n) => n.time + (n.duration || 0.25)));
    return {
      start: earliest,
      end: latest || (60 / Math.max(1, bpm)) * timeSig[0] * 4,
      label: `Full arrangement · ${Math.max(1, notes.length)} hits`,
    };
  }, [notes, bpm, timeSig, selectedRange]);

  const beatsInWindow = Math.max(1, (analysisWindow.end - analysisWindow.start) * (bpm / 60));

  const metrics = useMemo(() => {
    return CATEGORY_DEFS.map((category) => {
      const hits = notes.filter((note) => {
        if (note.time < analysisWindow.start || note.time > analysisWindow.end) {
          return false;
        }
        const lane = (note.lane || "").toLowerCase();
        return category.lanes.some((needle) => lane.includes(needle));
      }).length;

      const normalized = clamp(Math.round((hits / beatsInWindow) * 120));
      return {
        ...category,
        hits,
        intensity: normalized,
        description: describeIntensity(normalized),
      };
    });
  }, [notes, analysisWindow.start, analysisWindow.end, beatsInWindow]);

  const headline = metrics
    .filter((metric) => ["hats", "ride", "kick"].includes(metric.id))
    .map((metric) => `${metric.label.split(" ")[0]} ${metric.description}`)
    .join(" · ");

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-4 shadow-inner">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4 text-sm">
        <div>
          <div className="text-slate-300 font-semibold">Drum Performance Meter</div>
          <div className="text-xs text-slate-500">{analysisWindow.label}</div>
        </div>
        <div className="text-xs text-emerald-300 bg-emerald-500/10 px-2 py-1 rounded-full">
          {headline || "Waiting for drum activity"}
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {metrics.map((metric) => (
          <div
            key={metric.id}
            className={`rounded-lg border border-slate-800 bg-gradient-to-br ${metric.accent} p-3 flex flex-col gap-2`}
          >
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span className="font-semibold text-slate-100 flex items-center gap-1">
                <span>{metric.icon}</span>
                {metric.label}
              </span>
              <span className="text-slate-400">{metric.hits} hits</span>
            </div>
            <div className="text-[11px] uppercase tracking-wide text-slate-400">{metric.focus}</div>
            <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-slate-100"
                style={{ width: `${metric.intensity}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span className="text-slate-200 font-semibold">{metric.intensity}%</span>
              <span className="text-slate-400">{metric.description}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DrumPerformanceMeter;
