import React, { useEffect, useMemo } from "react";
import { BrainElementSlider } from "./BrainElementSlider";
import { BrainPresetBar } from "./BrainPresetBar";
import { filterElementsForMode } from "../../types/brain";
import { useBrainPanelStore } from "../../state/useBrainPanelStore";

interface BrainPanelProps {
  sectionId?: string | null;
  sectionLabel?: string;
  styleHint?: string;
  locked?: boolean;
}

export const BrainPanel: React.FC<BrainPanelProps> = ({
  sectionId,
  sectionLabel,
  styleHint,
  locked = false,
}) => {
  const definitions = useBrainPanelStore((state) => state.definitions);
  const config = useBrainPanelStore((state) => (sectionId ? state.configs[sectionId] : undefined));
  const loadingDefinitions = useBrainPanelStore((state) => state.loadingDefinitions);
  const loadingSectionId = useBrainPanelStore((state) => state.loadingSectionId);
  const error = useBrainPanelStore((state) => state.error);
  const clipboard = useBrainPanelStore((state) => state.clipboard);

  const fetchDefinitions = useBrainPanelStore((state) => state.fetchDefinitions);
  const ensureSectionConfig = useBrainPanelStore((state) => state.ensureSectionConfig);
  const updateElementValue = useBrainPanelStore((state) => state.updateElementValue);
  const toggleFreeze = useBrainPanelStore((state) => state.toggleFreeze);
  const toggleDisable = useBrainPanelStore((state) => state.toggleDisable);
  const resetElement = useBrainPanelStore((state) => state.resetElement);
  const resetAll = useBrainPanelStore((state) => state.resetAll);
  const randomizeElements = useBrainPanelStore((state) => state.randomizeElements);
  const setMode = useBrainPanelStore((state) => state.setMode);
  const copySection = useBrainPanelStore((state) => state.copySection);
  const pasteToSection = useBrainPanelStore((state) => state.pasteToSection);

  useEffect(() => {
    fetchDefinitions(styleHint);
  }, [styleHint, fetchDefinitions]);

  useEffect(() => {
    if (sectionId) {
      ensureSectionConfig(sectionId);
    }
  }, [sectionId, ensureSectionConfig]);

  const visibleElements = useMemo(() => {
    if (!config) return definitions;
    return filterElementsForMode(config.mode, definitions);
  }, [config, definitions]);

  const groupedElements = useMemo(() => {
    return visibleElements.reduce<Record<string, typeof definitions[number][]>>((groups, definition) => {
      if (!groups[definition.grouping]) {
        groups[definition.grouping] = [];
      }
      groups[definition.grouping].push(definition);
      return groups;
    }, {});
  }, [visibleElements]);

  if (!sectionId) {
    return (
      <div className="rounded-xl border border-dashed border-slate-600/60 bg-slate-900/40 p-6 text-center text-sm text-slate-400">
        Select a section in the timeline to edit brain elements.
      </div>
    );
  }

  const isLoading = loadingDefinitions || loadingSectionId === sectionId;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Drum Brain</p>
          <h4 className="text-lg font-semibold text-white">{sectionLabel || "Selected Section"}</h4>
        </div>
        <div className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
          Mode: {config?.mode?.toUpperCase() || "NORMAL"}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-500/50 bg-amber-900/20 px-3 py-2 text-xs text-amber-200">
          {error}
        </div>
      )}

      <BrainPresetBar
        mode={config?.mode || "normal"}
        locked={locked}
        clipboardAvailable={!!clipboard}
        onModeChange={(nextMode) => sectionId && setMode(sectionId, nextMode)}
        onRandomize={() => sectionId && randomizeElements(sectionId)}
        onResetAll={() => sectionId && resetAll(sectionId)}
        onCopy={() => sectionId && copySection(sectionId)}
        onPaste={() => sectionId && pasteToSection(sectionId)}
      />

      {isLoading && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center text-sm text-slate-400">
          Loading brain controls…
        </div>
      )}

      {!isLoading && (
        <div className="space-y-4">
          {Object.entries(groupedElements).map(([group, elements]) => (
            <div key={group} className="space-y-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {group}
              </div>
              <div className="space-y-3">
                {elements.map((definition) => {
                  const setting = config?.elementSettings.find((entry) => entry.elementId === definition.id);
                  const value = setting?.value ?? definition.defaultValue;
                  const frozen = setting?.frozen ?? false;
                  const disabled = setting?.disabled ?? false;
                  return (
                    <BrainElementSlider
                      key={definition.id}
                      definition={definition}
                      value={value}
                      frozen={frozen}
                      disabled={disabled}
                      locked={locked}
                      onChange={(nextValue) => sectionId && updateElementValue(sectionId, definition.id, nextValue)}
                      onReset={() => sectionId && resetElement(sectionId, definition.id)}
                      onToggleFreeze={() => sectionId && toggleFreeze(sectionId, definition.id)}
                      onToggleDisable={() => sectionId && toggleDisable(sectionId, definition.id)}
                    />
                  );
                })}
              </div>
            </div>
          ))}

          {Object.keys(groupedElements).length === 0 && (
            <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-400">
              All advanced controls are hidden in this mode. Switch to NORMAL or PRO to reveal more options.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BrainPanel;
