import { useMemo, useRef, useEffect } from "react";

export default function Ruler({ durationSec, zoom = 1 }: { durationSec: number; zoom?: number; }) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const width = Math.max(800, durationSec * 100 * zoom);

  useEffect(() => {
    const c = ref.current; if (!c) return;
    c.width = width; c.height = 28;
    const g = c.getContext("2d")!;
    g.fillStyle = "#0f172a"; g.fillRect(0,0,width,28);
    g.strokeStyle = "#334155"; g.fillStyle = "#94a3b8";
    const pxPerSec = 100 * zoom;
    for (let s=0; s<=durationSec; s++) {
      const x = Math.round(s * pxPerSec) + 0.5;
      g.beginPath(); g.moveTo(x, 0); g.lineTo(x, s % 5 === 0 ? 20 : 14); g.stroke();
      if (s % 5 === 0) { g.fillText(`${s}s`, x+3, 24); }
    }
  }, [width, durationSec, zoom]);

  return <div className="overflow-x-auto"><canvas ref={ref} style={{ width }} /></div>;
}
