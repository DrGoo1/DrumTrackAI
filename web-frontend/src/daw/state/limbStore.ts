import { create } from "zustand";

export type Handedness = "right" | "left";

export type LimbId = "RH" | "LH" | "RF" | "LF";

export interface KitInstrument {
  id: string;
  label: string;
  group:
    | "kick"
    | "snare"
    | "tom"
    | "hihat"
    | "ride"
    | "crash"
    | "perc"
    | "other";
  isPrimaryKick?: boolean;
  isSecondaryKick?: boolean;
  isHatPedal?: boolean;
}

export interface DrumKitConfig {
  name: string;
  instruments: KitInstrument[];
}

export interface LimbMappingConfig {
  handedness: Handedness;
  limbToInstrumentIds: Record<LimbId, string[]>;
}

interface LimbState {
  kit: DrumKitConfig;
  mapping: LimbMappingConfig;
  setHandedness: (h: Handedness) => void;
  setLimbInstruments: (limb: LimbId, ids: string[]) => void;
}

const defaultKit: DrumKitConfig = {
  name: "Studio 4-piece",
  instruments: [
    { id: "kick_main", label: "Kick", group: "kick", isPrimaryKick: true },
    { id: "kick_sub", label: "Kick 2", group: "kick", isSecondaryKick: true },
    { id: "snare_center", label: "Snare", group: "snare" },
    { id: "tom_high", label: "Rack Tom", group: "tom" },
    { id: "tom_floor", label: "Floor Tom", group: "tom" },
    { id: "hh_closed_main", label: "HH Closed", group: "hihat" },
    { id: "hh_open_main", label: "HH Open", group: "hihat" },
    { id: "hh_pedal", label: "HH Pedal", group: "hihat", isHatPedal: true },
    { id: "ride_bow", label: "Ride", group: "ride" },
    { id: "crash_1", label: "Crash 1", group: "crash" },
    { id: "crash_2", label: "Crash 2", group: "crash" },
  ],
};

const defaultMapping: LimbMappingConfig = {
  handedness: "right",
  limbToInstrumentIds: {
    RH: ["hh_closed_main", "hh_open_main", "ride_bow", "crash_1", "crash_2"],
    LH: ["snare_center", "tom_high", "tom_floor"],
    RF: ["kick_main"],
    LF: ["hh_pedal", "kick_sub"],
  },
};

export const useLimbStore = create<LimbState>((set) => ({
  kit: defaultKit,
  mapping: defaultMapping,
  setHandedness: (handedness) =>
    set((state) => ({ mapping: { ...state.mapping, handedness } })),
  setLimbInstruments: (limb, ids) =>
    set((state) => ({
      mapping: {
        ...state.mapping,
        limbToInstrumentIds: { ...state.mapping.limbToInstrumentIds, [limb]: ids },
      },
    })),
}));
