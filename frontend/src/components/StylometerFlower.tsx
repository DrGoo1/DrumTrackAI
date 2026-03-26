import React, { useMemo, useState } from "react";

type GenreKey =
  | "rock"
  | "jazz"
  | "funk"
  | "metal"
  | "blues"
  | "pop"
  | "latin"
  | "hiphop"
  | "soul";

type ControlKey = "intensity" | "variation" | "humanize" | "swing" | "ghosts" | "fills";

export type StylometerValues = {
  genres: Record<GenreKey, number>;
  grooveScore: number;
  controls: Record<ControlKey, number>;
};

function clamp01(v: number) {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(1, v));
}

function clamp(v: number, min: number, max: number) {
  if (!Number.isFinite(v)) return min;
  return Math.max(min, Math.min(max, v));
}

const GENRES: Array<{ key: GenreKey; label: string; hue: number }> = [
  { key: "rock", label: "Rock", hue: 18 },
  { key: "jazz", label: "Jazz", hue: 285 },
  { key: "funk", label: "Funk", hue: 140 },
  { key: "metal", label: "Metal", hue: 0 },
  { key: "blues", label: "Blues", hue: 220 },
  { key: "pop", label: "Pop", hue: 320 },
  { key: "latin", label: "Latin", hue: 50 },
  { key: "hiphop", label: "Hip-Hop", hue: 200 },
  { key: "soul", label: "Soul", hue: 25 },
];

const CONTROLS: Array<{ key: ControlKey; label: string }> = [
  { key: "intensity", label: "Intensity" },
  { key: "variation", label: "Dynamics" },
  { key: "humanize", label: "Humanize" },
  { key: "swing", label: "Swing" },
  { key: "ghosts", label: "Ghosts" },
  { key: "fills", label: "Fills" },
];

function polar(cx: number, cy: number, r: number, angleRad: number) {
  return { x: cx + r * Math.cos(angleRad), y: cy + r * Math.sin(angleRad) };
}

function petalPath(cx: number, cy: number, r0: number, r1: number, a0: number, a1: number) {
  const p0 = polar(cx, cy, r0, a0);
  const p1 = polar(cx, cy, r1, (a0 + a1) / 2);
  const p2 = polar(cx, cy, r0, a1);

  // Sharper petals: keep the side control points closer to the base, and push the tip control
  // slightly past the tip to create a more pointed, decisive shape.
  const c0 = polar(cx, cy, r0 + (r1 - r0) * 0.28, a0);
  const c1 = polar(cx, cy, r0 + (r1 - r0) * 1.10, (a0 + a1) / 2);
  const c2 = polar(cx, cy, r0 + (r1 - r0) * 0.28, a1);

  return `M ${p0.x.toFixed(2)} ${p0.y.toFixed(2)} Q ${c0.x.toFixed(2)} ${c0.y.toFixed(2)} ${p1.x.toFixed(2)} ${p1.y.toFixed(
    2,
  )} Q ${c2.x.toFixed(2)} ${c2.y.toFixed(2)} ${p2.x.toFixed(2)} ${p2.y.toFixed(2)} Z`;
}

function arcPath(cx: number, cy: number, r0: number, r1: number, a0: number, a1: number) {
  const p0 = polar(cx, cy, r0, a0);
  const p1 = polar(cx, cy, r1, a0);
  const p2 = polar(cx, cy, r1, a1);
  const p3 = polar(cx, cy, r0, a1);
  const largeArc = a1 - a0 > Math.PI ? 1 : 0;
  return `M ${p0.x.toFixed(2)} ${p0.y.toFixed(2)} L ${p1.x.toFixed(2)} ${p1.y.toFixed(2)} A ${r1.toFixed(2)} ${r1.toFixed(
    2,
  )} 0 ${largeArc} 1 ${p2.x.toFixed(2)} ${p2.y.toFixed(2)} L ${p3.x.toFixed(2)} ${p3.y.toFixed(2)} A ${r0.toFixed(2)} ${r0.toFixed(
    2,
  )} 0 ${largeArc} 0 ${p0.x.toFixed(2)} ${p0.y.toFixed(2)} Z`;
}

export default function StylometerFlower({
  values,
  title,
  subtitle,
  genreLabel,
  scopeLabel,
  onResetBaseline,
}: {
  values: StylometerValues;
  title?: string;
  subtitle?: string;
  genreLabel?: string;
  scopeLabel?: string;
  onResetBaseline?: () => void;
}) {
  const [hoverKey, setHoverKey] = useState<string | null>(null);

  const normalized = useMemo(() => {
    const g: Record<GenreKey, number> = {
      rock: 0,
      jazz: 0,
      funk: 0,
      metal: 0,
      blues: 0,
      pop: 0,
      latin: 0,
      hiphop: 0,
      soul: 0,
    };
    for (const { key } of GENRES) {
      g[key] = clamp01(values.genres[key] ?? 0);
    }
    const c: Record<ControlKey, number> = {
      intensity: clamp01(values.controls.intensity ?? 0),
      variation: clamp01(values.controls.variation ?? 0),
      humanize: clamp01(values.controls.humanize ?? 0),
      swing: clamp01(values.controls.swing ?? 0),
      ghosts: clamp01(values.controls.ghosts ?? 0),
      fills: clamp01(values.controls.fills ?? 0),
    };
    const grooveScore = clamp01(values.grooveScore ?? 0);
    return { genres: g, controls: c, grooveScore };
  }, [values]);

  const resolvedGenreLabel = useMemo(() => {
    if (genreLabel && genreLabel.trim()) return genreLabel;
    // fallback: show strongest genre
    const entries = GENRES.map((g) => ({ key: g.key, label: g.label, v: normalized.genres[g.key] }))
      .sort((a, b) => b.v - a.v);
    const top = entries[0];
    return top && top.v > 0 ? top.label : "";
  }, [genreLabel, normalized.genres]);

  const resolvedGenreHue = useMemo(() => {
    // Use first token of compound label to choose a consistent color.
    const first = (resolvedGenreLabel || "").split(/[-/]/)[0]?.trim()?.toLowerCase();
    const match = GENRES.find((g) => g.label.toLowerCase() === first || g.key === (first as any));
    return match?.hue ?? 285;
  }, [resolvedGenreLabel]);

  return (
    <div className="w-full border-b border-slate-800 bg-slate-950/70">
      <div className="max-w-[1400px] mx-auto px-4 py-4">
        <div className="flex flex-col items-center text-center">
          <div className="flex flex-col items-center gap-1">
            <div className="text-sm font-semibold text-slate-300">{title || "Stylometer"}</div>
            {(scopeLabel || onResetBaseline) && (
              <div className="flex items-center gap-2">
                {scopeLabel ? (
                  <div className="text-[11px] uppercase tracking-wide text-slate-500">{scopeLabel}</div>
                ) : null}
                {onResetBaseline ? (
                  <button
                    type="button"
                    onClick={onResetBaseline}
                    className="text-[11px] px-2 py-0.5 rounded border border-slate-700 bg-slate-900/70 text-slate-200 hover:border-slate-500"
                  >
                    Reset baseline
                  </button>
                ) : null}
              </div>
            )}
          </div>
          {resolvedGenreLabel ? (
            <div
              className="mt-0.5 text-2xl sm:text-3xl font-extrabold tracking-tight bg-clip-text text-transparent"
              style={{
                backgroundImage: `linear-gradient(90deg, hsla(${resolvedGenreHue},95%,72%,1), rgba(236,72,153,1), rgba(168,85,247,1))`,
              }}
            >
              {resolvedGenreLabel}
            </div>
          ) : null}
          <div className="text-xs text-slate-400 mt-0.5 max-w-2xl">
            {subtitle || "Your current style fingerprint (genre + feel)."}
          </div>
          {hoverKey && <div className="text-[11px] text-slate-300 mt-1">{hoverKey}</div>}

          <div className="mt-4 w-full max-w-3xl">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">Meters</div>

            <div className="mt-2 rounded-lg border border-slate-800 bg-slate-900/40 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-semibold text-slate-200">Groove</div>
                <div
                  className="text-base font-extrabold bg-clip-text text-transparent"
                  style={{
                    backgroundImage: `linear-gradient(90deg, hsla(${resolvedGenreHue},95%,72%,1), rgba(236,72,153,1), rgba(168,85,247,1))`,
                  }}
                >
                  {Math.round(normalized.grooveScore * 100)}%
                </div>
              </div>
              <div
                className="mt-2 h-3 rounded bg-slate-800 overflow-hidden"
                onMouseEnter={() => setHoverKey(`Groove: ${(normalized.grooveScore * 100).toFixed(0)}%`)}
                onMouseLeave={() => setHoverKey(null)}
              >
                <div
                  className="h-3 rounded"
                  style={{
                    width: `${Math.round(normalized.grooveScore * 100)}%`,
                    backgroundImage: `linear-gradient(90deg, hsla(${resolvedGenreHue},95%,72%,1), rgba(236,72,153,1), rgba(168,85,247,1))`,
                  }}
                />
              </div>
              <div
                className="mt-2 text-sm font-semibold bg-clip-text text-transparent"
                style={{
                  backgroundImage: `linear-gradient(90deg, hsla(${resolvedGenreHue},95%,72%,1), rgba(236,72,153,1), rgba(168,85,247,1))`,
                }}
              >
                Relative groove fingerprint strength
              </div>
            </div>

            <div className="mt-3 rounded-lg border border-slate-800 bg-slate-900/40 p-4">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Feel Controls</div>
              <div className="mt-3 space-y-2">
                {CONTROLS.map((c, idx) => {
                  const v = normalized.controls[c.key];
                  const hue = (resolvedGenreHue + 35 * (idx + 1)) % 360;
                  return (
                    <div key={c.key} className="grid grid-cols-[120px_1fr_52px] items-center gap-3">
                      <div className="text-sm font-semibold text-slate-300 text-left">{c.label}</div>
                      <div
                        className="h-2.5 rounded bg-slate-800 overflow-hidden"
                        onMouseEnter={() => setHoverKey(`${c.label}: ${(v * 100).toFixed(0)}%`)}
                        onMouseLeave={() => setHoverKey(null)}
                      >
                        <div
                          className="h-2.5 rounded"
                          style={{
                            width: `${Math.round(v * 100)}%`,
                            backgroundImage: `linear-gradient(90deg, hsla(${hue},95%,72%,1), rgba(236,72,153,0.9), rgba(168,85,247,0.85))`,
                          }}
                        />
                      </div>
                      <div className="text-right text-xs font-semibold text-slate-200">{Math.round(v * 100)}%</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
