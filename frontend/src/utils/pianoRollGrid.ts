/**
 * Piano Roll Grid Utilities
 * ==========================
 * Grid calculation and rendering helpers for 64th-note capable piano roll
 */

// ============================================================================
// Grid Configuration
// ============================================================================

export type GridResolution = 
  | '4th'      // Quarter notes
  | '8th'      // 8th notes
  | '16th'     // 16th notes
  | '32nd'     // 32nd notes
  | '64th'     // 64th notes (ultra-high res)
  | 'triplet_8th'
  | 'triplet_16th';

export interface GridConfig {
  resolution: GridResolution;
  ppq: number;  // Ticks per quarter note (960 or 1920)
  pixelsPerBeat: number;  // Zoom level
  showSubdivisions: boolean;
}

// ============================================================================
// Grid Line Types
// ============================================================================

export interface GridLine {
  tick: number;
  x: number;
  type: 'bar' | 'beat' | 'subdivision' | 'fine';
  strength: number;  // 0.0-1.0 for visual weight
}

// ============================================================================
// Grid Calculation
// ============================================================================

/**
 * Get number of subdivisions per bar for a given resolution
 */
export function getSubdivisionsPerBar(resolution: GridResolution): number {
  switch (resolution) {
    case '64th':
      return 64;
    case '32nd':
      return 32;
    case '16th':
      return 16;
    case '8th':
      return 8;
    case '4th':
      return 4;
    case 'triplet_8th':
      return 12;
    case 'triplet_16th':
      return 24;
    default:
      return 16;
  }
}

/**
 * Get ticks per subdivision for a given resolution
 * Overloaded version that accepts timeSignature parameter
 */
export function getTicksPerSubdivision(
  resolutionPPQ: number,
  timeSignature: [number, number],
  resolution: GridResolution
): number;
export function getTicksPerSubdivision(resolution: GridResolution, ppq: number): number;
export function getTicksPerSubdivision(
  arg1: GridResolution | number,
  arg2?: number | [number, number],
  arg3?: GridResolution
): number {
  // Handle overloaded signatures
  let resolution: GridResolution;
  let ppq: number;
  let timeSignature: [number, number] = [4, 4];
  
  if (typeof arg1 === 'number' && Array.isArray(arg2) && arg3) {
    // New signature: (resolutionPPQ, timeSignature, resolution)
    ppq = arg1;
    timeSignature = arg2;
    resolution = arg3;
  } else if (typeof arg1 === 'string' && typeof arg2 === 'number') {
    // Old signature: (resolution, ppq)
    resolution = arg1;
    ppq = arg2;
  } else {
    throw new Error('Invalid arguments to getTicksPerSubdivision');
  }
  
  const beatsPerBar = timeSignature[0];
  const barTicks = beatsPerBar * ppq;
  const subdivisions = getSubdivisionsPerBar(resolution);
  return Math.round(barTicks / subdivisions);
}

// Keep old function for backward compatibility
function getTicksPerSubdivisionOld(resolution: GridResolution, ppq: number): number {
  switch (resolution) {
    case '4th':
      return ppq;  // Quarter note
    case '8th':
      return ppq / 2;
    case '16th':
      return ppq / 4;
    case '32nd':
      return ppq / 8;
    case '64th':
      return ppq / 16;
    case 'triplet_8th':
      return ppq / 3;
    case 'triplet_16th':
      return ppq / 6;
    default:
      return ppq / 4;  // Default to 16th
  }
}

/**
 * Calculate grid lines for a given viewport
 */
export function calculateGridLines(
  config: GridConfig,
  viewportStartTick: number,
  viewportEndTick: number,
  timeSignature: [number, number] = [4, 4]
): GridLine[] {
  const lines: GridLine[] = [];
  const { ppq, pixelsPerBeat } = config;
  
  // Ticks per bar (assuming 4/4 time)
  const ticksPerBar = ppq * timeSignature[0];
  const ticksPerBeat = ppq;
  const ticksPerSub = getTicksPerSubdivision(config.resolution, ppq);
  
  // Start from bar boundary before viewport
  const startBar = Math.floor(viewportStartTick / ticksPerBar);
  const startTick = startBar * ticksPerBar;
  
  let currentTick = startTick;
  
  while (currentTick <= viewportEndTick) {
    const x = tickToPixel(currentTick, viewportStartTick, pixelsPerBeat, ppq);
    
    // Determine line type and strength
    let type: GridLine['type'];
    let strength: number;
    
    if (currentTick % ticksPerBar === 0) {
      // Bar line
      type = 'bar';
      strength = 1.0;
    } else if (currentTick % ticksPerBeat === 0) {
      // Beat line
      type = 'beat';
      strength = 0.7;
    } else if (currentTick % ticksPerSub === 0) {
      // Subdivision line
      type = 'subdivision';
      strength = 0.4;
    } else {
      // Fine grid (for very high zoom)
      type = 'fine';
      strength = 0.2;
    }
    
    lines.push({ tick: currentTick, x, type, strength });
    
    // Advance to next subdivision
    currentTick += ticksPerSub;
  }
  
  return lines;
}

/**
 * Convert tick position to pixel position
 */
export function tickToPixel(
  tick: number,
  viewportStartTick: number,
  pixelsPerBeat: number,
  ppq: number
): number {
  const relativeTick = tick - viewportStartTick;
  const beats = relativeTick / ppq;
  return beats * pixelsPerBeat;
}

/**
 * Convert pixel position to tick position
 */
export function pixelToTick(
  x: number,
  viewportStartTick: number,
  pixelsPerBeat: number,
  ppq: number
): number {
  const beats = x / pixelsPerBeat;
  const relativeTick = beats * ppq;
  return viewportStartTick + relativeTick;
}

/**
 * Snap tick to grid
 */
export function snapToGrid(
  tick: number,
  resolution: GridResolution,
  ppq: number
): number {
  const ticksPerSub = getTicksPerSubdivision(resolution, ppq);
  return Math.round(tick / ticksPerSub) * ticksPerSub;
}

/**
 * Get bar and beat from tick
 */
export function tickToBarBeat(
  tick: number,
  ppq: number,
  timeSignature: [number, number] = [4, 4]
): { bar: number; beat: number; tick: number } {
  const ticksPerBar = ppq * timeSignature[0];
  const ticksPerBeat = ppq;
  
  const bar = Math.floor(tick / ticksPerBar);
  const tickInBar = tick % ticksPerBar;
  const beat = Math.floor(tickInBar / ticksPerBeat);
  const tickInBeat = tickInBar % ticksPerBeat;
  
  return { bar, beat, tick: tickInBeat };
}

/**
 * Get tick from bar and beat
 */
export function barBeatToTick(
  bar: number,
  beat: number,
  tickInBeat: number,
  ppq: number,
  timeSignature: [number, number] = [4, 4]
): number {
  const ticksPerBar = ppq * timeSignature[0];
  const ticksPerBeat = ppq;
  
  return bar * ticksPerBar + beat * ticksPerBeat + tickInBeat;
}

// ============================================================================
// Zoom and Viewport
// ============================================================================

/**
 * Calculate appropriate grid resolution for zoom level
 */
export function getAppropriateResolution(pixelsPerBeat: number): GridResolution {
  if (pixelsPerBeat >= 400) return '64th';
  if (pixelsPerBeat >= 200) return '32nd';
  if (pixelsPerBeat >= 100) return '16th';
  if (pixelsPerBeat >= 50) return '8th';
  return '4th';
}

/**
 * Calculate visible tick range for viewport
 */
export function getVisibleTickRange(
  viewportWidth: number,
  viewportStartTick: number,
  pixelsPerBeat: number,
  ppq: number
): [number, number] {
  const endTick = pixelToTick(
    viewportWidth,
    viewportStartTick,
    pixelsPerBeat,
    ppq
  );
  
  return [viewportStartTick, Math.ceil(endTick)];
}

/**
 * Zoom to fit specific tick range
 */
export function zoomToFit(
  startTick: number,
  endTick: number,
  viewportWidth: number,
  ppq: number,
  padding: number = 0.1  // 10% padding on each side
): { pixelsPerBeat: number; viewportStartTick: number } {
  const tickRange = endTick - startTick;
  const beats = tickRange / ppq;
  
  // Apply padding
  const paddingBeats = beats * padding;
  const totalBeats = beats + (2 * paddingBeats);
  
  const pixelsPerBeat = viewportWidth / totalBeats;
  const viewportStartTick = startTick - (paddingBeats * ppq);
  
  return { pixelsPerBeat, viewportStartTick: Math.max(0, viewportStartTick) };
}

// ============================================================================
// 64th Note Support
// ============================================================================

/**
 * Check if resolution supports 64th notes
 */
export function supports64thNotes(ppq: number): boolean {
  // Need at least 15 ticks per 64th note for good precision
  // At 960 PPQ: 960/16 = 60 ticks per 64th ✓
  // At 480 PPQ: 480/16 = 30 ticks per 64th ✓ (acceptable)
  // At 240 PPQ: 240/16 = 15 ticks per 64th ✓ (minimum)
  return ppq >= 240;
}

/**
 * Get minimum PPQ required for resolution
 */
export function getMinimumPPQ(resolution: GridResolution): number {
  switch (resolution) {
    case '64th':
      return 240;
    case '32nd':
      return 120;
    case 'triplet_16th':
      return 180;
    default:
      return 96;
  }
}

// ============================================================================
// Grid Rendering Helpers
// ============================================================================

/**
 * Get grid line color based on type and strength
 */
export function getGridLineColor(
  type: GridLine['type'],
  strength: number,
  darkMode: boolean = false
): string {
  const baseColor = darkMode ? '255, 255, 255' : '0, 0, 0';
  
  let baseAlpha: number;
  switch (type) {
    case 'bar':
      baseAlpha = 0.3;
      break;
    case 'beat':
      baseAlpha = 0.2;
      break;
    case 'subdivision':
      baseAlpha = 0.1;
      break;
    case 'fine':
      baseAlpha = 0.05;
      break;
  }
  
  const finalAlpha = baseAlpha * strength;
  return `rgba(${baseColor}, ${finalAlpha})`;
}

/**
 * Get grid line width based on type
 */
export function getGridLineWidth(type: GridLine['type']): number {
  switch (type) {
    case 'bar':
      return 2;
    case 'beat':
      return 1;
    case 'subdivision':
      return 1;
    case 'fine':
      return 0.5;
  }
}

// Export module
export {};
