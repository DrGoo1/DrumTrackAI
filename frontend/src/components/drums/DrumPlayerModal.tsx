import React, { useEffect, useMemo, useRef, useState } from "react";
import ConsoleMixer, { type ConsoleMixerState } from "./ConsoleMixer";
import { getSharedDrumPlayerEngine, type DrumPlayerChannelId } from "../../audio/drumPlayerEngine";
import { getKitManifest, listKits } from "../../api/api";
import type { KitListItem, KitManifestV1 } from "../../types/kits";

type SampleCollection = {
  id: number;
  collection_name: string;
  description?: string;
  manufacturer?: string;
  category?: string;
  folder_path?: string;
  sample_count?: number;
  created_at?: string;
};

type DrumSample = {
  id: number;
  file_path: string;
  file_name: string;
  file_size?: number;
  drum_type?: string;
  variation?: string;
  format?: string;
  kit_name?: string;
};

function sampleDisplayLabel(s: DrumSample): string {
  const fileName = (s.file_name || "").trim();
  const path = (s.file_path || "").replace("\\", "/");
  const parts = path.split("/").filter(Boolean);
  const parent = parts.length >= 2 ? parts[parts.length - 2] : "";

  const generic = /^(instrument|sample|audio|track)(\s*\(\d+\))?\.(wav|mp3|aif|aiff|flac)$/i.test(fileName);
  const type = (s.drum_type || "").trim();
  const kit = (s.kit_name || "").trim();
  const variation = (s.variation || "").trim();

  const bits: string[] = [];
  if (type) bits.push(type.toUpperCase());
  if (kit) bits.push(kit);
  if (variation) bits.push(variation);
  if (generic && parent) bits.push(parent);

  const prefix = bits.length ? bits.join(" · ") + " — " : "";
  return prefix + (fileName || `#${s.id}`);
}

type DrumChannelId =
  | "kick"
  | "kick_sub"
  | "snare_top"
  | "snare_bottom"
  | "tom1"
  | "tom2"
  | "tom3"
  | "tom4"
  | "tom5"
  | "hat"
  | "ride"
  | "crash"
  | "oh"
  | "room"
  | "master";

type ChannelDef = {
  id: DrumChannelId;
  label: string;
  drumTypeQuery?: string;
};

const CHANNELS: ChannelDef[] = [
  { id: "kick", label: "Kick", drumTypeQuery: "kick" },
  { id: "kick_sub", label: "Kick Sub", drumTypeQuery: "kick" },
  { id: "snare_top", label: "Snare Top", drumTypeQuery: "snare" },
  { id: "snare_bottom", label: "Snare Bottom", drumTypeQuery: "snare" },
  { id: "hat", label: "HiHat", drumTypeQuery: "hihat" },
  { id: "tom1", label: "Tom 1", drumTypeQuery: "tom" },
  { id: "tom2", label: "Tom 2", drumTypeQuery: "tom" },
  { id: "tom3", label: "Tom 3", drumTypeQuery: "tom" },
  { id: "tom4", label: "Tom 4", drumTypeQuery: "tom" },
  { id: "tom5", label: "Tom 5", drumTypeQuery: "tom" },
  { id: "ride", label: "Ride", drumTypeQuery: "ride" },
  // DB classifies crashes under drum_type='cymbal'
  { id: "crash", label: "Crash", drumTypeQuery: "cymbal" },
  { id: "oh", label: "OH (stereo)" },
  { id: "room", label: "Room (stereo)" },
  { id: "master", label: "Master" },
];

function safeJsonParse<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} ${txt}`);
  }
  return (await res.json()) as T;
}

export default function DrumPlayerModal(props: { isOpen: boolean; onClose: () => void }) {
  const { isOpen, onClose } = props;

  const engineRef = useRef<ReturnType<typeof getSharedDrumPlayerEngine> | null>(null);
  const splitRef = useRef<HTMLDivElement | null>(null);
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [audioErr, setAudioErr] = useState<string | null>(null);

  const [kits, setKits] = useState<KitListItem[]>([]);
  const [selectedKitId, setSelectedKitId] = useState<string>("");
  const [loadingKits, setLoadingKits] = useState(false);
  const [loadingKitManifest, setLoadingKitManifest] = useState(false);
  const [kitErr, setKitErr] = useState<string | null>(null);

  const [collections, setCollections] = useState<SampleCollection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | "">("");
  const [samples, setSamples] = useState<DrumSample[]>([]);
  const [loadingCollections, setLoadingCollections] = useState(false);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  const [sampleQuery, setSampleQuery] = useState("");

  const [mixerState, setMixerState] = useState<ConsoleMixerState | null>(null);

  const [defaultKitLoaded, setDefaultKitLoaded] = useState(false);

  const [ohMicSim, setOhMicSim] = useState("XY - Small Diaphragm Condenser");
  const [roomSim, setRoomSim] = useState("Tight Dead Room");

  const [leftPaneWidth, setLeftPaneWidth] = useState(() => {
    const raw = window.localStorage.getItem("dtk.drumPlayer.leftPaneWidth");
    const n = raw ? Number(raw) : NaN;
    return Number.isFinite(n) ? n : 340;
  });
  const isResizingRef = useRef(false);

  useEffect(() => {
    window.localStorage.setItem("dtk.drumPlayer.leftPaneWidth", String(Math.round(leftPaneWidth)));
  }, [leftPaneWidth]);

  const [channelSampleId, setChannelSampleId] = useState<Record<string, number | "">>(() => {
    const saved = safeJsonParse<Record<string, number>>(window.localStorage.getItem("dtk.drumPlayer.channelSampleId"));
    if (!saved) return {};
    const normalized: Record<string, number | ""> = {};
    for (const [k, v] of Object.entries(saved)) normalized[k] = v;
    return normalized;
  });

  useEffect(() => {
    const toSave: Record<string, number> = {};
    for (const [k, v] of Object.entries(channelSampleId)) {
      if (typeof v === "number") toSave[k] = v;
    }
    window.localStorage.setItem("dtk.drumPlayer.channelSampleId", JSON.stringify(toSave));
  }, [channelSampleId]);

  useEffect(() => {
    if (!isOpen) return;
    setAudioErr(null);
    setKitErr(null);
    setDefaultKitLoaded(false);
  }, [isOpen]);

  const loadBuiltInDefaultKit = async () => {
    const engine = ensureEngine();
    await engine.ensureRunning();
    await Promise.all([
      engine.loadSampleForChannel("kick", "/samples/drums/kick.wav"),
      engine.loadSampleForChannel("snare_top", "/samples/drums/snare.wav"),
      engine.loadSampleForChannel("hat", "/samples/drums/hihat.wav"),
      engine.loadSampleForChannel("tom1", "/samples/drums/tom.wav"),
      engine.loadSampleForChannel("ride", "/samples/drums/ride.wav"),
      engine.loadSampleForChannel("crash", "/samples/drums/crash.wav"),
    ]);
    setDefaultKitLoaded(true);
  };

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    setLoadingKits(true);
    setKitErr(null);
    listKits()
      .then((data) => {
        if (cancelled) return;
        setKits(data.kits || []);
      })
      .catch((e: any) => {
        if (cancelled) return;
        setKitErr(e?.message ? String(e.message) : String(e));
      })
      .finally(() => {
        if (cancelled) return;
        setLoadingKits(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;
    setLoadErr(null);
    setLoadingCollections(true);
    fetchJson<{ collections: SampleCollection[] }>("/api/sample-collections")
      .then((data) => {
        if (cancelled) return;
        setCollections(data.collections || []);
      })
      .catch((e: any) => {
        if (cancelled) return;
        setLoadErr(e?.message ? String(e.message) : String(e));
      })
      .finally(() => {
        if (cancelled) return;
        setLoadingCollections(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    if (selectedCollectionId === "") {
      setSamples([]);
      return;
    }

    let cancelled = false;
    setLoadErr(null);
    setLoadingSamples(true);

    const collectionUrl = `/api/drum-samples?collection_id=${encodeURIComponent(String(selectedCollectionId))}&limit=800`;
    const cymbalUrl = `/api/drum-samples?collection_id=${encodeURIComponent(String(selectedCollectionId))}&drum_type=cymbal&limit=600`;
    Promise.all([fetchJson<{ samples: DrumSample[] }>(collectionUrl), fetchJson<{ samples: DrumSample[] }>(cymbalUrl)])
      .then(([collectionData, cymbalData]) => {
        if (cancelled) return;
        const merged: DrumSample[] = [];
        const seen = new Set<number>();
        for (const s of (collectionData.samples || [])) {
          if (typeof s?.id === "number" && !seen.has(s.id)) {
            seen.add(s.id);
            merged.push(s);
          }
        }
        for (const s of (cymbalData.samples || [])) {
          if (typeof s?.id === "number" && !seen.has(s.id)) {
            seen.add(s.id);
            merged.push(s);
          }
        }
        setSamples(merged);
      })
      .catch((e: any) => {
        if (cancelled) return;
        setLoadErr(e?.message ? String(e.message) : String(e));
      })
      .finally(() => {
        if (cancelled) return;
        setLoadingSamples(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, selectedCollectionId]);

  const samplesByType = useMemo(() => {
    const map = new Map<string, DrumSample[]>();
    for (const s of samples) {
      const dt = (s.drum_type || "").toLowerCase();
      if (!map.has(dt)) map.set(dt, []);
      map.get(dt)!.push(s);
    }
    return map;
  }, [samples]);

  const filteredSamples = useMemo(() => {
    const q = sampleQuery.trim().toLowerCase();
    if (!q) return samples;
    return samples.filter((s) => {
      const name = (s.file_name || "").toLowerCase();
      const kit = (s.kit_name || "").toLowerCase();
      const varx = (s.variation || "").toLowerCase();
      return name.includes(q) || kit.includes(q) || varx.includes(q);
    });
  }, [samples, sampleQuery]);

  const optionsForChannel = (ch: ChannelDef): DrumSample[] => {
    if (!ch.drumTypeQuery) return [];

    const q = ch.drumTypeQuery.toLowerCase();

    // Special case: crash lane should pull from cymbal category, but still prefer crash-ish names.
    if (ch.id === "crash") {
      const allCymbals: DrumSample[] = [];
      for (const s of filteredSamples) {
        const dt = (s.drum_type || "").toLowerCase();
        if (dt === "cymbal" || dt.includes("cymbal")) allCymbals.push(s);
      }

      const isCrashish = (s: DrumSample) => {
        const name = `${s.file_name || ""} ${(s.variation || "")} ${(s.kit_name || "")}`.toLowerCase();
        return name.includes("crash") || name.includes("china") || name.includes("splash") || name.includes("fx");
      };

      const crashishFromCymbals = allCymbals.filter(isCrashish);
      if (crashishFromCymbals.length) return crashishFromCymbals;
      if (allCymbals.length) return allCymbals;

      // Last resort: cymbal/crash-like names even if drum_type tagging is missing.
      return filteredSamples.filter(isCrashish);
    }

    const direct = samplesByType.get(q);
    if (direct && direct.length) return direct;

    const merged: DrumSample[] = [];
    for (const s of filteredSamples) {
      const dt = (s.drum_type || "").toLowerCase();
      if (dt.includes(q)) merged.push(s);
    }
    return merged;
  };

  const clampLeftWidth = (w: number) => {
    const min = 280;
    const max = 520;
    return Math.max(min, Math.min(max, w));
  };

  const beginResize = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingRef.current = true;
    const onMove = (ev: MouseEvent) => {
      if (!isResizingRef.current) return;
      const host = splitRef.current;
      if (!host) return;
      const rect = host.getBoundingClientRect();
      const next = clampLeftWidth(ev.clientX - rect.left);
      setLeftPaneWidth(next);
    };
    const onUp = () => {
      isResizingRef.current = false;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const ensureEngine = () => {
    const eng = getSharedDrumPlayerEngine();
    engineRef.current = eng;
    return eng;
  };

  const firstSampleUrlForInstrument = (manifest: KitManifestV1, instrumentId: string): string | null => {
    const entry = (manifest.articulations as any)?.[instrumentId];
    if (!entry || typeof entry !== "object") return null;

    const mics = entry.mics || {};
    const preferredMicIds = ["close", "oh", "room"];
    for (const micId of preferredMicIds) {
      const mic = mics[micId];
      const layers = mic?.velocityLayers;
      if (!Array.isArray(layers) || !layers.length) continue;
      const rr = layers[0]?.roundRobin;
      if (Array.isArray(rr) && rr.length && typeof rr[0] === "string") return rr[0];
    }

    const anyMicId = Object.keys(mics)[0];
    if (anyMicId) {
      const layers = mics[anyMicId]?.velocityLayers;
      const rr = Array.isArray(layers) && layers.length ? layers[0]?.roundRobin : null;
      if (Array.isArray(rr) && rr.length && typeof rr[0] === "string") return rr[0];
    }

    return null;
  };

  const loadKitIntoEngine = async (manifest: KitManifestV1) => {
    const engine = ensureEngine();
    await engine.ensureRunning();

    const channelCandidates: Array<{ channelId: DrumPlayerChannelId; candidates: string[] }> = [
      { channelId: "kick", candidates: ["kick", "bd"] },
      { channelId: "snare_top", candidates: ["snare_center", "snare_top", "snare"] },
      { channelId: "hat", candidates: ["hihat_closed", "hihat", "hat"] },
      { channelId: "tom1", candidates: ["tom_high", "tom1", "tom_mid", "tom"] },
      { channelId: "ride", candidates: ["ride_bow", "ride_bell", "ride"] },
      { channelId: "crash", candidates: ["crash_1", "crash_2", "crash_china", "crash"] },
    ];

    const missingChannels: string[] = [];
    const resolved: Array<{ channelId: DrumPlayerChannelId; instrumentId: string; url: string }> = [];
    for (const entry of channelCandidates) {
      let picked: string | null = null;
      let pickedInstrument: string | null = null;
      for (const instrumentId of entry.candidates) {
        const url = firstSampleUrlForInstrument(manifest, instrumentId);
        if (url) {
          picked = url;
          pickedInstrument = instrumentId;
          break;
        }
      }
      if (!picked) {
        missingChannels.push(entry.channelId);
        continue;
      }
      await engine.loadSampleForChannel(entry.channelId, picked);
      if (pickedInstrument) {
        resolved.push({ channelId: entry.channelId, instrumentId: pickedInstrument, url: picked });
      }
    }

    setDefaultKitLoaded(true);

    const urls = resolved.map((r) => r.url);
    const uniqueUrls = new Set(urls);
    const suspiciousSameUrl = resolved.length >= 2 && uniqueUrls.size === 1;

    if (missingChannels.length || suspiciousSameUrl) {
      const summary = resolved
        .map((r) => `${r.channelId}<=${r.instrumentId}`)
        .join(", ");
      const urlHint = uniqueUrls.size === 1 ? ` url=${Array.from(uniqueUrls)[0]}` : "";
      const missingHint = missingChannels.length ? ` missing=${missingChannels.join(", ")}` : "";
      const suspiciousHint = suspiciousSameUrl ? " (warning: all channels resolved to the same URL)" : "";
      setKitErr(`Kit loaded:${missingHint}${urlHint}${suspiciousHint} map=${summary}`);
    } else {
      setKitErr(null);
    }
  };

  const handleSelectKit = async (kitId: string) => {
    const next = String(kitId || "");
    setSelectedKitId(next);
    if (!next) return;

    try {
      setLoadingKitManifest(true);
      setKitErr(null);
      const manifest = await getKitManifest(next);
      await enableAudio();
      await loadKitIntoEngine(manifest);
      setAudioEnabled(true);
    } catch (e: any) {
      setKitErr(e?.message ? String(e.message) : String(e));
    } finally {
      setLoadingKitManifest(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    try {
      ensureEngine();
    } catch {
      // ignore
    }
  }, [isOpen]);

  const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
  const volToGain = (vol0to100: number) => {
    const v = Number.isFinite(vol0to100) ? vol0to100 : 0;
    return Math.max(0, Math.min(1.5, (v / 100) * 1.5));
  };
  const panTo01 = (panNeg50To50: number) => {
    const v = Number.isFinite(panNeg50To50) ? panNeg50To50 : 0;
    return Math.max(-1, Math.min(1, v / 50));
  };

  const applyMixerStateToEngine = async (state: ConsoleMixerState) => {
    const engine = ensureEngine();
    await engine.ensureRunning();

    engine.setMasterGain(volToGain(state.masterVolume));

    const oh = state.stereoChannels.find((c) => c.id === "oh");
    const room = state.stereoChannels.find((c) => c.id === "room");
    if (oh) engine.setBusGain("oh", volToGain(oh.volume));
    if (room) engine.setBusGain("room", volToGain(room.volume));

    for (const c of state.monoChannels) {
      engine.setChannelParams(c.id as DrumPlayerChannelId, {
        gain: volToGain(c.volume),
        pan: panTo01(c.pan),
        mute: !!c.muted,
        solo: !!c.solo,
        sendOh: clamp01((c.sendOH ?? 0) / 100),
        sendRoom: clamp01((c.sendRoom ?? 0) / 100),
      });
    }

    for (const c of state.stereoChannels) {
      if (c.id === "oh" || c.id === "room") continue;
      engine.setChannelParams(c.id as DrumPlayerChannelId, {
        gain: volToGain(c.volume),
        pan: panTo01(c.pan),
        mute: !!c.muted,
        solo: !!c.solo,
        sendOh: clamp01(((c.sendOH ?? 0) as number) / 100),
        sendRoom: clamp01(((c.sendRoom ?? 0) as number) / 100),
      });
    }
  };

  const handleMixerStateChange = (state: ConsoleMixerState) => {
    setMixerState(state);
    if (!engineRef.current) return;
    void applyMixerStateToEngine(state).catch((e: any) => {
      setAudioErr(e?.message ? String(e.message) : String(e));
    });
  };

  const enableAudio = async () => {
    try {
      const engine = ensureEngine();
      await engine.ensureRunning();
      if (mixerState) {
        await applyMixerStateToEngine(mixerState);
      }

      const hasCustomChannelMap = Object.values(channelSampleId).some(
        (v) => typeof v === "number" && Number.isFinite(v) && v > 0,
      );

      const shouldApplyCustomChannelMap = hasCustomChannelMap && !selectedKitId;

      if (shouldApplyCustomChannelMap) {
        const loads: Array<Promise<void>> = [];
        for (const [channelId, sampleId] of Object.entries(channelSampleId)) {
          if (channelId === "oh" || channelId === "room" || channelId === "master") continue;
          if (typeof sampleId !== "number" || !Number.isFinite(sampleId) || sampleId <= 0) continue;
          const url = `/api/drum-samples/${sampleId}/audio`;
          loads.push(engine.loadSampleForChannel(channelId as DrumPlayerChannelId, url));
        }
        if (loads.length) {
          await Promise.all(loads);
        }
      }

      if (!defaultKitLoaded && !shouldApplyCustomChannelMap && !selectedKitId) {
        await loadBuiltInDefaultKit();
      }
      setAudioEnabled(true);
      setAudioErr(null);
    } catch (e: any) {
      setAudioErr(e?.message ? String(e.message) : String(e));
    }
  };

  const stopAll = () => {
    try {
      const engine = ensureEngine();
      engine.stopAll();
    } catch {
      // ignore
    }
  };

  const PAD_DEFS = useMemo(
    () =>
      [
        { id: "kick" as DrumPlayerChannelId, label: "Kick", key: "A" },
        { id: "snare_top" as DrumPlayerChannelId, label: "Snare", key: "S" },
        { id: "hat" as DrumPlayerChannelId, label: "Hat", key: "D" },
        { id: "tom1" as DrumPlayerChannelId, label: "Tom", key: "F" },
        { id: "ride" as DrumPlayerChannelId, label: "Ride", key: "G" },
        { id: "crash" as DrumPlayerChannelId, label: "Crash", key: "H" },
      ],
    [],
  );

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.repeat) return;
      const k = (e.key || "").toUpperCase();
      if (k === " ") {
        e.preventDefault();
        stopAll();
        return;
      }
      const pad = PAD_DEFS.find((p) => p.key === k);
      if (!pad) return;
      e.preventDefault();
      try {
        const engine = ensureEngine();
        void engine.ensureRunning().then(() => {
          const ctx = engine.audioContext;
          const whenSec = ctx ? ctx.currentTime + 0.01 : undefined;
          engine.playChannelOneShot(pad.id, { whenSec });
          setAudioEnabled(true);
        });
      } catch {
        // ignore
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, PAD_DEFS]);

  const getAudioUrlForSample = (sampleId: number) => {
    return `/api/drum-samples/${sampleId}/audio`;
  };

  const handleLoadSample = async (channelId: DrumChannelId, sampleId: number) => {
    if (channelId === "oh" || channelId === "room" || channelId === "master") return;

    try {
      const engine = ensureEngine();
      await engine.ensureRunning();
      await engine.loadSampleForChannel(channelId as DrumPlayerChannelId, getAudioUrlForSample(sampleId));
      setAudioEnabled(true);
      setAudioErr(null);
    } catch (e: any) {
      setAudioErr(e?.message ? String(e.message) : String(e));
    }
  };

  const auditionChannel = async (channelId: DrumChannelId) => {
    if (channelId === "oh" || channelId === "room" || channelId === "master") return;

    try {
      const engine = ensureEngine();
      await engine.ensureRunning();
      const ctx = engine.audioContext;
      const whenSec = ctx ? ctx.currentTime + 0.01 : undefined;
      engine.playChannelOneShot(channelId as DrumPlayerChannelId, { whenSec });
      setAudioEnabled(true);
      setAudioErr(null);
    } catch (e: any) {
      setAudioErr(e?.message ? String(e.message) : String(e));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-lg shadow-2xl max-w-[96vw] w-[1400px] max-h-[92vh] overflow-hidden flex flex-col border border-slate-700">
        <div className="p-4 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
          <div>
            <div className="text-lg font-semibold text-slate-100">Drum Player</div>
            <div className="text-xs text-slate-400">Mixer, samples, OH/Room simulation</div>
          </div>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700" onClick={stopAll}>
              Stop All
            </button>
            <button className="px-3 py-1 rounded bg-slate-700 hover:bg-slate-600" onClick={onClose}>
              Close
            </button>
          </div>
        </div>

        <div ref={splitRef} className="flex-1 overflow-hidden flex min-w-0">
          <div
            className="border-r border-slate-800 overflow-y-auto p-4 space-y-4 shrink-0"
            style={{ width: `${leftPaneWidth}px` }}
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-slate-200">Audio Engine</div>
                <button
                  className={`px-3 py-1 rounded ${audioEnabled ? "bg-emerald-700" : "bg-emerald-600 hover:bg-emerald-500"}`}
                  onClick={enableAudio}
                >
                  {audioEnabled ? "Audio Enabled" : "Enable Audio"}
                </button>
              </div>
              <div className="text-xs text-slate-400">
                WebAudio requires a user gesture to start. Click Enable Audio once.
              </div>
              {audioErr && <div className="text-xs text-rose-300">{audioErr}</div>}
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium text-slate-200">Kit Packs</div>
              <div className="text-xs text-slate-400">Load a local kit manifest from frontend/public/kits (ignored by git).</div>
              <select
                className="w-full bg-slate-800 text-slate-100 rounded px-2 py-2 border border-slate-700"
                value={selectedKitId}
                onChange={(e) => {
                  void handleSelectKit(e.target.value);
                }}
                disabled={loadingKits || loadingKitManifest}
              >
                <option value="">Select kit…</option>
                {kits.map((k) => (
                  <option key={k.kitId} value={k.kitId}>
                    {k.name}
                  </option>
                ))}
              </select>
              {(loadingKits || loadingKitManifest) && (
                <div className="text-xs text-slate-500">{loadingKits ? "Loading kits…" : "Loading kit…"}</div>
              )}
              {kitErr && <div className="text-xs text-rose-300">{kitErr}</div>}
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium text-slate-200">Sample Library</div>
              <div className="text-xs text-slate-400">Choose a collection, then assign samples per channel.</div>

              <div className="space-y-2">
                <label className="text-xs text-slate-400">Collection</label>
                <select
                  className="w-full bg-slate-800 text-slate-100 rounded px-2 py-2 border border-slate-700"
                  value={selectedCollectionId}
                  onChange={(e) => {
                    const v = e.target.value;
                    setSelectedCollectionId(v === "" ? "" : Number(v));
                  }}
                  disabled={loadingCollections}
                >
                  <option value="">Select…</option>
                  {collections.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.collection_name}
                    </option>
                  ))}
                </select>
                {loadingCollections && <div className="text-xs text-slate-500">Loading collections…</div>}
              </div>

              <div className="space-y-2">
                <label className="text-xs text-slate-400">Search</label>
                <input
                  className="w-full bg-slate-800 text-slate-100 rounded px-2 py-2 border border-slate-700"
                  value={sampleQuery}
                  onChange={(e) => setSampleQuery(e.target.value)}
                  placeholder="Filter sample names…"
                />
              </div>

              {loadingSamples && <div className="text-xs text-slate-500">Loading samples…</div>}
              {loadErr && <div className="text-xs text-rose-300">{loadErr}</div>}
            </div>

            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-200">Channel Samples</div>
              <div className="space-y-2">
                {CHANNELS.filter((c) => c.id !== "master" && c.id !== "oh" && c.id !== "room").map((ch) => {
                  const opts = optionsForChannel(ch).filter((s) => {
                    const q = sampleQuery.trim().toLowerCase();
                    if (!q) return true;
                    return sampleDisplayLabel(s).toLowerCase().includes(q);
                  });
                  const selected = channelSampleId[ch.id] ?? "";
                  let displayOpts = opts;
                  if (typeof selected === "number") {
                    const selectedSample = samples.find((s) => s.id === selected);
                    if (selectedSample && !displayOpts.some((s) => s.id === selectedSample.id)) {
                      displayOpts = [selectedSample, ...displayOpts];
                    }
                  }
                  return (
                    <div key={ch.id} className="space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-xs text-slate-400">{ch.label}</div>
                        <button
                          className="px-2 py-1 text-[11px] rounded bg-slate-800 hover:bg-slate-700 border border-slate-700"
                          onClick={() => auditionChannel(ch.id)}
                          disabled={!audioEnabled}
                        >
                          Audition
                        </button>
                      </div>
                      <select
                        className="w-full bg-slate-800 text-slate-100 rounded px-2 py-2 border border-slate-700"
                        value={selected}
                        onChange={(e) => {
                          const v = e.target.value;
                          const next = v === "" ? "" : Number(v);
                          setChannelSampleId((prev) => ({ ...prev, [ch.id]: next }));
                          if (typeof next === "number") {
                            void handleLoadSample(ch.id, next);
                          }
                        }}
                        disabled={selectedCollectionId === "" || loadingSamples}
                      >
                        <option value="">Select sample…</option>
                        {displayOpts.slice(0, 250).map((s) => (
                          <option key={s.id} value={s.id}>
                            {sampleDisplayLabel(s)}
                          </option>
                        ))}
                      </select>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-200">Overheads & Room Simulation</div>

              <div className="space-y-2">
                <label className="text-xs text-slate-400">Overheads mic/config</label>
                <select
                  className="w-full bg-slate-800 text-slate-100 rounded px-2 py-2 border border-slate-700"
                  value={ohMicSim}
                  onChange={(e) => setOhMicSim(e.target.value)}
                >
                  <option value="XY - Small Diaphragm Condenser">XY - Small Diaphragm Condenser</option>
                  <option value="ORTF - Small Diaphragm Condenser">ORTF - Small Diaphragm Condenser</option>
                  <option value="Spaced Pair - Condensers">Spaced Pair - Condensers</option>
                  <option value="Glyn Johns">Glyn Johns</option>
                  <option value="Mono Overhead">Mono Overhead</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-slate-400">Room impulse preset</label>
                <select
                  className="w-full bg-slate-800 text-slate-100 rounded px-2 py-2 border border-slate-700"
                  value={roomSim}
                  onChange={(e) => setRoomSim(e.target.value)}
                >
                  <option value="Tight Dead Room">Tight Dead Room</option>
                  <option value="Small Live Room">Small Live Room</option>
                  <option value="Large Live Room">Large Live Room</option>
                  <option value="Large Hall">Large Hall</option>
                </select>
              </div>

              <div className="text-xs text-slate-500">
                OH/Room sends are shown on the mixer. Audio routing + IR processing will be wired next.
              </div>
            </div>
          </div>

          <div
            className="w-2 shrink-0 cursor-col-resize bg-slate-900 hover:bg-slate-800"
            onMouseDown={beginResize}
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize panels"
          />

          <div className="flex-1 overflow-auto bg-slate-950 min-w-0">
            <div className="p-4">
              <div className="mb-4 rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div>
                    <div className="text-sm font-medium text-slate-200">Default Pads</div>
                    <div className="text-xs text-slate-400">Keys: A S D F G H · Space = Stop</div>
                  </div>
                  <button
                    className={`px-3 py-1.5 rounded border ${
                      defaultKitLoaded ? "bg-slate-800 border-slate-700 text-slate-200" : "bg-emerald-600 hover:bg-emerald-500 border-emerald-700 text-white"
                    }`}
                    onClick={() => {
                      void enableAudio();
                    }}
                    type="button"
                  >
                    {defaultKitLoaded ? "Default Kit Loaded" : "Load Default Kit"}
                  </button>
                </div>

                <div className="mt-3 grid grid-cols-3 gap-2">
                  {PAD_DEFS.map((pad) => (
                    <button
                      key={pad.id}
                      className="rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 px-3 py-4 text-left"
                      onClick={() => {
                        void enableAudio().then(() => {
                          const engine = ensureEngine();
                          const ctx = engine.audioContext;
                          const whenSec = ctx ? ctx.currentTime + 0.01 : undefined;
                          engine.playChannelOneShot(pad.id, { whenSec });
                        });
                      }}
                      type="button"
                    >
                      <div className="text-sm font-semibold text-slate-100">{pad.label}</div>
                      <div className="text-xs text-slate-400">Key: {pad.key}</div>
                    </button>
                  ))}
                </div>
              </div>

              <ConsoleMixer onStateChange={handleMixerStateChange} drumEngine={ensureEngine()} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
