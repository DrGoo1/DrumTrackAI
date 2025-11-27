// web-frontend/src/ui/WaveformCanvas.tsx
import React, { useEffect, useRef, useState } from "react";

export default function WaveformCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);
  const [peaks, setPeaks] = useState<number[] | null>(null);

  useEffect(() => {
    const onLoaded = (e: any) => setPeaks([...(e.detail?.wf?.peaks || [])]);
    window.addEventListener("wf:loaded", onLoaded);
    return () => window.removeEventListener("wf:loaded", onLoaded);
  }, []);

  useEffect(() => {
    if (!peaks || !ref.current) return;
    const c = ref.current;
    const g = c.getContext("2d")!;
    const ratio = window.devicePixelRatio || 1;
    c.width = c.clientWidth * ratio;
    c.height = c.clientHeight * ratio;
    g.scale(ratio, ratio);
    g.clearRect(0, 0, c.clientWidth, c.clientHeight);
    const H = c.clientHeight, W = c.clientWidth, mid = H / 2, N = peaks.length;
    g.fillStyle = "#10b981";
    for (let x = 0; x < W; x++) {
      const i = Math.floor((x / W) * N);
      const v = Math.max(0, Math.min(1, peaks[i] || 0));
      const y = v * (H / 2 - 2);
      g.fillRect(x, mid - y, 1, y * 2);
    }
  }, [peaks]);

  return <canvas ref={ref} className="w-full h-[160px] bg-slate-950 rounded border border-slate-800" />;
}
