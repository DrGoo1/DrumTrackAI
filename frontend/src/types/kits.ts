import type { DrumInstrumentId } from "./drumTrack";

export type KitMicId = string;

export interface KitMicDefinition {
  id: KitMicId;
  label: string;
  defaultGainDb?: number;
}

export interface KitVelocityLayer {
  min: number;
  max: number;
  roundRobin: string[];
}

export interface KitMicArticulation {
  velocityLayers: KitVelocityLayer[];
}

export interface KitArticulation {
  mics: Record<KitMicId, KitMicArticulation>;
}

export interface KitManifestV1 {
  kitId: string;
  name: string;
  version: string;

  mics: KitMicDefinition[];

  chokeGroups?: Record<string, DrumInstrumentId[]>;

  articulations: Partial<Record<DrumInstrumentId, KitArticulation>>;

  mixDefaults?: {
    masterGainDb?: number;
    micGainsDb?: Record<KitMicId, number>;
  };
}

export interface KitListItem {
  kitId: string;
  name: string;
  version?: string;
}

export interface ListKitsResponse {
  kits: KitListItem[];
  kitsRoot?: string;
}
