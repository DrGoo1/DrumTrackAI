import React, { useMemo, useState } from "react";
import { KnobCircle } from "./KnobCircle";
import type { SectionRow } from "./SectionsPanel";
import type { DrumGenerationConfigDTO, BarDefaultsDTO, SlotMetaDTO } from "../../types/drumGenerationConfig";
import { generateDrums } from "../../services/api";
import type { EuclideanLaneConfig } from "../../euclidean/euclidean";
import { EUCLIDEAN_PRESETS } from "../../euclidean/presets";

interface DrumCreationPanelProps {
  sourceSong: { key: string; durationSec: number } | null;
  sections: SectionRow[];
  onApplyDrums?: (payload: { drum_track: any; midi_notes: any[]; metadata?: any }) => void;
  onConfigBuilt?: (cfg: DrumGenerationConfigDTO) => void;

  // Optional meta from Limb Bar Editor (per-bar and per-slot controls)
  barMetaDefaults?: BarDefaultsDTO[];
  barMetaSlots?: SlotMetaDTO[];
}

export const DrumCreationPanel: React.FC<DrumCreationPanelProps> = ({
  sourceSong,
  sections,
  onApplyDrums,
  onConfigBuilt,
  barMetaDefaults,
  barMetaSlots,
}) => {
  const [style, setStyle] = useState("Studio Rock");

  // Use DrumTracKAI drummer *categories* instead of literal drummer names.
  // These map to backend drummer IDs but present high-level categories in the UI.
  const drummerCategories: { id: string; label: string }[] = [
    { id: "studio_rock", label: "Studio Rock" },
    { id: "funk_pocket", label: "Funk Pocket" },
    { id: "fusion_pro", label: "Fusion / Prog" },
    { id: "neo_soul", label: "Neo-Soul" },
    { id: "metal_power", label: "Metal Power" },
  ];

  const [drummerCategoryId, setDrummerCategoryId] = useState<string>(drummerCategories[0]?.id ?? "studio_rock");
  const [intensity, setIntensity] = useState(0.7);
  const [variation, setVariation] = useState(0.5);
  const [humanizeOn, setHumanizeOn] = useState(true);
  const [humanizeAmount, setHumanizeAmount] = useState(0.7);
  const [ghostAmount, setGhostAmount] = useState(0.6);
  const [swingAmount, setSwingAmount] = useState(0.0);
  const [drumDensity, setDrumDensity] = useState(0.7);
  const [cymbalDensity, setCymbalDensity] = useState(0.6);
  const [fillType, setFillType] = useState("auto");
  const [fillDensity, setFillDensity] = useState(0.7);
  const [guideEnabled, setGuideEnabled] = useState(false);
  const [guideInstrument, setGuideInstrument] = useState<"mix" | "bass" | "guitar" | "keys" | "vocal" | "other">("mix");
  const [buildScope, setBuildScope] = useState<"full_song" | "selected_section">("selected_section");
  const [generationMode, setGenerationMode] = useState<"template" | "ai_variation" | "full_ai" | "euclidean">("template");
  const [drummerBrainEnabled, setDrummerBrainEnabled] = useState(false);
  const [articulationProfile, setArticulationProfile] = useState<"balanced" | "ghosty" | "tight_hats" | "crashy">("balanced");
  const [intensityCurve, setIntensityCurve] = useState<"flat" | "build" | "breakdown">("flat");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [euclidPresetId, setEuclidPresetId] = useState<string>(EUCLIDEAN_PRESETS[0]?.id ?? "in_fives");
  const [euclidLanes, setEuclidLanes] = useState<EuclideanLaneConfig[]>(EUCLIDEAN_PRESETS[0]?.lanes ?? []);

  const [openGroove, setOpenGroove] = useState(true);
  const [openFills, setOpenFills] = useState(true);
  const [openGuide, setOpenGuide] = useState(false);

  const hasSource = !!sourceSong;
  const hasSections = sections.length > 0;

  // Simple heuristic: put fills at the end of sections where fillOut is enabled
  // (or at the last bar of the song when using full song scope).
  const fillLocations = useMemo(() => {
    if (!hasSections) return [] as number[];
    const locs: number[] = [];
    sections.forEach((sec, idx) => {
      // Treat Fill Out as a full-bar fill on this section's bar index
      if (sec.fillOut) {
        locs.push(idx);
      }
      // Treat Fill In as a lighter lead-in fill on the preceding bar
      if (sec.fillIn && idx > 0) {
        locs.push(idx - 1);
      }
    });
    // Deduplicate and sort indices
    return Array.from(new Set(locs)).sort((a, b) => a - b);
  }, [sections, hasSections]);

  async function handleGenerate() {
    if (!sourceSong || !hasSections) return;
    setBusy(true);
    setErr(null);

    try {
      const first = sections[0];
      const last = sections[sections.length - 1];

      const bpm = 120; // TODO: replace with analyzed tempo when available
      const barsApprox = Math.max(4, Math.round(sourceSong.durationSec / (60 / bpm * 4)));

      // Use arrangement section densities to gently modulate overall intensity
      const avgSectionDensity = sections.length
        ? sections.reduce((sum, s) => sum + (s.density || 0), 0) / sections.length
        : 1.0;
      let effectiveIntensity = Math.min(1, Math.max(0, intensity * (0.5 + avgSectionDensity / 2)));
      let effectiveFillDensity = Math.min(1, Math.max(0, fillDensity * (0.5 + avgSectionDensity / 2)));

      if (intensityCurve === "build") {
        effectiveIntensity = Math.min(1, effectiveIntensity * 1.1);
        effectiveFillDensity = Math.min(1, effectiveFillDensity * 1.1);
      } else if (intensityCurve === "breakdown") {
        effectiveIntensity = Math.max(0, effectiveIntensity * 0.85);
        effectiveFillDensity = Math.max(0, effectiveFillDensity * 0.9);
      }

      const boolDrummerBrainEnabled = Boolean(drummerBrainEnabled) && generationMode !== "euclidean";

      const cfg: DrumGenerationConfigDTO = {
        sectionId: "main_section",
        startMeasure: 0,
        endMeasure: barsApprox - 1,
        tempos: Array.from({ length: barsApprox }, () => bpm),
        timeSignature: [4, 4],
        style,
        drummer: drummerCategoryId,
        publicDrummerId: drummerCategoryId,
        drummerBrainEnabled: boolDrummerBrainEnabled,
        intensity: effectiveIntensity,
        variation,
        generationMode,
        humanize: humanizeOn,
        fillLocations,
        fillType,
        fillDensity: effectiveFillDensity,
        humanizeAmount,
        ghostNoteAmount: ghostAmount,
        swingAmount,
        buildScope,
        guideEnabled,
        guideInstrument,
        articulationProfile,
        euclideanLanes:
          generationMode === "euclidean"
            ? euclidLanes.map((lane) => ({
                instrumentId: lane.instrumentId,
                steps: lane.steps,
                hits: lane.hits,
                accents: lane.accents,
                rotate: lane.rotate,
                velocity: lane.velocity,
                accentVelocity: lane.accentVelocity,
              }))
            : undefined,

        // Limb Bar Editor meta, if provided
        bars: barMetaDefaults,
        slots: barMetaSlots,
      };

      onConfigBuilt?.(cfg);

      const resp = await generateDrums(cfg);
      onApplyDrums?.({ drum_track: resp.drum_track, midi_notes: resp.midi_notes, metadata: resp.metadata });
    } catch (e: any) {
      setErr(e?.message || "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2 p-3 bg-neutral-900 rounded border border-neutral-800 text-[13px] leading-snug">
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-cyan-300 text-sm tracking-wide">Drum Creation</span>
        {!hasSource && <span className="text-[10px] text-amber-400">Upload a source song first</span>}
      </div>

      {/* Top-level selectors */}
      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-neutral-300 text-[12px] font-medium">Style</span>
          <select
            className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1"
            value={style}
            onChange={(e) => setStyle(e.target.value)}
          >
            <option>Studio Rock</option>
            <option>Funk Pocket</option>
            <option>Fusion / Prog</option>
            <option>Neo-Soul</option>
            <option>Afro 12/8</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-neutral-300 text-[12px] font-medium">Drummer Category</span>
          <select
            className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1"
            value={drummerCategoryId}
            onChange={(e) => setDrummerCategoryId(e.target.value)}
          >
            {drummerCategories.map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {/* Groove & Performance */}
      <div className="mt-1 border border-neutral-800 rounded bg-neutral-950/60">
        <button
          className="w-full flex items-center justify-between px-2 py-1 text-[14px] font-medium text-neutral-200 hover:bg-neutral-900"
          onClick={() => setOpenGroove(v => !v)}
        >
          <span>Groove & Performance</span>
          <span className="text-neutral-500">{openGroove ? "Hide" : "Show"}</span>
        </button>
        {openGroove && (
          <div className="p-2 space-y-3">
            <div className="flex items-center justify-between gap-3 mb-1">
              <div className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={humanizeOn}
                  onChange={(e) => setHumanizeOn(e.target.checked)}
                />
                <span className="text-[11px]">Humanize Enabled</span>
              </div>
              <div className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={drummerBrainEnabled}
                  onChange={(e) => setDrummerBrainEnabled(e.target.checked)}
                  disabled={generationMode === "euclidean"}
                />
                <span className={"text-[11px] " + (generationMode === "euclidean" ? "text-neutral-600" : "")}>Sentient Drummer</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-4 justify-between">
              <div className="flex gap-4">
                <KnobCircle
                  label="Intensity"
                  value={intensity}
                  onChange={setIntensity}
                />
                <KnobCircle
                  label="Variation"
                  value={variation}
                  onChange={setVariation}
                />
              </div>
              <div className="flex gap-4">
                <KnobCircle
                  label="Humanize"
                  value={humanizeAmount}
                  onChange={setHumanizeAmount}
                />
                <KnobCircle
                  label="Ghosts"
                  value={ghostAmount}
                  onChange={setGhostAmount}
                />
                <KnobCircle
                  label="Swing"
                  value={swingAmount}
                  onChange={setSwingAmount}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <label className="flex flex-col gap-1">
                <span className="text-neutral-400 text-[11px]">Swing</span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={swingAmount}
                  onChange={(e) => setSwingAmount(parseFloat(e.target.value))}
                  className="w-full h-1 accent-emerald-500"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-neutral-400 text-[11px]">Scope</span>
                <select
                  className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1"
                  value={buildScope}
                  onChange={(e) => setBuildScope(e.target.value as any)}
                >
                  <option value="selected_section">Selected section</option>
                  <option value="full_song">Full song</option>
                </select>
              </label>
            </div>
            <div className="flex gap-4 mt-2">
              <KnobCircle
                label="Drum Dens."
                value={drumDensity}
                onChange={setDrumDensity}
              />
              <KnobCircle
                label="Cymbal Dens."
                value={cymbalDensity}
                onChange={setCymbalDensity}
              />
            </div>
          </div>
        )}
      </div>

      {/* Fills & Structure */}
      <div className="mt-1 border border-neutral-800 rounded bg-neutral-950/60">
        <button
          className="w-full flex items-center justify-between px-2 py-1 text-[12px] font-medium text-neutral-200 hover:bg-neutral-900"
          onClick={() => setOpenFills(v => !v)}
        >
          <span>Fills & Structure</span>
          <span className="text-neutral-500">{openFills ? "Hide" : "Show"}</span>
        </button>
        {openFills && (
          <div className="p-2 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <label className="flex flex-col gap-1">
                <span className="text-neutral-400 text-[11px]">Fill Type</span>
                <select
                  className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1"
                  value={fillType}
                  onChange={(e) => setFillType(e.target.value)}
                >
                  <option value="auto">Auto</option>
                  <option value="tom_run">Tom Run</option>
                  <option value="crash_buildup">Crash Buildup</option>
                  <option value="snare_fill">Snare Fill</option>
                </select>
              </label>
              <div className="flex items-center gap-3">
                <div className="flex-1 flex flex-col gap-1">
                  <span className="text-neutral-400 text-[11px]">Fill Density</span>
                  <span className="text-[10px] text-neutral-500">
                    Locations follow Arrangement "Fill In/Out" flags ({sections.filter(s => s.fillIn).length} in, {sections.filter(s => s.fillOut).length} out)
                  </span>
                </div>
                <KnobCircle
                  label="Density"
                  value={fillDensity}
                  onChange={setFillDensity}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Guide & Articulation */}
      <div className="mt-1 border border-neutral-800 rounded bg-neutral-950/60">
        <button
          className="w-full flex items-center justify-between px-2 py-1 text-[11px] text-neutral-300 hover:bg-neutral-900"
          onClick={() => setOpenGuide(v => !v)}
        >
          <span>Guide & Articulation</span>
          <span className="text-neutral-500">{openGuide ? "Hide" : "Show"}</span>
        </button>
        {openGuide && (
          <div className="p-2 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <label className="flex flex-col gap-1">
                <span className="text-neutral-400 text-[11px]">Guide Track</span>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={guideEnabled}
                    onChange={(e) => setGuideEnabled(e.target.checked)}
                  />
                  <select
                    className="flex-1 bg-neutral-950 border border-neutral-700 rounded px-2 py-1"
                    value={guideInstrument}
                    onChange={(e) => setGuideInstrument(e.target.value as any)}
                    disabled={!guideEnabled}
                  >
                    <option value="mix">Full Mix</option>
                    <option value="bass">Bass</option>
                    <option value="guitar">Guitar</option>
                    <option value="keys">Keys</option>
                    <option value="vocal">Vocal</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-neutral-400 text-[11px]">Jamstix / Articulation</span>
                <select
                  className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1"
                  value={articulationProfile}
                  onChange={(e) => setArticulationProfile(e.target.value as any)}
                >
                  <option value="balanced">Balanced Groove</option>
                  <option value="ghosty">Ghost-Note Heavy</option>
                  <option value="tight_hats">Tight Hats / Minimal Cymbals</option>
                  <option value="crashy">Crash-Forward</option>
                </select>
              </label>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 text-[11px]">
        <div className="flex items-center gap-1">
          <span className="text-neutral-400">Mode</span>
          <select
            className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1"
            value={generationMode}
            onChange={(e) => setGenerationMode(e.target.value as any)}
          >
            <option value="template">Template</option>
            <option value="ai_variation">AI Variation</option>
            <option value="full_ai">Full AI</option>
            <option value="euclidean">Euclidean</option>
          </select>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-neutral-400">Intensity Curve</span>
          <select
            className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1"
            value={intensityCurve}
            onChange={(e) => setIntensityCurve(e.target.value as any)}
          >
            <option value="flat">Flat</option>
            <option value="build">Build</option>
            <option value="breakdown">Breakdown</option>
          </select>
        </div>
      </div>

      {generationMode === "euclidean" && (
        <div className="mt-2 space-y-2 border border-neutral-800 rounded p-2 bg-neutral-950/60">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-neutral-300">Euclidean Lanes</span>
            <select
              className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1"
              value={euclidPresetId}
              onChange={(e) => {
                const id = e.target.value;
                setEuclidPresetId(id);
                const preset = EUCLIDEAN_PRESETS.find((p) => p.id === id);
                if (preset) setEuclidLanes(preset.lanes);
              }}
            >
              {EUCLIDEAN_PRESETS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {euclidLanes.map((lane) => (
              <div key={lane.id} className="grid grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)] gap-1 items-center text-[11px]">
                <div className="flex items-center gap-1">
                  <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: lane.color }} />
                  <span className="text-neutral-300">{lane.label}</span>
                </div>
                <label className="flex items-center gap-1">
                  <span className="text-neutral-400">Hits</span>
                  <input
                    type="number"
                    className="w-14 bg-neutral-950 border border-neutral-700 rounded px-1 py-0.5"
                    value={lane.hits}
                    min={0}
                    max={lane.steps}
                    onChange={(e) => {
                      const v = Math.max(0, Math.min(lane.steps, Number(e.target.value) || 0));
                      setEuclidLanes((prev) => prev.map((ln) => (ln.id === lane.id ? { ...ln, hits: v } : ln)));
                    }}
                  />
                </label>
                <label className="flex items-center gap-1">
                  <span className="text-neutral-400">Rotate</span>
                  <input
                    type="number"
                    className="w-14 bg-neutral-950 border border-neutral-700 rounded px-1 py-0.5"
                    value={lane.rotate}
                    min={0}
                    max={lane.steps - 1}
                    onChange={(e) => {
                      const v = Math.max(0, Math.min(lane.steps - 1, Number(e.target.value) || 0));
                      setEuclidLanes((prev) => prev.map((ln) => (ln.id === lane.id ? { ...ln, rotate: v } : ln)));
                    }}
                  />
                </label>
              </div>
            ))}
          </div>
        </div>
      )}

      {err && <div className="text-[11px] text-rose-400">{err}</div>}

      <button
        className="mt-1 w-full px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-700 disabled:cursor-not-allowed text-xs"
        disabled={!hasSource || !hasSections || busy}
        onClick={handleGenerate}
      >
        {busy ? "Generating…" : "Generate Drum Track"}
      </button>
    </div>
  );
};
