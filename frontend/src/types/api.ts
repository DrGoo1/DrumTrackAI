// API Types for DrumTracKAI WebDAW Song-Aware Drum Composer

export interface UploadResponse {
  ok: boolean;
  key: string;
  size: number;
  sha1: string;
  tier: string;
}

export interface WaveformData {
  sr: number;
  peaks: number[];
  samples: number;
  duration: number;
}

export interface FileInfo {
  key: string;
  sha1: string;
  size: number;
  exists: boolean;
}

// SMAP (Song Map) Types
export interface TempoChange {
  t_sec: number;
  bpm: number;
  timesig: [number, number];
}

export interface SongSection {
  id: string;
  label: string;
  start_sec: number;
  end_sec: number;
  energy: number;
  repetition_id: string;
}

export interface GridConfig {
  ppq: number;
  swing: number;
}

export interface SMAP {
  sha1: string;
  tempo_map: TempoChange[];
  downbeats: number[];
  sections: SongSection[];
  grid: GridConfig;
  warp_map: [number, number][];
  sophistication?: number;
  energy_curve?: {
    times: number[];
    values: number[];
  };
  advanced_features?: {
    harmonic_percussive_ratio: number;
    spectral_centroid_mean: number;
    rhythmic_complexity: number;
    tonal_stability: number;
  };
}

// DGraph (Drum Graph) Types
export interface PatternGrid {
  ppq: number;
  bars: number;
  kick: number[];
  snare: number[];
  hh_closed: number[];
  hh_open: number[];
  ride: number[];
  tom_hi: number[];
  tom_mid: number[];
  tom_low: number[];
  crash: number[];
  vel?: {
    [kitPiece: string]: number[];
  };
  [kitPiece: string]: number[] | number | { [key: string]: number[] } | undefined;
}

export interface DrumFill {
  at_bar: number;
  length_bars: number;
  type: string;
}

export interface DrumSection {
  section_id: string;
  style: string;
  density: number;
  swing: number;
  ghosts: number;
  relation: string;
  pattern: PatternGrid;
  fills: DrumFill[];
  humanize?: number;
  humanize_per_lane?: Record<string, number>;
  quantize?: {
    grid: string;
    strength: number;
  };
  lane_settings?: Record<string, any>;
}

export interface DGraph {
  sha1: string;
  kit: string;
  sections: DrumSection[];
  transitions: any[];
}

// Analysis Types
export interface AnalysisConfig {
  user_tier: string;
  sophistication_level: number;
  available_profiles: DrummerProfile[];
  tier_limits: {
    monthly_uploads: number;
    max_file_size_mb: number;
  };
}

export interface DrummerProfile {
  id: string;
  name: string;
  style_tags: string[];
  signature_patterns: Record<string, any>;
  sophistication_score: number;
}

export interface AnalysisJob {
  job_id: string;
  config: AnalysisConfig;
}

export interface JobStatus {
  state: 'queued' | 'running' | 'completed' | 'failed';
  sha1: string;
  admin_job_id?: string;
  user_tier: string;
  sophistication_level: number;
  fallback?: boolean;
  error?: string;
  smap_key?: string;
}

// Request Types
export interface EnqueueAnalysisRequest {
  sha1: string;
  audio_key: string;
  user_id?: string;
  drummer_profile_id?: string;
}

export interface ComposeRequest {
  sha1: string;
  style: string;
  complexity: number;
  user_id?: string;
}

export interface UpdateSectionRequest {
  sha1: string;
  section_id: string;
  pattern: PatternGrid;
}

export interface MidiResponse {
  url: string;
}

// User Management Types
export interface UserTier {
  tier: 'basic' | 'professional' | 'expert';
  monthly_uploads: number;
  max_file_size_mb: number;
  sophistication_level: number;
}

export interface UploadLimitCheck {
  allowed: boolean;
  reason?: string;
  tier?: string;
}

// Error Types
export interface APIError {
  detail: string;
  status_code: number;
}

// WebDAW UI State Types
export interface TimelineState {
  zoom: number;
  scroll_position: number;
  playhead_position: number;
  selection_start?: number;
  selection_end?: number;
}

export interface MixerChannel {
  id: string;
  name: string;
  volume: number;
  pan: number;
  mute: boolean;
  solo: boolean;
  kit_piece: keyof PatternGrid;
}

export interface PianoRollState {
  active_section: string;
  grid_resolution: number; // 16, 32, 64, 128
  velocity_editing: boolean;
  selected_notes: number[];
}

export interface WebDAWProject {
  sha1: string;
  audio_key: string;
  name: string;
  tempo: number;
  smap?: SMAP;
  dgraph?: DGraph;
  timeline_state: TimelineState;
  mixer_channels: MixerChannel[];
  piano_roll_state: PianoRollState;
}

// Kit Piece Mapping
export const KIT_PIECES = [
  'kick',
  'snare', 
  'hh_closed',
  'hh_open',
  'ride',
  'tom_hi',
  'tom_mid', 
  'tom_low',
  'crash'
] as const;

export type KitPiece = typeof KIT_PIECES[number];

// Grid Resolution Options
export const GRID_RESOLUTIONS = [16, 32, 64, 128] as const;
export type GridResolution = typeof GRID_RESOLUTIONS[number];

// PPQ Options for high-resolution editing
export const PPQ_OPTIONS = [480, 960] as const;
export type PPQOption = typeof PPQ_OPTIONS[number];
