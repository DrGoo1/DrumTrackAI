import type { KitManifestV1, ListKitsResponse } from "../types/kits";
import type { DrumGenerationConfig, DrumGenerationResponse } from "../types/drumTrack";
import { attachSentientProfilesWithOverrides } from "./sentientProfileSession";

export type AnalyzeTempoResponse = { bpm: number; tempoCurve?: Array<{time:number,bpm:number}> };

// Use same-origin (relative URLs) since nginx proxies all API requests
const API_BASE = (import.meta as any).env?.VITE_API_BASE || '';

export function getApiBases(): string[] {
  const envBase = (import.meta as any).env?.VITE_API_BASE as string | undefined;
  if (envBase) return [envBase];
  // Use same origin - nginx will proxy to backend
  return [''];
}

async function fetchWithBases(path: string, init?: RequestInit): Promise<Response> {
  const bases = getApiBases();
  let lastErr: any = null;
  for (const base of bases) {
    try {
      const res = await fetch(`${base}${path}`, init);
      if (res.ok) return res;
      lastErr = new Error(`${res.status} ${res.statusText}`);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error('request failed');
}

export async function ping(): Promise<{ ok: boolean }> {
  try {
    const res = await fetchWithBases(`/healthz`);
    if (!res.ok) return { ok: false };
    await res.json();
    return { ok: true };
  } catch {
    return { ok: false };
  }
}

export async function analyzeTempo(fileKey: string, opts?: { start?: number; end?: number }): Promise<any> {
  const sp = new URLSearchParams();
  sp.set('key', fileKey);
  if (opts?.start != null) sp.set('start', String(opts.start));
  if (opts?.end != null) sp.set('end', String(opts.end));
  const res = await fetchWithBases(`/analyze/tempo?${sp.toString()}`);
  if (!res.ok) throw new Error('Tempo analysis failed');
  return res.json();
}

export async function sectionizeSmart(fileKey: string, bpm: number) {
  const res = await fetchWithBases(`/align/sections?key=${encodeURIComponent(fileKey)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify([]) });
  if (!res.ok) throw new Error('Sectionization failed');
  return res.json();
}

export async function generateMidi64(params: any): Promise<string> {
  const res = await fetchWithBases(`/generate/midi64`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params) });
  if (!res.ok) throw new Error('MIDI generation failed');
  const data = await res.json();
  return data.base64 || data;
}

export async function generateDrums(config: DrumGenerationConfig): Promise<DrumGenerationResponse> {
  const enriched = await attachSentientProfilesWithOverrides(config as any);
  const res = await fetchWithBases(`/api/generate-drums`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(enriched),
  });
  if (!res.ok) throw new Error("Drum generation failed");
  return res.json();
}

export type RenderPluginMidiRequest = {
  plugin: "jamstix" | "sd3" | "ssd5";
  advancedArticulations?: boolean;
  ppq: number;
  notes: Array<{
    t0: number;
    t1: number;
    pitch: number;
    vel: number;
    chan: number;
    articulationId?: string;
  }>;
};

export type RenderPluginMidiResponse = {
  plugin: string;
  midi_base64: string;
  ticks_per_beat: number;
};

export async function renderPluginMidi(payload: RenderPluginMidiRequest): Promise<RenderPluginMidiResponse> {
  const res = await fetchWithBases(`/api/render-plugin-midi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Plugin MIDI render failed");
  return res.json();
}

export type UploadResult = {
  success: boolean;
  key: string; // uploads/... path
  waveform?: { peaks: number[]; peaksL?: number[]; peaksR?: number[]; sr?: number; duration?: number };
};

export async function uploadFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append('file', file, file.name);
  // Backend exposes both /api/upload and /files/upload; use the latter
  const res = await fetchWithBases(`/files/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('Upload failed');
  return res.json();
}

export async function fetchWaveform(key: string, maxPoints = 3000): Promise<{ peaks: number[]; peaksL?: number[]; peaksR?: number[]; sr?: number; duration?: number }>{
  const res = await fetchWithBases(`/files/waveform?key=${encodeURIComponent(key)}&max_points=${maxPoints}`);
  if (!res.ok) throw new Error('Waveform fetch failed');
  return res.json();
}

export type AlignSectionsResponse = { tempo?: number; sections: Array<{ start: number; end: number }> };

export async function alignSections(fileKey: string, sections: Array<{ start: number; end: number }>): Promise<AlignSectionsResponse> {
  const res = await fetchWithBases(`/align/sections?key=${encodeURIComponent(fileKey)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sections),
  });
  if (!res.ok) throw new Error('Align sections failed');
  return res.json();
}

export type TempoSectionResult = { start: number; end: number; tempo: number | null; candidates: number[]; confidence: number };

export async function analyzeTempoSections(fileKey: string, sections: Array<{ start: number; end: number }>): Promise<{ results: TempoSectionResult[] }>{
  const res = await fetchWithBases(`/analyze/tempo_sections`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key: fileKey, sections })
  });
  if (!res.ok) throw new Error('Tempo sections analysis failed');
  return res.json();
}

export async function listKits(): Promise<ListKitsResponse> {
  const res = await fetchWithBases(`/api/kits`);
  if (!res.ok) throw new Error('List kits failed');
  return res.json();
}

export async function getKitManifest(kitId: string): Promise<KitManifestV1> {
  const safe = encodeURIComponent(String(kitId || "").trim());
  const res = await fetchWithBases(`/api/kits/${safe}/manifest`);
  if (!res.ok) throw new Error('Get kit manifest failed');
  return res.json();
}

export async function generateMidiSections(
  fileKey: string,
  sections: Array<{ start: number; end: number }>,
  options?: {
    swing?: number;
    velocity?: 'flat' | 'accent24';
    ride?: boolean;
    crash?: boolean;
    fill?: 'none' | 'random' | 'tomrun' | 'snarebuzz' | 'edmriser';
    fillBars?: number;
    velocityLanes?: {
      kick?: 'flat' | 'punchy';
      snare?: 'flat' | 'accent24' | 'ghost';
      hihat?: 'flat' | 'accent24';
      ride?: 'flat' | 'washy';
    };
  }
): Promise<{ filename: string; base64: string }>{
  const res = await fetchWithBases(`/generate/midi_sections`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key: fileKey, sections, options: options || {} })
  });
  if (!res.ok) throw new Error('MIDI sections generation failed');
  return res.json();
}
