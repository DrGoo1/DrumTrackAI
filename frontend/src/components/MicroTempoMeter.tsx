import React, { useEffect, useMemo, useRef, useState } from "react";

type MicroTempoMeterProps = {
  beatTimes: number[];
  playheadSec: number;
  sessionBpm: number;
  playing?: boolean;
  heightPx?: number;
};

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v));
}

function findBeatIndex(beatTimes: number[], t: number) {
  if (beatTimes.length < 2) return 0;
  let lo = 0;
  let hi = beatTimes.length - 2;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const a = beatTimes[mid];
    const b = beatTimes[mid + 1];
    if (t < a) {
      hi = mid - 1;
    } else if (t >= b) {
      lo = mid + 1;
    } else {
      return mid;
    }
  }
  return clamp(lo, 0, beatTimes.length - 2);
}

function computeInstantBpm(beatTimes: number[], t: number) {
  if (beatTimes.length < 2) return null;
  const i = findBeatIndex(beatTimes, t);
  const dt = beatTimes[i + 1] - beatTimes[i];
  if (!Number.isFinite(dt) || dt <= 0) return null;
  const bpm = 60 / dt;
  return Number.isFinite(bpm) && bpm > 0 ? bpm : null;
}

export default function MicroTempoMeter(props: MicroTempoMeterProps) {
  const {
    beatTimes,
    playheadSec,
    sessionBpm,
    playing = false,
    heightPx = 72,
  } = props;

  const [history, setHistory] = useState<number[]>([]);
  const lastSampleTsRef = useRef<number>(0);

  const instantBpm = useMemo(
    () => computeInstantBpm(beatTimes, playheadSec),
    [beatTimes, playheadSec],
  );

  const deltaBpm = useMemo(() => {
    if (instantBpm === null) return null;
    const base = Number.isFinite(sessionBpm) && sessionBpm > 0 ? sessionBpm : 120;
    return instantBpm - base;
  }, [instantBpm, sessionBpm]);

  useEffect(() => {
    if (!playing) {
      lastSampleTsRef.current = 0;
      return;
    }

    const tick = (ts: number) => {
      const last = lastSampleTsRef.current;
      if (!last || ts - last > 110) {
        lastSampleTsRef.current = ts;
        const bpm = computeInstantBpm(beatTimes, playheadSec);
        if (typeof bpm === "number" && Number.isFinite(bpm)) {
          setHistory((prev) => {
            const next = prev.length >= 64 ? prev.slice(prev.length - 63) : prev.slice();
            next.push(bpm);
            return next;
          });
        }
      }
      raf = window.requestAnimationFrame(tick);
    };

    let raf = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(raf);
  }, [beatTimes, playheadSec, playing]);

  const spark = useMemo(() => {
    if (!history.length) return "";
    const w = 220;
    const h = 32;
    const min = Math.min(...history);
    const max = Math.max(...history);
    const span = Math.max(0.001, max - min);

    const pts = history
      .map((v, idx) => {
        const x = (idx / Math.max(1, history.length - 1)) * w;
        const y = h - ((v - min) / span) * h;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");

    return { pts, min, max, w, h };
  }, [history]);

  const baseBpm = Number.isFinite(sessionBpm) && sessionBpm > 0 ? sessionBpm : 120;
  const instantText = instantBpm === null ? "--" : instantBpm.toFixed(1);
  const deltaText = deltaBpm === null ? "" : `${deltaBpm >= 0 ? "+" : ""}${deltaBpm.toFixed(1)}`;
  const wobble = deltaBpm === null ? 0 : Math.abs(deltaBpm);
  const wobblePct = clamp((wobble / Math.max(1, baseBpm)) * 100, 0, 9);
  const glow = wobblePct > 3 ? "rgba(34, 211, 238, 0.35)" : "rgba(99, 102, 241, 0.25)";

  return (
    <div
      className="rounded-xl border border-slate-700 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 px-3 py-2"
      style={{
        boxShadow: `0 0 0 1px rgba(255,255,255,0.04), 0 12px 30px -14px ${glow}`,
        height: heightPx,
      }}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <div className="text-[10px] uppercase tracking-widest text-slate-400">MicroTempo</div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl font-bold text-cyan-200 tabular-nums leading-none">{instantText}</div>
            <div className="text-[11px] text-slate-400">BPM</div>
            {deltaBpm !== null && (
              <div
                className="text-[11px] font-semibold tabular-nums px-2 py-0.5 rounded"
                style={{
                  background: "rgba(2, 132, 199, 0.12)",
                  border: "1px solid rgba(34, 211, 238, 0.25)",
                  color: "#a5f3fc",
                }}
                title={`Δ vs session (${baseBpm.toFixed(1)} BPM)`}
              >
                {deltaText}
              </div>
            )}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">
            Session: <span className="tabular-nums">{baseBpm.toFixed(1)}</span> BPM
          </div>
        </div>

        <div className="flex flex-col items-end gap-1">
          <div className="text-[10px] uppercase tracking-widest text-slate-400">Wobble</div>
          <div className="w-[220px]">
            <div
              className="h-2 rounded-full overflow-hidden"
              style={{ background: "rgba(15, 23, 42, 0.9)", border: "1px solid rgba(148, 163, 184, 0.18)" }}
            >
              <div
                className="h-full"
                style={{
                  width: `${clamp(wobblePct * 11, 0, 100)}%`,
                  background: "linear-gradient(90deg, rgba(34, 211, 238, 0.25), rgba(34, 211, 238, 0.95))",
                  boxShadow: "0 0 10px rgba(34, 211, 238, 0.35)",
                }}
              />
            </div>
          </div>
          <div className="h-[32px] w-[220px]">
            {typeof spark === "object" && spark.pts ? (
              <svg width={spark.w} height={spark.h} className="block">
                <defs>
                  <linearGradient id="mtk_grad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0" stopColor="rgba(99,102,241,0.35)" />
                    <stop offset="1" stopColor="rgba(34,211,238,0.9)" />
                  </linearGradient>
                </defs>
                <polyline
                  points={spark.pts}
                  fill="none"
                  stroke="url(#mtk_grad)"
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              </svg>
            ) : (
              <div
                className="h-full rounded"
                style={{ background: "rgba(15, 23, 42, 0.5)", border: "1px solid rgba(148, 163, 184, 0.12)" }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
