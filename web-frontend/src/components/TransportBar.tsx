import { useDawStore } from "../state/dawStore";
import { Engine } from "../audio/engine";
import { useState } from "react";

export default function TransportBar() {
  const { project, setBpm } = useDawStore();
  const [pos, setPos] = useState(0);
  if (!project) return null;
  return (
    <div className="flex items-center gap-3 p-2 bg-slate-800 rounded-xl text-slate-100">
      <button className="px-3 py-1 rounded bg-indigo-600" onClick={() => Engine.play(pos)}>Play</button>
      <button className="px-3 py-1 rounded bg-slate-600" onClick={() => Engine.stop()}>Stop</button>
      <div className="flex items-center gap-2">
        <span>BPM</span>
        <input className="w-16 bg-slate-700 rounded px-2" type="number" value={project.bpm}
               onChange={(e) => setBpm(parseInt(e.target.value || "120", 10))} />
      </div>
      <div className="flex items-center gap-2">
        <span>Start</span>
        <input className="w-24 bg-slate-700 rounded px-2" type="number" value={pos}
               onChange={(e) => setPos(parseFloat(e.target.value || "0"))} />
      </div>
    </div>
  );
}
