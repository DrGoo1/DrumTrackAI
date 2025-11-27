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

export interface DrumGenerationConfigDTO {
  style: string;
  drummer: string;
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
}
