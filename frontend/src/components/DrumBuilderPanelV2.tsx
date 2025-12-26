/**
 * Drum Builder Panel v2.0 - Enhanced with new performance controls
 * Integrates Drum Builder v2.0 features with existing UI
 */
import React, { useEffect, useState } from 'react';
import { DrumGenerationConfig, RudimentBlock, RudimentHandLead } from '../types/drumTrack';
import { useRudimentBlockStore } from '../state/useRudimentBlockStore';

type FillFrequencyOption = 'none' | 'every_4_bars' | 'section_transitions' | 'all_transitions';

interface RudimentBlockDraft {
  blockId: string;
  offset: number; // relative to section start, 0-based
  length: number;
  families: string[];
  rudimentId: string;
  density?: number;
  ensureDownbeatKick?: boolean;
  preserveHatTail?: boolean;
}

interface MeasureRange {
  sectionId: string;
  sectionLabel: string;
  startMeasure: number;
  endMeasure: number;
  measureCount: number;
  tempos: number[];
  avgTempo: number;
  timeSignature: [number, number];
}

interface DrumBuilderPanelV2Props {
  selectedRange: MeasureRange | null;
  onGenerate: (config: DrumGenerationConfig) => void;
  busy: boolean;
  lockedSections?: Set<string>;
}

export const DrumBuilderPanelV2: React.FC<DrumBuilderPanelV2Props> = ({
  selectedRange,
  onGenerate,
  busy,
  lockedSections = new Set()
}) => {
  // Existing settings
  const [style, setStyle] = useState('rock');
  const [drummer, setDrummer] = useState('jeff_porcaro');
  const [intensity, setIntensity] = useState(70);
  const [variation, setVariation] = useState(80);
  const [generationMode, setGenerationMode] = useState<'template' | 'ai_variation' | 'full_ai'>('ai_variation');
  const [humanize, setHumanize] = useState(true);
  const [fillType, setFillType] = useState('auto');
  const [fillFrequency, setFillFrequency] = useState<FillFrequencyOption>('section_transitions');
  const [fillDensity, setFillDensity] = useState(70);
  
  // NEW v2.0 settings
  const [humanizeAmount, setHumanizeAmount] = useState(70);
  const [ghostNoteAmount, setGhostNoteAmount] = useState(70);
  const [swingAmount, setSwingAmount] = useState(0);
  const [buildScope, setBuildScope] = useState<'full_song' | 'selected_section'>('selected_section');
  const [guideEnabled, setGuideEnabled] = useState(false);
  const [guideInstrument, setGuideInstrument] = useState<'mix' | 'bass' | 'guitar' | 'keys' | 'vocal'>('mix');

  // Rudiment/Fills controls
  const [rudimentsEnabled, setRudimentsEnabled] = useState(true);
  const [rudimentDensity, setRudimentDensity] = useState(70);
  const [rudimentFamilies, setRudimentFamilies] = useState<string[]>([]);
  const [preferredRudimentId, setPreferredRudimentId] = useState('');
  const [ensureDownbeatKick, setEnsureDownbeatKick] = useState(true);
  const [preserveHatTail, setPreserveHatTail] = useState(true);
  const [rudimentHandLead, setRudimentHandLead] = useState<RudimentHandLead>('auto');
  const [rudimentBlocks, setRudimentBlocks] = useState<RudimentBlockDraft[]>([]);
  const getBlocksForSection = useRudimentBlockStore((state) => state.getBlocksForSection);
  const setBlocksForSection = useRudimentBlockStore((state) => state.setBlocksForSection);
  const clearSectionBlocks = useRudimentBlockStore((state) => state.clearSectionBlocks);
  
  // Show advanced controls toggle
  const [showAdvanced, setShowAdvanced] = useState(false);

  const toggleRudimentFamily = (family: string) => {
    setRudimentFamilies((prev) =>
      prev.includes(family)
        ? prev.filter((f) => f !== family)
        : [...prev, family]
    );
  };

  const clampOffset = (value: number) => {
    if (!selectedRange) return 0;
    const maxOffset = Math.max(0, selectedRange.measureCount - 1);
    return Math.min(Math.max(0, Math.floor(value)), maxOffset);
  };

  const clampLength = (value: number, offsetOverride?: number) => {
    if (!selectedRange) return 1;
    const maxBars = Math.max(1, selectedRange.measureCount);
    const offset = clampOffset(offsetOverride ?? 0);
    const maxLength = Math.max(1, Math.min(maxBars - offset, maxBars));
    return Math.min(Math.max(1, Math.floor(value)), maxLength);
  };

  const serializeRudimentBlock = (block: RudimentBlockDraft): RudimentBlock => ({
    blockId: block.blockId,
    startBar: clampOffset(block.offset),
    lengthBars: clampLength(block.length, block.offset),
    families: block.families,
    rudimentId: block.rudimentId || undefined,
    density: block.density,
    ensureDownbeatKick: block.ensureDownbeatKick,
    preserveHatTail: block.preserveHatTail,
  });

  const addRudimentBlock = () => {
    if (!selectedRange) return;
    const defaultLength = Math.min(4, Math.max(1, selectedRange.measureCount));
    const block: RudimentBlockDraft = {
      blockId: `block-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      offset: 0,
      length: defaultLength,
      families: [],
      rudimentId: ''
    };
    setRudimentBlocks((prev) => [...prev, block]);
  };

  const updateRudimentBlock = (blockId: string, patch: Partial<RudimentBlockDraft>) => {
    setRudimentBlocks((prev) =>
      prev.map((block) => {
        if (block.blockId !== blockId) return block;
        let next: RudimentBlockDraft = { ...block, ...patch } as RudimentBlockDraft;
        if ('offset' in patch && selectedRange) {
          next.offset = clampOffset(patch.offset ?? block.offset);
        }
        if ('length' in patch && selectedRange) {
          next.length = clampLength(patch.length ?? block.length, next.offset);
        }
        if (!('length' in patch) && 'offset' in patch && selectedRange) {
          next.length = clampLength(next.length, next.offset);
        }
        return next;
      })
    );
  };

  const toggleBlockFamily = (blockId: string, family: string) => {
    setRudimentBlocks((prev) =>
      prev.map((block) =>
        block.blockId === blockId
          ? {
              ...block,
              families: block.families.includes(family)
                ? block.families.filter((f) => f !== family)
                : [...block.families, family]
            }
          : block
      )
    );
  };

  const removeRudimentBlock = (blockId: string) => {
    setRudimentBlocks((prev) => prev.filter((block) => block.blockId !== blockId));
  };

  useEffect(() => {
    if (!selectedRange) {
      setRudimentBlocks([]);
      return;
    }
    setRudimentBlocks((prev) =>
      prev.map((block) => {
        const offset = clampOffset(block.offset);
        const length = clampLength(block.length, offset);
        return { ...block, offset, length };
      })
    );
  }, [selectedRange?.measureCount]);

  useEffect(() => {
    if (!selectedRange?.sectionId) {
      setRudimentBlocks([]);
      return;
    }
    const savedBlocks = getBlocksForSection(selectedRange.sectionId);
    if (!savedBlocks?.length) {
      setRudimentBlocks([]);
      return;
    }
    setRudimentBlocks(
      savedBlocks.map((block) => ({
        blockId: block.blockId,
        offset: clampOffset(block.startBar),
        length: clampLength(block.lengthBars, block.startBar),
        families: block.families || [],
        rudimentId: block.rudimentId || '',
        density: block.density,
        ensureDownbeatKick: block.ensureDownbeatKick,
        preserveHatTail: block.preserveHatTail,
      }))
    );
  }, [selectedRange?.sectionId, selectedRange?.measureCount, getBlocksForSection]);

  useEffect(() => {
    if (!selectedRange?.sectionId) {
      return;
    }
    if (!rudimentBlocks.length) {
      clearSectionBlocks(selectedRange.sectionId);
      return;
    }
    const serialized = rudimentBlocks.map(serializeRudimentBlock);
    setBlocksForSection(selectedRange.sectionId, serialized);
  }, [rudimentBlocks, selectedRange?.sectionId, selectedRange?.measureCount, setBlocksForSection, clearSectionBlocks]);

  const styles = [
    { value: 'rock', label: 'Rock', icon: '🎸' },
    { value: 'funk', label: 'Funk', icon: '🎺' },
    { value: 'jazz', label: 'Jazz', icon: '🎷' },
    { value: 'latin', label: 'Latin', icon: '🎵' },
    { value: 'metal', label: 'Metal', icon: '⚡' },
    { value: 'pop', label: 'Pop', icon: '✨' }
  ];

  const drummersByStyle: Record<string, Array<{value: string, label: string}>> = {
    rock: [
      { value: 'jeff_porcaro', label: 'Jeff Porcaro' },
      { value: 'john_bonham', label: 'John Bonham' },
      { value: 'dave_grohl', label: 'Dave Grohl' },
      { value: 'neil_peart', label: 'Neil Peart' }
    ],
    funk: [
      { value: 'bernard_purdie', label: 'Bernard Purdie' },
      { value: 'clyde_stubblefield', label: 'Clyde Stubblefield' },
      { value: 'david_garibaldi', label: 'David Garibaldi' }
    ],
    jazz: [
      { value: 'buddy_rich', label: 'Buddy Rich' },
      { value: 'tony_williams', label: 'Tony Williams' },
      { value: 'elvin_jones', label: 'Elvin Jones' }
    ],
    latin: [
      { value: 'tito_puente', label: 'Tito Puente' },
      { value: 'poncho_sanchez', label: 'Poncho Sanchez' }
    ],
    metal: [
      { value: 'lars_ulrich', label: 'Lars Ulrich' },
      { value: 'dave_lombardo', label: 'Dave Lombardo' }
    ],
    pop: [
      { value: 'steve_gadd', label: 'Steve Gadd' },
      { value: 'vinnie_colaiuta', label: 'Vinnie Colaiuta' }
    ]
  };

  const fillTypes = [
    { value: 'auto', label: 'Auto (Context-Aware)' },
    { value: 'tom_run', label: 'Tom Run' },
    { value: 'crash_buildup', label: 'Crash Buildup' },
    { value: 'snare_buzz', label: 'Snare Buzz Roll' },
    { value: 'edm_riser', label: 'EDM Riser' },
    { value: 'none', label: 'No Fill' }
  ];

  const fillFrequencies = [
    { value: 'section_transitions', label: 'Section transitions' },
    { value: 'all_transitions', label: 'All transitions' },
    { value: 'every_4_bars', label: 'Every 4 bars' },
    { value: 'none', label: 'Never (disable fills)' }
  ];

  const rudimentFamilyOptions = [
    { value: 'snare', label: 'Snare rudiments' },
    { value: 'tom_run', label: 'Tom runs' },
    { value: 'hybrid', label: 'Hybrid/stackers' },
    { value: 'linear', label: 'Linear phrasing' }
  ];

  const guideInstrumentOptions: Array<{ value: typeof guideInstrument; label: string }> = [
    { value: 'mix', label: 'Full Mix' },
    { value: 'bass', label: 'Bass Guitar' },
    { value: 'guitar', label: 'Guitars' },
    { value: 'keys', label: 'Keys/Synths' },
    { value: 'vocal', label: 'Vocals' }
  ];

  const handleGenerate = () => {
    if (!selectedRange) {
      console.warn('DrumBuilderPanelV2: Cannot generate without a selected range');
      return;
    }

    const fillLocations = fillType === 'none' ? [] : [selectedRange.measureCount - 1];

    const fillControls = {
      fillType,
      density: fillDensity / 100,
      frequency: fillType === 'none' ? 'none' : fillFrequency
    } as const;

    const rudimentControls = rudimentsEnabled
      ? {
          enabled: true,
          preferredFamilies: rudimentFamilies,
          preferredRudiments: preferredRudimentId ? [preferredRudimentId] : [],
          density: rudimentDensity / 100,
          ensureDownbeatKick,
          preserveHatTail,
          handLead: rudimentHandLead
        }
      : undefined;

    const blocksPayload = rudimentsEnabled && rudimentBlocks.length
      ? rudimentBlocks.map(serializeRudimentBlock)
      : undefined;

    const rangeContext = {
      sectionId: selectedRange.sectionId,
      startMeasure: selectedRange.startMeasure,
      endMeasure: selectedRange.endMeasure,
      tempos: selectedRange.tempos?.length ? selectedRange.tempos : [selectedRange.avgTempo],
      timeSignature: selectedRange.timeSignature,
    } as const;

    if (!rangeContext.sectionId) {
      console.warn('DrumBuilderPanelV2: Selected range is missing sectionId');
      return;
    }

    const baseConfig: DrumGenerationConfig = {
      ...rangeContext,
      style,
      drummer,
      intensity: intensity / 100,
      variation: variation / 100,
      generationMode,
      humanize,
      fillLocations,
      fillType,
      fillDensity: fillDensity / 100,
      fillControls,
      humanizeAmount: humanizeAmount / 100,
      ghostNoteAmount: ghostNoteAmount / 100,
      swingAmount: swingAmount / 100,
      buildScope,
      guideEnabled,
      guideInstrument: guideEnabled ? guideInstrument : undefined,
      rudimentControls,
      rudimentBlocks: blocksPayload,
    };

    onGenerate(baseConfig);
  };

  if (!selectedRange) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 text-center">
        <div className="text-4xl mb-3">🥁</div>
        <h3 className="text-lg font-semibold text-slate-200 mb-2">No Section Selected</h3>
        <p className="text-sm text-slate-400">
          Click on a section in the timeline above to start building drums
        </p>
      </div>
    );
  }

  const isLocked = lockedSections.has(selectedRange.sectionId);

  return (
    <div className="bg-slate-800 rounded-lg p-4 space-y-4 max-h-[80vh] overflow-y-auto">
      {/* Header with v2.0 badge */}
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-bold text-white">Drum Builder</h2>
        <span className="text-xs font-bold bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-2 py-1 rounded">
          v2.0
        </span>
      </div>

      {/* Selected Range Info */}
      <div className="bg-gradient-to-r from-blue-900/40 to-purple-900/40 rounded-lg p-4 border border-blue-700/50">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-bold text-white">
            {selectedRange.sectionLabel}
          </h3>
          <div className="flex items-center space-x-2">
            {isLocked && (
              <span className="text-xs text-yellow-400 bg-yellow-900/30 px-2 py-1 rounded flex items-center">
                🔒 Locked
              </span>
            )}
            <span className="text-xs text-blue-300 bg-blue-900/50 px-2 py-1 rounded">
              {selectedRange.measureCount} measures
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-slate-400">Measures:</span>
            <span className="ml-2 text-white font-semibold">
              {selectedRange.startMeasure + 1}-{selectedRange.endMeasure + 1}
            </span>
          </div>
          <div>
            <span className="text-slate-400">Avg Tempo:</span>
            <span className="ml-2 text-white font-semibold">
              {selectedRange.avgTempo.toFixed(0)} BPM
            </span>
          </div>
        </div>
      </div>

      {/* Style Selection */}
      <div>
        <label className="block text-sm font-semibold text-slate-300 mb-2">
          Style
        </label>
        <div className="grid grid-cols-3 gap-2">
          {styles.map((s) => (
            <button
              key={s.value}
              onClick={() => {
                setStyle(s.value);
                if (drummersByStyle[s.value]) {
                  setDrummer(drummersByStyle[s.value][0].value);
                }
              }}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                style === s.value
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              <span className="mr-1">{s.icon}</span>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Drummer Selection */}
      <div>
        <label className="block text-sm font-semibold text-slate-300 mb-2">
          Drummer
        </label>
        <select
          value={drummer}
          onChange={(e) => setDrummer(e.target.value)}
          className="w-full px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none"
        >
          {drummersByStyle[style]?.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
      </div>

      {/* Intensity & Variation */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-xs font-semibold text-slate-300">
              Intensity
            </label>
            <span className="text-xs font-bold text-white bg-slate-700 px-2 py-0.5 rounded">
              {intensity}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={intensity}
            onChange={(e) => setIntensity(Number(e.target.value))}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-600"
          />
        </div>
        
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-xs font-semibold text-slate-300">
              Variation
            </label>
            <span className="text-xs font-bold text-white bg-slate-700 px-2 py-0.5 rounded">
              {variation}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={variation}
            onChange={(e) => setVariation(Number(e.target.value))}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
          />
        </div>
      </div>

      {/* Humanize Toggle & Amount */}
      <div className="bg-gradient-to-r from-purple-900/30 to-pink-900/30 rounded-lg p-3 border border-purple-700/30">
        <label className="flex items-center cursor-pointer mb-3">
          <input
            type="checkbox"
            checked={humanize}
            onChange={(e) => setHumanize(e.target.checked)}
            className="mr-3 w-5 h-5 accent-purple-600"
          />
          <div className="flex-1">
            <div className="font-medium text-white flex items-center">
              🎭 Humanize
              <span className="ml-2 text-xs bg-purple-600 px-2 py-0.5 rounded">NEW</span>
            </div>
            <div className="text-xs text-slate-400">
              LLM-driven performance layer
            </div>
          </div>
        </label>

        {humanize && (
          <div className="space-y-3 pl-8">
            {/* Humanize Amount */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-300">
                  Humanize Amount
                </label>
                <span className="text-xs font-bold text-white bg-purple-900/50 px-2 py-0.5 rounded">
                  {humanizeAmount}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={humanizeAmount}
                onChange={(e) => setHumanizeAmount(Number(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-0.5">
                <span>Tight</span>
                <span>Loose</span>
              </div>
            </div>

            {/* Ghost Notes */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-300">
                  Ghost Notes
                </label>
                <span className="text-xs font-bold text-white bg-purple-900/50 px-2 py-0.5 rounded">
                  {ghostNoteAmount}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={ghostNoteAmount}
                onChange={(e) => setGhostNoteAmount(Number(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-pink-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-0.5">
                <span>Minimal</span>
                <span>Dense</span>
              </div>
            </div>

            {/* Swing */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-300">
                  Swing Feel
                </label>
                <span className="text-xs font-bold text-white bg-purple-900/50 px-2 py-0.5 rounded">
                  {swingAmount}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={swingAmount}
                onChange={(e) => setSwingAmount(Number(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-0.5">
                <span>Straight</span>
                <span>Swung</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Advanced Controls Toggle */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="w-full py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium rounded-lg transition-colors flex items-center justify-center"
      >
        <span className="mr-2">{showAdvanced ? '▼' : '▶'}</span>
        {showAdvanced ? 'Hide' : 'Show'} Advanced Options
      </button>

      {showAdvanced && (
        <div className="space-y-4 p-3 bg-slate-900/50 rounded-lg border border-slate-700">
          {/* Fill Dynamics */}
          <div className="grid grid-cols-1 gap-3">
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-sm font-semibold text-slate-300">Fill Energy</label>
                <span className="text-xs font-bold text-white bg-slate-800 px-2 py-0.5 rounded">
                  {fillDensity}%
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={fillDensity}
                onChange={(e) => setFillDensity(Number(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-0.5">
                <span>Ghosty</span>
                <span>Explosive</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">Fill Frequency</label>
              <select
                value={fillFrequency}
                onChange={(e) => setFillFrequency(e.target.value as FillFrequencyOption)}
                className="w-full px-3 py-2 bg-slate-700 text-white text-sm rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none"
              >
                {fillFrequencies.map((freq) => (
                  <option key={freq.value} value={freq.value}>
                    {freq.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Fill Selection */}
          <div>
            <label className="block text-sm font-semibold text-slate-300 mb-2">
              Fill (End of Section)
            </label>
            <select
              value={fillType}
              onChange={(e) => setFillType(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 text-white text-sm rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none"
            >
              {fillTypes.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>

          {/* Guide Track Influence */}
          <div className="p-3 rounded-lg border border-emerald-700/40 bg-emerald-900/10 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-white">Guide Track Influence</p>
                <p className="text-xs text-slate-300">Derive power curve from uploaded audio</p>
              </div>
              <label className="flex items-center text-xs text-slate-200">
                <input
                  type="checkbox"
                  className="mr-2 accent-emerald-500"
                  checked={guideEnabled}
                  onChange={(event) => setGuideEnabled(event.target.checked)}
                />
                Use Guide Track
              </label>
            </div>

            {guideEnabled ? (
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300">
                  Dominant Instrument
                </label>
                <select
                  value={guideInstrument}
                  onChange={(event) => setGuideInstrument(event.target.value as typeof guideInstrument)}
                  className="w-full px-3 py-2 bg-slate-800 text-white rounded border border-emerald-600 focus:border-emerald-400 focus:outline-none text-sm"
                >
                  {guideInstrumentOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-emerald-200/80">
                  Helps the builder align crescendos and breakdowns with the chosen stem emphasis.
                </p>
              </div>
            ) : (
              <p className="text-[11px] text-slate-400">
                Enable to let Drum Builder match the energy curve of your uploaded track or stems.
              </p>
            )}
          </div>

          {/* Rudiment Engine */}
          <div className="p-3 rounded-lg border border-purple-700/40 bg-purple-900/20 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-white">Rudiment Engine</p>
                <p className="text-xs text-slate-300">Limb-aware fills on marked bars</p>
              </div>
              <label className="flex items-center text-sm text-slate-200">
                <input
                  type="checkbox"
                  className="mr-2 accent-purple-500"
                  checked={rudimentsEnabled}
                  onChange={(e) => setRudimentsEnabled(e.target.checked)}
                />
                Enable
              </label>
            </div>

            {rudimentsEnabled && (
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs font-semibold text-slate-300">Rudiment Energy</label>
                    <span className="text-xs font-bold text-white bg-purple-900/60 px-2 py-0.5 rounded">
                      {rudimentDensity}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={rudimentDensity}
                    onChange={(e) => setRudimentDensity(Number(e.target.value))}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-400"
                  />
                </div>

                <div>
                  <p className="text-xs font-semibold text-slate-300 mb-1">Preferred Families</p>
                  <div className="grid grid-cols-2 gap-2">
                    {rudimentFamilyOptions.map((family) => (
                      <button
                        key={family.value}
                        type="button"
                        onClick={() => toggleRudimentFamily(family.value)}
                        className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
                          rudimentFamilies.includes(family.value)
                            ? 'bg-purple-600/60 border-purple-300 text-white'
                            : 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700'
                        }`}
                      >
                        {family.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-200">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      className="accent-purple-500"
                      checked={ensureDownbeatKick}
                      onChange={(e) => setEnsureDownbeatKick(e.target.checked)}
                    />
                    <span>Keep kick on beat 1</span>
                  </label>
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      className="accent-purple-500"
                      checked={preserveHatTail}
                      onChange={(e) => setPreserveHatTail(e.target.checked)}
                    />
                    <span>Carry hat tail</span>
                  </label>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <label className="block mb-1 text-slate-300">Hand Lead</label>
                    <select
                      value={rudimentHandLead}
                      onChange={(e) => setRudimentHandLead(e.target.value as RudimentHandLead)}
                      className="w-full px-2 py-1 bg-slate-800 text-white rounded border border-slate-600"
                    >
                      <option value="auto">Auto</option>
                      <option value="left">Left-hand lead</option>
                      <option value="right">Right-hand lead</option>
                    </select>
                  </div>
                  <div>
                    <label className="block mb-1 text-slate-300">Pin Rudiment ID (optional)</label>
                    <input
                      type="text"
                      value={preferredRudimentId}
                      onChange={(e) => setPreferredRudimentId(e.target.value)}
                      placeholder="e.g. paradiddle_migration"
                      className="w-full px-2 py-1 bg-slate-800 text-white rounded border border-slate-600 placeholder-slate-500"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-300">Rudiment Blocks</p>
                      <p className="text-[11px] text-slate-400">
                        Reserve specific measures for signature fills
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={addRudimentBlock}
                      disabled={!selectedRange}
                      className="text-xs px-2 py-1 rounded border border-purple-400 text-purple-200 disabled:opacity-40"
                    >
                      + Add Block
                    </button>
                  </div>

                  {rudimentBlocks.length === 0 ? (
                    <p className="text-[11px] text-slate-500">
                      No blocks yet. Add one to pin a paradiddle or tom run across a bar range.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {rudimentBlocks.map((block) => {
                        const absoluteStart = (selectedRange?.startMeasure ?? 0) + block.offset + 1;
                        const absoluteEnd = absoluteStart + block.length - 1;
                        return (
                          <div
                            key={block.blockId}
                            className="bg-slate-800/60 border border-slate-600 rounded p-2 space-y-2"
                          >
                            <div className="flex items-center justify-between text-xs text-slate-200">
                              <div className="space-x-2 flex items-center">
                                <label>
                                  Start
                                  <input
                                    type="number"
                                    min={1}
                                    max={selectedRange?.measureCount ?? 1}
                                    value={block.offset + 1}
                                    onChange={(e) =>
                                      updateRudimentBlock(block.blockId, {
                                        offset: Number(e.target.value) - 1,
                                      })
                                    }
                                    className="w-16 ml-1 px-1 py-0.5 bg-slate-900 border border-slate-600 rounded"
                                  />
                                </label>
                                <label>
                                  Length
                                  <input
                                    type="number"
                                    min={1}
                                    max={selectedRange?.measureCount ?? 1}
                                    value={block.length}
                                    onChange={(e) =>
                                      updateRudimentBlock(block.blockId, {
                                        length: Number(e.target.value),
                                      })
                                    }
                                    className="w-16 ml-1 px-1 py-0.5 bg-slate-900 border border-slate-600 rounded"
                                  />
                                </label>
                                <span className="text-[11px] text-slate-400">
                                  Measures {absoluteStart}-{absoluteEnd}
                                </span>
                              </div>
                              <button
                                type="button"
                                aria-label="Remove rudiment block"
                                className="text-slate-400 hover:text-red-400"
                                onClick={() => removeRudimentBlock(block.blockId)}
                              >
                                ✕
                              </button>
                            </div>

                            <div className="text-[11px] text-slate-300 space-y-1">
                              <p className="font-semibold">Families</p>
                              <div className="grid grid-cols-2 gap-1">
                                {rudimentFamilyOptions.map((family) => (
                                  <button
                                    key={`${block.blockId}-${family.value}`}
                                    type="button"
                                    onClick={() => toggleBlockFamily(block.blockId, family.value)}
                                    className={`px-2 py-0.5 rounded border text-[11px] ${
                                      block.families.includes(family.value)
                                        ? 'bg-purple-600/60 border-purple-300 text-white'
                                        : 'bg-slate-900 border-slate-600 text-slate-300 hover:bg-slate-800'
                                    }`}
                                  >
                                    {family.label}
                                  </button>
                                ))}
                              </div>
                            </div>

                            <div className="text-[11px] text-slate-300">
                              <label className="block font-semibold mb-1">Pinned Rudiment</label>
                              <input
                                type="text"
                                value={block.rudimentId}
                                onChange={(e) =>
                                  updateRudimentBlock(block.blockId, { rudimentId: e.target.value })
                                }
                                placeholder="e.g. swiss_triplet_stack"
                                className="w-full px-2 py-1 bg-slate-900 border border-slate-600 rounded placeholder-slate-500"
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Generation Mode */}
          <div>
            <label className="block text-sm font-semibold text-slate-300 mb-2">
              Generation Mode
            </label>
            <div className="space-y-2">
              {[
                { value: 'template', label: '⚡ Fast Template', desc: '~50ms' },
                { value: 'ai_variation', label: '🎨 AI Variation', desc: '~1s' },
                { value: 'full_ai', label: '🤖 Full AI', desc: '~3s' }
              ].map((mode) => (
                <label key={mode.value} className="flex items-center p-2 bg-slate-700 rounded cursor-pointer hover:bg-slate-600">
                  <input
                    type="radio"
                    name="mode"
                    value={mode.value}
                    checked={generationMode === mode.value}
                    onChange={(e) => setGenerationMode(e.target.value as any)}
                    className="mr-2"
                  />
                  <div className="flex-1 flex items-center justify-between">
                    <span className="text-white text-sm">{mode.label}</span>
                    <span className="text-xs text-slate-400">{mode.desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Build Scope */}
          <div>
            <label className="block text-sm font-semibold text-slate-300 mb-2">
              Build Scope
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setBuildScope('selected_section')}
                className={`px-3 py-2 rounded text-sm ${
                  buildScope === 'selected_section'
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                This Section
              </button>
              <button
                onClick={() => setBuildScope('full_song')}
                className={`px-3 py-2 rounded text-sm ${
                  buildScope === 'full_song'
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                Full Song
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Generate Button */}
      <button
        onClick={handleGenerate}
        disabled={busy || isLocked}
        className="w-full py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 disabled:from-slate-600 disabled:to-slate-700 text-white font-bold text-lg rounded-lg shadow-xl transition-all transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"
      >
        {busy ? (
          <>
            <span className="inline-block animate-spin mr-2">⏳</span>
            Generating Drums...
          </>
        ) : isLocked ? (
          <>
            <span className="mr-2">🔒</span>
            Section Locked
          </>
        ) : (
          <>
            <span className="mr-2">🎵</span>
            Generate Section Specific Track
          </>
        )}
      </button>

      {/* Info Footer */}
      <div className="text-xs text-slate-500 text-center pt-2 border-t border-slate-700">
        💡 v2.0 features: LLM-driven micro-timing, per-note control, 960 PPQ resolution
      </div>
    </div>
  );
};

export default DrumBuilderPanelV2;
