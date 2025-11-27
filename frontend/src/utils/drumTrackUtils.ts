/**
 * Drum Track Utilities - Drum Builder v2.0
 * ========================================
 * Utility functions for working with high-resolution drum tracks
 */

import {
  DrumTrackForDCSM,
  DrumNoteEvent,
  DrumInstrumentId,
  TimeConversion,
  DRUM_INSTRUMENT_MIDI_MAP
} from '../types/drumTrack';

// ============================================================================
// Time Conversion
// ============================================================================

export function ticksToSeconds(
  ticks: number,
  bpm: number,
  resolution: number = 960
): number {
  const quarterNoteDuration = 60.0 / bpm;
  return (ticks / resolution) * quarterNoteDuration;
}

export function secondsToTicks(
  seconds: number,
  bpm: number,
  resolution: number = 960
): number {
  const quarterNoteDuration = 60.0 / bpm;
  return (seconds / quarterNoteDuration) * resolution;
}

export function ticksToBarsBeatsTicks(
  ticks: number,
  timeSignature: [number, number],
  resolution: number = 960
): TimeConversion {
  const ticksPerBeat = resolution;
  const ticksPerBar = ticksPerBeat * timeSignature[0];
  
  const bars = Math.floor(ticks / ticksPerBar);
  const remainingTicks = ticks % ticksPerBar;
  const beats = Math.floor(remainingTicks / ticksPerBeat);
  const ticksInBeat = remainingTicks % ticksPerBeat;
  
  return {
    bars,
    beats,
    ticks: ticksInBeat,
    seconds: 0  // Computed separately if needed
  };
}

export function barsBeatsTicksToTicks(
  bars: number,
  beats: number,
  ticks: number,
  timeSignature: [number, number],
  resolution: number = 960
): number {
  const ticksPerBeat = resolution;
  const ticksPerBar = ticksPerBeat * timeSignature[0];
  
  return bars * ticksPerBar + beats * ticksPerBeat + ticks;
}

// ============================================================================
// Track Analysis
// ============================================================================

export function getTrackBounds(track: DrumTrackForDCSM): {
  startTick: number;
  endTick: number;
  duration: number;
} {
  if (track.notes.length === 0) {
    return { startTick: 0, endTick: 0, duration: 0 };
  }
  
  let minTick = Infinity;
  let maxTick = -Infinity;
  
  for (const note of track.notes) {
    const noteTick = note.barIndex * track.resolution_ppq * 4 + note.tickInBar;
    minTick = Math.min(minTick, noteTick);
    maxTick = Math.max(maxTick, noteTick + note.tickLength);
  }
  
  return {
    startTick: minTick,
    endTick: maxTick,
    duration: maxTick - minTick
  };
}

export function getNotesInRange(
  track: DrumTrackForDCSM,
  startTick: number,
  endTick: number
): DrumNoteEvent[] {
  return track.notes.filter(note => {
    const noteTick = note.barIndex * track.resolution_ppq * 4 + note.tickInBar;
    return noteTick >= startTick && noteTick < endTick;
  });
}

export function getNotesForInstrument(
  track: DrumTrackForDCSM,
  instrumentId: DrumInstrumentId
): DrumNoteEvent[] {
  return track.notes.filter(note => note.instrumentId === instrumentId);
}

// ============================================================================
// Note Manipulation
// ============================================================================

export function quantizeNote(
  note: DrumNoteEvent,
  grid: number,
  resolution: number = 960
): DrumNoteEvent {
  const noteTick = note.barIndex * resolution * 4 + note.tickInBar;
  const quantizedTick = Math.round(noteTick / grid) * grid;
  
  const newBarIndex = Math.floor(quantizedTick / (resolution * 4));
  const newTickInBar = quantizedTick % (resolution * 4);
  
  return {
    ...note,
    barIndex: newBarIndex,
    tickInBar: newTickInBar,
    microTimingMs: 0  // Reset micro-timing on quantize
  };
}

export function transposeNote(
  note: DrumNoteEvent,
  semitones: number
): DrumNoteEvent {
  return {
    ...note,
    midiPitch: Math.max(0, Math.min(127, note.midiPitch + semitones))
  };
}

export function adjustVelocity(
  note: DrumNoteEvent,
  delta: number
): DrumNoteEvent {
  return {
    ...note,
    velocity: Math.max(1, Math.min(127, note.velocity + delta))
  };
}

// ============================================================================
// Track Merging
// ============================================================================

export function mergeTracks(
  tracks: DrumTrackForDCSM[],
  resolution: number = 960
): DrumTrackForDCSM {
  if (tracks.length === 0) {
    throw new Error('Cannot merge empty track list');
  }
  
  const allNotes: DrumNoteEvent[] = [];
  
  for (const track of tracks) {
    allNotes.push(...track.notes);
  }
  
  // Sort by time
  allNotes.sort((a, b) => {
    const aTick = a.barIndex * resolution * 4 + a.tickInBar;
    const bTick = b.barIndex * resolution * 4 + b.tickInBar;
    return aTick - bTick;
  });
  
  return {
    track_id: `merged_${Date.now()}`,
    style_id: tracks[0].style_id,
    resolution_ppq: resolution,
    notes: allNotes,
    performance_spec: tracks[0].performance_spec  // Use first track's spec
  };
}

// ============================================================================
// Track Splitting
// ============================================================================

export function splitTrackByBar(
  track: DrumTrackForDCSM,
  barIndex: number
): [DrumTrackForDCSM, DrumTrackForDCSM] {
  const beforeNotes = track.notes.filter(note => note.barIndex < barIndex);
  const afterNotes = track.notes.filter(note => note.barIndex >= barIndex);
  
  const trackBefore: DrumTrackForDCSM = {
    ...track,
    track_id: `${track.track_id}_before`,
    notes: beforeNotes
  };
  
  const trackAfter: DrumTrackForDCSM = {
    ...track,
    track_id: `${track.track_id}_after`,
    notes: afterNotes.map(note => ({
      ...note,
      barIndex: note.barIndex - barIndex  // Renormalize
    }))
  };
  
  return [trackBefore, trackAfter];
}

// ============================================================================
// Instrument Mapping
// ============================================================================

export function getInstrumentForMidiPitch(pitch: number): DrumInstrumentId {
  for (const [instrumentId, midiPitch] of Object.entries(DRUM_INSTRUMENT_MIDI_MAP)) {
    if (midiPitch === pitch) {
      return instrumentId as DrumInstrumentId;
    }
  }
  return 'other';
}

export function getMidiPitchForInstrument(instrumentId: DrumInstrumentId): number {
  return DRUM_INSTRUMENT_MIDI_MAP[instrumentId] || 39;
}

// ============================================================================
// Statistics
// ============================================================================

export interface TrackStatistics {
  noteCount: number;
  averageVelocity: number;
  velocityRange: [number, number];
  ghostNoteCount: number;
  accentCount: number;
  flamCount: number;
  dragCount: number;
  instrumentCounts: Record<DrumInstrumentId, number>;
  averageMicroTiming: number;
  microTimingRange: [number, number];
}

export function analyzeTrack(track: DrumTrackForDCSM): TrackStatistics {
  const stats: TrackStatistics = {
    noteCount: track.notes.length,
    averageVelocity: 0,
    velocityRange: [127, 0],
    ghostNoteCount: 0,
    accentCount: 0,
    flamCount: 0,
    dragCount: 0,
    instrumentCounts: {} as Record<DrumInstrumentId, number>,
    averageMicroTiming: 0,
    microTimingRange: [0, 0]
  };
  
  if (track.notes.length === 0) return stats;
  
  let totalVelocity = 0;
  let totalMicroTiming = 0;
  let microTimingCount = 0;
  
  for (const note of track.notes) {
    // Velocity
    totalVelocity += note.velocity;
    stats.velocityRange[0] = Math.min(stats.velocityRange[0], note.velocity);
    stats.velocityRange[1] = Math.max(stats.velocityRange[1], note.velocity);
    
    // Articulations
    if (note.isGhost) stats.ghostNoteCount++;
    if (note.isAccent) stats.accentCount++;
    if (note.isFlam) stats.flamCount++;
    if (note.isDrag) stats.dragCount++;
    
    // Instrument counts
    if (!stats.instrumentCounts[note.instrumentId]) {
      stats.instrumentCounts[note.instrumentId] = 0;
    }
    stats.instrumentCounts[note.instrumentId]++;
    
    // Micro-timing
    if (note.microTimingMs !== undefined && note.microTimingMs !== 0) {
      totalMicroTiming += Math.abs(note.microTimingMs);
      microTimingCount++;
      stats.microTimingRange[0] = Math.min(stats.microTimingRange[0], note.microTimingMs);
      stats.microTimingRange[1] = Math.max(stats.microTimingRange[1], note.microTimingMs);
    }
  }
  
  stats.averageVelocity = totalVelocity / track.notes.length;
  stats.averageMicroTiming = microTimingCount > 0 ? totalMicroTiming / microTimingCount : 0;
  
  return stats;
}

// ============================================================================
// Validation
// ============================================================================

export function validateTrack(track: DrumTrackForDCSM): string[] {
  const errors: string[] = [];
  
  if (!track.track_id) {
    errors.push('Missing track_id');
  }
  
  if (track.resolution_ppq <= 0) {
    errors.push('Invalid resolution_ppq');
  }
  
  if (!Array.isArray(track.notes)) {
    errors.push('Notes must be an array');
  }
  
  for (let i = 0; i < track.notes.length; i++) {
    const note = track.notes[i];
    
    if (!note.id) {
      errors.push(`Note ${i}: Missing id`);
    }
    
    if (note.velocity < 1 || note.velocity > 127) {
      errors.push(`Note ${i}: Invalid velocity ${note.velocity}`);
    }
    
    if (note.midiPitch < 0 || note.midiPitch > 127) {
      errors.push(`Note ${i}: Invalid MIDI pitch ${note.midiPitch}`);
    }
    
    if (note.barIndex < 0) {
      errors.push(`Note ${i}: Invalid bar index ${note.barIndex}`);
    }
    
    if (note.tickInBar < 0 || note.tickInBar >= track.resolution_ppq * 4) {
      errors.push(`Note ${i}: Invalid tickInBar ${note.tickInBar}`);
    }
  }
  
  return errors;
}

// ============================================================================
// Export/Import
// ============================================================================

export function serializeTrack(track: DrumTrackForDCSM): string {
  return JSON.stringify(track, null, 2);
}

export function deserializeTrack(json: string): DrumTrackForDCSM {
  const track = JSON.parse(json) as DrumTrackForDCSM;
  const errors = validateTrack(track);
  
  if (errors.length > 0) {
    throw new Error(`Invalid track: ${errors.join(', ')}`);
  }
  
  return track;
}
