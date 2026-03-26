/**
 * Groove Weight Types
 * ===================
 * Types for the limb-aware groove weight system
 * Groove weights emphasize certain subdivisions for feel
 */

// ============================================================================
// Groove Weight Types
// ============================================================================

export type GrooveWeightStyle = 'heavy' | 'neutral' | 'syncopated' | 'custom';

export interface GrooveWeight {
  subdivision: number;  // Which subdivision (0-15 for 16th notes)
  weight: number;  // Emphasis level (0.0-2.0, where 1.0 is neutral)
}

export interface GrooveWeightProfile {
  style: GrooveWeightStyle;
  label: string;
  weights: GrooveWeight[];
  description?: string;
}

// ============================================================================
// Preset Groove Weight Profiles
// ============================================================================

export const GROOVE_WEIGHT_PRESETS: Record<GrooveWeightStyle, GrooveWeightProfile> = {
  heavy: {
    style: 'heavy',
    label: 'Heavy (On-Beat)',
    weights: [
      { subdivision: 0, weight: 1.5 },   // Downbeat
      { subdivision: 1, weight: 0.7 },
      { subdivision: 2, weight: 1.3 },   // Quarter beat
      { subdivision: 3, weight: 0.7 },
      { subdivision: 4, weight: 1.5 },   // Downbeat
      { subdivision: 5, weight: 0.7 },
      { subdivision: 6, weight: 1.3 },   // Quarter beat
      { subdivision: 7, weight: 0.7 },
      { subdivision: 8, weight: 1.5 },   // Downbeat
      { subdivision: 9, weight: 0.7 },
      { subdivision: 10, weight: 1.3 },  // Quarter beat
      { subdivision: 11, weight: 0.7 },
      { subdivision: 12, weight: 1.5 },  // Downbeat
      { subdivision: 13, weight: 0.7 },
      { subdivision: 14, weight: 1.3 },  // Quarter beat
      { subdivision: 15, weight: 0.7 },
    ],
    description: 'Emphasizes downbeats and quarter notes for a heavy, driving feel',
  },
  
  neutral: {
    style: 'neutral',
    label: 'Neutral (Balanced)',
    weights: Array.from({ length: 16 }, (_, i) => ({
      subdivision: i,
      weight: 1.0,
    })),
    description: 'All subdivisions equally weighted, no emphasis',
  },
  
  syncopated: {
    style: 'syncopated',
    label: 'Syncopated (Off-Beat)',
    weights: [
      { subdivision: 0, weight: 0.9 },   // Downbeat slightly reduced
      { subdivision: 1, weight: 1.3 },   // Off-beat emphasized
      { subdivision: 2, weight: 0.9 },
      { subdivision: 3, weight: 1.4 },   // Syncopation
      { subdivision: 4, weight: 0.9 },
      { subdivision: 5, weight: 1.3 },
      { subdivision: 6, weight: 0.9 },
      { subdivision: 7, weight: 1.4 },
      { subdivision: 8, weight: 0.9 },
      { subdivision: 9, weight: 1.3 },
      { subdivision: 10, weight: 0.9 },
      { subdivision: 11, weight: 1.4 },
      { subdivision: 12, weight: 0.9 },
      { subdivision: 13, weight: 1.3 },
      { subdivision: 14, weight: 0.9 },
      { subdivision: 15, weight: 1.4 },
    ],
    description: 'Emphasizes off-beats and syncopation for funky, rhythmic feel',
  },
  
  custom: {
    style: 'custom',
    label: 'Custom',
    weights: Array.from({ length: 16 }, (_, i) => ({
      subdivision: i,
      weight: 1.0,
    })),
    description: 'User-defined groove weight pattern',
  },
};

// ============================================================================
// Groove Weight UI State
// ============================================================================

export interface GrooveWeightUIState {
  enabled: boolean;
  currentProfile: GrooveWeightProfile;
  showOverlay: boolean;
  opacity: number;  // 0.0-1.0 for overlay transparency
}

/**
 * Map of groove weights by bar and subdivision
 * For piano roll overlay visualization
 */
export interface GrooveWeightEntry {
  weight: 'heavy' | 'neutral' | 'syncopated';
  forceHit?: boolean;
  forceSilent?: boolean;
}

export interface GrooveWeightMap {
  [barIndex: number]: {
    [subdivisionIndex: number]: GrooveWeightEntry;
  };
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get groove weight for a specific tick position
 */
export function getGrooveWeightAtTick(
  tick: number,
  profile: GrooveWeightProfile,
  ppq: number
): number {
  // Calculate which 16th note subdivision this tick falls on
  const ticksPerSixteenth = ppq / 4;
  const subdivision = Math.floor((tick % (ppq * 4)) / ticksPerSixteenth);
  
  const weight = profile.weights.find(w => w.subdivision === subdivision);
  return weight ? weight.weight : 1.0;
}

/**
 * Apply groove weight to velocity
 */
export function applyGrooveWeightToVelocity(
  velocity: number,
  weight: number,
  minVelocity: number = 1,
  maxVelocity: number = 127
): number {
  const adjusted = Math.round(velocity * weight);
  return Math.max(minVelocity, Math.min(maxVelocity, adjusted));
}

/**
 * Create custom groove weight profile
 */
export function createCustomGrooveWeight(
  weights: number[]
): GrooveWeightProfile {
  if (weights.length !== 16) {
    throw new Error('Custom groove weight must have exactly 16 values');
  }
  
  return {
    style: 'custom',
    label: 'Custom',
    weights: weights.map((weight, i) => ({
      subdivision: i,
      weight,
    })),
    description: 'Custom user-defined groove pattern',
  };
}

/**
 * Interpolate between two groove weight profiles
 */
export function interpolateGrooveWeights(
  profileA: GrooveWeightProfile,
  profileB: GrooveWeightProfile,
  amount: number  // 0.0 = all A, 1.0 = all B
): GrooveWeightProfile {
  return {
    style: 'custom',
    label: `Blend (${Math.round(amount * 100)}%)`,
    weights: profileA.weights.map((weightA, i) => {
      const weightB = profileB.weights[i];
      return {
        subdivision: i,
        weight: weightA.weight * (1 - amount) + weightB.weight * amount,
      };
    }),
    description: `Blend of ${profileA.label} and ${profileB.label}`,
  };
}

// Export module
export {};
