export type GenerationMode = "template" | "ai_variation" | "full_ai" | "euclidean";

export interface EuclideanLaneConfigDTO {
  instrumentId: string;
  steps: number;
  hits: number;
  accents: number;
  rotate: number;
  velocity: number;
  accentVelocity: number;
}

export interface BarDefaultsDTO {
  barIndex: number;   // 0-based within generated range
  open: number;       // 0..1, 0.5 = neutral
  power: number;      // 0..1, 0.5 = neutral
  timing: number;     // 0..1, 0.5 = neutral
  priority: number;   // 0..1, 0.5 = neutral
}

export type LimbIdDTO = "LH" | "RH" | "LF" | "RF";

export interface SlotMetaDTO {
  barIndex: number;
  limb: LimbIdDTO;
  step: number;       // 0..(resolution-1) for that bar
  open?: number;
  power?: number;
  timing?: number;
  priority?: number;
}

export interface DrumGenerationConfigDTO {
  style: string;
  drummer: string;
  // Public drummer/profile identifier (e.g. "studio_rock"), decoupled from
  // any internal real-drummer analysis names used on the admin side.
  publicDrummerId?: string;
  drummerBrainEnabled?: boolean;
  tempos: number[];
  timeSignature: [number, number];
  startMeasure: number;
  endMeasure: number;
  intensity: number;
  variation: number;
  humanize: boolean;
  humanizeAmount: number;
  ghostNoteAmount: number;
  swingAmount: number;
  buildScope: "full_song" | "selected_section";
  sectionId: string;
  fillLocations: number[];
  fillType: string;
  fillDensity?: number;
  generationMode: GenerationMode;

  // Guide track controls
  guideEnabled?: boolean;
  guideInstrument?: "mix" | "bass" | "guitar" | "keys" | "vocal" | "other";

  // Jamstix / articulation profile selector
  articulationProfile?: "balanced" | "ghosty" | "tight_hats" | "crashy";

  euclideanLanes?: EuclideanLaneConfigDTO[];

  // Limb Bar Editor meta (optional)
  bars?: BarDefaultsDTO[];
  slots?: SlotMetaDTO[];
}
