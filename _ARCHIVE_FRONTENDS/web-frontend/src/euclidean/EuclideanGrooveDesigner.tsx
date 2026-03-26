import React, { useMemo, useState } from "react";
import {
  EuclideanLaneConfig,
  buildEuclideanPattern,
  euclideanPattern,
} from "./euclidean";
import { EUCLIDEAN_PRESETS, EuclideanPreset } from "./presets";

interface EuclideanGrooveDesignerProps {
  onPreviewPattern?: (events: ReturnType<typeof buildEuclideanPattern>, tempo: number) => void;
  onSendToDCSM?: (events: ReturnType<typeof buildEuclideanPattern>, tempo: number) => void;
}

export const EuclideanGrooveDesigner: React.FC<EuclideanGrooveDesignerProps> = ({
  onPreviewPattern,
  onSendToDCSM,
}) => {
  const [tempo, setTempo] = useState(120);
  const [bars, setBars] = useState(4);
  const [swing, setSwing] = useState(0.18);
  const [lanes, setLanes] = useState<EuclideanLaneConfig[]>(() => EUCLIDEAN_PRESETS[0].lanes);
  const [selectedPresetId, setSelectedPresetId] = useState<string>(EUCLIDEAN_PRESETS[0].id);

  const patternEvents = useMemo(
    () => buildEuclideanPattern(lanes, bars),
    [lanes, bars]
  );

  function updateLane(id: string, patch: Partial<EuclideanLaneConfig>) {
    setLanes((prev) =>
      prev.map((lane) => (lane.id === id ? { ...lane, ...patch } : lane))
    );
  }

  function handleClickStep(laneIndex: number, stepIndex: number) {
    const lane = lanes[laneIndex];
    const pattern = euclideanPattern(lane.steps, lane.hits);
    const idx = (stepIndex + lane.rotate) % lane.steps;
    const currentHit = pattern[idx] === 1;
    const newHits = Math.max(
      0,
      Math.min(lane.steps, lane.hits + (currentHit ? -1 : 1)),
    );
    updateLane(lane.id, { hits: newHits });
  }

  function loadPreset(preset: EuclideanPreset) {
    setSelectedPresetId(preset.id);
    setLanes(preset.lanes);
  }

  function handlePreview() {
    if (onPreviewPattern) onPreviewPattern(patternEvents, tempo);
  }

  function handleSendToDCSM() {
    if (onSendToDCSM) onSendToDCSM(patternEvents, tempo);
  }

  return (
    <div className="flex flex-col h-full bg-[#0f0f14] text-slate-100 rounded-xl border border-slate-800 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-[#11141f] border-b border-slate-800">
        <div className="text-xs tracking-wide uppercase text-slate-400">
          Euclidean Groove Designer
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">Preset</span>
          <select
            className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
            value={selectedPresetId}
            onChange={(e) => {
              const p = EUCLIDEAN_PRESETS.find((p) => p.id === e.target.value);
              if (p) loadPreset(p);
            }}
          >
            {EUCLIDEAN_PRESETS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-1 min-h-[520px]">
        <div className="w-64 border-r border-slate-800 overflow-y-auto">
          {lanes.map((lane) => (
            <div
              key={lane.id}
              className="m-2 p-2 rounded-lg bg-[#1a1d26] border border-slate-700 text-xs"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold">{lane.label}</span>
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: lane.color }}
                />
              </div>
              <div className="grid grid-cols-2 gap-1 mb-1">
                <label className="flex flex-col">
                  <span className="text-[10px] text-slate-400">Steps</span>
                  <input
                    type="number"
                    className="bg-slate-900 border border-slate-700 rounded px-1 py-0.5"
                    value={lane.steps}
                    min={1}
                    max={64}
                    onChange={(e) =>
                      updateLane(lane.id, { steps: parseInt(e.target.value, 10) || 0 })
                    }
                  />
                </label>
                <label className="flex flex-col">
                  <span className="text-[10px] text-slate-400">Hits</span>
                  <input
                    type="number"
                    className="bg-slate-900 border border-slate-700 rounded px-1 py-0.5"
                    value={lane.hits}
                    min={0}
                    max={lane.steps}
                    onChange={(e) =>
                      updateLane(lane.id, { hits: parseInt(e.target.value, 10) || 0 })
                    }
                  />
                </label>
                <label className="flex flex-col">
                  <span className="text-[10px] text-slate-400">Accent</span>
                  <input
                    type="number"
                    className="bg-slate-900 border border-slate-700 rounded px-1 py-0.5"
                    value={lane.accents}
                    min={0}
                    max={lane.hits}
                    onChange={(e) =>
                      updateLane(lane.id, { accents: parseInt(e.target.value, 10) || 0 })
                    }
                  />
                </label>
                <label className="flex flex-col">
                  <span className="text-[10px] text-slate-400">Rotate</span>
                  <input
                    type="number"
                    className="bg-slate-900 border border-slate-700 rounded px-1 py-0.5"
                    value={lane.rotate}
                    min={0}
                    max={lane.steps - 1}
                    onChange={(e) =>
                      updateLane(lane.id, { rotate: parseInt(e.target.value, 10) || 0 })
                    }
                  />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-1">
                <label className="flex flex-col">
                  <span className="text-[10px] text-slate-400">Vel</span>
                  <input
                    type="number"
                    className="bg-slate-900 border border-slate-700 rounded px-1 py-0.5"
                    value={lane.velocity}
                    min={1}
                    max={127}
                    onChange={(e) =>
                      updateLane(lane.id, { velocity: parseInt(e.target.value, 10) || 1 })
                    }
                  />
                </label>
                <label className="flex flex-col">
                  <span className="text-[10px] text-slate-400">Accent Vel</span>
                  <input
                    type="number"
                    className="bg-slate-900 border border-slate-700 rounded px-1 py-0.5"
                    value={lane.accentVelocity}
                    min={1}
                    max={127}
                    onChange={(e) =>
                      updateLane(lane.id, {
                        accentVelocity: parseInt(e.target.value, 10) || 1,
                      })
                    }
                  />
                </label>
              </div>
            </div>
          ))}
        </div>

        <div className="flex-1 relative flex items-center justify-center bg-[#0f1018] border-r border-slate-800">
          <OrbitSequencer lanes={lanes} onClickStep={handleClickStep} />
        </div>

        <div className="w-64 p-3 bg-[#111319] flex flex-col text-xs">
          <div className="font-semibold mb-2">DrumBrain Controls</div>
          <label className="flex flex-col mb-2">
            <span className="text-[10px] text-slate-400">Style</span>
            <select className="bg-slate-900 border border-slate-700 rounded px-2 py-1">
              <option>Rock Tight</option>
              <option>Funk</option>
              <option>Neo-Soul</option>
              <option>Afro 12/8</option>
            </select>
          </label>
          <label className="flex flex-col mb-2">
            <span className="text-[10px] text-slate-400">Drummer</span>
            <select className="bg-slate-900 border border-slate-700 rounded px-2 py-1">
              <option>Generic Studio</option>
              <option>Porcaro AI</option>
              <option>Purdie AI</option>
            </select>
          </label>
          <label className="flex flex-col mb-2">
            <span className="text-[10px] text-slate-400">Humanize</span>
            <input type="range" min={0} max={1} step={0.01} defaultValue={0.7} />
          </label>
          <label className="flex flex-col mb-2">
            <span className="text-[10px] text-slate-400">Ghost Notes</span>
            <input type="range" min={0} max={1} step={0.01} defaultValue={0.6} />
          </label>
          <label className="flex items-center gap-1 mb-3">
            <input type="checkbox" defaultChecked />
            <span>Articulation Mode</span>
          </label>
          <button
            className="mt-auto bg-purple-600 hover:bg-purple-500 text-white rounded px-2 py-1 mb-1"
            onClick={handleSendToDCSM}
          >
            Send to DCSM
          </button>
          <button className="bg-slate-800 hover:bg-slate-700 rounded px-2 py-1 text-slate-100">
            Randomize Seed
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 px-4 py-2 bg-[#11141f] border-t border-slate-800 text-xs">
        <button
          className="w-7 h-7 rounded-full bg-green-500 hover:bg-green-400 flex items-center justify-center text-black"
          onClick={handlePreview}
        >
          ▶
        </button>
        <span className="text-[10px] text-slate-400">Tempo</span>
        <input
          type="number"
          value={tempo}
          onChange={(e) => setTempo(parseInt(e.target.value, 10) || 0)}
          className="w-14 bg-slate-900 border border-slate-700 rounded px-1 py-0.5"
        />
        <span className="text-[10px] text-slate-400">BPM</span>

        <span className="ml-4 text-[10px] text-slate-400">Bars</span>
        <input
          type="number"
          value={bars}
          min={1}
          max={16}
          onChange={(e) => setBars(parseInt(e.target.value, 10) || 1)}
          className="w-10 bg-slate-900 border border-slate-700 rounded px-1 py-0.5"
        />

        <span className="ml-4 text-[10px] text-slate-400">Swing</span>
        <input
          type="range"
          min={0}
          max={0.5}
          step={0.01}
          value={swing}
          onChange={(e) => setSwing(parseFloat(e.target.value))}
          className="w-32"
        />
        <span className="text-[10px] text-slate-300">{Math.round(swing * 100)}%</span>

        <span className="ml-auto text-[10px] text-slate-400">Kit</span>
        <select className="bg-slate-900 border border-slate-700 rounded px-2 py-1">
          <option>DrumTracKAI Studio Kit</option>
          <option>Dry Vintage Kit</option>
          <option>Big Room Kit</option>
        </select>
      </div>
    </div>
  );
};

interface OrbitSequencerProps {
  lanes: EuclideanLaneConfig[];
  onClickStep?: (laneIndex: number, stepIndex: number) => void;
}

const OrbitSequencer: React.FC<OrbitSequencerProps> = ({ lanes, onClickStep }) => {
  const maxSteps = Math.max(...lanes.map((l) => l.steps));

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      {lanes.map((lane, laneIdx) => {
        const steps = lane.steps;
        // Make the rings large and well-centered so the Euclidean circle
        // dominates the middle column on a typical desktop viewport.
        const radius = 180 + laneIdx * 70;
        const angleStep = (2 * Math.PI) / Math.max(steps, 1);
        const pattern = euclideanPattern(steps, lane.hits);

        const cx = radius + 60;
        const cy = radius + 60;

        return (
          <svg
            key={lane.id}
            className="absolute"
            style={{
              width: radius * 2 + 120,
              height: radius * 2 + 120,
              overflow: "visible",
            }}
          >
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              stroke={lane.color}
              strokeWidth={1}
              fill="none"
              opacity={0.3}
            />
            {Array.from({ length: steps }).map((_, stepIdx) => {
              const angle = stepIdx * angleStep - Math.PI / 2;
              const x = cx + radius * Math.cos(angle);
              const y = cy + radius * Math.sin(angle);

              const rotatedIdx = (stepIdx + lane.rotate) % steps;
              const isHit = pattern[rotatedIdx] === 1;

              return (
                <circle
                  key={stepIdx}
                  cx={x}
                  cy={y}
                  r={isHit ? 4 : 2}
                  fill={isHit ? lane.color : "#444a60"}
                  className="cursor-pointer transition-transform"
                  onClick={() => onClickStep && onClickStep(laneIdx, stepIdx)}
                />
              );
            })}
          </svg>
        );
      })}
    </div>
  );
};
