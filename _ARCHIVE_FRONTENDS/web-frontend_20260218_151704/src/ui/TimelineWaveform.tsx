// src/ui/TimelineWaveform.tsx  (RESILIENT LOADER)
import React, { useEffect, useRef, useState } from "react";
import FallbackUploader from "./fallback/FallbackUploader";
import WaveformCanvas from "./WaveformCanvas";

type St = "loading" | "ready" | "error";

export default function TimelineWaveform() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [st, setSt] = useState<St>("loading");

  useEffect(() => {
    const FORCE_FALLBACK = false; // Ensure fallback is disabled after backend fixes

    if (FORCE_FALLBACK) {
      setSt("error");
      return;
    }
    
    let cancelled = false, completed = false;
    const hard = setTimeout(() => { if (!completed && !cancelled) setSt("error"); }, 2500);
    console.log("[Timeline] init start");

    import(/* webpackChunkName: "waveform" */ "waveform-playlist")
      .then((m: any) => m?.default || m)
      .then((WP: any) => {
        if (cancelled) return;
        completed = true;
        console.log("[Timeline] WP loaded:", !!WP?.init);
        const el = hostRef.current!;
        try {
          const playlist = WP.init({
            container: el,
            waveHeight: 80,
            samplesPerPixel: 512,
            state: "cursor",
            timescale: true,
            colors: { waveOutlineColor: "#22c55e" },
          });
          playlist.load([]);
          setSt("ready");
        } catch (e:any) {
          console.error("[Timeline] WP.init failed:", e?.message||e);
          setSt("error");
        }
      })
      .catch((err) => {
        console.error("[Timeline] import failed:", err?.message || err);
        completed = true;
        setSt("error");
      });

    return () => { cancelled = true; clearTimeout(hard); };
  }, []);

  if (st === "ready") return <div ref={hostRef} className="h-[260px] bg-slate-900 rounded border border-slate-800" />;
  if (st === "error") return (<><FallbackUploader/><div className="mt-2"><WaveformCanvas/></div></>);
  return <div className="h-[260px] grid place-items-center bg-slate-900 text-slate-400">Loading timeline…</div>;
}
