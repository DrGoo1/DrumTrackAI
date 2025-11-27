import React, { useMemo } from "react";
import { useMidi } from "../../midi/midiStore";
import type { MidiNote } from "../../midi/types";
import { useLimbStore, LimbId } from "../state/limbStore";

interface LimbViewProps {
  trackId: string;
  clipId: string;
}

const LIMB_ORDER: LimbId[] = ["RH", "LH", "RF", "LF"];

// Simple inference for now when limb info is not present:
// kick -> RF/LF, snare/toms -> LH, hats/ride/crash -> RH
function inferLimbForNote(n: MidiNote): LimbId {
  const p = n.pitch;
  if (p === 36 || p === 35) return "RF"; // main kick
  if (p === 38 || p === 40 || (p >= 41 && p <= 48)) return "LH"; // snare/toms
  if (p === 44 || p === 42 || p === 46 || (p >= 49 && p <= 59)) return "RH"; // hats/cymbals
  return "LH";
}

export const LimbView: React.FC<LimbViewProps> = ({ trackId, clipId }) => {
  const { song, getClip } = useMidi();
  const { mapping } = useLimbStore();
  const clip = getClip(trackId, clipId);

  const notesByLimb = useMemo(() => {
    const out: Record<LimbId, MidiNote[]> = { RH: [], LH: [], RF: [], LF: [] };
    if (!clip) return out;
    for (const n of clip.notes || []) {
      const limb = inferLimbForNote(n);
      out[limb].push(n);
    }
    return out;
  }, [clip]);

  if (!clip) {
    return <div className="text-[11px] text-neutral-500">No clip selected.</div>;
  }

  const ppq = song.ppq;
  const durationTicks = Math.max(1, clip.endTick - clip.startTick);

  return (
    <div className="w-full h-48 bg-neutral-950 border border-neutral-800 rounded p-2 flex flex-col gap-1 text-[11px]">
      <div className="flex items-center justify-between mb-1">
        <span className="text-neutral-300 font-medium">Limb View</span>
        <span className="text-neutral-500">Handedness: {mapping.handedness}</span>
      </div>
      <div className="flex-1 flex flex-col gap-1 overflow-hidden">
        {LIMB_ORDER.map((limb) => {
          const notes = notesByLimb[limb];
          return (
            <div key={limb} className="flex items-center gap-1 h-1/4">
              <div className="w-20 text-right pr-1 text-neutral-400">
                {limb}
              </div>
              <div className="flex-1 h-full relative bg-neutral-900 rounded overflow-hidden">
                <div className="absolute inset-0 flex">
                  {notes.map((n) => {
                    const relStart = (n.t0 - clip.startTick) / durationTicks;
                    const relLen = Math.max(0.01, (n.t1 - n.t0) / durationTicks);
                    const left = `${Math.max(0, Math.min(1, relStart)) * 100}%`;
                    const width = `${Math.max(1, Math.min(1, relLen)) * 100}%`;
                    const velNorm = Math.min(1, Math.max(0, n.vel / 127));
                    const isGhost = velNorm < 0.35;
                    const bg = `rgba(${Math.round(40 + 120 * velNorm)}, ${Math.round(
                      200 * velNorm
                    )}, ${Math.round(160)}, ${isGhost ? 0.4 : 0.85})`;
                    return (
                      <div
                        key={n.id}
                        className="absolute top-[3px] bottom-[3px] rounded-sm border border-emerald-500/40"
                        style={{ left, width, backgroundColor: bg, opacity: isGhost ? 0.6 : 1 }}
                        title={`pitch ${n.pitch} vel ${n.vel}`}
                      />
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
