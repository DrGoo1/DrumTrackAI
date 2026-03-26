import React, { useEffect, useMemo, useRef } from "react";

const clampNumber = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

type V3KnobProps = {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  size?: number;
  label?: string;
  formatValue?: (v: number) => string;
  testId?: string;
};

export function V3Knob(props: V3KnobProps) {
  const {
    value,
    onChange,
    min = 0,
    max = 1,
    step = 0.01,
    size = 84,
    label,
    formatValue,
    testId,
  } = props;

  const pointerRef = useRef<number | null>(null);
  const dragRef = useRef<{ value: number; y: number } | null>(null);
  const knobRef = useRef<HTMLDivElement | null>(null);

  const finishDrag = () => {
    if (pointerRef.current !== null && knobRef.current) {
      try {
        knobRef.current.releasePointerCapture(pointerRef.current);
      } catch {
        // ignore
      }
    }
    pointerRef.current = null;
    dragRef.current = null;
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    pointerRef.current = event.pointerId;
    dragRef.current = { value, y: event.clientY };
    knobRef.current = event.currentTarget;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (pointerRef.current !== event.pointerId) return;
    if (!dragRef.current) return;
    event.preventDefault();

    const range = max - min;
    const px = event.shiftKey ? 260 : 160;
    const delta = (dragRef.current.y - event.clientY) / px;
    const raw = dragRef.current.value + delta * range;
    const snapped = Math.round(raw / step) * step;
    onChange(Number(clampNumber(snapped, min, max).toFixed(4)));
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    if (pointerRef.current !== event.pointerId) return;
    finishDrag();
  };

  const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    const direction = event.deltaY < 0 ? 1 : -1;
    const multiplier = event.shiftKey ? 0.2 : 1;
    const raw = value + direction * step * multiplier;
    onChange(Number(clampNumber(raw, min, max).toFixed(4)));
  };

  useEffect(() => () => finishDrag(), []);

  const pct = useMemo(() => {
    if (!Number.isFinite(value)) return 0;
    const denom = Math.max(1e-9, max - min);
    return clampNumber((value - min) / denom, 0, 1);
  }, [value, min, max]);

  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.38;
  const stroke = Math.max(3, Math.round(size * 0.06));
  const circ = 2 * Math.PI * r;

  const startAngle = -225;
  const sweep = 270;
  const angle = startAngle + pct * sweep;

  const valueText = formatValue ? formatValue(value) : String(Math.round(pct * 100));

  const ticks = useMemo(() => {
    const out: Array<{ x1: number; y1: number; x2: number; y2: number; major: boolean }> = [];
    const count = 31;
    for (let i = 0; i < count; i++) {
      const t = i / (count - 1);
      const a = ((startAngle + t * sweep) * Math.PI) / 180;
      const major = i % 5 === 0;
      const r0 = r + stroke * 0.85;
      const r1 = r0 + (major ? stroke * 0.85 : stroke * 0.45);
      out.push({
        x1: cx + Math.cos(a) * r0,
        y1: cy + Math.sin(a) * r0,
        x2: cx + Math.cos(a) * r1,
        y2: cy + Math.sin(a) * r1,
        major,
      });
    }
    return out;
  }, [cx, cy, r, stroke]);

  const dash = circ * 0.78;
  const dashOffset = dash * (1 - pct);

  // Much darker at low values, much brighter at high values.
  const activeAlpha = 0.05 + pct * 0.95;
  const cyanStroke = `rgba(34,211,238,${activeAlpha.toFixed(3)})`;
  const purpleStroke = `rgba(168,85,247,${(0.05 + pct * 0.85).toFixed(3)})`;

  const outerCyan = 0.06 + pct * 0.28;
  const outerPurple = 0.04 + pct * 0.22;
  const innerCyan = 0.04 + pct * 0.18;
  const innerPurple = 0.03 + pct * 0.14;

  const glowBlurCyan = 2 + pct * 4;
  const glowBlurPurple = 3 + pct * 5;
  const glowAlphaCyan = 0.18 + pct * 0.82;
  const glowAlphaPurple = 0.10 + pct * 0.65;

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className="relative rounded-full bg-slate-950/80 border border-cyan-400/20 select-none"
        data-testid={testId}
        style={{
          width: size,
          height: size,
          touchAction: "none",
          boxShadow: `0 0 18px rgba(34,211,238,${outerCyan.toFixed(3)}), 0 0 22px rgba(168,85,247,${outerPurple.toFixed(
            3
          )}), inset 0 0 18px rgba(34,211,238,${innerCyan.toFixed(3)}), inset 0 0 22px rgba(168,85,247,${innerPurple.toFixed(3)})`,
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onWheel={handleWheel}
      >
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="block">
          <defs>
            <filter id="v3KnobGlowCyan" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation={glowBlurCyan} result="blur" />
              <feColorMatrix
                in="blur"
                type="matrix"
                values={`0 0 0 0 0.13  0 0 0 0 0.82  0 0 0 0 0.93  0 0 0 ${glowAlphaCyan.toFixed(3)} 0`}
                result="cyanBlur"
              />
              <feMerge>
                <feMergeNode in="cyanBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            <filter id="v3KnobGlowPurple" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation={glowBlurPurple} result="blur" />
              <feColorMatrix
                in="blur"
                type="matrix"
                values={`0 0 0 0 0.66  0 0 0 0 0.20  0 0 0 0 0.98  0 0 0 ${glowAlphaPurple.toFixed(3)} 0`}
                result="purpleBlur"
              />
              <feMerge>
                <feMergeNode in="purpleBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            <linearGradient id="v3KnobActiveGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor={"rgba(34,211,238,0.25)"} />
              <stop offset="55%" stopColor={"rgba(34,211,238,0.85)"} />
              <stop offset="100%" stopColor={"rgba(168,85,247,0.85)"} />
            </linearGradient>
          </defs>

          <g opacity={0.9}>
            {ticks.map((t, idx) => (
              <line
                key={idx}
                x1={t.x1}
                y1={t.y1}
                x2={t.x2}
                y2={t.y2}
                stroke={t.major ? "rgba(148,163,184,0.55)" : "rgba(148,163,184,0.28)"}
                strokeWidth={t.major ? 1.4 : 1}
                strokeLinecap="round"
              />
            ))}
          </g>

          <g transform={`rotate(${startAngle + 45} ${cx} ${cy})`}>
            <circle
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke="rgba(51,65,85,0.85)"
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${circ}`}
            />
            <circle
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={purpleStroke}
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${circ}`}
              strokeDashoffset={dashOffset}
              filter="url(#v3KnobGlowPurple)"
            />
            <circle
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={cyanStroke}
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${circ}`}
              strokeDashoffset={dashOffset}
              filter="url(#v3KnobGlowCyan)"
            />
            <circle
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={"url(#v3KnobActiveGrad)"}
              opacity={activeAlpha}
              strokeWidth={Math.max(2, stroke - 1)}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${circ}`}
              strokeDashoffset={dashOffset}
            />
          </g>

          <g transform={`rotate(${angle} ${cx} ${cy})`}>
            <line
              x1={cx}
              y1={cy - r + stroke * 0.25}
              x2={cx}
              y2={cy - r - stroke * 0.9}
              stroke="rgba(226,232,240,0.85)"
              strokeWidth={2}
              strokeLinecap="round"
            />
          </g>

          <circle cx={cx} cy={cy} r={r - stroke * 0.55} fill="rgba(2,6,23,0.85)" />
          <circle cx={cx} cy={cy} r={r - stroke * 0.8} fill="rgba(15,23,42,0.85)" />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-[11px] text-slate-400 leading-none">{label || ""}</div>
          <div className="mt-0.5 text-lg font-semibold text-cyan-100 tracking-tight leading-none">
            {valueText}
          </div>
        </div>
      </div>
    </div>
  );
}
