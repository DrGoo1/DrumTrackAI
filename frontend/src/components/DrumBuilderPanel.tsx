/**
 * Drum Builder Panel - Main control interface for drum generation
 * Integrates with all existing analytics and generation tools
 */
import React, { useState } from 'react';
import type { DrumBrainConfig } from '../types/brain';

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

interface DrumBuilderPanelProps {
  selectedRange: MeasureRange | null;
  onGenerate: (config: DrumGenerationConfig) => void;
  busy: boolean;
}

export interface DrumGenerationConfig {
  sectionId: string;
  startMeasure: number;
  endMeasure: number;
  tempos: number[];
  timeSignature: [number, number];
  style: string;
  drummer: string;
  intensity: number;
  variation: number;
  generationMode: 'template' | 'ai_variation' | 'full_ai';
  humanize: boolean;
  fillLocations: number[];
  fillType: string;
  brainConfig?: DrumBrainConfig;
}

export const DrumBuilderPanel: React.FC<DrumBuilderPanelProps> = ({
  selectedRange,
  onGenerate,
  busy
}) => {
  // Generation settings
  const [style, setStyle] = useState('rock');
  const [drummer, setDrummer] = useState('jeff_porcaro');
  const [intensity, setIntensity] = useState(70);
  const [variation, setVariation] = useState(80);
  const [generationMode, setGenerationMode] = useState<'template' | 'ai_variation' | 'full_ai'>('ai_variation');
  const [humanize, setHumanize] = useState(true);
  const [fillType, setFillType] = useState('auto');

  // Style options
  const styles = [
    { value: 'rock', label: 'Rock', icon: '🎸' },
    { value: 'funk', label: 'Funk', icon: '🎺' },
    { value: 'jazz', label: 'Jazz', icon: '🎷' },
    { value: 'latin', label: 'Latin', icon: '🎵' },
    { value: 'metal', label: 'Metal', icon: '⚡' },
    { value: 'pop', label: 'Pop', icon: '✨' }
  ];

  // Drummer options by style
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

  // Fill options
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

    // Determine fill locations (end of section by default)
    const fillLocations = fillType === 'none' ? [] : [selectedRange.measureCount - 1];

    const config: DrumGenerationConfig = {
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
      fillType
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

  return (
    <div className="bg-slate-800 rounded-lg p-4 space-y-4">
      {/* Selected Range Info */}
      <div className="bg-gradient-to-r from-blue-900/40 to-purple-900/40 rounded-lg p-4 border border-blue-700/50">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-bold text-white">
            {selectedRange.sectionLabel}
          </h3>
          <span className="text-xs text-blue-300 bg-blue-900/50 px-2 py-1 rounded">
            {selectedRange.measureCount} measures
          </span>
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
          <div>
            <span className="text-slate-400">Time Sig:</span>
            <span className="ml-2 text-white font-semibold">
              {selectedRange.timeSignature[0]}/{selectedRange.timeSignature[1]}
            </span>
          </div>
          <div>
            <span className="text-slate-400">Tempo Range:</span>
            <span className="ml-2 text-white font-semibold">
              {Math.min(...selectedRange.tempos).toFixed(0)}-{Math.max(...selectedRange.tempos).toFixed(0)}
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
                // Reset drummer to first in new style
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

      {/* Intensity Slider */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="text-sm font-semibold text-slate-300">
            Intensity
          </label>
          <span className="text-sm font-bold text-white bg-slate-700 px-2 py-1 rounded">
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
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>Minimal</span>
          <span>Heavy</span>
        </div>
      </div>

      {/* Variation Slider */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="text-sm font-semibold text-slate-300">
            Variation
          </label>
          <span className="text-sm font-bold text-white bg-slate-700 px-2 py-1 rounded">
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
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>Repetitive</span>
          <span>Unique</span>
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
          className="w-full px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none"
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
        <label className="block text-sm font-semibold text-slate-300 mb-3">
          Generation Mode
        </label>
        <div className="space-y-2">
          <label className="flex items-center p-3 bg-slate-700 rounded-lg cursor-pointer hover:bg-slate-600 transition-colors">
            <input
              type="radio"
              name="mode"
              value="template"
              checked={generationMode === 'template'}
              onChange={(e) => setGenerationMode(e.target.value as any)}
              className="mr-3"
            />
            <div className="flex-1">
              <div className="font-medium text-white">⚡ Fast Template</div>
              <div className="text-xs text-slate-400">Pre-computed pattern (~50ms)</div>
            </div>
          </label>

          <label className="flex items-center p-3 bg-slate-700 rounded-lg cursor-pointer hover:bg-slate-600 transition-colors">
            <input
              type="radio"
              name="mode"
              value="ai_variation"
              checked={generationMode === 'ai_variation'}
              onChange={(e) => setGenerationMode(e.target.value as any)}
              className="mr-3"
            />
            <div className="flex-1">
              <div className="font-medium text-white">🎨 AI Variation (Recommended)</div>
              <div className="text-xs text-slate-400">GrooVAE variation (~1s)</div>
            </div>
          </label>

          <label className="flex items-center p-3 bg-slate-700 rounded-lg cursor-pointer hover:bg-slate-600 transition-colors">
            <input
              type="radio"
              name="mode"
              value="full_ai"
              checked={generationMode === 'full_ai'}
              onChange={(e) => setGenerationMode(e.target.value as any)}
              className="mr-3"
            />
            <div className="flex-1">
              <div className="font-medium text-white">🤖 Full AI Generation</div>
              <div className="text-xs text-slate-400">Complete AI composition (~3s)</div>
            </div>
          </label>
        </div>
      </div>

      {/* Humanize Toggle */}
      <label className="flex items-center p-3 bg-slate-700 rounded-lg cursor-pointer">
        <input
          type="checkbox"
          checked={humanize}
          onChange={(e) => setHumanize(e.target.checked)}
          className="mr-3 w-5 h-5 accent-purple-600"
        />
        <div className="flex-1">
          <div className="font-medium text-white">🎭 Humanize</div>
          <div className="text-xs text-slate-400">
            Add timing/velocity variations for natural feel
          </div>
        </div>
      </label>

      {/* Generate Button */}
      <button
        onClick={handleGenerate}
        disabled={busy}
        className="w-full py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 disabled:from-slate-600 disabled:to-slate-700 text-white font-bold text-lg rounded-lg shadow-xl transition-all transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"
      >
        {busy ? (
          <>
            <span className="inline-block animate-spin mr-2">⏳</span>
            Generating Drums...
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
        💡 Generated drums adapt to per-measure tempo changes automatically
      </div>
    </div>
  );
};

export default DrumBuilderPanel;
