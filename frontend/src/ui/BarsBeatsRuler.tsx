import React, { useMemo } from "react";
import { useDawStore } from "../state/dawStore";

export default function BarsBeatsRuler({ seconds, beatTimes }:{ seconds:number; beatTimes?: number[] }) {
  const { project, pxPerSecond } = useDawStore();
  const bpm = project?.bpm || 120;
  const timeSig = project?.timeSig || [4, 4];
  const spb = 60 / bpm, barDur = spb * timeSig[0], width = seconds * pxPerSecond;
  const ticks = useMemo(() => {
    const arr: {x:number,label:string,major:boolean}[] = [];

    // Prefer beatTimes (beat->sec) when provided.
    if (Array.isArray(beatTimes) && beatTimes.length >= 2) {
      const beatsPerBar = Number(timeSig?.[0] || 4) || 4;
      let bar = 1;
      for (let i = 0; i < beatTimes.length; i++) {
        const t = Number(beatTimes[i]);
        if (!Number.isFinite(t)) continue;
        if (t > seconds + 0.01) break;
        const isBar = i % beatsPerBar === 0;
        arr.push({ x: t * pxPerSecond, label: isBar ? `${bar++}` : "", major: isBar });
      }
      return arr;
    }

    for (let t=0, bar=1; t<=seconds+0.01; t+=spb/2) {
      const isBar = Math.abs((t/barDur) - Math.round(t/barDur)) < 1e-3;
      arr.push({ x: t*pxPerSecond, label: isBar? `${bar++}` : "", major: isBar });
    }
    return arr;
  }, [beatTimes, seconds,bpm,timeSig,pxPerSecond]);

  return (
    <div className="relative h-8 bg-slate-950 text-slate-300 select-none">
      <div className="absolute inset-0" style={{ width }}>
        {ticks.map((tk,i)=> (
          <div key={i} className="absolute" style={{ left: tk.x }}>
            <div className={`w-px ${tk.major?'h-8 bg-white':'h-4 bg-slate-600'}`}/>
            {tk.major && <div className="text-xs -mt-6 ml-1">{tk.label}</div>}
          </div>
        ))}
      </div>
      <div className="absolute right-2 top-1 text-xs opacity-60">Bars/Beats</div>
    </div>
  );
}
