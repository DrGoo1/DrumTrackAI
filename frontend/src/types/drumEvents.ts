import type { DrumInstrumentId } from "./drumTrack";

export type DrumEventId = string;

export type DrumEventSource = "generator" | "editor" | "import" | "unknown";

export interface DrumEventV1 {
  id: DrumEventId;
  timeSec: number;
  durationSec?: number;
  instrumentId: DrumInstrumentId;
  velocity: number;

  barIndex?: number;

  isGhost?: boolean;
  isAccent?: boolean;

  hatOpen01?: number;

  chokeGroupId?: string;

  source?: DrumEventSource;
}
