import { create } from "zustand";
import {
  BrainElementDefinition,
  BrainElementSetting,
  BrainPanelMode,
  DrumBrainConfig,
  FALLBACK_BRAIN_ELEMENTS,
  cloneConfig,
  createDefaultBrainConfig,
} from "../types/brain";
import { fetchBrainConfig, fetchBrainElements, patchBrainConfig } from "../api/brain";

type BrainPanelState = {
  definitions: BrainElementDefinition[];
  definitionMap: Record<string, BrainElementDefinition>;
  definitionsStyleKey: string;
  loadingDefinitions: boolean;
  loadingSectionId: string | null;
  configs: Record<string, DrumBrainConfig>;
  clipboard: DrumBrainConfig | null;
  error: string | null;
  fetchDefinitions: (styleHint?: string) => Promise<void>;
  ensureSectionConfig: (sectionId: string | null | undefined) => Promise<DrumBrainConfig | undefined>;
  setMode: (sectionId: string, mode: BrainPanelMode) => Promise<void>;
  updateElementValue: (sectionId: string, elementId: string, value: number) => Promise<void>;
  toggleFreeze: (sectionId: string, elementId: string) => Promise<void>;
  toggleDisable: (sectionId: string, elementId: string) => Promise<void>;
  resetElement: (sectionId: string, elementId: string) => Promise<void>;
  resetAll: (sectionId: string) => Promise<void>;
  randomizeElements: (sectionId: string) => Promise<void>;
  copySection: (sectionId: string) => void;
  pasteToSection: (sectionId: string) => Promise<void>;
};

type ConfigMutator = (draft: DrumBrainConfig) => DrumBrainConfig;

const DEFAULT_STYLE_KEY = "__default__";

function toStyleKey(styleHint?: string | null): string {
  return styleHint?.toLowerCase() || DEFAULT_STYLE_KEY;
}

function indexDefinitions(definitions: BrainElementDefinition[]): Record<string, BrainElementDefinition> {
  return definitions.reduce<Record<string, BrainElementDefinition>>((acc, def) => {
    acc[def.id] = def;
    return acc;
  }, {});
}

function hydrateConfig(
  config: DrumBrainConfig,
  definitions: BrainElementDefinition[] = FALLBACK_BRAIN_ELEMENTS,
): DrumBrainConfig {
  const definitionMap = indexDefinitions(definitions);
  const mergedSettings = Object.values(definitionMap).map((definition) => {
    const existing = config.elementSettings.find((setting) => setting.elementId === definition.id);
    if (existing) {
      return {
        elementId: definition.id,
        value: typeof existing.value === "number" ? existing.value : definition.defaultValue,
        frozen: existing.frozen ?? false,
        disabled: existing.disabled ?? false,
      } satisfies BrainElementSetting;
    }
    return {
      elementId: definition.id,
      value: definition.defaultValue,
      frozen: false,
      disabled: false,
    } satisfies BrainElementSetting;
  });

  return {
    mode: config.mode,
    randomizeSeed: config.randomizeSeed,
    elementSettings: mergedSettings,
  };
}

function formatError(error: unknown, fallback: string): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  return fallback;
}

export const useBrainPanelStore = create<BrainPanelState>((set, get) => {
  const applyAndPersist = async (sectionId: string, mutator: ConfigMutator) => {
    if (!sectionId) return;
    const baseline = (await get().ensureSectionConfig(sectionId)) ?? createDefaultBrainConfig(get().definitions);
    const draft = cloneConfig(baseline);
    const nextConfig = mutator(draft);
    set((state) => ({
      configs: { ...state.configs, [sectionId]: nextConfig },
      error: null,
    }));
    try {
      const saved = await patchBrainConfig(sectionId, nextConfig);
      const reconciled = hydrateConfig(saved, get().definitions);
      set((state) => ({
        configs: { ...state.configs, [sectionId]: reconciled },
        error: null,
      }));
    } catch (error) {
      console.error("Failed to persist brain configuration", error);
      set((state) => ({
        configs: { ...state.configs, [sectionId]: baseline },
        error: formatError(error, "Unable to save brain settings"),
      }));
    }
  };

  return {
    definitions: FALLBACK_BRAIN_ELEMENTS,
    definitionMap: indexDefinitions(FALLBACK_BRAIN_ELEMENTS),
    definitionsStyleKey: DEFAULT_STYLE_KEY,
    loadingDefinitions: false,
    loadingSectionId: null,
    configs: {},
    clipboard: null,
    error: null,

    fetchDefinitions: async (styleHint) => {
      const styleKey = toStyleKey(styleHint);
      if (styleKey === get().definitionsStyleKey && get().definitions.length) {
        return;
      }
      set({ loadingDefinitions: true });
      try {
        const definitions = await fetchBrainElements(styleHint);
        const definitionMap = indexDefinitions(definitions);
        set((state) => {
          const reconciledConfigs = Object.keys(state.configs).reduce<Record<string, DrumBrainConfig>>((acc, sectionId) => {
            acc[sectionId] = hydrateConfig(state.configs[sectionId], definitions);
            return acc;
          }, {});
          return {
            definitions,
            definitionMap,
            definitionsStyleKey: styleKey,
            configs: reconciledConfigs,
            loadingDefinitions: false,
            error: null,
          };
        });
      } catch (error) {
        console.warn("Unable to fetch brain element definitions", error);
        set({
          loadingDefinitions: false,
          error: formatError(error, "Using fallback brain element definitions"),
        });
      }
    },

    ensureSectionConfig: async (sectionId) => {
      if (!sectionId) return undefined;
      const existing = get().configs[sectionId];
      if (existing) {
        return existing;
      }
      set({ loadingSectionId: sectionId });
      try {
        const remoteConfig = await fetchBrainConfig(sectionId);
        const hydrated = hydrateConfig(remoteConfig, get().definitions);
        set((state) => ({
          configs: { ...state.configs, [sectionId]: hydrated },
          loadingSectionId: null,
          error: null,
        }));
        return hydrated;
      } catch (error) {
        console.warn("Falling back to default brain config", error);
        const fallback = createDefaultBrainConfig(get().definitions);
        set((state) => ({
          configs: { ...state.configs, [sectionId]: fallback },
          loadingSectionId: null,
          error: formatError(error, "Using default brain config"),
        }));
        return fallback;
      }
    },

    setMode: async (sectionId, mode) => {
      await applyAndPersist(sectionId, (draft) => ({
        ...draft,
        mode,
      }));
    },

    updateElementValue: async (sectionId, elementId, value) => {
      const definition = get().definitionMap[elementId];
      await applyAndPersist(sectionId, (draft) => {
        const nextSettings = draft.elementSettings.map((setting) =>
          setting.elementId === elementId
            ? {
                ...setting,
                value: Math.min(Math.max(value, definition?.minValue ?? 0), definition?.maxValue ?? 1),
              }
            : setting,
        );
        return {
          ...draft,
          elementSettings: nextSettings,
        };
      });
    },

    toggleFreeze: async (sectionId, elementId) => {
      await applyAndPersist(sectionId, (draft) => ({
        ...draft,
        elementSettings: draft.elementSettings.map((setting) =>
          setting.elementId === elementId ? { ...setting, frozen: !setting.frozen } : setting,
        ),
      }));
    },

    toggleDisable: async (sectionId, elementId) => {
      await applyAndPersist(sectionId, (draft) => ({
        ...draft,
        elementSettings: draft.elementSettings.map((setting) =>
          setting.elementId === elementId ? { ...setting, disabled: !setting.disabled } : setting,
        ),
      }));
    },

    resetElement: async (sectionId, elementId) => {
      const definition = get().definitionMap[elementId];
      await applyAndPersist(sectionId, (draft) => ({
        ...draft,
        elementSettings: draft.elementSettings.map((setting) =>
          setting.elementId === elementId
            ? {
                ...setting,
                value: definition?.defaultValue ?? 0,
                frozen: false,
                disabled: false,
              }
            : setting,
        ),
      }));
    },

    resetAll: async (sectionId) => {
      const currentMode = get().configs[sectionId]?.mode ?? "normal";
      await applyAndPersist(sectionId, () => createDefaultBrainConfig(get().definitions, currentMode));
    },

    randomizeElements: async (sectionId) => {
      const definitions = get().definitions;
      const randomSeed = Math.floor(Math.random() * 1_000_000);
      await applyAndPersist(sectionId, (draft) => {
        const settings = draft.elementSettings.map((setting) => {
          const definition = definitions.find((def) => def.id === setting.elementId);
          if (!definition || setting.frozen) {
            return setting;
          }
          const value = definition.minValue + Math.random() * (definition.maxValue - definition.minValue);
          return { ...setting, value };
        });
        return {
          ...draft,
          randomizeSeed: randomSeed,
          elementSettings: settings,
        };
      });
    },

    copySection: (sectionId) => {
      const existing = get().configs[sectionId];
      if (!existing) return;
      set({ clipboard: cloneConfig(existing) });
    },

    pasteToSection: async (sectionId) => {
      const clipboard = get().clipboard;
      if (!clipboard) return;
      await applyAndPersist(sectionId, () => cloneConfig(clipboard));
    },
  };
});
