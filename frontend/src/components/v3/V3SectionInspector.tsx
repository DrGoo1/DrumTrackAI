import React, { useEffect, useMemo, useState } from "react";
import { useV3Store } from "../../state/v3/store";
import type { DrumGenerationConfig, DrumInstrumentId } from "../../types/drumTrack";
import { DRUM_INSTRUMENT_MIDI_MAP } from "../../types/drumTrack";
import { DRUM_INSTRUMENT_COLORS } from "../../types/drumTrack";
import type { V3FieldGroup, V3InheritFlag, V3SectionDirective } from "../../state/v3/types";
import { V3Knob } from "./V3Knob";
import { beatFloatToTimeSec, timeSecToBeatFloat } from "../../time/v3TimelineKernel";

const generationModes: Array<{ value: DrumGenerationConfig["generationMode"]; label: string }> = [
  { value: "template", label: "Template" },
  { value: "ai_variation", label: "AI Variation" },
  { value: "full_ai", label: "Full AI" },
];

const guideInstrumentOptions: Array<{
  value: NonNullable<DrumGenerationConfig["guideInstrument"]>;
  label: string;
}> = [
  { value: "bass", label: "Bass" },
  { value: "guitar", label: "Guitar" },
  { value: "keys", label: "Keys" },
  { value: "vocal", label: "Vocal" },
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

function sectionIdForIdx(idx: number, s: { startSec: number; endSec: number }): string {
  return `v3-${idx}-${Number(s.startSec || 0).toFixed(3)}-${Number(s.endSec || 0).toFixed(3)}`;
}

function beatsAtTimeFromTempoMap(tempoMap: Array<{ tSec: number; bpm: number }>, fallbackBpm: number, tSec: number): number {
  const pts = Array.isArray(tempoMap)
    ? tempoMap
        .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
        .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
        .sort((a, b) => a.tSec - b.tSec)
    : [];

  const bpm0 = Number.isFinite(fallbackBpm) && fallbackBpm > 0 ? fallbackBpm : 120;
  const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);

  if (!pts.length) {
    return (t * bpm0) / 60;
  }
  if (pts.length === 1) {
    return (t * pts[0].bpm) / 60;
  }

  let beats = 0;
  let prevT = pts[0].tSec;
  let prevBpm = pts[0].bpm;
  if (t <= prevT) return 0;
  for (let i = 1; i < pts.length; i++) {
    const cur = pts[i];
    if (t <= cur.tSec) {
      beats += ((t - prevT) * prevBpm) / 60;
      return beats;
    }
    beats += ((cur.tSec - prevT) * prevBpm) / 60;
    prevT = cur.tSec;
    prevBpm = cur.bpm;
  }
  beats += ((t - prevT) * prevBpm) / 60;
  return beats;
}

function secondsToBeatsFromBeatTimesWithOffset(beatTimes: number[], tSec: number, beatZeroOffsetSec: number): number {
  // beatTimes are already in the audio timeline (seconds). Do not shift by beatZeroOffsetSec.
  void beatZeroOffsetSec;
  return timeSecToBeatFloat(beatTimes, Number(tSec) || 0);
}

function beatsToSecondsFromBeatTimesWithOffset(beatTimes: number[], beatsIn: number, beatZeroOffsetSec: number): number {
  // beatTimes are already in the audio timeline (seconds). Do not shift by beatZeroOffsetSec.
  void beatZeroOffsetSec;
  return beatFloatToTimeSec(beatTimes, beatsIn);
}

function timeAtBeatsFromTempoMap(tempoMap: Array<{ tSec: number; bpm: number }>, fallbackBpm: number, beatsIn: number): number {
  const pts = Array.isArray(tempoMap)
    ? tempoMap
        .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
        .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
        .sort((a, b) => a.tSec - b.tSec)
    : [];

  const bpm0 = Number.isFinite(fallbackBpm) && fallbackBpm > 0 ? fallbackBpm : 120;
  const beats = Math.max(0, Number.isFinite(beatsIn) ? beatsIn : 0);
  if (!pts.length) return (beats * 60) / bpm0;
  if (pts.length === 1) return (beats * 60) / pts[0].bpm;

  const beatsAtPoint: number[] = new Array(pts.length);
  beatsAtPoint[0] = 0;
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1];
    const cur = pts[i];
    const dt = Math.max(0, cur.tSec - prev.tSec);
    beatsAtPoint[i] = beatsAtPoint[i - 1] + (dt * prev.bpm) / 60;
  }

  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1];
    const b0 = beatsAtPoint[i - 1];
    const b1 = beatsAtPoint[i];
    if (beats <= b1) {
      const db = Math.max(0, beats - b0);
      return prev.tSec + (db * 60) / prev.bpm;
    }
  }

  const last = pts[pts.length - 1];
  const bLast = beatsAtPoint[beatsAtPoint.length - 1];
  const db = Math.max(0, beats - bLast);
  return last.tSec + (db * 60) / last.bpm;
}

function InheritToggle(props: { group: V3FieldGroup; flag: V3InheritFlag; disabled?: boolean; onChange: (flag: V3InheritFlag) => void }) {
  const { group, flag, disabled, onChange } = props;
  return (
    <div className="flex items-center gap-2">
      <div className="min-w-[84px] text-[11px] text-slate-300 capitalize">{group}</div>
      <label className="flex items-center gap-1 text-[11px] text-slate-200">
        <input
          type="radio"
          name={`v3-section-${group}`}
          checked={flag === "inherit"}
          disabled={disabled}
          data-testid={`v3.section.inherit.${group}.inherit`}
          onChange={() => onChange("inherit")}
        />
        Inherit
      </label>
      <label className="flex items-center gap-1 text-[11px] text-slate-200">
        <input
          type="radio"
          name={`v3-section-${group}`}
          checked={flag === "override"}
          disabled={disabled}
          data-testid={`v3.section.inherit.${group}.override`}
          onChange={() => onChange("override")}
        />
        Override
      </label>
    </div>
  );
}

export function V3SectionInspector() {
  const globalDefaults = useV3Store((s) => s.globalDefaults);
  const arrangement = useV3Store((s) => s.arrangement);
  const sectionOverrides = useV3Store((s) => s.sectionOverrides);
  const barEdits = useV3Store((s) => s.barEdits);
  const generatedDrumTrack = useV3Store((s) => s.generatedDrumTrack);
  const selectedSectionId = useV3Store((s) => s.selection.selectedSectionId);
  const selectedBarIndex = useV3Store((s) => s.selection.selectedBarIndex);
  const setSelectedBarIndex = useV3Store((s) => s.setSelectedBarIndex);
  const setSectionLocked = useV3Store((s) => s.setSectionLocked);
  const setSectionInheritFlag = useV3Store((s) => s.setSectionInheritFlag);
  const setSectionOverrides = useV3Store((s) => s.setSectionOverrides);
  const setSectionsBB = useV3Store((s) => s.setSectionsBB);
  const setDrummerPickerTarget = useV3Store((s) => s.setDrummerPickerTarget);
  const setDrummerPickerOpen = useV3Store((s) => s.setDrummerPickerOpen);
  const clearSectionOverrides = useV3Store((s) => s.clearSectionOverrides);
  const ensureSection = useV3Store((s) => s.ensureSection);
  const setSectionInheritGlobalPresets = useV3Store((s) => s.setSectionInheritGlobalPresets);

  const presetPreview = useV3Store((s) => s.ui.presetPreview);
  const setPresetPreview = useV3Store((s) => s.setPresetPreview);

  const ensureBarEdit = useV3Store((s) => s.ensureBarEdit);
  const addBarEditNote = useV3Store((s) => s.addBarEditNote);
  const deleteBarEditNote = useV3Store((s) => s.deleteBarEditNote);
  const nudgeBarEditNote = useV3Store((s) => s.nudgeBarEditNote);
  const clearBarEditsForBar = useV3Store((s) => s.clearBarEditsForBar);
  const applyBarEditsToGeneratedTrack = useV3Store((s) => s.applyBarEditsToGeneratedTrack);
  const setBarFillDirective = useV3Store((s) => s.setBarFillDirective);
  const upsertSectionPreset = useV3Store((s) => s.upsertSectionPreset);
  const removeSectionPreset = useV3Store((s) => s.removeSectionPreset);
  const requestAuditionBarPreview = useV3Store((s) => s.requestAuditionBarPreview);
  const stopAudition = useV3Store((s) => s.stopAudition);

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

  const presetById = useMemo(() => {
    const out: Record<string, any> = {};
    for (const p of availablePresets || []) {
      const id = String((p as any)?.preset_id || (p as any)?.presetId || "").trim();
      if (!id) continue;
      out[id] = p;
    }
    return out;
  }, [availablePresets]);

  const [editScope, setEditScope] = useState<"section" | "bar">("section");

  const [newNoteInst, setNewNoteInst] = useState<DrumInstrumentId>("kick");
  const [newNoteStep16, setNewNoteStep16] = useState<number>(0);
  const [newNoteVel, setNewNoteVel] = useState<number>(100);

  const [auditioning, setAuditioning] = useState(false);

  const miniGridLanes: DrumInstrumentId[] = useMemo(
    () => [
      "kick",
      "snare_center",
      "hihat_closed",
      "hihat_open",
      "hihat_pedal",
      "ride_bow",
      "ride_bell",
      "tom_high",
      "tom_mid",
      "tom_floor",
      "crash_1",
      "crash_2",
    ],
    []
  );

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
        const profileType = String(globalDefaults.styleGroup || "").trim().toLowerCase();
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
  }, [globalDefaults.styleGroup]);

  const selectedInfo = useMemo(() => {
    const secsBB = arrangement.sectionsBB || [];
    const matchIdx = selectedSectionId ? secsBB.findIndex((s: any) => String(s?.id || "") === String(selectedSectionId)) : -1;
    const idx = matchIdx >= 0 ? matchIdx : null;
    const secBB = idx !== null ? (secsBB as any)[idx] : null;
    const label = secBB ? String((secBB as any)?.label || `Section ${idx! + 1}`) : null;
    return { idx, secBB, label };
  }, [arrangement.sectionsBB, selectedSectionId]);

  const sectionBarRange = useMemo(() => {
    const sec = selectedInfo.secBB as any;
    if (!sec) return null;

    const beatsPerBar = Number(arrangement.timeSig?.[0] || 4) || 4;

    const startBar = Math.max(0, Number(sec?.start?.barIndex ?? 0) || 0);
    const endBarRaw = Math.max(0, Number(sec?.end?.barIndex ?? 0) || 0);
    const endBeatInBar = Number(sec?.end?.beatInBar ?? 0) || 0;
    // If the section ends exactly on a bar boundary, last in-section bar is previous bar.
    const barEnd = Math.max(startBar, endBeatInBar <= 0 ? endBarRaw - 1 : endBarRaw);
    return { barStart: startBar, barEnd, beatsPerBar };
  }, [arrangement.timeSig, selectedInfo.secBB]);

  const selectedDirective = useMemo(() => {
    const sec = selectedInfo.secBB as any;
    return (sec?.directive as V3SectionDirective | undefined) ?? "simple";
  }, [selectedInfo.secBB]);

  const setSelectedDirective = (dir: V3SectionDirective) => {
    if (!selectedSectionId) return;
    const secsBB = arrangement.sectionsBB || [];
    const next = (secsBB as any[]).map((s) => (String((s as any)?.id || "") === String(selectedSectionId) ? { ...(s as any), directive: dir } : s));
    setSectionsBB(next as any);
  };

  const perBarAllowed = editScope === "bar";
  const selectedBarInSection = useMemo(() => {
    if (!perBarAllowed) return true;
    if (!sectionBarRange) return false;
    if (selectedBarIndex === null || selectedBarIndex === undefined) return false;
    return selectedBarIndex >= sectionBarRange.barStart && selectedBarIndex <= sectionBarRange.barEnd;
  }, [perBarAllowed, sectionBarRange, selectedBarIndex]);

  const activeBarEdit = useMemo(() => {
    if (!selectedSectionId) return null;
    if (editScope !== "bar") return null;
    if (!sectionBarRange) return null;
    if (!selectedBarInSection) return null;
    const bi = Number(selectedBarIndex);
    if (!Number.isFinite(bi)) return null;
    return (barEdits[String(selectedSectionId)] || {})[bi] || null;
  }, [barEdits, editScope, sectionBarRange, selectedBarInSection, selectedBarIndex, selectedSectionId]);

  useEffect(() => {
    if (editScope !== "bar") return;
    if (!selectedSectionId) return;
    if (!selectedBarInSection) return;
    if (selectedBarIndex === null || selectedBarIndex === undefined) return;
    ensureBarEdit(selectedSectionId, selectedBarIndex);
  }, [editScope, ensureBarEdit, selectedBarIndex, selectedBarInSection, selectedSectionId]);

  const barNotesPreview = useMemo(() => {
    if (editScope !== "bar") return [] as any[];
    if (!selectedBarInSection) return [] as any[];
    if (!generatedDrumTrack || !Array.isArray((generatedDrumTrack as any).notes)) return [] as any[];
    const bi = Number(selectedBarIndex);
    const base = (generatedDrumTrack as any).notes.filter((n: any) => Number(n?.barIndex ?? -1) === bi);

    const edit = activeBarEdit;
    if (!edit) return base.slice().sort((a: any, b: any) => Number(a.tickInBar || 0) - Number(b.tickInBar || 0));

    const deleted = new Set((edit.deletedNoteIds || []).map((x: any) => String(x)));
    const deltaById = edit.tickDeltaByNoteId || {};

    const patched = base
      .filter((n: any) => !deleted.has(String(n?.id || "")))
      .map((n: any) => {
        const nid = String(n?.id || "");
        const d = Number(deltaById[nid] || 0);
        if (!Number.isFinite(d) || d === 0) return n;
        return { ...n, tickInBar: Number(n.tickInBar || 0) + d };
      });

    const added = (edit.addedNotes || []).map((n: any) => ({ ...n, barIndex: bi }));
    return [...patched, ...added].sort((a: any, b: any) => Number(a.tickInBar || 0) - Number(b.tickInBar || 0));
  }, [activeBarEdit, editScope, generatedDrumTrack, selectedBarInSection, selectedBarIndex]);

  useEffect(() => {
    if (editScope !== "bar") return;
    if (!selectedSectionId) return;
    if (!sectionBarRange) return;
    if (selectedBarIndex === null || selectedBarIndex === undefined) {
      setSelectedBarIndex(sectionBarRange.barStart);
      return;
    }
    if (selectedBarIndex < sectionBarRange.barStart || selectedBarIndex > sectionBarRange.barEnd) {
      setSelectedBarIndex(sectionBarRange.barStart);
    }
  }, [editScope, sectionBarRange, selectedBarIndex, selectedSectionId, setSelectedBarIndex]);

  useEffect(() => {
    if (!selectedSectionId) return;
    ensureSection(selectedSectionId);
  }, [ensureSection, selectedSectionId]);

  const sectionState = selectedSectionId ? sectionOverrides[selectedSectionId] ?? null : null;
  const locked = !!sectionState?.locked;
  const inherit = sectionState?.inherit;
  const overrides = (sectionState?.overrides || {}) as Partial<DrumGenerationConfig>;
  const inheritGlobalPresets = sectionState?.inheritGlobalPresets !== false;
  const sectionPresetStack = Array.isArray(sectionState?.presetStack) ? sectionState?.presetStack : [];

  const effectiveDrummerId = String(
    (overrides as any)?.publicDrummerId ||
      (overrides as any)?.drummer ||
      (globalDefaults as any)?.publicDrummerId ||
      (globalDefaults as any)?.drummer ||
      "",
  ).trim();

  const effectiveProfileType = String((overrides as any)?.styleGroup || (globalDefaults as any)?.styleGroup || "").trim();

  const combinedPresetStack = useMemo(() => {
    const globalStack = Array.isArray((globalDefaults as any)?.presetStack) ? ((globalDefaults as any).presetStack as any[]) : [];
    const sectionStack = Array.isArray(sectionState?.presetStack) ? (sectionState?.presetStack as any[]) : [];
    return (inheritGlobalPresets ? globalStack : []).concat(sectionStack);
  }, [globalDefaults, inheritGlobalPresets, sectionState]);

  const groupFlag = (g: V3FieldGroup): V3InheritFlag => (inherit?.[g] || "inherit") as V3InheritFlag;
  const groupEnabled = (group: V3FieldGroup) => groupFlag(group) === "override";

  const overrideKeys = useMemo(() => {
    const out = new Set<string>();
    if (!sectionState) return out;
    for (const g of Object.keys(sectionState.inherit || {}) as V3FieldGroup[]) {
      if (sectionState.inherit[g] !== "override") continue;
      const p: any = sectionState.overrides || {};
      if (g === "identity") {
        if (p.style !== undefined) out.add("style");
        if (p.drummer !== undefined || p.publicDrummerId !== undefined) out.add("drummer");
      }
      if (g === "generation") {
        if (p.generationMode !== undefined) out.add("generationMode");
        if (p.intensity !== undefined) out.add("intensity");
        if (p.variation !== undefined) out.add("variation");
      }
      if (g === "humanization") {
        if (p.humanize !== undefined) out.add("humanize");
        if (p.humanizeAmount !== undefined) out.add("humanizeAmount");
        if (p.swingAmount !== undefined) out.add("swingAmount");
        if (p.ghostNoteAmount !== undefined) out.add("ghostNoteAmount");
        if ((p as any).quantizeStrength !== undefined) out.add("quantizeStrength");
        if ((p as any).quantizeBase !== undefined) out.add("quantizeBase");
        if ((p as any).timingHumanizeMs !== undefined) out.add("timingHumanizeMs");
        if ((p as any).velocityHumanize !== undefined) out.add("velocityHumanize");
        if ((p as any).pushPullMs !== undefined) out.add("pushPullMs");
        if ((p as any).feelSeed !== undefined) out.add("feelSeed");
      }
      if (g === "groove") {
        if (p.selectedGrooveId !== undefined) out.add("selectedGrooveId");
        if (p.grooveUse !== undefined) out.add("grooveUse");
        if (p.fillGrooveId !== undefined) out.add("fillGrooveId");
      }
    }
    return out;
  }, [sectionState]);

  const presetAffectedKeys = useMemo(() => {
    const out = new Set<string>();
    const globalStack = Array.isArray((globalDefaults as any)?.presetStack) ? ((globalDefaults as any).presetStack as any[]) : [];
    const sectionStack = Array.isArray(sectionState?.presetStack) ? (sectionState?.presetStack as any[]) : [];
    const combined = (inheritGlobalPresets ? globalStack : []).concat(sectionStack);
    for (const item of combined) {
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
  }, [globalDefaults, inheritGlobalPresets, presetById, sectionState]);

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

    const base: any = {
      ...globalDefaults,
      ...(sectionState?.overrides || {}),
    };

    const globalStack = Array.isArray((globalDefaults as any)?.presetStack) ? ((globalDefaults as any).presetStack as any[]) : [];
    const sectionStack = Array.isArray(sectionState?.presetStack) ? (sectionState?.presetStack as any[]) : [];
    const tierOrder = { utility: 0, flavor: 1, song: 2 } as const;
    const sortTier = (a: any, b: any) => (tierOrder[a?.tier || "flavor"] ?? 1) - (tierOrder[b?.tier || "flavor"] ?? 1);
    const globalSorted = (inheritGlobalPresets ? globalStack : []).slice().sort(sortTier);
    const sectionSorted = sectionStack.slice().sort(sortTier);

    let cur: any = { ...base };
    for (const item of globalSorted) {
      const pid = String((item as any)?.presetId || "");
      const preset = presetById[pid];
      const deltas = (preset as any)?.deltas || {};
      const t = clamp01(((item as any)?.intensity ?? 0) / 100);
      cur = applyDeltas(cur, deltas, t);
    }
    for (const item of sectionSorted) {
      const pid = String((item as any)?.presetId || "");
      const preset = presetById[pid];
      const deltas = (preset as any)?.deltas || {};
      const t = clamp01(((item as any)?.intensity ?? 0) / 100);
      cur = applyDeltas(cur, deltas, t);
    }
    return cur as any;
  }, [globalDefaults, inheritGlobalPresets, presetById, sectionState]);

  const fmtPreview = (baseVal: any, effVal: any, digits = 2) => {
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

  const baseIntensity = Number(overrides.intensity ?? globalDefaults.intensity);
  const baseVariation = Number(overrides.variation ?? globalDefaults.variation);
  const baseHumanizeAmount = Number(overrides.humanizeAmount ?? globalDefaults.humanizeAmount ?? 0);
  const baseSwingAmount = Number(overrides.swingAmount ?? globalDefaults.swingAmount ?? 0);
  const baseGhostAmount = Number(overrides.ghostNoteAmount ?? globalDefaults.ghostNoteAmount ?? 0);

  const baseQuantizeStrength = Number((overrides as any).quantizeStrength ?? (globalDefaults as any).quantizeStrength ?? 0);
  const baseTimingHumanizeMs = Number((overrides as any).timingHumanizeMs ?? (globalDefaults as any).timingHumanizeMs ?? 0);
  const baseVelocityHumanize = Number((overrides as any).velocityHumanize ?? (globalDefaults as any).velocityHumanize ?? 0);
  const basePushPullMs = Number((overrides as any).pushPullMs ?? (globalDefaults as any).pushPullMs ?? 0);
  const baseFeelSeed = Number((overrides as any).feelSeed ?? (globalDefaults as any).feelSeed ?? 0);

  const intensityLabel = useMemo(
    () => String(fmtPreview(baseIntensity, Number((effectiveFromPresets as any).intensity), 2)),
    [baseIntensity, effectiveFromPresets, presetPreview]
  );
  const variationLabel = useMemo(
    () => String(fmtPreview(baseVariation, Number((effectiveFromPresets as any).variation), 2)),
    [baseVariation, effectiveFromPresets, presetPreview]
  );
  const humanizeAmountLabel = useMemo(
    () => String(fmtPreview(baseHumanizeAmount, Number((effectiveFromPresets as any).humanizeAmount), 2)),
    [baseHumanizeAmount, effectiveFromPresets, presetPreview]
  );
  const swingAmountLabel = useMemo(
    () => String(fmtPreview(baseSwingAmount, Number((effectiveFromPresets as any).swingAmount), 2)),
    [baseSwingAmount, effectiveFromPresets, presetPreview]
  );

  const ghostAmountLabel = useMemo(
    () => String(fmtPreview(baseGhostAmount, Number((effectiveFromPresets as any).ghostNoteAmount), 2)),
    [baseGhostAmount, effectiveFromPresets, presetPreview]
  );

  const fillDensityLabel = useMemo(() => {
    const d = Number(overrides.fillControls?.density ?? overrides.fillDensity ?? globalDefaults.fillControls?.density ?? 0);
    return Number.isFinite(d) ? d.toFixed(2) : "0.00";
  }, [globalDefaults.fillControls?.density, overrides.fillControls?.density, overrides.fillDensity]);

  const baseFillDensity = Number(overrides.fillControls?.density ?? overrides.fillDensity ?? globalDefaults.fillControls?.density ?? 0.7);
  const fillDensityPreviewLabel = useMemo(
    () => String(fmtPreview(baseFillDensity, Number((effectiveFromPresets as any)?.fillControls?.density), 2)),
    [baseFillDensity, effectiveFromPresets, presetPreview]
  );

  const rudimentDensityLabel = useMemo(() => {
    const d = Number(overrides.rudimentControls?.density ?? globalDefaults.rudimentControls?.density ?? 0);
    return Number.isFinite(d) ? d.toFixed(2) : "0.00";
  }, [globalDefaults.rudimentControls?.density, overrides.rudimentControls?.density]);

  const baseHatsToRideBlend = Number(overrides.hatsToRideBlend ?? globalDefaults.hatsToRideBlend ?? 0);
  const baseHatsToRideThreshold = Number(overrides.hatsToRideThreshold ?? globalDefaults.hatsToRideThreshold ?? 0.6);
  const baseChorusRidePref = Number(overrides.chorusRidePreference ?? globalDefaults.chorusRidePreference ?? 0);
  const baseRideBellPercent = Number(overrides.rideBellPercent ?? globalDefaults.rideBellPercent ?? 0.2);

  const hatsToRideBlendLabel = useMemo(
    () => String(fmtPreview(baseHatsToRideBlend, Number((effectiveFromPresets as any).hatsToRideBlend), 2)),
    [baseHatsToRideBlend, effectiveFromPresets, presetPreview]
  );
  const hatsToRideThresholdLabel = useMemo(
    () => String(fmtPreview(baseHatsToRideThreshold, Number((effectiveFromPresets as any).hatsToRideThreshold), 2)),
    [baseHatsToRideThreshold, effectiveFromPresets, presetPreview]
  );
  const chorusRidePrefLabel = useMemo(
    () => String(fmtPreview(baseChorusRidePref, Number((effectiveFromPresets as any).chorusRidePreference), 2)),
    [baseChorusRidePref, effectiveFromPresets, presetPreview]
  );

  const rideBellPercentLabel = useMemo(
    () => String(fmtPreview(baseRideBellPercent, Number((effectiveFromPresets as any).rideBellPercent), 2)),
    [baseRideBellPercent, effectiveFromPresets, presetPreview]
  );

  if (!selectedSectionId) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
        <div className="text-xs font-semibold text-purple-300 tracking-wide">SECTION Inspector</div>
        <div className="text-[11px] text-slate-400 mt-1">Select a section in the arrangement strip to edit overrides.</div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-purple-300 tracking-wide">SECTION Inspector</div>
          <div className="text-[11px] text-slate-400 mt-1">
            {selectedInfo.label || "Selected Section"}
            {selectedInfo.idx !== null ? ` • idx ${selectedInfo.idx}` : ""}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-[11px] text-slate-300 select-none">
            <input type="checkbox" checked={presetPreview} onChange={(e) => setPresetPreview(e.target.checked)} />
            Preset Preview
          </label>
          <label className="flex items-center gap-2 text-[11px] text-slate-300 select-none">
            <input
              type="checkbox"
              checked={locked}
              onChange={(e) => setSectionLocked(selectedSectionId, e.target.checked)}
            />
            Locked
          </label>
          <button
            type="button"
            className="px-2 py-1 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 disabled:opacity-50"
            disabled={locked}
            onClick={() => clearSectionOverrides(selectedSectionId)}
          >
            Reset
          </button>
        </div>
      </div>

      <div className="mt-3 rounded border border-slate-800 bg-slate-950/60 p-2">
        <div className="text-[11px] text-slate-400">Edit Scope</div>
        <div className="mt-1 flex items-center gap-3">
          <label className="flex items-center gap-1 text-[11px] text-slate-200">
            <input type="radio" name="v3-section-scope" checked={editScope === "section"} onChange={() => setEditScope("section")} />
            Entire section
          </label>
          <label className="flex items-center gap-1 text-[11px] text-slate-200">
            <input type="radio" name="v3-section-scope" checked={editScope === "bar"} onChange={() => setEditScope("bar")} />
            Per bar
          </label>
          {editScope === "bar" && sectionBarRange && (
            <div className="ml-auto text-[11px] text-slate-400">
              Bars {sectionBarRange.barStart + 1}–{sectionBarRange.barEnd + 1}
            </div>
          )}
        </div>
        {editScope === "bar" && !sectionBarRange && (
          <div className="mt-1 text-[11px] text-rose-300">Per-bar edits unavailable: section boundaries are not valid.</div>
        )}
        {editScope === "bar" && sectionBarRange && !selectedBarInSection && (
          <div className="mt-1 text-[11px] text-rose-300">Select a bar inside this section to edit per-bar.</div>
        )}
        {editScope === "bar" && sectionBarRange && selectedBarInSection && (
          <div className="mt-1 text-[11px] text-slate-300">Editing bar {Number(selectedBarIndex) + 1}</div>
        )}
      </div>

      {editScope === "bar" && sectionBarRange && selectedBarInSection && (
        <div className="mt-3 rounded border border-slate-800 bg-slate-950/60 p-2">
          <div className="flex items-center justify-between gap-2">
            <div className="text-[11px] font-semibold text-slate-200">Bar Edits</div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className={
                  "px-2 py-1 rounded text-[11px] border disabled:opacity-50 " +
                  (auditioning
                    ? "bg-amber-600/20 text-amber-100 border-amber-500/40"
                    : "bg-emerald-600/20 text-emerald-100 border-emerald-500/40")
                }
                disabled={locked || !generatedDrumTrack}
                onClick={() => {
                  if (!selectedSectionId || selectedBarIndex == null) return;
                  if (!sectionBarRange) return;
                  if (!selectedBarInSection) return;
                  if (!generatedDrumTrack) return;

                  if (auditioning) {
                    stopAudition();
                    setAuditioning(false);
                    return;
                  }

                  const beatsPerBar = arrangement.timeSig?.[0] || 4;
                  const ticksPerBeat = Number((generatedDrumTrack as any)?.resolution_ppq || 960) || 960;
                  const ticksPerBar = ticksPerBeat * beatsPerBar;
                  const barStartTicks = Number(selectedBarIndex) * ticksPerBar;
                  const barEndTicks = (Number(selectedBarIndex) + 1) * ticksPerBar;
                  const beatsStart = barStartTicks / Math.max(1, ticksPerBeat);
                  const beatsEnd = barEndTicks / Math.max(1, ticksPerBeat);

                  const startSec = Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2
                    ? beatsToSecondsFromBeatTimesWithOffset(arrangement.beatTimes, beatsStart, arrangement.beatZeroOffsetSec || 0)
                    : timeAtBeatsFromTempoMap(arrangement.tempoMap || [], arrangement.tempoMap?.[0]?.bpm || 120, beatsStart);
                  const endSec = Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2
                    ? beatsToSecondsFromBeatTimesWithOffset(arrangement.beatTimes, beatsEnd, arrangement.beatZeroOffsetSec || 0)
                    : timeAtBeatsFromTempoMap(arrangement.tempoMap || [], arrangement.tempoMap?.[0]?.bpm || 120, beatsEnd);

                  requestAuditionBarPreview(selectedSectionId, selectedBarIndex, startSec, endSec, barNotesPreview as any);
                  setAuditioning(true);
                }}
              >
                {auditioning ? "Stop" : "Play"}
              </button>
              <button
                type="button"
                className="px-2 py-1 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 disabled:opacity-50"
                disabled={locked || !generatedDrumTrack}
                onClick={() => {
                  if (!selectedSectionId || selectedBarIndex == null) return;
                  applyBarEditsToGeneratedTrack(selectedSectionId, selectedBarIndex);
                }}
              >
                Apply
              </button>
              <button
                type="button"
                className="px-2 py-1 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 disabled:opacity-50"
                disabled={locked}
                onClick={() => {
                  if (!selectedSectionId || selectedBarIndex == null) return;
                  clearBarEditsForBar(selectedSectionId, selectedBarIndex);
                }}
              >
                Discard
              </button>
            </div>
          </div>

          <div className="mt-2 grid grid-cols-2 gap-2">
            <label className="flex items-center gap-2 text-[11px] text-slate-300 select-none">
              <input
                type="checkbox"
                data-testid="v3.bar.forceFill"
                checked={!!(activeBarEdit as any)?.forceFill}
                disabled={locked || !selectedSectionId || selectedBarIndex == null}
                onChange={(e) => {
                  if (!selectedSectionId || selectedBarIndex == null) return;
                  ensureBarEdit(selectedSectionId, selectedBarIndex);
                  setBarFillDirective(selectedSectionId, selectedBarIndex, { forceFill: e.target.checked, suppressFill: false });
                }}
              />
              Force fill on this bar
            </label>

            <label className="flex items-center gap-2 text-[11px] text-slate-300 select-none">
              <input
                type="checkbox"
                data-testid="v3.bar.suppressFill"
                checked={!!(activeBarEdit as any)?.suppressFill}
                disabled={locked || !selectedSectionId || selectedBarIndex == null}
                onChange={(e) => {
                  if (!selectedSectionId || selectedBarIndex == null) return;
                  ensureBarEdit(selectedSectionId, selectedBarIndex);
                  setBarFillDirective(selectedSectionId, selectedBarIndex, { suppressFill: e.target.checked, forceFill: false });
                }}
              />
              Suppress fill on this bar
            </label>
          </div>

          <div className="mt-2 grid grid-cols-3 gap-2">
            <Field label="Instrument">
              <select
                className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                value={newNoteInst}
                onChange={(e) => setNewNoteInst(e.target.value as DrumInstrumentId)}
                disabled={locked}
              >
                {Object.keys(DRUM_INSTRUMENT_MIDI_MAP).map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Step (16th)">
              <input
                type="number"
                min={0}
                max={15}
                value={newNoteStep16}
                onChange={(e) => setNewNoteStep16(Math.max(0, Math.min(15, Number(e.target.value) || 0)))}
                className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                disabled={locked}
              />
            </Field>
            <Field label="Velocity">
              <input
                type="number"
                min={1}
                max={127}
                value={newNoteVel}
                onChange={(e) => setNewNoteVel(Math.max(1, Math.min(127, Number(e.target.value) || 100)))}
                className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                disabled={locked}
              />
            </Field>
          </div>

          <div className="mt-2">
            <button
              type="button"
              data-testid="v3.bar.notes.add"
              className="px-2 py-1 rounded bg-slate-800 text-slate-100 text-[11px] border border-slate-700 disabled:opacity-50"
              disabled={locked || !generatedDrumTrack}
              onClick={() => {
                if (!selectedSectionId || selectedBarIndex == null) return;
                const ppq = Number((generatedDrumTrack as any)?.resolution_ppq || 960) || 960;
                const tickPer16 = Math.max(1, Math.floor(ppq / 4));
                const tickInBar = Math.max(0, Math.min(15, Math.floor(newNoteStep16))) * tickPer16;
                const inst = newNoteInst;
                const pitch = (DRUM_INSTRUMENT_MIDI_MAP as any)[inst] ?? 36;
                const color = (DRUM_INSTRUMENT_COLORS as any)[inst] ?? "#94A3B8";
                const id = `bar-${selectedSectionId}-${selectedBarIndex}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
                addBarEditNote(selectedSectionId, selectedBarIndex, {
                  id,
                  barIndex: selectedBarIndex,
                  tickInBar,
                  tickLength: tickPer16,
                  channel: 9,
                  midiPitch: pitch,
                  velocity: Math.max(1, Math.min(127, Math.floor(newNoteVel))),
                  instrumentId: inst,
                  isGhost: false,
                  isAccent: false,
                  isFlam: false,
                  isDrag: false,
                } as any);
                void color;
              }}
            >
              Add note
            </button>
          </div>

          <div className="mt-3">
            <div className="text-[11px] text-slate-400">Mini Grid (click to toggle)</div>
            <div className="mt-2 overflow-x-auto">
              <div className="min-w-[520px]">
                <div className="grid" style={{ gridTemplateColumns: `120px repeat(16, 1fr)` }}>
                  <div className="text-[10px] text-slate-500 px-1 py-0.5">&nbsp;</div>
                  {Array.from({ length: 16 }).map((_, i) => (
                    <div key={`h-${i}`} className="text-[10px] text-slate-500 text-center px-0.5 py-0.5">
                      {i + 1}
                    </div>
                  ))}
                </div>

                {miniGridLanes.map((inst) => {
                  const laneColor = (DRUM_INSTRUMENT_COLORS as any)[inst] ?? "#94A3B8";
                  const ppq = Number((generatedDrumTrack as any)?.resolution_ppq || 960) || 960;
                  const tickPer16 = Math.max(1, Math.floor(ppq / 4));

                  const notesForLane = barNotesPreview.filter((n: any) => String(n?.instrumentId || "") === inst);
                  const notesByStep: Record<number, any[]> = {};
                  for (const n of notesForLane) {
                    const t = Number(n?.tickInBar || 0);
                    const step = Math.max(0, Math.min(15, Math.floor((t + tickPer16 / 2) / tickPer16)));
                    if (!notesByStep[step]) notesByStep[step] = [];
                    notesByStep[step].push(n);
                  }

                  return (
                    <div key={inst} className="grid items-stretch" style={{ gridTemplateColumns: `120px repeat(16, 1fr)` }}>
                      <div className="flex items-center gap-2 px-1 py-1">
                        <div className="w-2 h-2 rounded" style={{ background: laneColor }} />
                        <div className="text-[11px] text-slate-200 truncate" title={inst}>
                          {inst}
                        </div>
                      </div>
                      {Array.from({ length: 16 }).map((_, step) => {
                        const hits = notesByStep[step] || [];
                        const isOn = hits.length > 0;
                        const title = isOn
                          ? `${inst} @ ${step + 1}/16 (${hits.length} hit${hits.length === 1 ? "" : "s"})`
                          : `${inst} @ ${step + 1}/16`;
                        return (
                          <button
                            key={`${inst}-${step}`}
                            type="button"
                            data-testid="v3.bar.notes.cell"
                            data-inst={inst}
                            data-step={String(step)}
                            title={title}
                            className={`h-6 border border-slate-800 ${
                              isOn ? "bg-slate-700" : "bg-slate-950"
                            } hover:bg-slate-800 disabled:opacity-50`}
                            disabled={locked || !generatedDrumTrack}
                            onClick={() => {
                              if (!selectedSectionId || selectedBarIndex == null) return;
                              ensureBarEdit(selectedSectionId, selectedBarIndex);
                              if (hits.length > 0) {
                                deleteBarEditNote(selectedSectionId, selectedBarIndex, String(hits[0]?.id || ""));
                                return;
                              }

                              const pitch = (DRUM_INSTRUMENT_MIDI_MAP as any)[inst] ?? 36;
                              const id = `bar-${selectedSectionId}-${selectedBarIndex}-${inst}-${step}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
                              addBarEditNote(selectedSectionId, selectedBarIndex, {
                                id,
                                barIndex: selectedBarIndex,
                                tickInBar: step * tickPer16,
                                tickLength: tickPer16,
                                channel: 9,
                                midiPitch: pitch,
                                velocity: Math.max(1, Math.min(127, Math.floor(newNoteVel))),
                                instrumentId: inst,
                                isGhost: false,
                                isAccent: false,
                                isFlam: false,
                                isDrag: false,
                              } as any);
                            }}
                          >
                            {isOn ? (
                              <div className="w-full h-full" style={{ background: laneColor, opacity: hits.length > 1 ? 0.85 : 0.7 }} />
                            ) : null}
                          </button>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="mt-3 space-y-1">
            {barNotesPreview.length === 0 ? (
              <div className="text-[11px] text-slate-500">No notes in this bar.</div>
            ) : (
              barNotesPreview.map((n: any) => {
                const inst: DrumInstrumentId = (n?.instrumentId as any) || "other";
                const color = (DRUM_INSTRUMENT_COLORS as any)[inst] ?? "#94A3B8";
                const ppq = Number((generatedDrumTrack as any)?.resolution_ppq || 960) || 960;
                const tickPer16 = Math.max(1, Math.floor(ppq / 4));
                return (
                  <div key={String(n?.id || "")} className="flex items-center gap-2 text-[11px]">
                    <div className="w-2 h-2 rounded" style={{ background: color }} />
                    <div className="min-w-[86px] text-slate-200">{inst}</div>
                    <div className="text-slate-400">t={Number(n?.tickInBar || 0)}</div>
                    <div className="text-slate-400">v={Number(n?.velocity || 0)}</div>
                    <div className="ml-auto flex items-center gap-1">
                      <button
                        type="button"
                        data-testid="v3.bar.notes.nudge_left"
                        data-note-id={String(n?.id || "")}
                        className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-200 border border-slate-700 disabled:opacity-50"
                        disabled={locked}
                        onClick={() => {
                          if (!selectedSectionId || selectedBarIndex == null) return;
                          nudgeBarEditNote(selectedSectionId, selectedBarIndex, String(n?.id || ""), -tickPer16);
                        }}
                      >
                        -
                      </button>
                      <button
                        type="button"
                        data-testid="v3.bar.notes.nudge_right"
                        data-note-id={String(n?.id || "")}
                        className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-200 border border-slate-700 disabled:opacity-50"
                        disabled={locked}
                        onClick={() => {
                          if (!selectedSectionId || selectedBarIndex == null) return;
                          nudgeBarEditNote(selectedSectionId, selectedBarIndex, String(n?.id || ""), tickPer16);
                        }}
                      >
                        +
                      </button>
                      <button
                        type="button"
                        data-testid="v3.bar.notes.delete"
                        data-note-id={String(n?.id || "")}
                        className="px-1.5 py-0.5 rounded bg-slate-900 text-rose-200 border border-slate-700 disabled:opacity-50"
                        disabled={locked}
                        onClick={() => {
                          if (!selectedSectionId || selectedBarIndex == null) return;
                          deleteBarEditNote(selectedSectionId, selectedBarIndex, String(n?.id || ""));
                        }}
                      >
                        Del
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      <div className="mt-3 rounded border border-slate-800 bg-slate-950/60 p-2 space-y-2">
        <InheritToggle
          group="identity"
          flag={groupFlag("identity")}
          disabled={locked}
          onChange={(flag) => setSectionInheritFlag(selectedSectionId, "identity", flag)}
        />
        <InheritToggle
          group="guide"
          flag={groupFlag("guide")}
          disabled={locked}
          onChange={(flag) => setSectionInheritFlag(selectedSectionId, "guide", flag)}
        />
        <InheritToggle
          group="generation"
          flag={groupFlag("generation")}
          disabled={locked}
          onChange={(flag) => setSectionInheritFlag(selectedSectionId, "generation", flag)}
        />
        <InheritToggle
          group="humanization"
          flag={groupFlag("humanization")}
          disabled={locked}
          onChange={(flag) => setSectionInheritFlag(selectedSectionId, "humanization", flag)}
        />
        <InheritToggle
          group="fills"
          flag={groupFlag("fills")}
          disabled={locked}
          onChange={(flag) => setSectionInheritFlag(selectedSectionId, "fills", flag)}
        />
        <InheritToggle
          group="rudiments"
          flag={groupFlag("rudiments")}
          disabled={locked}
          onChange={(flag) => setSectionInheritFlag(selectedSectionId, "rudiments", flag)}
        />
        <InheritToggle
          group="groove"
          flag={groupFlag("groove")}
          disabled={locked}
          onChange={(flag) => setSectionInheritFlag(selectedSectionId, "groove", flag)}
        />
      </div>

      <div className="mt-3 space-y-3">
        {selectedSectionId ? (
          <div className="rounded border border-slate-800 bg-slate-950/60 p-2">
            <div className="text-[11px] font-semibold text-slate-200">Presets</div>
            <div className="mt-2 flex items-center gap-2">
              <button
                type="button"
                className="px-2 py-0.5 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 disabled:opacity-50"
                disabled={presetExplainBusy || !effectiveDrummerId}
                onClick={async () => {
                  try {
                    setPresetExplainBusy(true);
                    setPresetExplainError(null);
                    const presetNames = (combinedPresetStack || [])
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
                        profileType: effectiveProfileType,
                        drummerId: effectiveDrummerId,
                        presetStack: combinedPresetStack,
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
            <div className="mt-2">
              <label className="flex items-center gap-2 text-[11px] text-slate-300 select-none">
                <input
                  type="checkbox"
                  checked={inheritGlobalPresets}
                  disabled={locked}
                  onChange={(e) => setSectionInheritGlobalPresets(selectedSectionId, e.target.checked)}
                />
                Inherit global presets
              </label>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <Field label="Add preset">
                <select
                  value={presetAddId}
                  onChange={(e) => setPresetAddId(e.target.value)}
                  className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                  disabled={locked}
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
                  disabled={locked}
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
                  disabled={locked}
                />
              </Field>
              <div className="flex items-end">
                <button
                  type="button"
                  className="w-full px-2 py-1 rounded bg-slate-800 text-slate-100 text-[11px] border border-slate-700 disabled:opacity-50"
                  disabled={locked || !presetAddId || !selectedSectionId}
                  onClick={() => {
                    if (!selectedSectionId) return;
                    const pid = String(presetAddId || "").trim();
                    if (!pid) return;
                    upsertSectionPreset(selectedSectionId, {
                      presetId: pid,
                      tier: presetAddTier,
                      intensity: Math.max(0, Math.min(100, Math.round(presetAddIntensity))),
                    });
                    setPresetAddId("");
                  }}
                >
                  Add
                </button>
              </div>
            </div>
            {presetError ? <div className="mt-2 text-[11px] text-rose-400">{presetError}</div> : null}
            <div className="mt-2 space-y-2">
              {sectionPresetStack.length === 0 ? (
                <div className="text-[11px] text-slate-500">No section presets.</div>
              ) : (
                sectionPresetStack.map((p: any) => (
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
                        if (!selectedSectionId) return;
                        upsertSectionPreset(selectedSectionId, {
                          presetId: String(p?.presetId || ""),
                          tier: (p?.tier || "flavor") as any,
                          intensity: Math.max(0, Math.min(100, Number(e.target.value) || 0)),
                        });
                      }}
                      className="flex-1"
                      disabled={locked}
                    />
                    <div className="text-[11px] text-slate-400 w-10 text-right">{Math.round(Number(p?.intensity ?? 0))}</div>
                    <button
                      type="button"
                      className="px-2 py-1 rounded bg-slate-900 text-rose-200 text-[11px] border border-slate-700 disabled:opacity-50"
                      disabled={locked || !selectedSectionId}
                      onClick={() => {
                        if (!selectedSectionId) return;
                        removeSectionPreset(selectedSectionId, String(p?.presetId || ""));
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : null}

        {groupEnabled("identity") && (
          <div
            className={
              "rounded border bg-slate-950/60 p-2 " +
              (overrideKeys.has("style") || overrideKeys.has("drummer") ? "border-amber-500/40" : "border-slate-800")
            }
          >
            <div className="text-[11px] font-semibold text-slate-200">Identity (override)</div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <Field label="Style">
                <input
                  value={String(overrides.style ?? "")}
                  onChange={(e) => setSectionOverrides(selectedSectionId, { style: e.target.value })}
                  className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                  placeholder={globalDefaults.style || "rock"}
                  disabled={locked}
                />
              </Field>
              <Field label="Drummer">
                <div className="space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-[11px] text-slate-300 truncate">
                      {String(overrides.publicDrummerId || overrides.drummer || "")
                        ? drummerNameById[String(overrides.publicDrummerId || overrides.drummer || "")] || String(overrides.publicDrummerId || overrides.drummer || "")
                        : "Inherit global…"}
                    </div>
                    <div className="flex items-center gap-2">
                      {(overrides.publicDrummerId || overrides.drummer) ? (
                        <button
                          type="button"
                          className="px-2 py-1 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 hover:border-slate-500 disabled:opacity-50"
                          disabled={locked}
                          onClick={() => {
                            setSectionOverrides(selectedSectionId, { publicDrummerId: undefined as any, drummer: undefined as any });
                          }}
                        >
                          Clear
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="px-2 py-1 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 hover:border-slate-500 disabled:opacity-50"
                        disabled={locked}
                        onClick={() => {
                          setDrummerPickerTarget({ scope: "section", sectionId: selectedSectionId });
                          setDrummerPickerOpen(true);
                        }}
                      >
                        Change Drummer
                      </button>
                    </div>
                  </div>
                  {drummerError && <div className="text-[11px] text-rose-400">{drummerError}</div>}
                </div>
              </Field>
            </div>
          </div>
        )}

        {groupEnabled("guide") && (
          <div className={"rounded border bg-slate-950/60 p-2 border-slate-800"}>
            <div className="text-[11px] font-semibold text-slate-200">Guide (override)</div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <div className={affectedBorder(["guideEnabled"])}>
                <Field label="Guide Enabled">
                  <label className="flex items-center gap-2 text-[11px] text-slate-300 select-none">
                    <input
                      type="checkbox"
                      data-testid="v3.section.guide.enabled"
                      checked={!!(overrides as any)?.guideEnabled}
                      disabled={locked}
                      onChange={(e) => {
                        setSectionOverrides(selectedSectionId, {
                          guideEnabled: e.target.checked,
                          guideInstrument: e.target.checked ? ((overrides as any)?.guideInstrument ?? "bass") : undefined,
                        } as any);
                      }}
                    />
                    Enable guide
                  </label>
                </Field>
              </div>

              <div className={affectedBorder(["guideInstrument"])}>
                <Field label="Guide Instrument">
                  <select
                    data-testid="v3.section.guide.instrument"
                    className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                    value={String((overrides as any)?.guideInstrument ?? "bass")}
                    disabled={locked || !(overrides as any)?.guideEnabled}
                    onChange={(e) => {
                      setSectionOverrides(selectedSectionId, {
                        guideInstrument: e.target.value as any,
                        guideEnabled: true,
                      } as any);
                    }}
                  >
                    {guideInstrumentOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
            </div>
          </div>
        )}

        {groupEnabled("generation") && (
          <div
            className={
              "rounded border bg-slate-950/60 p-2 " +
              (overrideKeys.has("generationMode") || overrideKeys.has("intensity") || overrideKeys.has("variation") || overrideKeys.has("hatsToRideBlend") || overrideKeys.has("hatsToRideThreshold") || overrideKeys.has("chorusRidePreference") || overrideKeys.has("footHatPulseSubdivision") || overrideKeys.has("footHatPulseApply")
                ? "border-amber-500/40"
                : "border-slate-800")
            }
          >
            <div className="text-[11px] font-semibold text-slate-200">Generation (override)</div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <Field label="Generation Mode">
                <select
                  value={(overrides.generationMode || globalDefaults.generationMode) as any}
                  onChange={(e) => setSectionOverrides(selectedSectionId, { generationMode: e.target.value as any })}
                  className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                  disabled={locked}
                >
                  {generationModes.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </Field>
              <div />

              <div className={affectedBorder(["intensity"])}>
              <Field label={`Intensity (${intensityLabel})`}>
                <V3Knob
                  label="Intensity"
                  value={Number(overrides.intensity ?? globalDefaults.intensity)}
                  onChange={(v) => setSectionOverrides(selectedSectionId, { intensity: v })}
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
                  label="Variation"
                  value={Number(overrides.variation ?? globalDefaults.variation)}
                  onChange={(v) => setSectionOverrides(selectedSectionId, { variation: v })}
                  min={0}
                  max={1}
                  step={0.01}
                  formatValue={(v) => v.toFixed(2)}
                />
              </Field>
              </div>

              <div className="col-span-2 rounded border border-slate-800 bg-slate-950/60 p-2">
                <div className="text-[11px] font-semibold text-slate-200">Cymbal Focus</div>
                <div className="mt-2 grid grid-cols-2 gap-3">
                  <div className={affectedBorder(["cymbalFocusMode"])}>
                  <Field label="Focus Mode">
                    <select
                      value={String(overrides.cymbalFocusMode ?? globalDefaults.cymbalFocusMode ?? "continuous")}
                      onChange={(e) => setSectionOverrides(selectedSectionId, { cymbalFocusMode: e.target.value as any })}
                      className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                      disabled={locked}
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
                      value={Number(overrides.rideBellPercent ?? globalDefaults.rideBellPercent ?? 0.2)}
                      onChange={(v) => setSectionOverrides(selectedSectionId, { rideBellPercent: v })}
                      min={0}
                      max={1}
                      step={0.01}
                      formatValue={(v) => v.toFixed(2)}
                    />
                  </Field>
                  </div>

                  <div className={affectedBorder(["hatsToRideBlend"])}>
                  <Field label={`Hat Ride Blend (${hatsToRideBlendLabel})`}>
                    <V3Knob
                      label="Blend"
                      value={Number(overrides.hatsToRideBlend ?? globalDefaults.hatsToRideBlend ?? 0)}
                      onChange={(v) => setSectionOverrides(selectedSectionId, { hatsToRideBlend: v })}
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
                      value={Number(overrides.hatsToRideThreshold ?? globalDefaults.hatsToRideThreshold ?? 0.6)}
                      onChange={(v) => setSectionOverrides(selectedSectionId, { hatsToRideThreshold: v })}
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
                      value={Number(overrides.chorusRidePreference ?? globalDefaults.chorusRidePreference ?? 0)}
                      onChange={(v) => setSectionOverrides(selectedSectionId, { chorusRidePreference: v })}
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
                      value={String(overrides.footHatPulseSubdivision ?? globalDefaults.footHatPulseSubdivision ?? "off")}
                      onChange={(e) => setSectionOverrides(selectedSectionId, { footHatPulseSubdivision: e.target.value as any })}
                      className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                      disabled={locked}
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
                      value={String(overrides.footHatPulseApply ?? globalDefaults.footHatPulseApply ?? "both")}
                      onChange={(e) => setSectionOverrides(selectedSectionId, { footHatPulseApply: e.target.value as any })}
                      className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                      disabled={locked}
                    >
                      <option value="transition">Transition only</option>
                      <option value="ride_bars">Ride bars</option>
                      <option value="both">Both</option>
                    </select>
                  </Field>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {groupEnabled("humanization") && (
          <div
            className={
              "rounded border bg-slate-950/60 p-2 " +
              (overrideKeys.has("humanize") ||
              overrideKeys.has("humanizeAmount") ||
              overrideKeys.has("swingAmount") ||
              overrideKeys.has("ghostNoteAmount") ||
              overrideKeys.has("quantizeStrength") ||
              overrideKeys.has("quantizeBase") ||
              overrideKeys.has("timingHumanizeMs") ||
              overrideKeys.has("velocityHumanize") ||
              overrideKeys.has("pushPullMs") ||
              overrideKeys.has("feelSeed")
                ? "border-amber-500/40"
                : "border-slate-800")
            }
          >
            <div className="text-[11px] font-semibold text-slate-200">Humanization (override)</div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <Field label={`Humanize (${(overrides.humanize ?? globalDefaults.humanize) ? "on" : "off"})`}>
                <label className="flex items-center gap-2 text-xs text-slate-300 select-none">
                  <input
                    type="checkbox"
                    data-testid="v3.section.humanization.humanize"
                    checked={!!(overrides.humanize ?? globalDefaults.humanize)}
                    onChange={(e) => setSectionOverrides(selectedSectionId, { humanize: e.target.checked })}
                    disabled={locked}
                  />
                  Enable
                </label>
              </Field>
              <div />

              <div className={affectedBorder(["humanizeAmount"])}>
              <Field label={`Humanize Amount (${humanizeAmountLabel})`}>
                <V3Knob
                  label="Humanize"
                  value={Number(overrides.humanizeAmount ?? globalDefaults.humanizeAmount ?? 0)}
                  onChange={(v) => setSectionOverrides(selectedSectionId, { humanizeAmount: v })}
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
                  label="Swing"
                  value={Number(overrides.swingAmount ?? globalDefaults.swingAmount ?? 0)}
                  onChange={(v) => setSectionOverrides(selectedSectionId, { swingAmount: v })}
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
                  label="Ghost"
                  value={Number(overrides.ghostNoteAmount ?? globalDefaults.ghostNoteAmount ?? 0)}
                  onChange={(v) => setSectionOverrides(selectedSectionId, { ghostNoteAmount: v })}
                  min={0}
                  max={1}
                  step={0.01}
                  formatValue={(v) => v.toFixed(2)}
                />
              </Field>
              </div>

              <div className={affectedBorder(["quantizeStrength"])}>
              <Field label={`Quantize Strength (${Number.isFinite(baseQuantizeStrength) ? baseQuantizeStrength.toFixed(2) : "0.00"})`}>
                <V3Knob
                  label="Quantize"
                  value={baseQuantizeStrength}
                  onChange={(v) => setSectionOverrides(selectedSectionId, { quantizeStrength: v } as any)}
                  min={0}
                  max={1}
                  step={0.01}
                  formatValue={(v) => Number(v).toFixed(2)}
                />
              </Field>
              </div>

              <div className={affectedBorder(["quantizeBase"])}>
              <Field label="Quantize Base">
                <select
                  value={String((overrides as any).quantizeBase ?? (globalDefaults as any).quantizeBase ?? "16th")}
                  onChange={(e) => setSectionOverrides(selectedSectionId, { quantizeBase: e.target.value as any } as any)}
                  className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                  disabled={locked}
                >
                  <option value="16th">16th</option>
                  <option value="8th">8th</option>
                  <option value="triplet_8th">Triplet 8th</option>
                  <option value="triplet_16th">Triplet 16th</option>
                </select>
              </Field>
              </div>

              <div className={affectedBorder(["timingHumanizeMs"])}>
              <Field label="Timing Humanize (ms)">
                <input
                  type="number"
                  value={String(Number.isFinite(baseTimingHumanizeMs) ? baseTimingHumanizeMs : 0)}
                  onChange={(e) => setSectionOverrides(selectedSectionId, { timingHumanizeMs: Number(e.target.value) } as any)}
                  className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                  disabled={locked}
                  min={0}
                  step={1}
                />
              </Field>
              </div>

              <div className={affectedBorder(["velocityHumanize"])}>
              <Field label={`Velocity Humanize (${Number.isFinite(baseVelocityHumanize) ? baseVelocityHumanize.toFixed(2) : "0.00"})`}>
                <V3Knob
                  label="Velocity"
                  value={baseVelocityHumanize}
                  onChange={(v) => setSectionOverrides(selectedSectionId, { velocityHumanize: v } as any)}
                  min={0}
                  max={1}
                  step={0.01}
                  formatValue={(v) => Number(v).toFixed(2)}
                />
              </Field>
              </div>

              <div className={affectedBorder(["pushPullMs"])}>
              <Field label="Push/Pull (ms)">
                <input
                  type="number"
                  value={String(Number.isFinite(basePushPullMs) ? basePushPullMs : 0)}
                  onChange={(e) => setSectionOverrides(selectedSectionId, { pushPullMs: Number(e.target.value) } as any)}
                  className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                  disabled={locked}
                  step={1}
                />
              </Field>
              </div>

              <div className={affectedBorder(["feelSeed"])}>
              <Field label="Feel Seed">
                <input
                  type="number"
                  value={String(Number.isFinite(baseFeelSeed) ? baseFeelSeed : 0)}
                  onChange={(e) => setSectionOverrides(selectedSectionId, { feelSeed: Number(e.target.value) } as any)}
                  className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                  disabled={locked}
                  step={1}
                />
              </Field>
              </div>
            </div>
          </div>
        )}

        {groupEnabled("fills") && (
          <div className={"rounded border bg-slate-950/60 p-2 border-slate-800"}>
            <div className="text-[11px] font-semibold text-slate-200">Fills (override)</div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <div className={affectedBorder(["fillControls.fillType"])}>
                <Field label="Fill Type">
                  <select
                    data-testid="v3.section.fills.fillType"
                    value={String((overrides as any)?.fillControls?.fillType ?? (overrides as any)?.fillType ?? globalDefaults.fillControls?.fillType ?? "auto")}
                    onChange={(e) => {
                      const fillType = e.target.value as any;
                      const prev: any = overrides.fillControls || globalDefaults.fillControls || {};
                      const next = { ...prev, fillType };
                      setSectionOverrides(selectedSectionId, { fillControls: next as any, fillType: next.fillType, fillDensity: next.density });
                    }}
                    className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                    disabled={locked}
                  >
                    <option value="auto">Auto</option>
                    <option value="none">None</option>
                    <option value="bar">Bar</option>
                    <option value="half_bar">Half-bar</option>
                    <option value="quarter_bar">Quarter-bar</option>
                  </select>
                </Field>
              </div>

              <div className={affectedBorder(["fillControls.frequency"])}>
                <Field label="Frequency">
                  <select
                    data-testid="v3.section.fills.frequency"
                    value={String((overrides as any)?.fillControls?.frequency ?? globalDefaults.fillControls?.frequency ?? "auto")}
                    onChange={(e) => {
                      const frequency = e.target.value as any;
                      const prev: any = overrides.fillControls || globalDefaults.fillControls || {};
                      const next = { ...prev, frequency };
                      setSectionOverrides(selectedSectionId, { fillControls: next as any, fillType: next.fillType, fillDensity: next.density });
                    }}
                    className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                    disabled={locked}
                  >
                    <option value="none">None</option>
                    <option value="sparse">Sparse</option>
                    <option value="medium">Medium</option>
                    <option value="dense">Dense</option>
                    <option value="auto">Auto</option>
                  </select>
                </Field>
              </div>

              <div className={affectedBorder(["fillControls.density", "fillDensity"])}>
                <Field label={`Fill Density (${fillDensityPreviewLabel})`}>
                  <V3Knob
                    testId="v3.section.fills.density.knob"
                    label="Density"
                    value={Number(overrides.fillControls?.density ?? (overrides as any)?.fillDensity ?? globalDefaults.fillControls?.density ?? 0.7)}
                    onChange={(v) => {
                      const prev: any = overrides.fillControls || globalDefaults.fillControls || {};
                      const next = { ...prev, density: v };
                      setSectionOverrides(selectedSectionId, { fillControls: next as any, fillType: next.fillType, fillDensity: next.density });
                    }}
                    min={0}
                    max={1}
                    step={0.01}
                    formatValue={(v) => Number(v).toFixed(2)}
                  />
                </Field>
              </div>
              <div />
            </div>
          </div>
        )}

        {groupEnabled("rudiments") && (
          <div className={"rounded border bg-slate-950/60 p-2 border-slate-800"}>
            <div className="text-[11px] font-semibold text-slate-200">Rudiments (override)</div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <div className={affectedBorder(["rudimentControls.handLead"])}>
                <Field label="Hand Lead">
                  <select
                    data-testid="v3.section.rudiments.handLead"
                    value={String((overrides as any)?.rudimentControls?.handLead ?? globalDefaults.rudimentControls?.handLead ?? "auto")}
                    onChange={(e) => {
                      const handLead = e.target.value as any;
                      const prev: any = overrides.rudimentControls || globalDefaults.rudimentControls || {};
                      const next = { ...prev, handLead };
                      setSectionOverrides(selectedSectionId, { rudimentControls: next as any });
                    }}
                    className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                    disabled={locked}
                  >
                    <option value="auto">Auto</option>
                    <option value="right">Right</option>
                    <option value="left">Left</option>
                  </select>
                </Field>
              </div>

              <div className={affectedBorder(["rudimentControls.density"])}>
                <Field label={`Density (${rudimentDensityLabel})`}>
                  <V3Knob
                    testId="v3.section.rudiments.density.knob"
                    label="Rud"
                    value={Number(overrides.rudimentControls?.density ?? globalDefaults.rudimentControls?.density ?? 0)}
                    onChange={(v) => {
                      const prev: any = overrides.rudimentControls || globalDefaults.rudimentControls || {};
                      const next = { ...prev, density: v };
                      setSectionOverrides(selectedSectionId, { rudimentControls: next as any });
                    }}
                    min={0}
                    max={1}
                    step={0.01}
                    formatValue={(v) => Number(v).toFixed(2)}
                  />
                </Field>
              </div>
            </div>
          </div>
        )}

        {groupEnabled("groove") && (
          <div className={"rounded border bg-slate-950/60 p-2 border-slate-800"}>
            <div className="text-[11px] font-semibold text-slate-200">Groove (override)</div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <Field label="Selected Groove Id">
                <input
                  data-testid="v3.section.groove.selectedGrooveId"
                  value={String(overrides.selectedGrooveId ?? "")}
                  onChange={(e) => setSectionOverrides(selectedSectionId, { selectedGrooveId: e.target.value })}
                  className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                  placeholder={String(globalDefaults.selectedGrooveId ?? "") || "(none)"}
                  disabled={locked}
                />
              </Field>
              <Field label="Groove Use">
                <select
                  data-testid="v3.section.groove.grooveUse"
                  value={String(overrides.grooveUse ?? globalDefaults.grooveUse ?? "use_as_groove")}
                  onChange={(e) => setSectionOverrides(selectedSectionId, { grooveUse: e.target.value as any })}
                  className="w-auto bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                  disabled={locked}
                >
                  <option value="use_as_groove">Use as groove</option>
                  <option value="use_as_fill">Use as fill</option>
                </select>
              </Field>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
