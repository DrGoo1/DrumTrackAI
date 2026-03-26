import React, { useEffect, useRef } from "react";

type WF = { sr: number; peaks: number[]; key: string; duration?: number };

export default function WaveformPanel({ data }: { data: WF }) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!data || !ref.current) return;
    const canvas = ref.current;
    const dpr = window.devicePixelRatio || 1;

    const W = Math.max(600, Math.min(window.innerWidth - 80, 1600));
    const H = 120;

    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width = `${W}px`;
    canvas.style.height = `${H}px`;

    const g = canvas.getContext("2d")!;
    g.resetTransform();
    g.scale(dpr, dpr);

    g.fillStyle = "#0f172a";
    g.fillRect(0, 0, W, H);

    if (!data.peaks?.length) return;

    // draw zero line
    g.strokeStyle = "#1f2937";
    g.beginPath();
    g.moveTo(0, H / 2 + 0.5);
    g.lineTo(W, H / 2 + 0.5);
    g.stroke();

    // render peaks
    g.strokeStyle = "#22d3ee";
    g.lineWidth = 1;
    g.beginPath();

    const n = data.peaks.length;
    for (let x = 0; x < W; x++) {
      const i = Math.floor((x / W) * n);
      const v = Math.max(0, Math.min(1, data.peaks[i] ?? 0));
      const h = Math.max(1, v * (H * 0.9));
      g.moveTo(x + 0.5, H / 2 - h / 2);
      g.lineTo(x + 0.5, H / 2 + h / 2);
    }
    g.stroke();
  }, [data]);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
      <div className="text-slate-300 text-sm mb-2">
        <span className="font-medium">File:</span> {data.key}
        {typeof data.duration === "number" && (
          <span className="ml-3 opacity-70">
            ~{data.duration.toFixed(1)}s @ {data.sr} Hz
          </span>
        )}
      </div>
      <canvas ref={ref} />
    </div>
  );
}
