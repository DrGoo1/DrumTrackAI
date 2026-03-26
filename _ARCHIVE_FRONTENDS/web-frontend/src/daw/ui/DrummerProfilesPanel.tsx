import React, { useEffect, useState } from "react";
import { fetchDrummerPersonas } from "../../services/api";

interface PersonaStyle {
  [key: string]: any;
}

interface DrummerPersona {
  persona_id: string;
  display_name: string;
  archetypes: string[];
  style: PersonaStyle;
}

export const DrummerProfilesPanel: React.FC = () => {
  const [personas, setPersonas] = useState<DrummerPersona[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetchDrummerPersonas();
        if (!cancelled) {
          setPersonas(resp.personas || []);
          console.log("[Admin] Loaded drummer personas:", resp.personas || []);
          setLoading(false);
        }
      } catch (e: any) {
        if (!cancelled) {
          console.error("[Admin] Failed to load drummer personas", e);
          setErr(e?.message || "Failed to load personas");
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="p-3 bg-neutral-900 border border-neutral-800 rounded text-[12px] space-y-2">
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-cyan-300 text-sm tracking-wide">Drummer Profiles (Admin)</span>
        {err && <span className="text-[10px] text-rose-400">{err}</span>}
      </div>

      {loading && (
        <div className="text-[11px] text-neutral-400">Loading drummer personas…</div>
      )}

      {!loading && personas.length === 0 && !err && (
        <div className="text-[11px] text-neutral-400">No personas found. Run the admin analysis + persona tools.</div>
      )}

      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {personas.map((p) => {
          const s = p.style || {};
          const backbeat = s["backbeat_late_ms"] ?? 0;
          const kickD = s["kick_density"] ?? 0;
          const snareD = s["snare_density"] ?? 0;
          const cymD = s["cymbal_density"] ?? 0;
          const dyn = s["dynamics_spread"] ?? 0;
          const rideD = s["ride_density"] ?? 0;
          const rideBell = s["ride_bell_ratio"] ?? 0;

          const norm = (v: number, max: number) => Math.max(0, Math.min(1, max === 0 ? 0 : v / max));

          return (
            <div key={p.persona_id} className="border border-neutral-800 rounded bg-neutral-950/70 p-2 space-y-1">
              <div className="flex items-baseline justify-between gap-2">
                <div>
                  <div className="text-neutral-100 text-[13px] font-semibold">{p.display_name}</div>
                  <div className="text-[10px] text-neutral-500">ID: {p.persona_id}</div>
                </div>
                <div className="text-[10px] text-neutral-400 text-right">
                  Archetypes: <span className="text-neutral-200">{p.archetypes.join(", ")}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 mt-1">
                <MetricBar label="Timing (backbeat)" value={backbeat} unit="ms" min={-20} max={20} />
                <MetricBar label="Dynamics spread" value={dyn} unit="" min={0} max={25} />
                <MetricBar label="Kick density" value={kickD} unit="/bar" min={0} max={20} />
                <MetricBar label="Snare density" value={snareD} unit="/bar" min={0} max={20} />
                <MetricBar label="Cymbal density" value={cymD} unit="/bar" min={0} max={32} />
                <MetricBar label="Ride density" value={rideD} unit="/bar" min={0} max={32} />
                <MetricBar label="Ride bell" value={rideBell} unit="ratio" min={0} max={1} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface MetricBarProps {
  label: string;
  value: number;
  unit: string;
  min: number;
  max: number;
}

const MetricBar: React.FC<MetricBarProps> = ({ label, value, unit, min, max }) => {
  const clamped = Math.max(min, Math.min(max, value));
  const frac = max === min ? 0 : (clamped - min) / (max - min);
  const pct = Math.round(frac * 100);

  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[10px] text-neutral-300">
        <span>{label}</span>
        <span className="text-neutral-400">
          {value.toFixed(1)}{unit && ` ${unit}`}
        </span>
      </div>
      <div className="w-full h-1.5 bg-neutral-800 rounded overflow-hidden">
        <div
          className="h-full bg-emerald-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};
