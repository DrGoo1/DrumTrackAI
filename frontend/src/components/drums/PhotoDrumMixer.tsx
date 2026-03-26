import React, { useMemo, useState } from "react";
import { Engine } from "../../audio/engine";

export type PhotoMixerChannel = {
  id: string;
  label: string;
  engineKey: string;
};

const CHANNELS: PhotoMixerChannel[] = [
  { id: "kick", label: "Kick", engineKey: "__drums__" },
  { id: "kick_sub", label: "Kick Sub", engineKey: "__drums__" },
  { id: "snare_top", label: "Snare Top", engineKey: "__drums__" },
  { id: "snare_bottom", label: "Snare Bottom", engineKey: "__drums__" },
  { id: "tom1", label: "Tom 1", engineKey: "__drums__" },
  { id: "tom2", label: "Tom 2", engineKey: "__drums__" },
  { id: "tom3", label: "Tom 3", engineKey: "__drums__" },
  { id: "tom4", label: "Tom 4", engineKey: "__drums__" },
  { id: "tom5", label: "Tom 5", engineKey: "__drums__" },
  { id: "tom_fx", label: "Tom FX", engineKey: "__drums__" },
  { id: "hat", label: "Hat (st)", engineKey: "__drums__" },
  { id: "ride", label: "Ride", engineKey: "__drums__" },
  { id: "spot_ride", label: "Spot Ride", engineKey: "__drums__" },
  { id: "crash", label: "Crash", engineKey: "__drums__" },
  { id: "oh", label: "OH (st)", engineKey: "__drums__" },
  { id: "room", label: "Room (st)", engineKey: "__drums__" },
  { id: "master", label: "Master", engineKey: "__drums__" },
];

function clamp01(v: number) {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(1, v));
}

export default function PhotoDrumMixer(props: {
  widthPx?: number;
  backgroundUrl?: string;
}) {
  const widthPx = props.widthPx ?? 420;
  const backgroundUrl = props.backgroundUrl ?? "/images/Drum_Mixer.jpg";

  const initialGains = useMemo(() => {
    const m: Record<string, number> = {};
    for (const ch of CHANNELS) m[ch.id] = ch.id === "master" ? 1 : 0.9;
    return m;
  }, []);

  const [gain, setGain] = useState<Record<string, number>>(initialGains);
  const [mute, setMute] = useState<Record<string, boolean>>({});
  const [solo, setSolo] = useState<Record<string, boolean>>({});

  const activeSolo = useMemo(() => Object.values(solo).some(Boolean), [solo]);

  const channelPositions = useMemo(() => {
    const n = CHANNELS.length;
    const positions: Array<{ id: string; leftPct: number }> = [];
    for (let i = 0; i < n; i++) {
      const leftPct = ((i + 0.5) / n) * 100;
      positions.push({ id: CHANNELS[i].id, leftPct });
    }
    return positions;
  }, []);

  const applyEngineGain = (chId: string, value01: number) => {
    const ch = CHANNELS.find((c) => c.id === chId);
    if (!ch) return;
    try {
      Engine.setGain(ch.engineKey, clamp01(value01));
    } catch {
      // ignore
    }
  };

  const applyEngineMuteSolo = (chId: string, nextMute?: boolean, nextSolo?: boolean) => {
    const ch = CHANNELS.find((c) => c.id === chId);
    if (!ch) return;

    const m = nextMute ?? !!mute[chId];
    const s = nextSolo ?? !!solo[chId];
    const someSolo = activeSolo || s;
    const effectiveMute = m || (someSolo && !s);

    try {
      Engine.setMute(ch.engineKey, effectiveMute);
    } catch {
      // ignore
    }

    try {
      Engine.setSolo(ch.engineKey, s);
    } catch {
      // ignore
    }
  };

  return (
    <div
      className="shrink-0 border-r border-slate-800 bg-slate-950"
      style={{ width: `${widthPx}px` }}
    >
      <div className="relative w-full select-none">
        <img
          src={backgroundUrl}
          alt="Drum Mixer"
          className="block w-full h-auto"
          draggable={false}
        />

        {channelPositions.map((pos) => {
          const ch = CHANNELS.find((c) => c.id === pos.id);
          if (!ch) return null;

          const g = gain[ch.id] ?? 1;
          const isMuted = !!mute[ch.id];
          const isSolo = !!solo[ch.id];

          return (
            <div
              key={ch.id}
              className="absolute"
              style={{
                left: `${pos.leftPct}%`,
                top: "12%",
                transform: "translateX(-50%)",
                width: "5.2%",
                height: "82%",
              }}
            >
              <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] text-slate-200 bg-slate-900/70 px-1 rounded whitespace-nowrap">
                {ch.label}
              </div>

              <div className="absolute left-1/2 -translate-x-1/2 top-[18%] w-[18px]">
                <input
                  aria-label={`${ch.label} volume`}
                  className="w-[120px] h-[18px] origin-left rotate-[-90deg] accent-cyan-400"
                  type="range"
                  min={0}
                  max={1.5}
                  step={0.01}
                  value={g}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value);
                    setGain((prev) => ({ ...prev, [ch.id]: v }));
                    applyEngineGain(ch.id, v);
                  }}
                />
              </div>

              <div className="absolute bottom-[10%] left-1/2 -translate-x-1/2 flex flex-col gap-1">
                <button
                  className={`w-6 h-6 text-xs font-bold rounded border ${
                    isSolo
                      ? "bg-yellow-600 text-white border-yellow-400"
                      : "bg-slate-900/70 text-slate-200 border-slate-600"
                  }`}
                  onClick={() => {
                    const next = !isSolo;
                    setSolo((prev) => ({ ...prev, [ch.id]: next }));
                    applyEngineMuteSolo(ch.id, undefined, next);
                  }}
                >
                  S
                </button>
                <button
                  className={`w-6 h-6 text-xs font-bold rounded border ${
                    isMuted
                      ? "bg-red-600 text-white border-red-400"
                      : "bg-slate-900/70 text-slate-200 border-slate-600"
                  }`}
                  onClick={() => {
                    const next = !isMuted;
                    setMute((prev) => ({ ...prev, [ch.id]: next }));
                    applyEngineMuteSolo(ch.id, next, undefined);
                  }}
                >
                  M
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
