import React, { useEffect, useRef, useState } from "react";
import { Engine } from "../audio/engine";

export type MixerTrack = { key: string; name: string; color?: string };

export default function Mixer({ tracks }: { tracks: MixerTrack[] }) {
  const [meters, setMeters] = useState<Record<string, number>>({});
  const [muted, setMuted] = useState<Record<string, boolean>>({});
  const [solo, setSolo] = useState<Record<string, boolean>>({});
  const raf = useRef(0);

  useEffect(() => {
    function tick(){
      const next: Record<string, number> = {};
      for (const t of tracks) next[t.key] = Engine.getMeter(t.key);
      setMeters(next);
      raf.current = requestAnimationFrame(tick);
    }
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [tracks.length]);

  const toggleMute = (key: string) => {
    const newMuted = !muted[key];
    setMuted(prev => ({ ...prev, [key]: newMuted }));
    Engine.setMute(key, newMuted);
  };

  const toggleSolo = (key: string) => {
    const newSolo = !solo[key];
    setSolo(prev => ({ ...prev, [key]: newSolo }));
    Engine.setSolo(key, newSolo);
  };

  return (
    <div className="w-[280px] shrink-0 bg-slate-900 border-r border-slate-800 p-3 space-y-3 overflow-y-auto">
      <div className="text-slate-300 font-medium mb-2">DCSM Mixer</div>
      {tracks.map((t) => (
        <div key={t.key} className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full" style={{ background: t.color || "#60a5fa" }} />
              <div className="text-sm text-slate-200 truncate font-medium" title={t.name}>{t.name}</div>
            </div>
            <div className="flex gap-1">
              <button 
                className={`px-2 py-1 text-xs rounded font-medium ${muted[t.key] ? 'bg-red-600 text-white' : 'bg-slate-700 hover:bg-slate-600'}`}
                onClick={() => toggleMute(t.key)}
              >
                M
              </button>
              <button 
                className={`px-2 py-1 text-xs rounded font-medium ${solo[t.key] ? 'bg-yellow-600 text-white' : 'bg-slate-700 hover:bg-slate-600'}`}
                onClick={() => toggleSolo(t.key)}
              >
                S
              </button>
            </div>
          </div>
          <div className="flex gap-3 items-end">
            <div className="h-40 w-6 bg-slate-800 rounded overflow-hidden relative border border-slate-700">
              <div 
                className="absolute bottom-0 left-0 right-0 transition-all duration-75" 
                style={{ 
                  height: `${Math.round(((meters[t.key] || 0)) * 100)}%`, 
                  background: `linear-gradient(to top, ${t.color || "#60a5fa"}, ${t.color || "#60a5fa"}80)` 
                }} 
              />
              <div className="absolute inset-0 pointer-events-none">
                {[0.25, 0.5, 0.75].map(level => (
                  <div 
                    key={level}
                    className="absolute left-0 right-0 h-px bg-slate-600"
                    style={{ bottom: `${level * 100}%` }}
                  />
                ))}
              </div>
            </div>
            <div className="flex-1">
              <div className="text-xs text-slate-400 mb-1">Volume</div>
              <input 
                type="range" 
                min={0} 
                max={1.5} 
                step={0.01} 
                defaultValue={1} 
                onChange={(e) => Engine.setGain(t.key, parseFloat(e.target.value))} 
                className="w-full accent-blue-500"
              />
              <div className="text-xs text-slate-500 mt-1 text-center">
                {Math.round(((meters[t.key] || 0)) * 100)}%
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
