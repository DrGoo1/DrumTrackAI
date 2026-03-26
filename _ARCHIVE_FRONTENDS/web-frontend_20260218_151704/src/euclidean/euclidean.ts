export type DrumInstrumentId =
  | "kick"
  | "snare"
  | "hihat_closed"
  | "hihat_open"
  | "tom_high"
  | "tom_mid"
  | "tom_floor"
  | "ride"
  | "crash";

export interface EuclideanLaneConfig {
  id: string;
  instrumentId: DrumInstrumentId;
  label: string;
  color: string;
  steps: number;
  hits: number;
  accents: number;
  rotate: number;
  velocity: number;
  accentVelocity: number;
}

export interface EuclideanPatternEvent {
  timeBeats: number;
  instrumentId: DrumInstrumentId;
  velocity: number;
  isAccent: boolean;
}

export function euclideanPattern(steps: number, hits: number): number[] {
  if (steps <= 0) return [];
  if (hits <= 0) return new Array(steps).fill(0);
  if (hits >= steps) return new Array(steps).fill(1);

  const pattern: number[] = [];
  let bucket = 0;
  for (let i = 0; i < steps; i++) {
    bucket += hits;
    if (bucket >= steps) {
      bucket -= steps;
      pattern.push(1);
    } else {
      pattern.push(0);
    }
  }
  return pattern;
}

export function buildEuclideanEventsForLane(
  lane: EuclideanLaneConfig,
  bars: number = 1,
): EuclideanPatternEvent[] {
  const { steps, hits, rotate, velocity, accentVelocity, instrumentId, accents } = lane;
  const basePattern = euclideanPattern(steps, hits);

  const accentIndices: number[] = [];
  if (accents > 0) {
    let count = 0;
    for (let i = 0; i < steps && count < accents; i++) {
      if (basePattern[i] === 1) {
        accentIndices.push(i);
        count++;
      }
    }
  }

  const events: EuclideanPatternEvent[] = [];

  for (let bar = 0; bar < bars; bar++) {
    const barOffsetSteps = bar * steps;
    for (let i = 0; i < steps; i++) {
      const rotatedIdx = (i + rotate) % steps;
      if (basePattern[rotatedIdx] !== 1) continue;

      const timeBeats = (barOffsetSteps + i) * (4 / steps);
      const isAccent = accentIndices.includes(rotatedIdx);
      events.push({
        timeBeats,
        instrumentId,
        velocity: isAccent ? accentVelocity : velocity,
        isAccent,
      });
    }
  }

  return events;
}

export function buildEuclideanPattern(
  lanes: EuclideanLaneConfig[],
  bars: number,
): EuclideanPatternEvent[] {
  const events = lanes.flatMap((lane) => buildEuclideanEventsForLane(lane, bars));
  return events.sort((a, b) => a.timeBeats - b.timeBeats);
}
