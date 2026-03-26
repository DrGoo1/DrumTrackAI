import React, { useMemo, useRef, useState } from "react";
import type { LimbId } from "../constants/limbs";

export type MidiNote = {
  id: string;
  time: number;
  duration: number;
  lane: string;
  vel: number;
  aspect?: "groove" | "accent" | "fill";
  phraseMarker?: string;
  rudimentId?: string;
  limbId?: LimbId | null;
};
const LANES = ["kick","snare","hihat","tom","ride","crash","openhat","clap"] as const;

const makeNoteId = () => `note-${Math.random().toString(36).slice(2, 9)}`;

export default function PianoRoll({
  bpm,
  gridSec,
  notes,
  onChange,
}: {
  bpm: number;
  gridSec: number;
  notes: MidiNote[];
  onChange: (n: MidiNote[]) => void;
}) {
  const [zoom, setZoom] = useState(1.5);
  const [selectedLane, setSelectedLane] = useState<string | null>(null);
  const pxPerSec = 120 * zoom;
  const laneHeight = 24;
  const headerHeight = 40;
  const height = laneHeight * LANES.length + headerHeight;
  const seconds = Math.max(8, ...notes.map(n => n.time + (n.duration || gridSec))) + 4;
  const width = Math.ceil(seconds * pxPerSec);
  const ref = useRef<HTMLCanvasElement | null>(null);

  const grid = useMemo(() => ({ beat: (60 / bpm), sec: gridSec }), [bpm, gridSec]);

  const laneColors = {
    kick: "#ef4444",
    snare: "#f59e0b", 
    hihat: "#10b981",
    tom: "#8b5cf6",
    ride: "#06b6d4",
    crash: "#f97316",
    openhat: "#84cc16",
    clap: "#ec4899"
  };

  function redraw(){
    const c = ref.current; if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    c.width = Math.round(width * dpr); c.height = Math.round(height * dpr);
    c.style.width = width + "px"; c.style.height = height + "px";
    const g = c.getContext("2d")!; g.resetTransform(); g.scale(dpr, dpr);
    
    // Background
    g.fillStyle = "#0f172a"; g.fillRect(0,0,width,height);

    // Grid lines (1/64 resolution)
    g.strokeStyle = "#1e293b"; g.lineWidth = 0.5;
    for(let t=0; t<=seconds; t+=grid.sec){ 
      const x = Math.round(t*pxPerSec)+0.5; 
      g.beginPath(); g.moveTo(x, headerHeight); g.lineTo(x, height); g.stroke(); 
    }
    
    // Beat lines (heavier)
    g.strokeStyle = "#334155"; g.lineWidth = 1;
    for(let t=0; t<=seconds; t+=grid.beat){ 
      const x = Math.round(t*pxPerSec)+0.5; 
      g.beginPath(); g.moveTo(x, headerHeight); g.lineTo(x, height); g.stroke(); 
    }

    // Bar lines (heaviest)
    g.strokeStyle = "#475569"; g.lineWidth = 2;
    for(let t=0; t<=seconds; t+=(grid.beat*4)){ 
      const x = Math.round(t*pxPerSec)+0.5; 
      g.beginPath(); g.moveTo(x, headerHeight); g.lineTo(x, height); g.stroke(); 
    }

    // Time ruler
    g.fillStyle = "#1e293b"; g.fillRect(0, 0, width, headerHeight);
    g.strokeStyle = "#475569"; g.lineWidth = 1;
    g.beginPath(); g.moveTo(0, headerHeight-0.5); g.lineTo(width, headerHeight-0.5); g.stroke();
    
    g.fillStyle = "#94a3b8"; g.font = "11px monospace";
    for(let bar=0; bar*grid.beat*4<=seconds; bar++){
      const x = bar * grid.beat * 4 * pxPerSec;
      g.fillText(`${bar+1}`, x + 4, 16);
    }

    // Lanes
    for(let i=0; i<LANES.length; i++){ 
      const y = headerHeight + i * laneHeight;
      const isSelected = selectedLane === LANES[i];
      g.fillStyle = isSelected ? "#1e293b" : (i%2 ? "#0f172a" : "#1a202c"); 
      g.fillRect(0, y, width, laneHeight);
      
      // Lane separator
      g.strokeStyle = "#334155"; g.lineWidth = 0.5;
      g.beginPath(); g.moveTo(0, y+laneHeight-0.5); g.lineTo(width, y+laneHeight-0.5); g.stroke();
      
      // Lane label
      const laneColor = laneColors[LANES[i] as keyof typeof laneColors] || "#60a5fa";
      g.fillStyle = laneColor; 
      g.fillRect(2, y+2, 8, laneHeight-4);
      g.fillStyle = "#e2e8f0"; g.font = "12px sans-serif";
      g.fillText(LANES[i].toUpperCase(), 14, y + laneHeight/2 + 4);
    }

    // Notes
    for(const n of notes){ 
      const x = Math.round(n.time * pxPerSec); 
      const i = LANES.indexOf(n.lane as any); 
      if(i < 0) continue; 
      const y = headerHeight + i * laneHeight + 2;
      const laneColor = laneColors[n.lane as keyof typeof laneColors] || "#60a5fa";
      const noteWidth = Math.max(8, pxPerSec * (n.duration || grid.sec));
      
      // Note shadow
      g.fillStyle = "rgba(0,0,0,0.3)";
      g.fillRect(x+1, y+1, noteWidth, laneHeight-5);
      
      // Note body
      const highlightFill = n.rudimentId || n.aspect === "fill";
      g.fillStyle = highlightFill ? "#d946ef" : laneColor;
      g.fillRect(x, y, noteWidth, laneHeight-4);
      
      // Velocity indicator
      const velHeight = Math.round((laneHeight-4) * n.vel);
      g.fillStyle = "rgba(255,255,255,0.3)";
      g.fillRect(x, y + (laneHeight-4) - velHeight, noteWidth, velHeight);

      if (n.rudimentId || n.phraseMarker) {
        const label = n.rudimentId ?? n.phraseMarker ?? "";
        g.fillStyle = "rgba(15,23,42,0.8)";
        g.fillRect(x, y - 10, Math.max(24, Math.min(noteWidth, 80)), 10);
        g.fillStyle = "#fce7f3";
        g.font = "9px 'JetBrains Mono', monospace";
        g.fillText(label.slice(0, 10), x + 2, y - 2);
      }
    }
  }

  React.useEffect(redraw, [notes, width, height, pxPerSec, bpm, gridSec, selectedLane]);

  function posToNote(e: React.MouseEvent){
    const r = ref.current!.getBoundingClientRect();
    const x = e.clientX - r.left; 
    const y = e.clientY - r.top - headerHeight;
    const time = Math.round(((x/pxPerSec)/grid.sec)) * grid.sec;
    const laneIndex = Math.max(0, Math.min(LANES.length-1, Math.floor(y / laneHeight)));
    const lane = LANES[laneIndex] || "kick";
    return { time, lane, laneIndex } as const;
  }

  function onClick(e: React.MouseEvent){
    const { time, lane } = posToNote(e);
    const hit = notes.findIndex(n => n.lane === lane && Math.abs(n.time - time) < grid.sec/2);
    if (hit >= 0) {
      const next = [...notes]; 
      next.splice(hit, 1); 
      onChange(next);
    } else {
      const velocity = 0.7 + Math.random() * 0.3; // Humanize velocity
      onChange([...notes, { id: makeNoteId(), time, lane, vel: velocity, duration: grid.sec }]);
    }
  }

  function onMouseMove(e: React.MouseEvent){
    const { laneIndex } = posToNote(e);
    setSelectedLane(LANES[laneIndex]);
  }

  function clearAll() {
    onChange([]);
  }

  function quantize() {
    const quantized = notes.map(n => ({
      ...n,
      time: Math.round(n.time / grid.sec) * grid.sec
    }));
    onChange(quantized);
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
      <div className="flex items-center justify-between mb-3 text-sm text-slate-300">
        <div className="font-medium">DCSM Piano Roll (1/64 Grid)</div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="opacity-70">Zoom</span>
            <button 
              className="px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-xs" 
              onClick={() => setZoom(z => Math.max(0.5, z * 0.8))}
            >
              −
            </button>
            <div className="w-12 text-center text-xs">{zoom.toFixed(1)}×</div>
            <button 
              className="px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-xs" 
              onClick={() => setZoom(z => Math.min(4, z * 1.25))}
            >
              +
            </button>
          </div>
          <button 
            className="px-3 py-1 rounded bg-orange-600 hover:bg-orange-700 text-xs font-medium"
            onClick={quantize}
          >
            Quantize
          </button>
          <button 
            className="px-3 py-1 rounded bg-red-600 hover:bg-red-700 text-xs font-medium"
            onClick={clearAll}
          >
            Clear
          </button>
          <div className="text-xs opacity-70">
            {notes.length} notes
          </div>
        </div>
      </div>
      <div className="overflow-auto border border-slate-700 rounded bg-slate-950">
        <canvas 
          ref={ref} 
          onClick={onClick}
          onMouseMove={onMouseMove}
          onMouseLeave={() => setSelectedLane(null)}
          className="cursor-crosshair"
        />
      </div>
      <div className="mt-2 text-xs text-slate-400">
        Click to add/remove notes • Hover to highlight lanes • 1/64 note resolution
      </div>
    </div>
  );
}
