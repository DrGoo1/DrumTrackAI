import React, { useMemo, useRef, useState } from "react";
import type { BeatPadHit } from "../services/api";

const PAD_LAYOUT = [
  {
    id: "kick",
    label: "Kick",
    emoji: "🥁",
    gradient: "from-orange-500 via-amber-400 to-amber-200",
    ring: "shadow-orange-500/40",
    border: "border-orange-200/60",
    baseVelocity: 115,
  },
  {
    id: "snare",
    label: "Snare",
    emoji: "🔥",
    gradient: "from-pink-500 via-rose-500 to-orange-300",
    ring: "shadow-pink-500/50",
    border: "border-pink-200/60",
    baseVelocity: 108,
  },
  {
    id: "hihat",
    label: "Hi-Hat",
    emoji: "✨",
    gradient: "from-emerald-500 via-teal-400 to-green-200",
    ring: "shadow-emerald-500/40",
    border: "border-emerald-200/60",
    baseVelocity: 92,
  },
  {
    id: "openhat",
    label: "Open Hat",
    emoji: "🌊",
    gradient: "from-cyan-500 via-sky-400 to-blue-200",
    ring: "shadow-cyan-500/40",
    border: "border-cyan-200/60",
    baseVelocity: 96,
  },
  {
    id: "tom",
    label: "Tom",
    emoji: "💥",
    gradient: "from-violet-500 via-purple-500 to-fuchsia-300",
    ring: "shadow-violet-500/40",
    border: "border-violet-200/60",
    baseVelocity: 104,
  },
  {
    id: "perc",
    label: "Perc",
    emoji: "⚡",
    gradient: "from-amber-500 via-yellow-400 to-lime-200",
    ring: "shadow-amber-500/40",
    border: "border-amber-200/60",
    baseVelocity: 100,
  },
] as const;

export type BeatPadGridProps = {
  tempo: number;
  disabled?: boolean;
  onHitsChange?: (hits: BeatPadHit[]) => void;
};

export function BeatPadGrid({ tempo, disabled = false, onHitsChange }: BeatPadGridProps) {
  const [hits, setHits] = useState<BeatPadHit[]>([]);
  const [sessionActive, setSessionActive] = useState(false);
  const sessionStartRef = useRef<number | null>(null);

  const handlePadTrigger = (padId: typeof PAD_LAYOUT[number]["id"], baseVelocity: number, inputVelocity?: number) => {
    if (disabled) {
      return;
    }
    if (sessionStartRef.current === null) {
      sessionStartRef.current = performance.now();
      setSessionActive(true);
    }
    const now = performance.now();
    const elapsed = sessionStartRef.current ? (now - sessionStartRef.current) / 1000 : 0;
    const beatPosition = (elapsed * tempo) / 60;
    const velocity = Math.max(40, Math.min(127, inputVelocity ?? baseVelocity));
    const hit: BeatPadHit = {
      instrument: padId,
      beat_position: beatPosition,
      time: elapsed,
      velocity,
      confidence: 0.98,
    };
    setHits((prev) => {
      const next = [...prev, hit];
      onHitsChange?.(next);
      return next;
    });
  };

  const resetSession = () => {
    setHits([]);
    setSessionActive(false);
    sessionStartRef.current = null;
    onHitsChange?.([]);
  };

  const summary = useMemo(() => {
    return hits.reduce<Record<string, number>>((acc, hit) => {
      acc[hit.instrument] = (acc[hit.instrument] || 0) + 1;
      return acc;
    }, {});
  }, [hits]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={resetSession}
          className="px-3 py-2 rounded-full text-sm font-semibold bg-white/10 border border-white/20 hover:bg-white/20 transition"
        >
          Reset Pad Take
        </button>
        <span className="text-xs uppercase tracking-widest text-slate-400">
          {sessionActive ? "Recording" : "Tap to start"} • Tempo {tempo} BPM
        </span>
        <span className="text-xs text-slate-400">Hits: {hits.length}</span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PAD_LAYOUT.map((pad) => (
          <button
            key={pad.id}
            type="button"
            disabled={disabled}
            onPointerDown={(evt) => {
              evt.preventDefault();
              const pressure = evt.pressure && evt.pressure > 0 ? evt.pressure : 0.7;
              const dynamicVelocity = pad.baseVelocity + Math.round((pressure - 0.5) * 60);
              handlePadTrigger(pad.id, pad.baseVelocity, dynamicVelocity);
            }}
            onClick={(evt) => evt.preventDefault()}
            className={`relative h-32 rounded-3xl border ${pad.border} bg-gradient-to-br ${pad.gradient} text-white shadow-xl ${pad.ring} flex flex-col justify-center items-center gap-2 text-lg font-semibold tracking-wide transition-transform active:scale-95 disabled:opacity-40`}
          >
            <span className="text-4xl drop-shadow-lg">{pad.emoji}</span>
            <span>{pad.label}</span>
            <span className="text-xs uppercase tracking-widest text-white/70">Tap</span>
          </button>
        ))}
      </div>

      {hits.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-lg p-4 text-sm text-slate-200">
          <div className="flex flex-wrap items-center gap-4">
            <span className="text-xs uppercase tracking-widest text-slate-400">Summary</span>
            {Object.entries(summary).map(([instrument, count]) => (
              <span key={instrument} className="text-xs font-semibold text-white/80">
                {instrument}: {count}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
