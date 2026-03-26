export type BrainPanelMode = "easy" | "normal" | "pro";

export interface BrainElementDefinition {
  id: string;
  label: string;
  description: string;
  minValue: number;
  maxValue: number;
  defaultValue: number;
  supportsFreeze: boolean;
  supportsDisable: boolean;
  grouping: string;
}

export interface BrainElementSetting {
  elementId: string;
  value: number;
  frozen?: boolean;
  disabled?: boolean;
}

export interface DrumBrainConfig {
  mode: BrainPanelMode;
  randomizeSeed?: number | null;
  elementSettings: BrainElementSetting[];
}

export const FALLBACK_BRAIN_ELEMENTS: BrainElementDefinition[] = [
  {
    id: "feel_processor",
    label: "Feel Processor",
    description: "Controls pocket, timing variance, and power variance",
    minValue: -1,
    maxValue: 1,
    defaultValue: 0,
    supportsFreeze: true,
    supportsDisable: true,
    grouping: "timing",
  },
  {
    id: "redirection",
    label: "Redirection",
    description: "Routes one limb's pattern to an alternate instrument",
    minValue: 0,
    maxValue: 1,
    defaultValue: 0.5,
    supportsFreeze: true,
    supportsDisable: true,
    grouping: "kit",
  },
  {
    id: "power_hand",
    label: "Power Hand",
    description: "Switches hats to ride/crash when power exceeds threshold",
    minValue: 0,
    maxValue: 1,
    defaultValue: 0.5,
    supportsFreeze: true,
    supportsDisable: true,
    grouping: "kit",
  },
  {
    id: "reduction",
    label: "Reduction",
    description: "Drops notes as intensity falls for softer sections",
    minValue: 0,
    maxValue: 1,
    defaultValue: 0.5,
    supportsFreeze: true,
    supportsDisable: true,
    grouping: "dynamics",
  },
  {
    id: "auto_snare",
    label: "Auto Snare",
    description: "Switch between sidestick and center hits based on power",
    minValue: 0,
    maxValue: 1,
    defaultValue: 0.5,
    supportsFreeze: true,
    supportsDisable: true,
    grouping: "kit",
  },
  {
    id: "ghost_density",
    label: "Ghost Density",
    description: "Adds or removes ghost-note articulations",
    minValue: 0,
    maxValue: 1.5,
    defaultValue: 0.5,
    supportsFreeze: true,
    supportsDisable: true,
    grouping: "dynamics",
  },
  {
    id: "fill_aggression",
    label: "Fill Aggression",
    description: "Controls how busy drum fills are",
    minValue: 0,
    maxValue: 1,
    defaultValue: 0.5,
    supportsFreeze: true,
    supportsDisable: true,
    grouping: "fills",
  },
  {
    id: "hat_openness",
    label: "Hat Openness",
    description: "Bias toward more open or tight hi-hat articulations",
    minValue: 0,
    maxValue: 1,
    defaultValue: 0.5,
    supportsFreeze: true,
    supportsDisable: true,
    grouping: "kit",
  },
];

export const MODE_ELEMENT_WHITELIST: Record<BrainPanelMode, string[] | null> = {
  pro: null,
  normal: [
    "feel_processor",
    "reduction",
    "ghost_density",
    "power_hand",
    "fill_aggression",
    "hat_openness",
  ],
  easy: ["feel_processor", "power_hand", "fill_aggression", "reduction"],
};

export function filterElementsForMode(
  mode: BrainPanelMode,
  definitions: BrainElementDefinition[],
): BrainElementDefinition[] {
  const whitelist = MODE_ELEMENT_WHITELIST[mode];
  if (!whitelist) return definitions;
  return definitions.filter((def) => whitelist.includes(def.id));
}

export function createDefaultBrainConfig(
  definitions: BrainElementDefinition[] = FALLBACK_BRAIN_ELEMENTS,
  mode: BrainPanelMode = "normal",
): DrumBrainConfig {
  return {
    mode,
    randomizeSeed: null,
    elementSettings: definitions.map((def) => ({
      elementId: def.id,
      value: def.defaultValue,
      frozen: false,
      disabled: false,
    })),
  };
}

export function resolveElementValue(
  config: DrumBrainConfig | undefined,
  elementId: string,
  fallback: number,
): number {
  if (!config) return fallback;
  const setting = config.elementSettings.find((s) => s.elementId === elementId);
  if (!setting) return fallback;
  return setting.value;
}

export function updateSetting(
  config: DrumBrainConfig,
  definition: BrainElementDefinition | undefined,
  patch: Partial<BrainElementSetting> & { elementId: string },
): DrumBrainConfig {
  const clampedValue = definition
    ? clampValue(patch.value ?? definition.defaultValue, definition.minValue, definition.maxValue)
    : patch.value ?? 0;

  const nextSettings = config.elementSettings.some((s) => s.elementId === patch.elementId)
    ? config.elementSettings.map((setting) =>
        setting.elementId === patch.elementId
          ? { ...setting, ...patch, value: clampedValue }
          : setting,
      )
    : [...config.elementSettings, { elementId: patch.elementId, value: clampedValue, frozen: false, disabled: false }];

  return {
    ...config,
    elementSettings: nextSettings,
  };
}

export function removeSetting(config: DrumBrainConfig, elementId: string): DrumBrainConfig {
  return {
    ...config,
    elementSettings: config.elementSettings.filter((setting) => setting.elementId !== elementId),
  };
}

export function cloneConfig(config: DrumBrainConfig): DrumBrainConfig {
  return {
    mode: config.mode,
    randomizeSeed: config.randomizeSeed,
    elementSettings: config.elementSettings.map((setting) => ({ ...setting })),
  };
}

function clampValue(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.min(Math.max(value, min), max);
}
