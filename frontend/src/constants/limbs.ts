export type LimbId = "RH" | "LH" | "RF" | "LF";

export type LimbConfig = {
  label: string;
  lanes: string[];
  defaultLane: string;
  accentColor: string;
};

export const LIMB_CONFIG: Record<LimbId, LimbConfig> = {
  RH: {
    label: "Right Hand",
    lanes: ["hihat", "openhat", "ride", "crash"],
    defaultLane: "hihat",
    accentColor: "#38bdf8",
  },
  LH: {
    label: "Left Hand",
    lanes: ["snare", "clap", "tom"],
    defaultLane: "snare",
    accentColor: "#f97316",
  },
  RF: {
    label: "Right Foot",
    lanes: ["kick"],
    defaultLane: "kick",
    accentColor: "#34d399",
  },
  LF: {
    label: "Left Foot",
    lanes: ["hihat_pedal"],
    defaultLane: "hihat_pedal",
    accentColor: "#a78bfa",
  },
};

export const LIMB_ORDER: LimbId[] = ["RH", "LH", "RF", "LF"];

export const inferLimbFromLane = (lane?: string): LimbId | null => {
  if (!lane) return null;
  const normalized = lane.toLowerCase();
  for (const limb of LIMB_ORDER) {
    if (LIMB_CONFIG[limb].lanes.some((l) => l === normalized)) {
      return limb;
    }
  }
  if (normalized.includes("kick")) return "RF";
  if (normalized.includes("snare")) return "LH";
  if (normalized.includes("pedal")) return "LF";
  if (normalized.includes("hat")) return "RH";
  if (normalized.includes("ride") || normalized.includes("crash")) return "RH";
  if (normalized.includes("tom")) return "LH";
  return null;
};

export const inferLimbFromInstrument = (instrumentId?: string): LimbId | null => {
  if (!instrumentId) return null;
  const id = instrumentId.toLowerCase();
  if (id.startsWith("kick") || id.includes("bd") || id.includes("bass")) return "RF";
  if (id.startsWith("snare") || id.includes("rim")) return "LH";
  if (id.includes("pedal")) return "LF";
  if (id.includes("hat")) return "RH";
  if (id.includes("ride") || id.includes("crash") || id.includes("splash")) return "RH";
  if (id.includes("floor") || id.includes("tom")) return "LH";
  return null;
};
