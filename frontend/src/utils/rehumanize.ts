/**
 * Re-Humanization Utilities - Drum Builder v2.0 Client-Side
 * ==========================================================
 * Apply real-time humanization adjustments without backend roundtrip
 */

import {
  DrumTrackForDCSM,
  DrumNoteEvent,
  DrumInstrumentId
} from '../types/drumTrack';

// ============================================================================
// Re-Humanization Parameters
// ============================================================================

export interface RehumanizeParams {
  microTimingAmount: number;  // 0.0-1.0 (how much to adjust timing)
  velocityAmount: number;  // 0.0-1.0 (how much to adjust velocity)
  swingAmount: number;  // 0.0-1.0 (swing feel)
  ghostNoteAmount: number;  // 0.0-1.0 (ghost note density)
  tightenLoosen: number;  // -1.0 to +1.0 (tighten or loosen timing)
  seed?: number;  // Random seed for consistency
}

// ============================================================================
// Main Re-Humanization Function
// ============================================================================

export function rehumanizeTrack(
  track: DrumTrackForDCSM,
  params: RehumanizeParams
): DrumTrackForDCSM {
  const rng = createSeededRNG(params.seed ?? 0);
  
  const newNotes = track.notes.map(note => {
    let newNote = { ...note };
    
    // Apply micro-timing adjustments
    if (params.microTimingAmount > 0) {
      newNote = applyMicroTiming(newNote, params, rng);
    }
    
    // Apply velocity adjustments
    if (params.velocityAmount > 0) {
      newNote = applyVelocityVariation(newNote, params, rng);
    }
    
    // Apply swing
    if (params.swingAmount > 0) {
      newNote = applySwing(newNote, params, track.resolution_ppq);
    }
    
    // Apply ghost note density
    if (params.ghostNoteAmount > 0) {
      newNote = applyGhostNoteDensity(newNote, params, rng);
    }
    
    return newNote;
  });
  
  return {
    ...track,
    notes: newNotes
  };
}

// ============================================================================
// Micro-Timing Adjustment
// ============================================================================

function applyMicroTiming(
  note: DrumNoteEvent,
  params: RehumanizeParams,
  rng: () => number
): DrumNoteEvent {
  const baseOffset = note.microTimingMs || 0;
  
  // Calculate max offset based on amount and tighten/loosen
  let maxOffset = params.microTimingAmount * 10.0;  // Up to 10ms at max
  
  // Adjust for tighten/loosen (-1 = tighter, +1 = looser)
  maxOffset *= (1.0 + params.tightenLoosen);
  
  // Generate random offset with instrument-specific characteristics
  const offset = generateInstrumentOffset(note.instrumentId, maxOffset, rng);
  
  // Combine with existing offset (weighted blend)
  const newOffset = baseOffset * 0.3 + offset * 0.7;
  
  return {
    ...note,
    microTimingMs: Math.max(-20, Math.min(20, newOffset))  // Clamp to ±20ms
  };
}

function generateInstrumentOffset(
  instrumentId: DrumInstrumentId,
  maxOffset: number,
  rng: () => number
): number {
  // Different instruments have different timing characteristics
  const instrumentTimingFactors: Partial<Record<DrumInstrumentId, number>> = {
    kick: 1.2,  // Kick tends to rush slightly
    snare_center: 1.0,
    hihat_closed: 0.8,  // Hi-hat is tighter
    hihat_open: 0.9,
    ride_bow: 0.9,
    tom_high: 1.1,
    tom_mid: 1.1,
    tom_floor: 1.1,
    crash_1: 1.3,  // Crashes can be looser
    crash_2: 1.3
  };
  
  const factor = instrumentTimingFactors[instrumentId] || 1.0;
  
  // Gaussian-ish distribution (sum of two random values)
  const r1 = rng();
  const r2 = rng();
  const gaussian = (r1 + r2) / 2;
  
  // Convert to range [-1, 1] with bias toward center
  const normalized = (gaussian - 0.5) * 2;
  
  return normalized * maxOffset * factor;
}

// ============================================================================
// Velocity Variation
// ============================================================================

function applyVelocityVariation(
  note: DrumNoteEvent,
  params: RehumanizeParams,
  rng: () => number
): DrumNoteEvent {
  // Preserve accents and ghosts
  if (note.isAccent || note.isGhost) {
    return note;
  }
  
  const baseVelocity = note.velocity;
  const variation = params.velocityAmount * 15;  // Up to ±15 at max
  
  // Generate variation
  const r = (rng() - 0.5) * 2;  // -1 to 1
  const delta = r * variation;
  
  const newVelocity = Math.round(baseVelocity + delta);
  
  return {
    ...note,
    velocity: Math.max(1, Math.min(127, newVelocity))
  };
}

// ============================================================================
// Swing Application
// ============================================================================

function applySwing(
  note: DrumNoteEvent,
  params: RehumanizeParams,
  resolution: number
): DrumNoteEvent {
  // Swing applies to off-beats (8th notes on the "and")
  const eighthNote = resolution / 2;
  const positionInBeat = note.tickInBar % resolution;
  
  // Check if this is an off-beat (around the halfway point)
  const isOffBeat = positionInBeat >= (eighthNote * 0.9) && 
                    positionInBeat <= (eighthNote * 1.1);
  
  if (!isOffBeat) {
    return note;
  }
  
  // Apply swing by delaying the off-beat
  const swingDelay = params.swingAmount * (eighthNote * 0.3);  // Up to 30% delay
  const swingMs = (swingDelay / resolution) * (60000 / 120);  // Rough conversion
  
  return {
    ...note,
    microTimingMs: (note.microTimingMs || 0) + swingMs
  };
}

// ============================================================================
// Ghost Note Density
// ============================================================================

function applyGhostNoteDensity(
  note: DrumNoteEvent,
  params: RehumanizeParams,
  rng: () => number
): DrumNoteEvent {
  // Only apply to snare and hi-hat
  if (note.instrumentId !== 'snare_center' && 
      note.instrumentId !== 'hihat_closed') {
    return note;
  }
  
  // Don't affect already-marked ghosts or accents
  if (note.isGhost || note.isAccent) {
    return note;
  }
  
  // Probability of becoming a ghost note
  const ghostProbability = params.ghostNoteAmount * 0.3;  // Max 30% chance
  
  if (rng() < ghostProbability) {
    return {
      ...note,
      isGhost: true,
      velocity: Math.max(1, Math.round(note.velocity * 0.4))  // Reduce to 40%
    };
  }
  
  return note;
}

// ============================================================================
// Preset Adjustments
// ============================================================================

export const REHUMANIZE_PRESETS: Record<string, RehumanizeParams> = {
  tight: {
    microTimingAmount: 0.2,
    velocityAmount: 0.3,
    swingAmount: 0.0,
    ghostNoteAmount: 0.2,
    tightenLoosen: -0.5
  },
  natural: {
    microTimingAmount: 0.5,
    velocityAmount: 0.5,
    swingAmount: 0.0,
    ghostNoteAmount: 0.5,
    tightenLoosen: 0.0
  },
  loose: {
    microTimingAmount: 0.8,
    velocityAmount: 0.7,
    swingAmount: 0.0,
    ghostNoteAmount: 0.7,
    tightenLoosen: 0.5
  },
  swing_light: {
    microTimingAmount: 0.5,
    velocityAmount: 0.5,
    swingAmount: 0.3,
    ghostNoteAmount: 0.5,
    tightenLoosen: 0.0
  },
  swing_heavy: {
    microTimingAmount: 0.5,
    velocityAmount: 0.5,
    swingAmount: 0.7,
    ghostNoteAmount: 0.5,
    tightenLoosen: 0.0
  },
  robotic: {
    microTimingAmount: 0.0,
    velocityAmount: 0.0,
    swingAmount: 0.0,
    ghostNoteAmount: 0.0,
    tightenLoosen: -1.0
  }
};

// ============================================================================
// Advanced: Groove Adjustment
// ============================================================================

export interface GrooveAdjustment {
  laidBack: number;  // -1.0 to +1.0 (negative = pushed, positive = laid back)
  pocketDepth: number;  // 0.0-1.0 (how deep in the pocket)
}

export function adjustGroove(
  track: DrumTrackForDCSM,
  groove: GrooveAdjustment
): DrumTrackForDCSM {
  const newNotes = track.notes.map(note => {
    let offset = note.microTimingMs || 0;
    
    // Laid back = consistent positive offset
    // Pushed = consistent negative offset
    const grooveOffset = groove.laidBack * 8.0;  // Up to ±8ms
    
    // Pocket depth adds subtle consistent latency
    const pocketOffset = groove.pocketDepth * 3.0;  // Up to 3ms
    
    return {
      ...note,
      microTimingMs: offset + grooveOffset + pocketOffset
    };
  });
  
  return {
    ...track,
    notes: newNotes
  };
}

// ============================================================================
// Utilities
// ============================================================================

function createSeededRNG(seed: number): () => number {
  // Simple seeded RNG (Mulberry32)
  return function() {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// ============================================================================
// Diff/Restore
// ============================================================================

export interface TrackDiff {
  originalNotes: Map<string, DrumNoteEvent>;
  modifiedNotes: Map<string, DrumNoteEvent>;
}

export function createTrackDiff(
  originalTrack: DrumTrackForDCSM,
  modifiedTrack: DrumTrackForDCSM
): TrackDiff {
  const originalNotes = new Map(
    originalTrack.notes.map(n => [n.id, n])
  );
  const modifiedNotes = new Map(
    modifiedTrack.notes.map(n => [n.id, n])
  );
  
  return {
    originalNotes,
    modifiedNotes
  };
}

export function restoreOriginal(
  track: DrumTrackForDCSM,
  diff: TrackDiff
): DrumTrackForDCSM {
  const restoredNotes = track.notes.map(note => {
    const original = diff.originalNotes.get(note.id);
    return original || note;
  });
  
  return {
    ...track,
    notes: restoredNotes
  };
}

// ============================================================================
// Batch Operations
// ============================================================================

export function rehumanizeSelection(
  track: DrumTrackForDCSM,
  selectedNoteIds: Set<string>,
  params: RehumanizeParams
): DrumTrackForDCSM {
  const rng = createSeededRNG(params.seed ?? 0);
  
  const newNotes = track.notes.map(note => {
    if (!selectedNoteIds.has(note.id)) {
      return note;
    }
    
    let newNote = { ...note };
    
    if (params.microTimingAmount > 0) {
      newNote = applyMicroTiming(newNote, params, rng);
    }
    
    if (params.velocityAmount > 0) {
      newNote = applyVelocityVariation(newNote, params, rng);
    }
    
    if (params.swingAmount > 0) {
      newNote = applySwing(newNote, params, track.resolution_ppq);
    }
    
    if (params.ghostNoteAmount > 0) {
      newNote = applyGhostNoteDensity(newNote, params, rng);
    }
    
    return newNote;
  });
  
  return {
    ...track,
    notes: newNotes
  };
}
