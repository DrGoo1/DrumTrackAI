import React, { useEffect, useMemo, useState } from "react";
import { useV3Store } from "../../state/v3/store";
import type { DrumGenerationConfig } from "../../types/drumTrack";
import { V3Knob } from "./V3Knob";

const generationModes: Array<{ value: DrumGenerationConfig["generationMode"]; label: string }> = [
  { value: "template", label: "Template" },
  { value: "ai_variation", label: "AI Variation" },
  { value: "full_ai", label: "Full AI" },
];

type FieldProps = {
  label: string;
  children: React.ReactNode;
};

function Field(props: FieldProps) {
  return (
    <label className="block">
      <div className="text-[11px] text-slate-400">{props.label}</div>
      <div className="mt-1">{props.children}</div>
    </label>
  );
}

export function V3GlobalDefaultsPanel() {
  const gd = useV3Store((s) => s.globalDefaults);
  const setGlobalDefaults = useV3Store((s) => s.setGlobalDefaults);
  const upsertGlobalPreset = useV3Store((s) => s.upsertGlobalPreset);
  const removeGlobalPreset = useV3Store((s) => s.removeGlobalPreset);
  const setDrummerPickerTarget = useV3Store((s) => s.setDrummerPickerTarget);
  const setDrummerPickerOpen = useV3Store((s) => s.setDrummerPickerOpen);
  const presetPreview = useV3Store((s) => s.ui.presetPreview);
  const setPresetPreview = useV3Store((s) => s.setPresetPreview);
  const selectedSectionId = useV3Store((s) => s.selection.selectedSectionId);
  const sectionOverrides = useV3Store((s) => s.sectionOverrides);

  const overrideKeys = useMemo(() => {
    const out = new Set<string>();
    if (!selectedSectionId) return out;
    const sec = sectionOverrides[selectedSectionId];
    if (!sec) return out;
    const p: any = sec.overrides || {};
    const inherit: any = sec.inherit || {};

    const hasGroup = (g: string) => inherit[g] === "override";
    if (hasGroup("identity")) {
      if (p.style !== undefined) out.add("style");
      if (p.drummer !== undefined || p.publicDrummerId !== undefined) out.add("drummer");
    }
    if (hasGroup("generation")) {
      if (p.generationMode !== undefined) out.add("generationMode");
      if (p.intensity !== undefined) out.add("intensity");
      if (p.variation !== undefined) out.add("variation");
    }
    if (hasGroup("humanization")) {
      if (p.humanize !== undefined) out.add("humanize");
      if (p.humanizeAmount !== undefined) out.add("humanizeAmount");
      if (p.swingAmount !== undefined) out.add("swingAmount");
      if (p.ghostNoteAmount !== undefined) out.add("ghostNoteAmount");
    }
    if (hasGroup("groove")) {
      if (p.selectedGrooveId !== undefined) out.add("selectedGrooveId");
      if (p.grooveUse !== undefined) out.add("grooveUse");
      if (p.fillGrooveId !== undefined) out.add("fillGrooveId");
    }
    return out;
  }, [sectionOverrides, selectedSectionId]);

  const [drummerOptions, setDrummerOptions] = useState<Array<{ id: string; display_name: string }>>([]);
  const [drummerError, setDrummerError] = useState<string | null>(null);

  const [availablePresets, setAvailablePresets] = useState<any[]>([]);
  const [presetError, setPresetError] = useState<string | null>(null);
  const [presetAddId, setPresetAddId] = useState<string>("");
  const [presetAddTier, setPresetAddTier] = useState<"song" | "flavor" | "utility">("flavor");
  const [presetAddIntensity, setPresetAddIntensity] = useState<number>(70);

  const [presetExplainBusy, setPresetExplainBusy] = useState(false);
  const [presetExplainError, setPresetExplainError] = useState<string | null>(null);
  const [presetExplain, setPresetExplain] = useState<any | null>(null);

  const drummerNameById = useMemo(() => {
    const out: Record<string, string> = {};
    for (const d of drummerOptions || []) {
      const id = String((d as any)?.id || "");
      if (!id) continue;
      out[id] = String((d as any)?.display_name || id);
    }
    return out;
  }, [drummerOptions]);

  const selectedDrummerId = String(gd.publicDrummerId || gd.drummer || "").trim();
  const selectedDrummerLabel = selectedDrummerId ? drummerNameById[selectedDrummerId] || selectedDrummerId : "None";

  const presetById = useMemo(() => {
    const out: Record<string, any> = {};
    for (const p of availablePresets || []) {
      const id = String((p as any)?.preset_id || (p as any)?.presetId || "").trim();
      if (!id) continue;
      out[id] = p;
    }
    return out;
  }, [availablePresets]);

  const presetAffectedKeys = useMemo(() => {
    const out = new Set<string>();
    const stack = Array.isArray((gd as any)?.presetStack) ? ((gd as any).presetStack as any[]) : [];
    for (const item of stack) {
      const pid = String((item as any)?.presetId || "");
      const preset = presetById[pid];
      const deltas = (preset as any)?.deltas || {};
      if (!deltas || typeof deltas !== "object") continue;
      for (const k of Object.keys(deltas)) {
        if (k === "fillControls" && deltas.fillControls && typeof deltas.fillControls === "object") {
          for (const kk of Object.keys(deltas.fillControls)) out.add(`fillControls.${kk}`);
        } else {
          out.add(k);
        }
      }
    }
    return out;
  }, [gd, presetById]);

  const effectiveFromPresets = useMemo(() => {
    const clamp01 = (v: any) => Math.max(0, Math.min(1, Number(v) || 0));
    const applyDeltas = (base: any, deltas: any, t: number) => {
      const out: any = { ...base };
      for (const k of Object.keys(deltas || {})) {
        const dv = (deltas as any)[k];
        const bv = (base as any)[k];
        if (k === "fillControls" && dv && typeof dv === "object") {
          const bfc = (base as any).fillControls && typeof (base as any).fillControls === "object" ? (base as any).fillControls : {};
          out.fillControls = { ...bfc };
          for (const fk of Object.keys(dv)) {
            const fTarget = (dv as any)[fk];
            const fBase = (bfc as any)[fk];
            if (typeof fTarget === "number" && typeof fBase === "number") {
              (out.fillControls as any)[fk] = fBase + (fTarget - fBase) * t;
            } else {
              (out.fillControls as any)[fk] = t > 0 ? fTarget : fBase;
            }
          }
          continue;
        }

        if (typeof dv === "number" && typeof bv === "number") {
          out[k] = bv + (dv - bv) * t;
        } else {
          out[k] = t > 0 ? dv : bv;
        }
      }
      return out;
    };

    const stack = Array.isArray((gd as any)?.presetStack) ? ((gd as any).presetStack as any[]) : [];
    const tierOrder = { utility: 0, flavor: 1, song: 2 } as const;
    const sorted = stack
      .slice()
      .sort((a, b) => (tierOrder[(a as any)?.tier || "flavor"] ?? 1) - (tierOrder[(b as any)?.tier || "flavor"] ?? 1));

    let cur: any = { ...gd };
    for (const item of sorted) {
      const pid = String((item as any)?.presetId || "");
      const preset = presetById[pid];
      const deltas = (preset as any)?.deltas || {};
      const t = clamp01(((item as any)?.intensity ?? 0) / 100);
      cur = applyDeltas(cur, deltas, t);
    }
    return cur as any;
  }, [gd, presetById]);

  const fmtPreview = (key: string, baseVal: any, effVal: any, digits = 2) => {
    if (!presetPreview) return baseVal;
    const b = Number(baseVal);
    const e = Number(effVal);
    if (!Number.isFinite(b) || !Number.isFinite(e)) return baseVal;
    const bs = b.toFixed(digits);
    const es = e.toFixed(digits);
    if (bs === es) return bs;
    return `${bs} → ${es}`;
  };

  const affectedBorder = (keys: string[]) => {
    const isOverride = keys.some((k) => overrideKeys.has(k));
    const isPreset = keys.some((k) => presetAffectedKeys.has(k));
    if (isOverride) return "rounded border border-amber-500/40 p-2";
    if (isPreset) return "rounded border border-cyan-500/40 p-2";
    return "";
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setDrummerError(null);
        const res = await fetch(`/api/drummers`);
        if (!res.ok) throw new Error(`Failed to fetch drummers (${res.status})`);
        const data = await res.json();
        const list = Array.isArray(data?.drummers) ? data.drummers : [];
        const mapped = list
          .map((d: any) => ({ id: String(d?.id || ""), display_name: String(d?.display_name || d?.id || "") }))
          .filter((d: any) => d.id);
        if (!cancelled) setDrummerOptions(mapped);
      } catch (e: any) {
        if (!cancelled) setDrummerError(e?.message || String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setPresetError(null);
        const profileType = String(gd.styleGroup || "").trim().toLowerCase();
        if (!profileType) {
          if (!cancelled) setAvailablePresets([]);
          return;
        }
        const res = await fetch(`/api/drummer-presets?profileType=${encodeURIComponent(profileType)}`);
        if (!res.ok) throw new Error(`Failed to fetch presets (${res.status})`);
        const data = await res.json();
        const items = Array.isArray(data?.items) ? data.items : [];
        if (!cancelled) setAvailablePresets(items);
      } catch (e: any) {
        if (!cancelled) {
          setAvailablePresets([]);
          setPresetError(e?.message || String(e));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [gd.styleGroup]);

  const intensityLabel = useMemo(
    () => String(fmtPreview("intensity", gd.intensity, (effectiveFromPresets as any).intensity, 2)),
    [effectiveFromPresets, gd.intensity, presetPreview]
  );
  const variationLabel = useMemo(
    () => String(fmtPreview("variation", gd.variation, (effectiveFromPresets as any).variation, 2)),
    [effectiveFromPresets, gd.variation, presetPreview]
  );
  const humanizeAmountLabel = useMemo(
    () => String(fmtPreview("humanizeAmount", Number(gd.humanizeAmount), Number((effectiveFromPresets as any).humanizeAmount), 2)),
    [effectiveFromPresets, gd.humanizeAmount, presetPreview]
  );
  const swingAmountLabel = useMemo(
    () => String(fmtPreview("swingAmount", Number(gd.swingAmount), Number((effectiveFromPresets as any).swingAmount), 2)),
    [effectiveFromPresets, gd.swingAmount, presetPreview]
  );

  const ghostAmountLabel = useMemo(
    () => String(fmtPreview("ghostNoteAmount", Number(gd.ghostNoteAmount), Number((effectiveFromPresets as any).ghostNoteAmount), 2)),
    [effectiveFromPresets, gd.ghostNoteAmount, presetPreview]
  );

  const hatsToRideBlendLabel = useMemo(
    () => String(fmtPreview("hatsToRideBlend", Number(gd.hatsToRideBlend), Number((effectiveFromPresets as any).hatsToRideBlend), 2)),
    [effectiveFromPresets, gd.hatsToRideBlend, presetPreview]
  );
  const hatsToRideThresholdLabel = useMemo(
    () => String(fmtPreview("hatsToRideThreshold", Number(gd.hatsToRideThreshold), Number((effectiveFromPresets as any).hatsToRideThreshold), 2)),
    [effectiveFromPresets, gd.hatsToRideThreshold, presetPreview]
  );
  const chorusRidePrefLabel = useMemo(
    () => String(fmtPreview("chorusRidePreference", Number(gd.chorusRidePreference), Number((effectiveFromPresets as any).chorusRidePreference), 2)),
    [effectiveFromPresets, gd.chorusRidePreference, presetPreview]
  );
  const rideBellPercentLabel = useMemo(
    () => String(fmtPreview("rideBellPercent", Number(gd.rideBellPercent), Number((effectiveFromPresets as any).rideBellPercent), 2)),
    [effectiveFromPresets, gd.rideBellPercent, presetPreview]
  );

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <div className="text-xs font-semibold text-cyan-300 tracking-wide">GLOBAL Defaults</div>
      <div className="text-[11px] text-slate-400 mt-1">Baseline generation settings used when sections inherit.</div>

      <div className="mt-2 flex items-center justify-between">
        <div className="text-[11px] text-slate-400">Preset highlight uses cyan. Section overrides use amber.</div>
        <label className="flex items-center gap-2 text-[11px] text-slate-200 select-none">
          <input type="checkbox" checked={presetPreview} onChange={(e) => setPresetPreview(e.target.checked)} />
          Preset Preview
        </label>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <div className={affectedBorder(["style"])}>
          <Field label="Style">
          <input
            value={gd.style || ""}
            onChange={(e) => setGlobalDefaults({ style: e.target.value })}
            className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
            placeholder="rock"
          />
          </Field>
        </div>

        <div className={affectedBorder(["drummer"])}>
          <Field label="Drummer">
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <div className="text-[11px] text-slate-300 truncate">{selectedDrummerLabel}</div>
                <button
                  type="button"
                  className="px-2 py-1 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 hover:border-slate-500"
                  onClick={() => {
                    setDrummerPickerTarget({ scope: "global" });
                    setDrummerPickerOpen(true);
                  }}
                >
                  Change Drummer
                </button>
              </div>
              {!selectedDrummerId ? (
                <div className="text-[11px] text-amber-300">Select a drummer to begin generating drums.</div>
              ) : null}
              {drummerError && <div className="text-[11px] text-rose-400">{drummerError}</div>}
            </div>
          </Field>
        </div>

        <div className={affectedBorder(["generationMode"])}>
          <Field label="Generation Mode">
          <select
            data-testid="v3.global.generationMode"
            value={gd.generationMode}
            onChange={(e) => setGlobalDefaults({ generationMode: e.target.value as DrumGenerationConfig["generationMode"] })}
            className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
          >
            {generationModes.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
          </Field>
        </div>

        <div className={affectedBorder(["drummerBrainEnabled"])}>
          <Field label={`Sentient Drummer (${(gd as any).drummerBrainEnabled ? "on" : "off"})`}>
          <label className="flex items-center gap-2 text-xs text-slate-300 select-none">
            <input
              type="checkbox"
              checked={!!(gd as any).drummerBrainEnabled}
              onChange={(e) => setGlobalDefaults({ drummerBrainEnabled: e.target.checked } as any)}
            />
            Enable
          </label>
          </Field>
        </div>

        <div className={affectedBorder(["humanize"])}>
          <Field label={`Humanize (${gd.humanize ? "on" : "off"})`}>
          <label className="flex items-center gap-2 text-xs text-slate-300 select-none">
            <input
              type="checkbox"
              checked={!!gd.humanize}
              onChange={(e) => setGlobalDefaults({ humanize: e.target.checked })}
            />
            Enable
          </label>
          </Field>
        </div>

        <div className={affectedBorder(["intensity"])}>
          <Field label={`Intensity (${intensityLabel})`}>
          <V3Knob
            testId="v3.global.intensity.knob"
            label="Intensity"
            value={gd.intensity}
            onChange={(v) => setGlobalDefaults({ intensity: v })}
            min={0}
            max={1}
            step={0.01}
            formatValue={(v) => v.toFixed(2)}
          />
          </Field>
        </div>

        <div className={affectedBorder(["variation"])}>
          <Field label={`Variation (${variationLabel})`}>
          <V3Knob
            testId="v3.global.variation.knob"
            label="Variation"
            value={gd.variation}
            onChange={(v) => setGlobalDefaults({ variation: v })}
            min={0}
            max={1}
            step={0.01}
            formatValue={(v) => v.toFixed(2)}
          />
          </Field>
        </div>

        <div className={"rounded border border-slate-800 bg-slate-950/60 p-2 col-span-2"}>
          <div className="text-[11px] font-semibold text-slate-200">Presets</div>
          <div className="mt-2 flex items-center gap-2">
            <button
              type="button"
              className="px-2 py-0.5 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 disabled:opacity-50"
              disabled={presetExplainBusy || !selectedDrummerId}
              onClick={async () => {
                try {
                  setPresetExplainBusy(true);
                  setPresetExplainError(null);
                  const stack = Array.isArray((gd as any)?.presetStack) ? ((gd as any).presetStack as any[]) : [];
                  const presetNames = stack
                    .map((it: any) => {
                      const pid = String(it?.presetId || "");
                      const p = presetById[pid];
                      return String((p as any)?.name || pid || "");
                    })
                    .filter((s: string) => !!s);
                  const res = await fetch(`/api/preset-preview/knowledge`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      profileType: String(gd.styleGroup || ""),
                      drummerId: selectedDrummerId,
                      presetStack: stack,
                      presetNames,
                    }),
                  });
                  const j = await res.json();
                  if (!res.ok || !(j as any)?.ok) throw new Error(String((j as any)?.error || `HTTP ${res.status}`));
                  setPresetExplain(j);
                } catch (e: any) {
                  setPresetExplainError(e?.message || String(e));
                  setPresetExplain(null);
                } finally {
                  setPresetExplainBusy(false);
                }
              }}
            >
              {presetExplainBusy ? "Explaining..." : "Explain preset stack"}
            </button>
            {presetExplainError ? <div className="text-[11px] text-rose-400">{presetExplainError}</div> : null}
          </div>
          {presetExplain && (presetExplain as any)?.what_to_listen_for ? (
            <div className="mt-2 rounded border border-slate-800 bg-slate-950 p-2">
              <div className="text-[11px] text-slate-300">What to listen for</div>
              <div className="mt-1 space-y-1">
                {((presetExplain as any).what_to_listen_for || []).map((t: any, idx: number) => (
                  <div key={idx} className="text-[11px] text-slate-400">
                    {String(t || "")}
                  </div>
                ))}
              </div>
              {Array.isArray((presetExplain as any)?.citations) && (presetExplain as any).citations.length ? (
                <div className="mt-2">
                  <div className="text-[11px] text-slate-300">Citations</div>
                  <div className="mt-1 space-y-1">
                    {((presetExplain as any).citations || []).slice(0, 4).map((c: any) => {
                      const cid = String(c?.chunk_id || c?.chunkId || "");
                      const doc = String(c?.doc_id || c?.docId || "");
                      const src = c?.source || {};
                      const page = src?.page ? ` p${src.page}` : "";
                      return (
                        <div key={cid || doc} className="text-[10px] text-slate-500">
                          {doc}{page} {cid ? `(${cid})` : ""}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
          <div className="mt-2 grid grid-cols-2 gap-2">
            <Field label="Add preset">
              <select
                value={presetAddId}
                onChange={(e) => setPresetAddId(e.target.value)}
                className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
              >
                <option value="">Select…</option>
                {availablePresets.map((p: any) => (
                  <option key={String(p?.preset_id || p?.presetId || "")} value={String(p?.preset_id || p?.presetId || "")}>
                    {String(p?.name || p?.preset_id || p?.presetId || "")}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Tier">
              <select
                value={presetAddTier}
                onChange={(e) => setPresetAddTier(e.target.value as any)}
                className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
              >
                <option value="song">Song</option>
                <option value="flavor">Flavor</option>
                <option value="utility">Utility</option>
              </select>
            </Field>
            <Field label={`Intensity (${Math.round(presetAddIntensity)})`}>
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={Number(presetAddIntensity) || 0}
                onChange={(e) => setPresetAddIntensity(Number(e.target.value) || 0)}
                className="w-full"
              />
            </Field>
            <div className="flex items-end">
              <button
                type="button"
                className="w-full px-2 py-1 rounded bg-slate-800 text-slate-100 text-[11px] border border-slate-700 disabled:opacity-50"
                disabled={!presetAddId}
                onClick={() => {
                  const pid = String(presetAddId || "").trim();
                  if (!pid) return;
                  upsertGlobalPreset({ presetId: pid, tier: presetAddTier, intensity: Math.max(0, Math.min(100, Math.round(presetAddIntensity))) });
                  setPresetAddId("");
                }}
              >
                Add
              </button>
            </div>
          </div>
          {presetError ? <div className="mt-2 text-[11px] text-rose-400">{presetError}</div> : null}
          <div className="mt-2 space-y-2">
            {(gd.presetStack || []).length === 0 ? (
              <div className="text-[11px] text-slate-500">No presets.</div>
            ) : (
              (gd.presetStack || []).map((p: any) => (
                <div key={String(p?.presetId || "")} className="flex items-center gap-2">
                  <div className="text-[11px] text-slate-200 min-w-[140px] truncate" title={String(p?.presetId || "")}>
                    {String(p?.presetId || "")}
                  </div>
                  <div className="text-[11px] text-slate-400 w-16">{String(p?.tier || "")}</div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    step={1}
                    value={Number(p?.intensity ?? 0)}
                    onChange={(e) => {
                      upsertGlobalPreset({
                        presetId: String(p?.presetId || ""),
                        tier: (p?.tier || "flavor") as any,
                        intensity: Math.max(0, Math.min(100, Number(e.target.value) || 0)),
                      });
                    }}
                    className="flex-1"
                  />
                  <div className="text-[11px] text-slate-400 w-10 text-right">{Math.round(Number(p?.intensity ?? 0))}</div>
                  <button
                    type="button"
                    className="px-2 py-1 rounded bg-slate-900 text-rose-200 text-[11px] border border-slate-700"
                    onClick={() => removeGlobalPreset(String(p?.presetId || ""))}
                  >
                    Remove
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className={"rounded border border-slate-800 bg-slate-950/60 p-2 col-span-2"}>
          <div className="text-[11px] font-semibold text-slate-200">Cymbal Focus</div>
          <div className="mt-2 grid grid-cols-2 gap-3">
            <div className={affectedBorder(["cymbalFocusMode"])}>
            <Field label="Focus Mode">
              <select
                value={String(gd.cymbalFocusMode ?? "continuous")}
                onChange={(e) => setGlobalDefaults({ cymbalFocusMode: e.target.value as any })}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
              >
                <option value="continuous">Continuous (blend knob)</option>
                <option value="section_rule">Section rule (chorus preference)</option>
              </select>
            </Field>
            </div>
            <div className={affectedBorder(["rideBellPercent"])}>
            <Field label={`Ride Bell % (${rideBellPercentLabel})`}>
              <V3Knob
                label="Bell"
                value={Number(gd.rideBellPercent ?? 0.2)}
                onChange={(v) => setGlobalDefaults({ rideBellPercent: v })}
                min={0}
                max={1}
                step={0.01}
                formatValue={(v) => v.toFixed(2)}
              />
            </Field>
            </div>

            <div className={affectedBorder(["hatsToRideBlend"])}>
            <Field label={`Hat ↔ Ride Blend (${hatsToRideBlendLabel})`}>
              <V3Knob
                label="Blend"
                value={Number(gd.hatsToRideBlend ?? 0)}
                onChange={(v) => setGlobalDefaults({ hatsToRideBlend: v })}
                min={0}
                max={1}
                step={0.01}
                formatValue={(v) => v.toFixed(2)}
              />
            </Field>
            </div>
            <div className={affectedBorder(["hatsToRideThreshold"])}>
            <Field label={`Ride Threshold (${hatsToRideThresholdLabel})`}>
              <V3Knob
                label="Thresh"
                value={Number(gd.hatsToRideThreshold ?? 0.6)}
                onChange={(v) => setGlobalDefaults({ hatsToRideThreshold: v })}
                min={0}
                max={1}
                step={0.01}
                formatValue={(v) => v.toFixed(2)}
              />
            </Field>
            </div>

            <div className={affectedBorder(["chorusRidePreference"])}>
            <Field label={`Chorus Ride Preference (${chorusRidePrefLabel})`}>
              <V3Knob
                label="Chorus"
                value={Number(gd.chorusRidePreference ?? 0)}
                onChange={(v) => setGlobalDefaults({ chorusRidePreference: v })}
                min={0}
                max={1}
                step={0.01}
                formatValue={(v) => v.toFixed(2)}
              />
            </Field>
            </div>
            <div />

            <div className={affectedBorder(["footHatPulseSubdivision"])}>
            <Field label="Foot Hat Pulse (left foot)">
              <select
                value={String(gd.footHatPulseSubdivision ?? "off")}
                onChange={(e) => setGlobalDefaults({ footHatPulseSubdivision: e.target.value as any })}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
              >
                <option value="off">Off</option>
                <option value="quarter">Quarter</option>
                <option value="eighth">Eighth</option>
                <option value="sixteenth">Sixteenth</option>
              </select>
            </Field>
            </div>
            <div className={affectedBorder(["footHatPulseApply"])}>
            <Field label="Pulse Apply">
              <select
                value={String(gd.footHatPulseApply ?? "both")}
                onChange={(e) => setGlobalDefaults({ footHatPulseApply: e.target.value as any })}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
              >
                <option value="transition">Transition only</option>
                <option value="ride_bars">Ride bars</option>
                <option value="both">Both</option>
              </select>
            </Field>
            </div>
          </div>
        </div>

        <div className={affectedBorder(["humanizeAmount"])}>
          <Field label={`Humanize Amount (${humanizeAmountLabel})`}>
          <V3Knob
            testId="v3.global.humanizeAmount.knob"
            label="Humanize"
            value={Number(gd.humanizeAmount ?? 0)}
            onChange={(v) => setGlobalDefaults({ humanizeAmount: v })}
            min={0}
            max={1}
            step={0.01}
            formatValue={(v) => v.toFixed(2)}
          />
          </Field>
        </div>

        <div className={affectedBorder(["swingAmount"])}>
          <Field label={`Swing Amount (${swingAmountLabel})`}>
          <V3Knob
            testId="v3.global.swingAmount.knob"
            label="Swing"
            value={Number(gd.swingAmount ?? 0)}
            onChange={(v) => setGlobalDefaults({ swingAmount: v })}
            min={0}
            max={1}
            step={0.01}
            formatValue={(v) => v.toFixed(2)}
          />
          </Field>
        </div>

        <div className={affectedBorder(["ghostNoteAmount"])}>
          <Field label={`Ghost Amount (${ghostAmountLabel})`}>
          <V3Knob
            testId="v3.global.ghostNoteAmount.knob"
            label="Ghost"
            value={Number(gd.ghostNoteAmount ?? 0)}
            onChange={(v) => setGlobalDefaults({ ghostNoteAmount: v })}
            min={0}
            max={1}
            step={0.01}
            formatValue={(v) => v.toFixed(2)}
          />
          </Field>
        </div>
      </div>
    </div>
  );
}
