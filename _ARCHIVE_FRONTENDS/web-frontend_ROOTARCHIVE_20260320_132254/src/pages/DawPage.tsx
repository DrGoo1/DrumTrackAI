import { useEffect } from "react";
import { useDawStore } from "../state/dawStore";
import TransportBar from "../components/TransportBar";
import Ruler from "../components/Ruler";
import TrackLane from "../components/TrackLane";
import { Engine } from "../audio/engine";

export default function DawPage() {
  const { project, newProject, pxPerSecond, setZoom } = useDawStore();

  useEffect(() => { if (!project) newProject("Session 1"); }, [project]);
  useEffect(() => { if (project) { Engine.ensureStarted(); } }, [project]);

  if (!project) return null;
  const duration = project.lengthSec;

  return (
    <div className="p-4 space-y-3">
      <TransportBar />
      <div className="flex items-center gap-2">
        <span className="text-slate-300">Zoom</span>
        <button className="px-2 py-1 bg-slate-700 rounded" onClick={() => setZoom(pxPerSecond/1.25)}>-</button>
        <span className="text-slate-200">{pxPerSecond.toFixed(1)}x</span>
        <button className="px-2 py-1 bg-slate-700 rounded" onClick={() => setZoom(pxPerSecond*1.25)}>+</button>
      </div>
      <Ruler durationSec={duration} zoom={pxPerSecond} />
      {project?.tracks?.map(t => (
        <TrackLane key={t.id} track={t} zoom={pxPerSecond} />
      )) || []}
    </div>
  );
}
