import type { DrumBrainConfig } from "./brain";

/**
 * DrumTrack Types - Drum Builder v2.0
 * ===================================
 * TypeScript types for high-resolution drum track format
 */

// ============================================================================
// Drum Instrument IDs
// ============================================================================

export type DrumInstrumentId =
  | 'kick'
  | 'snare_center'
  | 'snare_rim'
  | 'snare_ghost'
  | 'hihat_closed'
  | 'hihat_open'
  | 'hihat_pedal'
  | 'ride_bow'
  | 'ride_bell'
  | 'ride_edge'
  | 'tom_high'
  | 'tom_mid'
  | 'tom_floor'
  | 'crash_1'
  | 'crash_2'
  | 'other';

// ============================================================================
// Performance Types
// ============================================================================

export type GlobalFeel = 'straight' | 'swing' | 'shuffle' | 'laid_back' | 'pushed';
export type QuantizationBase = '16th' | '8th' | 'triplet_8th' | 'triplet_16th';
export type PhraseShape = 'flat' | 'swell' | 'decay' | 'wave';

// Limb-aware attribute types
export type LimbId = 'LH' | 'RH' | 'LF' | 'RF' | 'LS' | 'RS' | 'other';
export type HitStyle = 'single' | 'double' | 'bounce';
export type NoteAspect = 'groove' | 'accent' | 'fill';

// ============================================================================
// Drum Note Event
// ============================================================================

export interface DrumNoteEvent {
  // Core identification
  id: string;
  
  // Timing (high-resolution)
  barIndex: number;
  tickInBar: number;
  tickLength: number;
  
  // MIDI attributes
  channel: number;
  midiPitch: number;
  velocity: number;
  
  // Drum-specific identification
  instrumentId: DrumInstrumentId;
  
  // Optional aspect classification
  aspect?: NoteAspect;
  
  // Limb-aware attributes
  limbId?: LimbId;  // Which limb plays this note
  priority?: number;  // 0..1 (importance in limb conflicts)
  timingOffsetMs?: number;  // Per-note timing offset (±50ms)
  hatOpenLevel?: number;  // 0..1 (for hi-hat open amount)
  hitStyle?: HitStyle;  // Single/double/bounce
  locked?: boolean;  // If true, note cannot be overwritten
  
  // Performance flags
  isGhost: boolean;
  isAccent: boolean;
  isFlam: boolean;
  isDrag: boolean;
  
  // Performance grouping
  performanceGroupId?: string;
  microTimingMs?: number;  // From LLM performance spec

  // Rudiment metadata
  phraseMarker?: string;
  rudimentId?: string;
}

// ============================================================================
// Performance Specification
// ============================================================================

export interface MicroTimingProfile {
  subdivisionOffsetsMs: number[];  // Per-subdivision offsets
  offsetRangeMs: [number, number]; // Min/max variation
}

export interface VelocityProfile {
  base: number;  // Base velocity (1-127)
  accentBoost: number;  // Accent increase
  ghostReduction: number;  // Ghost reduction
  phraseShape: PhraseShape;  // Dynamic contour
  shapeDepth: number;  // Shape intensity
}

export interface ArticulationProfile {
  flamProbability: number;  // 0.0-1.0
  dragProbability: number;  // 0.0-1.0
  ghostDensity: number;  // 0.0-1.0
}

export interface InstrumentPerformanceProfile {
  instrumentId: DrumInstrumentId;
  microTiming: MicroTimingProfile;
  velocityProfile: VelocityProfile;
  articulation: ArticulationProfile;
}

export interface DrumPhrasePerformance {
  phraseId: string;
  startBar: number;
  endBar: number;
  profiles: InstrumentPerformanceProfile[];
}

export interface DrumPerformanceSpec {
  styleId: string;
  globalFeel: GlobalFeel;
  quantizationBase: QuantizationBase;
  phrases: DrumPhrasePerformance[];
}

// ============================================================================
// Complete Drum Track
// ============================================================================

export interface DrumTrackForDCSM {
  track_id: string;
  style_id: string;
  resolution_ppq: number;  // Ticks per quarter note (usually 960)
  notes: DrumNoteEvent[];
  performance_spec: DrumPerformanceSpec;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface DrumGenerationResponse {
  ok: boolean;
  drum_track?: DrumTrackForDCSM;  // New high-res format
  midi_notes?: LegacyMidiNote[];  // Legacy format
  midi_base64?: string;
  metadata: DrumGenerationMetadata;
  error?: string;
}

export interface LegacyMidiNote {
  time: number;
  note: number;
  velocity: number;
  drum: string;
  length?: number;
}

export interface DrumGenerationMetadata {
  builder_version: 'v2.0' | 'v1.1_legacy';
  generation_time_ms: number;
  drummer_used: string;
  style: string;
  mode: string;
  humanized: boolean;
  humanize_amount?: number;
  ghost_notes?: number;
  swing?: number;
  measure_count: number;
  tempo_range?: string;
  resolution_ppq?: number;
  performance_from_llm?: boolean;
}

// ============================================================================
// Generation Config (Extended for v2.0)
// ============================================================================

export type FillFrequency = 'none' | 'every_4_bars' | 'section_transitions' | 'all_transitions';

export interface SongSectionConfig {
  name: string;
  bars: number;
}

export interface FillControls {
  fillType: string;
  density: number;
  frequency: FillFrequency;
}

export type RudimentHandLead = 'auto' | 'left' | 'right';

export interface RudimentControls {
  enabled: boolean;
  preferredFamilies: string[];
  preferredRudiments: string[];
  density: number;
  ensureDownbeatKick: boolean;
  preserveHatTail: boolean;
  handLead: RudimentHandLead;
}

export interface RudimentBlock {
  blockId: string;
  startBar: number;
  lengthBars: number;
  families?: string[];
  rudimentId?: string;
  density?: number;
  ensureDownbeatKick?: boolean;
  preserveHatTail?: boolean;
}

export interface DrumGenerationConfig {
  // Required fields
  sectionId: string;
  startMeasure: number;
  endMeasure: number;
  tempos: number[];
  timeSignature: [number, number];
  style: string;
  drummer: string;
  intensity: number;  // 0.0-1.0
  variation: number;  // 0.0-1.0
  generationMode: 'template' | 'ai_variation' | 'full_ai';
  humanize: boolean;
  fillLocations: number[];
  fillType: string;
  fillDensity?: number;

  // Optional output controls
  midiMapName?: string;

  // Optional groove library controls
  grooveSource?: string;
  styleGroup?: string;
  grooveControls?: Record<string, any>;
  
  // New v2.0 fields
  humanizeAmount?: number;  // 0.0-1.0 (default: 0.7)
  ghostNoteAmount?: number;  // 0.0-1.0 (default: 0.7)
  swingAmount?: number;  // 0.0-1.0 (default: 0.0)
  buildScope?: 'full_song' | 'selected_section';
  guideEnabled?: boolean;
  guideInstrument?: 'mix' | 'bass' | 'guitar' | 'keys' | 'vocal' | 'other';
  brainConfig?: DrumBrainConfig;
  songStyle?: 'pop' | 'rock' | 'blues' | 'jazz' | 'metal' | 'funk' | 'shoegaze' | 'edm' | 'dance';
  songSections?: SongSectionConfig[];
  fillControls?: FillControls;
  rudimentControls?: RudimentControls;
  rudimentBlocks?: RudimentBlock[];
}

// ============================================================================
// Section Lock State
// ============================================================================

export interface SectionLockState {
  sectionId: string;
  locked: boolean;
  trackData?: DrumTrackForDCSM;
  lockedAt?: Date;
}

// ============================================================================
// UI State Types
// ============================================================================

export interface DrumTrackUIState {
  currentTrack?: DrumTrackForDCSM;
  sectionLocks: Map<string, SectionLockState>;
  selectedNotes: Set<string>;  // Note IDs
  viewportStartTick: number;
  viewportEndTick: number;
  zoom: number;
  playheadTick: number;
}

// ============================================================================
// Utility Types
// ============================================================================

export interface NoteRenderInfo {
  note: DrumNoteEvent;
  x: number;  // Screen position
  y: number;
  width: number;
  color: string;
  alpha: number;
}

export interface InstrumentLane {
  instrumentId: DrumInstrumentId;
  label: string;
  midiPitch: number;
  color: string;
  y: number;  // Lane Y position
  height: number;
}

// ============================================================================
// Conversion Utilities Types
// ============================================================================

export interface TimeConversion {
  bars: number;
  beats: number;
  ticks: number;
  seconds: number;
}

// ============================================================================
// MIDI Mapping
// ============================================================================

export const DRUM_INSTRUMENT_MIDI_MAP: Record<DrumInstrumentId, number> = {
  kick: 36,
  snare_center: 38,
  snare_rim: 37,
  snare_ghost: 38,  // Same as center, distinguished by velocity
  hihat_closed: 42,
  hihat_open: 46,
  hihat_pedal: 44,
  ride_bow: 51,
  ride_bell: 53,
  ride_edge: 59,
  tom_high: 50,
  tom_mid: 47,
  tom_floor: 43,
  crash_1: 49,
  crash_2: 57,
  other: 39
};

// ============================================================================
// Color Mapping for Visualization
// ============================================================================

export const DRUM_INSTRUMENT_COLORS: Record<DrumInstrumentId, string> = {
  kick: '#FF6B6B',
  snare_center: '#4ECDC4',
  snare_rim: '#45B7D1',
  snare_ghost: '#95E1D3',
  hihat_closed: '#FFA07A',
  hihat_open: '#FFD93D',
  hihat_pedal: '#FCB42C',
  ride_bow: '#A8E6CF',
  ride_bell: '#7FD1B9',
  ride_edge: '#61C0BF',
  tom_high: '#C084FC',
  tom_mid: '#A855F7',
  tom_floor: '#9333EA',
  crash_1: '#F472B6',
  crash_2: '#EC4899',
  other: '#94A3B8'
};

// Export module
export {};
