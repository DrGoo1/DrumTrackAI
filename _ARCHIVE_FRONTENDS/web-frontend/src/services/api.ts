/*
 * DrumTracKAI API client – safe defaults + fallbacks
 * Fixes: default export vs named export confusion; adds fullWorkflow & uploadAndAnalyze
 */

const fallbackOrigin = (() => {
  if (typeof window === "undefined" || !window.location?.origin) return "http://127.0.0.1:8000";

  // In local dev, the React dev server origin is NOT the backend API.
  // Default to the python backend on :8000 unless explicitly overridden.
  const origin = window.location.origin;
  const isLocalDev = /localhost:(3000|3001|5173)$/i.test(origin) || /127\.0\.0\.1:(3000|3001|5173)$/i.test(origin);
  return isLocalDev ? "http://127.0.0.1:8000" : origin;
})();

const resolvedApiBase =
  process.env.REACT_APP_API_BASE || process.env.REACT_APP_API_URL || fallbackOrigin;

const API_BASE = (
  (window as any).__API_BASE = resolvedApiBase
).replace(/\/$/, "");

// small fetch helper with timeout
async function fetchJSON<T>(input: RequestInfo, init: RequestInit = {}, timeoutMs = 20000): Promise<T> {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(input, { ...init, signal: ctrl.signal });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${res.statusText} – ${txt}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(id);
  }
}

function timeout(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function health(): Promise<boolean> {
  try {
    await fetchJSON(`${API_BASE}/healthz`, { method: "GET" }, 5000);
    return true;
  } catch {
    return false;
  }
}

// --- Upload paths -----------------------------------------------------------

async function uploadDirect(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  return fetchJSON<{ success: boolean; file_id: string; message: string }>(`${API_BASE}/api/upload`, { method: "POST", body: fd }, 60000);
}

async function analyzeAudio(fileId: string) {
  return fetchJSON<{ success: boolean; job_id: string; status: string; estimated_time: string }>(`${API_BASE}/api/analyze`, { 
    method: "POST", 
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_id: fileId })
  }, 60000);
}

async function getResults(jobId: string) {
  return fetchJSON<{ job_id: string; sophistication: string; accuracy: string; tempo: string; patterns: string[]; confidence: string; drummer_style: string }>(`${API_BASE}/api/results/${jobId}`, { method: "GET" }, 30000);
}

export type BeatboxTranslateOptions = {
  swing?: number;
  quantization?: string;
  confidence_threshold?: number;
  plugin?: string;
};

export type BeatboxTranslateResponse = {
  success: boolean;
  job_id: string;
  tempo: number;
  hits: Array<{ instrument: string; beat_position: number; time: number; velocity: number; confidence: number }>;
  summary: Record<string, number>;
  preview_midi: string | null;
  plugin?: string;
  ticks_per_beat?: number;
  persona_id?: string;
  style_pack?: string;
};

export type BeatPadHit = {
  instrument: string;
  beat_position: number;
  time: number;
  velocity: number;
  confidence?: number;
};

export type BeatPromptSectionPayload = {
  label: string;
  bars: number;
  tempo: number;
  meter?: string;
  persona_id?: string;
  style_pack?: string;
  pattern_template?: string;
  modifiers?: string[];
};

export type BeatPromptPayload = {
  prompt: string;
  sections: BeatPromptSectionPayload[];
};

async function translateBeatbox(
  fileId: string,
  params: { persona_id?: string; style_pack?: string; options?: BeatboxTranslateOptions } = {}
) {
  return fetchJSON<BeatboxTranslateResponse>(
    `${API_BASE}/api/beatbox/translate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id: fileId, ...params }),
    },
    60000,
  );
}

async function translateTapPattern(payload: {
  hits: BeatPadHit[];
  tempo: number;
  persona_id?: string;
  style_pack?: string;
  plugin?: string;
  options?: BeatboxTranslateOptions;
}) {
  return fetchJSON<BeatboxTranslateResponse>(
    `${API_BASE}/api/beatbox/tap-input`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    60000,
  );
}

async function renderBeatPrompt(payload: BeatPromptPayload) {
  return fetchJSON<BeatboxTranslateResponse & { sections?: BeatPromptSectionPayload[] }>(
    `${API_BASE}/api/beatprompt/render`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    60000,
  );
}

// Full workflow using the v1.1.7 backend API
async function fullWorkflow(file: File) {
  // Upload file
  const uploadResult = await uploadDirect(file);
  
  if (!uploadResult.success) {
    throw new Error(uploadResult.message || 'Upload failed');
  }

  // Start analysis
  const analysisResult = await analyzeAudio(uploadResult.file_id);
  
  if (!analysisResult.success) {
    throw new Error('Analysis failed to start');
  }

  // Get results (in real backend, you'd poll for completion)
  const results = await getResults(analysisResult.job_id);

  // Try to fetch waveform peaks from legacy files API; fall back to empty peaks
  let waveform: { sr: number; peaks: number[]; key: string; duration?: number } = {
    sr: 44100,
    peaks: [],
    key: uploadResult.file_id,
  };

  try {
    const wfUrl = new URL(`/files/waveform`, API_BASE);
    wfUrl.searchParams.set('key', uploadResult.file_id);
    const wfResp = await fetchJSON<{ sr:number; peaks:number[]; duration?:number }>(wfUrl.toString());
    waveform = { sr: wfResp.sr, peaks: wfResp.peaks || [], key: uploadResult.file_id, duration: wfResp.duration };
  } catch {
    // safe fallback: keep empty peaks
  }

  return { 
    key: uploadResult.file_id, 
    waveform,
    analysis: results
  };
}

// alias kept for compatibility
async function uploadAndAnalyze(file: File) {
  return fullWorkflow(file);
}

export const webdawApi = {
  API_BASE,
  health,
  uploadDirect,
  analyzeAudio,
  getResults,
  fullWorkflow,
  uploadAndAnalyze,
  translateBeatbox,
  translateTapPattern,
  renderBeatPrompt,
};

// Export both named *and* default to avoid webpack import shape issues
export type WebDAWAPIType = typeof webdawApi;
export { webdawApi as WebDAWAPI };
export { translateBeatbox };
export { translateTapPattern };
export { renderBeatPrompt };
export async function analyzeOnsets(key: string){
  const url = new URL(`/analyze/onsets`, API_BASE);
  url.searchParams.set('key', key);
  return await fetchJSON<{ sr:number; onsets:number[] }>(url.toString());
}
export async function analyzeTempo(key: string){
  const url = new URL(`/analyze/tempo`, API_BASE);
  url.searchParams.set('key', key);
  return await fetchJSON<{ tempo:number; beats:number[] }>(url.toString());
}
export async function alignSections(key: string, sections: {start:number; end:number}[]){
  const url = new URL(`/align/sections`, API_BASE);
  url.searchParams.set('key', key);
  return await fetchJSON<{ tempo:number; sections:{start:number; end:number}[] }>(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sections)
  });
}
export async function saveSession(sid:string, payload:any){
  return await fetchJSON<{ok: boolean}>(`${API_BASE}/session/${sid}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}
export async function loadSession(sid:string){
  return await fetchJSON(`${API_BASE}/session/${sid}`);
}

// Benchmarking endpoints
export async function benchPeaks(key:string, impl: "both"|"python"|"rust" = "both"){
  const url = `${API_BASE}/bench/peaks?key=${encodeURIComponent(key)}&impl=${impl}`;
  return await fetchJSON<{ python_ms?:number; rust_ms?:number; python_error?:string; rust_error?:string }>(url);
}

export async function benchAnalysis(key:string, impl: "both"|"python"|"rust" = "both"){
  const url = `${API_BASE}/bench/analysis?key=${encodeURIComponent(key)}&impl=${impl}`;
  return await fetchJSON<{ python_ms?:number; rust_ms?:number; python_error?:string; rust_error?:string }>(url);
}

export async function benchGenerate(bpm:number, bars:number = 8, style:string = "rock"){
  const url = `${API_BASE}/bench/generate?bpm=${bpm}&bars=${bars}&style=${encodeURIComponent(style)}`;
  return await fetchJSON<{ rust_ms:number; notes:number; rust_error?:string }>(url);
}

// DCSM & Drum generation endpoints
export async function sectionizeAudio(key: string, minSectionSec: number = 2.0) {
  const url = `${API_BASE}/dcsm/sectionize?key=${encodeURIComponent(key)}&min_section_sec=${minSectionSec}`;
  return await fetchJSON<{ sections: Array<{start: number; end: number; energy: number; confidence: number}> }>(url);
}

export async function dcsmSectionizeSmart(key:string, bpm:number, minBars=4, maxBars=16){
  const url = `${API_BASE}/dcsm/sectionize?key=${encodeURIComponent(key)}&bpm=${bpm}&mode=smart&min_bars=${minBars}&max_bars=${maxBars}`;
  return await fetchJSON<{ sections: Array<{start:number; end:number; label:string}> }>(url);
}

export async function dcsmGenerate(bpm:number, section:{start:number; end:number; density:number; swing:number; humanize:number; style:string}){
  return await fetchJSON<{ notes: Array<{time:number; lane:string; vel:number; articulationId?: string}>; midi_b64:string }>(
    `${API_BASE}/dcsm/generate`, 
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bpm, section })
    }
  );
}

// Drummer personas (brain visualization)
export async function fetchDrummerPersonas(){
  return await fetchJSON<{
    personas: Array<{
      persona_id: string;
      display_name: string;
      archetypes: string[];
      style: Record<string, any>;
    }>;
    error?: string;
  }>(
    `${API_BASE}/api/drummer-personas`,
    { method: 'GET' },
    20000,
  );
}

export async function generateDrumPattern(payload: {
  bpm: number;
  density: number;
  swing: number;
  humanize: number;
  seed: number;
  sections: Array<{start: number; end: number; fill_in: boolean; fill_out: boolean; density: number}>;
}) {
  return await fetchJSON<{ notes: Array<{time: number; lane: string; vel: number; articulationId?: string}>; midi_base64: string }>(
    `${API_BASE}/dcsm/generate`, 
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }
  );
}

export async function dcsmExportMidi(payload: {
  plugin: string;
  ppq: number;
  notes: Array<{ t0: number; t1: number; pitch: number; vel: number; chan: number; articulationId?: string }>;
}) {
  return await fetchJSON<{
    plugin: string;
    midi_base64: string;
    ticks_per_beat: number;
    filename: string;
    error?: string;
  }>(
    `${API_BASE}/dcsm/export_midi`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  );
}

// Drum Builder v2.0 generate-drums endpoint (including Euclidean mode)
import type { DrumGenerationConfigDTO } from "../types/drumGenerationConfig";

export async function generateDrums(cfg: DrumGenerationConfigDTO) {
  return await fetchJSON<{
    ok: boolean;
    drum_track: any;
    midi_notes: any[];
    midi_base64: string;
    metadata: any;
  }>(
    `${API_BASE}/api/generate-drums`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    },
    60000,
  );
}

export default webdawApi;
