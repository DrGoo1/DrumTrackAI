// src/pages/Studio.tsx
import React from "react";
import TransportBar from "../ui/TransportBar";
import BarsBeatsRuler from "../ui/BarsBeatsRuler";
import TimelineWaveform from "../ui/TimelineWaveform";

export default function Studio() {
  const totalSec = 180;
  return (
    <div className="h-screen w-full bg-slate-950 text-slate-100 flex flex-col">
      <div className="p-2 border-b border-slate-800"><TransportBar/></div>
      <BarsBeatsRuler seconds={totalSec}/>
      <div className="flex-1 flex overflow-hidden">
        <div className="w-[300px] shrink-0 p-2 space-y-2 bg-slate-950 border-r border-slate-800">
          <div className="text-xs text-slate-400">Mixer Panel</div>
        </div>
        <div className="flex-1 overflow-auto p-2">
          <TimelineWaveform />
          {/* MIDI editors/lanes mount below */}
        </div>
      </div>
    </div>
  );
}
