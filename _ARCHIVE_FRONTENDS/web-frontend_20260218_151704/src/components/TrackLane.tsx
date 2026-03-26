import { useEffect, useMemo, useRef, useState } from "react";
import type { Track } from "../state/dawStore";
import { fetchWaveform } from "../api/files";

export default function TrackLane({ track, zoom=1 }: { track: Track; zoom?: number; }) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const [peaksByClip, setPeaks] = useState<Record<string, number[]>>({});
  const height = 80;

  useEffect(() => {
    (async () => {
      const out: Record<string, number[]> = {};
      for (const c of track.clips) {
        out[c.id] = await fetchWaveform(c.key, 3000);
      }
      setPeaks(out);
    })();
  }, [track.id, track.clips.map(c => c.key).join(",")]);

  useEffect(() => {
    const c = ref.current; if (!c) return;
    const width = Math.max(800, Math.ceil((track.clips.reduce((m,c)=>Math.max(m, c.startSec + c.durationSec), 0)) * 100 * zoom));
    c.width = width; c.height = height;
    const g = c.getContext("2d")!;
    g.fillStyle = "#0b1020"; g.fillRect(0,0,width,height);
    g.strokeStyle = "#22c55e";

    const pxPerSec = 100 * zoom;
    for (const cinfo of track.clips) {
      const peaks = peaksByClip[cinfo.id];
      if (!peaks) continue;
      const yMid = height/2; const amp = (height/2)-6;
      const len = peaks.length;
      const secPerBin = cinfo.durationSec / len;
      g.beginPath();
      for (let i=0; i<len; i++) {
        const x = Math.floor((cinfo.startSec + i*secPerBin) * pxPerSec);
        const v = peaks[i];
        const y = amp * v;
        g.moveTo(x, yMid - y);
        g.lineTo(x, yMid + y);
      }
      g.stroke();
    }
  }, [peaksByClip, zoom, track.clips]);

  return (
    <div className="bg-slate-800 rounded-xl p-2 mb-2">
      <div className="text-slate-200 text-sm mb-1">{track.name}</div>
      <div className="overflow-x-auto"><canvas ref={ref} style={{ width: "100%" }} /></div>
    </div>
  );
}
