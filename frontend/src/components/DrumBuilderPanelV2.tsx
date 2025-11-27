/**
 * Drum Builder Panel v2.0 - Enhanced with new performance controls
 * Integrates Drum Builder v2.0 features with existing UI
 */
import React, { useState } from 'react';
import { DrumGenerationConfig } from '../types/drumTrack';

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
  
  // NEW v2.0 settings
  const [humanizeAmount, setHumanizeAmount] = useState(70);
  const [ghostNoteAmount, setGhostNoteAmount] = useState(70);
  const [swingAmount, setSwingAmount] = useState(0);
  const [buildScope, setBuildScope] = useState<'full_song' | 'selected_section'>('selected_section');
  const [guideEnabled, setGuideEnabled] = useState(false);
  const [guideInstrument, setGuideInstrument] = useState<'mix' | 'bass' | 'guitar' | 'keys' | 'vocal'>('mix');
  
  // Show advanced controls toggle
  const [showAdvanced, setShowAdvanced] = useState(false);

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

  const handleGenerate = () => {
    if (!selectedRange) return;

    const fillLocations = fillType === 'none' ? [] : [selectedRange.measureCount - 1];

    const config: DrumGenerationConfig = {
      // Required fields
      sectionId: selectedRange.sectionId,
      startMeasure: selectedRange.startMeasure,
      endMeasure: selectedRange.endMeasure,
      tempos: selectedRange.tempos,
      timeSignature: selectedRange.timeSignature,
      style,
      drummer,
      intensity: intensity / 100,
      variation: variation / 100,
      generationMode,
      humanize,
      fillLocations,
      fillType,
      
      // NEW v2.0 fields
      humanizeAmount: humanizeAmount / 100,
      ghostNoteAmount: ghostNoteAmount / 100,
      swingAmount: swingAmount / 100,
      buildScope,
      guideEnabled,
      guideInstrument
    };

    onGenerate(config);
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
            Generate Drums
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
