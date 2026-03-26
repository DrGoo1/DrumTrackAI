/**
 * Re-Humanization Panel - Client-side drum track adjustments
 * Part of Drum Builder v2.0 - Phase 5
 */
import React, { useState, useEffect } from 'react';
import {
  rehumanizeTrack,
  adjustGroove,
  RehumanizeParams,
  GrooveAdjustment,
  REHUMANIZE_PRESETS,
  rehumanizeSelection
} from '../utils/rehumanize';
import { DrumTrackForDCSM } from '../types/drumTrack';

interface RehumanizePanelProps {
  track: DrumTrackForDCSM | null;
  selectedNoteIds?: Set<string>;
  onTrackUpdate: (track: DrumTrackForDCSM) => void;
  className?: string;
}

export const RehumanizePanel: React.FC<RehumanizePanelProps> = ({
  track,
  selectedNoteIds,
  onTrackUpdate,
  className = ''
}) => {
  // Re-humanize parameters
  const [microTimingAmount, setMicroTimingAmount] = useState(50);
  const [velocityAmount, setVelocityAmount] = useState(50);
  const [swingAmount, setSwingAmount] = useState(0);
  const [ghostNoteAmount, setGhostNoteAmount] = useState(50);
  const [tightenLoosen, setTightenLoosen] = useState(0);
  
  // Groove parameters
  const [laidBack, setLaidBack] = useState(0);
  const [pocketDepth, setPocketDepth] = useState(0);
  
  // UI state
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [showGroove, setShowGroove] = useState(false);
  
  // Original track for reset
  const [originalTrack, setOriginalTrack] = useState<DrumTrackForDCSM | null>(null);

  // Store original track when track changes
  useEffect(() => {
    if (track && !originalTrack) {
      setOriginalTrack(track);
    }
  }, [track, originalTrack]);

  const hasSelection = selectedNoteIds && selectedNoteIds.size > 0;

  const getParams = (): RehumanizeParams => ({
    microTimingAmount: microTimingAmount / 100,
    velocityAmount: velocityAmount / 100,
    swingAmount: swingAmount / 100,
    ghostNoteAmount: ghostNoteAmount / 100,
    tightenLoosen: tightenLoosen / 100,
    seed: Array.from(String(track?.track_id || '')).reduce((acc, ch) => (acc * 31 + ch.charCodeAt(0)) >>> 0, 0)
  });

  const getGrooveParams = (): GrooveAdjustment => ({
    laidBack: laidBack / 100,
    pocketDepth: pocketDepth / 100
  });

  const handleApply = () => {
    if (!track) return;

    let newTrack = track;
    const params = getParams();

    // Apply to selection or entire track
    if (hasSelection && selectedNoteIds) {
      newTrack = rehumanizeSelection(track, selectedNoteIds, params);
    } else {
      newTrack = rehumanizeTrack(track, params);
    }

    // Apply groove if enabled
    if (showGroove) {
      newTrack = adjustGroove(newTrack, getGrooveParams());
    }

    onTrackUpdate(newTrack);
  };

  const handleReset = () => {
    if (originalTrack) {
      onTrackUpdate(originalTrack);
      setOriginalTrack(null);
    }
  };

  const handlePreset = (presetName: string) => {
    const preset = REHUMANIZE_PRESETS[presetName];
    if (!preset) return;

    setMicroTimingAmount(preset.microTimingAmount * 100);
    setVelocityAmount(preset.velocityAmount * 100);
    setSwingAmount(preset.swingAmount * 100);
    setGhostNoteAmount(preset.ghostNoteAmount * 100);
    setTightenLoosen(preset.tightenLoosen * 100);
    setSelectedPreset(presetName);
  };

  if (!track) {
    return (
      <div className={`bg-slate-800 rounded-lg p-6 text-center ${className}`}>
        <div className="text-4xl mb-3">🎚️</div>
        <h3 className="text-lg font-semibold text-slate-200 mb-2">No Track Loaded</h3>
        <p className="text-sm text-slate-400">
          Generate a drum track first to use re-humanization
        </p>
      </div>
    );
  }

  return (
    <div className={`bg-slate-800 rounded-lg p-4 space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center">
            <span className="mr-2">🎚️</span>
            Re-Humanize
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Adjust feel in real-time • No backend call
          </p>
        </div>
        <span className="text-xs font-bold bg-gradient-to-r from-green-600 to-emerald-600 text-white px-2 py-1 rounded">
          CLIENT-SIDE
        </span>
      </div>

      {/* Selection Info */}
      {hasSelection && (
        <div className="bg-blue-900/30 border border-blue-700/50 rounded-lg p-2 text-xs text-blue-200">
          <span className="font-semibold">Selection Mode:</span> Adjusting {selectedNoteIds!.size} selected notes
        </div>
      )}

      {/* Presets */}
      <div>
        <label className="block text-sm font-semibold text-slate-300 mb-2">
          Quick Presets
        </label>
        <div className="grid grid-cols-3 gap-2">
          {Object.keys(REHUMANIZE_PRESETS).map((presetName) => (
            <button
              key={presetName}
              onClick={() => handlePreset(presetName)}
              className={`px-2 py-1.5 rounded text-xs font-medium transition-all ${
                selectedPreset === presetName
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {presetName.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Micro-Timing Amount */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="text-xs font-semibold text-slate-300">
            Micro-Timing
          </label>
          <span className="text-xs font-bold text-white bg-slate-700 px-2 py-0.5 rounded">
            {microTimingAmount}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={microTimingAmount}
          onChange={(e) => {
            setMicroTimingAmount(Number(e.target.value));
            setSelectedPreset(null);
          }}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-0.5">
          <span>Quantized</span>
          <span>Natural</span>
          <span>Loose</span>
        </div>
      </div>

      {/* Tighten/Loosen */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="text-xs font-semibold text-slate-300">
            Feel
          </label>
          <span className="text-xs font-bold text-white bg-slate-700 px-2 py-0.5 rounded">
            {tightenLoosen > 0 ? `+${tightenLoosen}` : tightenLoosen}%
          </span>
        </div>
        <input
          type="range"
          min="-100"
          max="100"
          value={tightenLoosen}
          onChange={(e) => {
            setTightenLoosen(Number(e.target.value));
            setSelectedPreset(null);
          }}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-0.5">
          <span>Tight</span>
          <span>Natural</span>
          <span>Loose</span>
        </div>
      </div>

      {/* Velocity Amount */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="text-xs font-semibold text-slate-300">
            Velocity Variation
          </label>
          <span className="text-xs font-bold text-white bg-slate-700 px-2 py-0.5 rounded">
            {velocityAmount}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={velocityAmount}
          onChange={(e) => {
            setVelocityAmount(Number(e.target.value));
            setSelectedPreset(null);
          }}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-pink-500"
        />
      </div>

      {/* Swing Amount */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="text-xs font-semibold text-slate-300">
            Swing
          </label>
          <span className="text-xs font-bold text-white bg-slate-700 px-2 py-0.5 rounded">
            {swingAmount}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={swingAmount}
          onChange={(e) => {
            setSwingAmount(Number(e.target.value));
            setSelectedPreset(null);
          }}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-0.5">
          <span>Straight</span>
          <span>Swung</span>
        </div>
      </div>

      {/* Ghost Notes */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="text-xs font-semibold text-slate-300">
            Ghost Note Density
          </label>
          <span className="text-xs font-bold text-white bg-slate-700 px-2 py-0.5 rounded">
            {ghostNoteAmount}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={ghostNoteAmount}
          onChange={(e) => {
            setGhostNoteAmount(Number(e.target.value));
            setSelectedPreset(null);
          }}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-green-500"
        />
      </div>

      {/* Advanced Groove Controls */}
      <button
        onClick={() => setShowGroove(!showGroove)}
        className="w-full py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs font-medium rounded transition-colors flex items-center justify-center"
      >
        <span className="mr-2">{showGroove ? '▼' : '▶'}</span>
        {showGroove ? 'Hide' : 'Show'} Groove Controls
      </button>

      {showGroove && (
        <div className="space-y-3 p-3 bg-slate-900/50 rounded-lg border border-slate-700">
          {/* Laid Back/Pushed */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-semibold text-slate-300">
                Laid Back / Pushed
              </label>
              <span className="text-xs font-bold text-white bg-slate-700 px-2 py-0.5 rounded">
                {laidBack > 0 ? `+${laidBack}` : laidBack}%
              </span>
            </div>
            <input
              type="range"
              min="-100"
              max="100"
              value={laidBack}
              onChange={(e) => setLaidBack(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
            />
            <div className="flex justify-between text-xs text-slate-500 mt-0.5">
              <span>Pushed</span>
              <span>On Beat</span>
              <span>Laid Back</span>
            </div>
          </div>

          {/* Pocket Depth */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-semibold text-slate-300">
                Pocket Depth
              </label>
              <span className="text-xs font-bold text-white bg-slate-700 px-2 py-0.5 rounded">
                {pocketDepth}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={pocketDepth}
              onChange={(e) => setPocketDepth(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-teal-500"
            />
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-700">
        <button
          onClick={handleApply}
          className="py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white font-semibold text-sm rounded-lg transition-all"
        >
          ✨ Apply
        </button>
        <button
          onClick={handleReset}
          disabled={!originalTrack}
          className="py-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-600 text-white font-semibold text-sm rounded-lg transition-all disabled:cursor-not-allowed"
        >
          ↺ Reset
        </button>
      </div>

      {/* Info */}
      <div className="text-xs text-slate-500 text-center pt-2">
        💡 Changes apply instantly • No server call needed
      </div>
    </div>
  );
};

export default RehumanizePanel;
