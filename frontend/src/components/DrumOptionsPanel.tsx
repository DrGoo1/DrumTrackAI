import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Info } from 'lucide-react';

export interface DrumOptions {
  // Basic parameters
  bpm: number;
  bars: number;
  density: number;
  swing: number;
  humanize: number;
  style: string;
  label: string;
  swing_preset: string;
  vel_preset: string;
  fill_preset: string;
  
  // Velocity controls
  drum_velocity: number;
  cymbal_velocity: number;
  kick_velocity: number;
  snare_velocity: number;
  tom_velocity: number;
  hihat_velocity: number;
  crash_velocity: number;
  ride_velocity: number;
  
  // Density controls
  drum_density: number;
  cymbal_density: number;
  hihat_density: number;
  ride_density: number;
  crash_density: number;
  
  // Fill controls
  fill_density: number;
  fill_location: string;
  fill_frequency: number;
  
  // Hi-hat complexity
  hihat_complexity: number;
  hihat_pattern: string;
  hihat_open_ratio: number;
  hihat_ghost_notes: number;
  
  // Ride cymbal
  ride_complexity: number;
  ride_pattern: string;
  ride_vs_hihat_ratio: number;
  ride_bell_ratio: number;
  
  // Bass line reference
  bass_line_mode: string;
  bass_kick_sync: number;
  bass_lock_downbeats: boolean;
  
  // Additional controls
  tom_usage: number;
  crash_frequency: number;
  ghost_note_density: number;
  dynamic_range: number;
}

interface Props {
  options: DrumOptions;
  onChange: (options: DrumOptions) => void;
  drummerType?: string;
}

export default function DrumOptionsPanel({ options, onChange, drummerType }: Props) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['basic', 'velocity', 'density'])
  );

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const updateOption = (key: keyof DrumOptions, value: any) => {
    onChange({ ...options, [key]: value });
  };

  const Slider = ({ 
    label, 
    value, 
    onChange, 
    min = 0, 
    max = 1, 
    step = 0.01, 
    info 
  }: { 
    label: string; 
    value: number; 
    onChange: (v: number) => void; 
    min?: number; 
    max?: number; 
    step?: number;
    info?: string;
  }) => (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <label className="text-sm text-gray-300 flex items-center gap-1">
          {label}
          {info && (
            <div className="group relative">
              <Info className="h-3 w-3 text-gray-500 cursor-help" />
              <div className="hidden group-hover:block absolute bottom-full left-0 mb-2 w-48 bg-gray-800 text-xs text-gray-200 p-2 rounded shadow-lg z-10">
                {info}
              </div>
            </div>
          )}
        </label>
        <span className="text-sm text-blue-400 font-mono">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
      />
    </div>
  );

  const Select = ({ 
    label, 
    value, 
    options: selectOptions, 
    onChange, 
    info 
  }: { 
    label: string; 
    value: string; 
    options: string[]; 
    onChange: (v: string) => void;
    info?: string;
  }) => (
    <div className="space-y-1">
      <label className="text-sm text-gray-300 flex items-center gap-1">
        {label}
        {info && (
          <div className="group relative">
            <Info className="h-3 w-3 text-gray-500 cursor-help" />
            <div className="hidden group-hover:block absolute bottom-full left-0 mb-2 w-48 bg-gray-800 text-xs text-gray-200 p-2 rounded shadow-lg z-10">
              {info}
            </div>
          </div>
        )}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
      >
        {selectOptions.map(opt => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </div>
  );

  const CollapsibleSection = ({ 
    id, 
    title, 
    children, 
    icon 
  }: { 
    id: string; 
    title: string; 
    children: React.ReactNode;
    icon?: string;
  }) => {
    const isExpanded = expandedSections.has(id);
    return (
      <div className="border border-gray-700 rounded-lg overflow-hidden">
        <button
          onClick={() => toggleSection(id)}
          className="w-full px-4 py-3 bg-gray-800 hover:bg-gray-750 flex items-center justify-between transition-colors"
        >
          <span className="text-white font-semibold flex items-center gap-2">
            {icon && <span>{icon}</span>}
            {title}
          </span>
          {isExpanded ? <ChevronDown className="h-5 w-5 text-gray-400" /> : <ChevronRight className="h-5 w-5 text-gray-400" />}
        </button>
        {isExpanded && (
          <div className="p-4 bg-gray-800/50 space-y-4">
            {children}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-3">
      <style>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 16px;
          height: 16px;
          background: #3b82f6;
          cursor: pointer;
          border-radius: 50%;
        }
        .slider::-moz-range-thumb {
          width: 16px;
          height: 16px;
          background: #3b82f6;
          cursor: pointer;
          border-radius: 50%;
          border: none;
        }
      `}</style>

      {/* Basic Parameters */}
      <CollapsibleSection id="basic" title="Basic Parameters" icon="🎵">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-gray-300">BPM</label>
            <input
              type="number"
              min={40}
              max={240}
              value={options.bpm}
              onChange={(e) => updateOption('bpm', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-sm text-gray-300">Bars</label>
            <input
              type="number"
              min={1}
              max={64}
              value={options.bars}
              onChange={(e) => updateOption('bars', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>
        
        <Select
          label="Style"
          value={options.style}
          options={['rock', 'funk', 'edm', 'hiphop', 'jazz', 'pop']}
          onChange={(v) => updateOption('style', v)}
          info="Musical genre/style for drum pattern"
        />
        
        <Select
          label="Section Label"
          value={options.label}
          options={['intro', 'verse', 'chorus', 'bridge', 'outro']}
          onChange={(v) => updateOption('label', v)}
          info="Song section for appropriate pattern density"
        />
        
        <Slider
          label="Overall Density"
          value={options.density}
          onChange={(v) => updateOption('density', v)}
          info="How busy/complex the overall pattern is"
        />
        
        <Slider
          label="Humanize"
          value={options.humanize}
          onChange={(v) => updateOption('humanize', v)}
          info="Add human timing variations for realism"
        />
      </CollapsibleSection>

      {/* Velocity Controls */}
      <CollapsibleSection id="velocity" title="Velocity (Volume)" icon="🔊">
        <div className="space-y-3">
          <div className="bg-blue-500/10 border border-blue-500/30 rounded p-3">
            <p className="text-xs text-blue-300 mb-2">Master Volume Controls</p>
            <div className="grid grid-cols-2 gap-3">
              <Slider
                label="Drums"
                value={options.drum_velocity}
                onChange={(v) => updateOption('drum_velocity', v)}
                info="Overall volume for kick, snare, toms"
              />
              <Slider
                label="Cymbals"
                value={options.cymbal_velocity}
                onChange={(v) => updateOption('cymbal_velocity', v)}
                info="Overall volume for hi-hat, crash, ride"
              />
            </div>
          </div>
          
          <details className="bg-gray-700/30 rounded p-3">
            <summary className="text-sm text-gray-300 cursor-pointer hover:text-white">
              Individual Instrument Volumes
            </summary>
            <div className="mt-3 space-y-2">
              <Slider label="Kick" value={options.kick_velocity} onChange={(v) => updateOption('kick_velocity', v)} />
              <Slider label="Snare" value={options.snare_velocity} onChange={(v) => updateOption('snare_velocity', v)} />
              <Slider label="Toms" value={options.tom_velocity} onChange={(v) => updateOption('tom_velocity', v)} />
              <Slider label="Hi-Hat" value={options.hihat_velocity} onChange={(v) => updateOption('hihat_velocity', v)} />
              <Slider label="Crash" value={options.crash_velocity} onChange={(v) => updateOption('crash_velocity', v)} />
              <Slider label="Ride" value={options.ride_velocity} onChange={(v) => updateOption('ride_velocity', v)} />
            </div>
          </details>
        </div>
      </CollapsibleSection>

      {/* Density Controls */}
      <CollapsibleSection id="density" title="Density (Complexity)" icon="🎚️">
        <div className="space-y-3">
          <div className="bg-purple-500/10 border border-purple-500/30 rounded p-3">
            <p className="text-xs text-purple-300 mb-2">Master Density Controls</p>
            <div className="grid grid-cols-2 gap-3">
              <Slider
                label="Drums"
                value={options.drum_density}
                onChange={(v) => updateOption('drum_density', v)}
                info="How busy kick, snare, toms are"
              />
              <Slider
                label="Cymbals"
                value={options.cymbal_density}
                onChange={(v) => updateOption('cymbal_density', v)}
                info="How busy hi-hat, crash, ride are"
              />
            </div>
          </div>
          
          <details className="bg-gray-700/30 rounded p-3">
            <summary className="text-sm text-gray-300 cursor-pointer hover:text-white">
              Individual Cymbal Density
            </summary>
            <div className="mt-3 space-y-2">
              <Slider label="Hi-Hat" value={options.hihat_density} onChange={(v) => updateOption('hihat_density', v)} />
              <Slider label="Ride" value={options.ride_density} onChange={(v) => updateOption('ride_density', v)} />
              <Slider label="Crash" value={options.crash_density} onChange={(v) => updateOption('crash_density', v)} />
            </div>
          </details>
        </div>
      </CollapsibleSection>

      {/* Fill Controls */}
      <CollapsibleSection id="fills" title="Fill Options" icon="🥁">
        <Select
          label="Fill Type"
          value={options.fill_preset}
          options={['none', 'random', 'tomrun', 'snarebuzz', 'edmriser']}
          onChange={(v) => updateOption('fill_preset', v)}
          info="Type of drum fill at transitions"
        />
        
        <Slider
          label="Fill Density"
          value={options.fill_density}
          onChange={(v) => updateOption('fill_density', v)}
          info="How complex/busy the fills are (0=sparse, 1=insane)"
        />
        
        <Select
          label="Fill Location"
          value={options.fill_location}
          options={['auto', 'end', 'middle', 'front']}
          onChange={(v) => updateOption('fill_location', v)}
          info="Where in the measure fills occur"
        />
        
        <div>
          <label className="text-sm text-gray-300">Fill Frequency (every N bars)</label>
          <input
            type="number"
            min={1}
            max={16}
            value={options.fill_frequency}
            onChange={(e) => updateOption('fill_frequency', parseInt(e.target.value))}
            className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
          />
        </div>
      </CollapsibleSection>

      {/* Groove Options */}
      <CollapsibleSection id="groove" title="Groove Options" icon="🎼">
        <Select
          label="Swing Preset"
          value={options.swing_preset}
          options={['off', 'light', 'heavy']}
          onChange={(v) => updateOption('swing_preset', v)}
          info="Timing offset for swing feel"
        />
        
        <Slider
          label="Fine Swing Amount"
          value={options.swing}
          onChange={(v) => updateOption('swing', v)}
          info="Additional swing adjustment"
        />
        
        <Select
          label="Velocity Pattern"
          value={options.vel_preset}
          options={['flat', 'accent24', 'funk16']}
          onChange={(v) => updateOption('vel_preset', v)}
          info="Dynamic emphasis pattern"
        />
      </CollapsibleSection>

      {/* Hi-Hat Complexity (STUB) */}
      <CollapsibleSection id="hihat" title="Hi-Hat Complexity ⚠️ Coming Soon" icon="🎩">
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded p-3 mb-3">
          <p className="text-xs text-yellow-300">These controls are stubs and will be fully implemented soon.</p>
        </div>
        
        <Slider
          label="Hi-Hat Complexity"
          value={options.hihat_complexity}
          onChange={(v) => updateOption('hihat_complexity', v)}
          info="Overall hi-hat pattern complexity"
        />
        
        <Select
          label="Hi-Hat Pattern"
          value={options.hihat_pattern}
          options={['standard', 'disco', 'funk', 'latin', 'techno', 'jazz']}
          onChange={(v) => updateOption('hihat_pattern', v)}
          info="Hi-hat pattern style"
        />
        
        <Slider
          label="Open Hi-Hat Ratio"
          value={options.hihat_open_ratio}
          onChange={(v) => updateOption('hihat_open_ratio', v)}
          info="How often hi-hat opens"
        />
        
        <Slider
          label="Ghost Notes"
          value={options.hihat_ghost_notes}
          onChange={(v) => updateOption('hihat_ghost_notes', v)}
          info="Quiet hi-hat ghost notes"
        />
      </CollapsibleSection>

      {/* Ride Cymbal (STUB) */}
      <CollapsibleSection id="ride" title="Ride Cymbal ⚠️ Coming Soon" icon="🔔">
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded p-3 mb-3">
          <p className="text-xs text-yellow-300">These controls are stubs and will be fully implemented soon.</p>
        </div>
        
        <Slider
          label="Ride Complexity"
          value={options.ride_complexity}
          onChange={(v) => updateOption('ride_complexity', v)}
          info="Ride cymbal pattern complexity"
        />
        
        <Select
          label="Ride Pattern"
          value={options.ride_pattern}
          options={['rock', 'jazz', 'fusion', 'latin']}
          onChange={(v) => updateOption('ride_pattern', v)}
          info="Ride cymbal style"
        />
        
        <Slider
          label="Ride vs Hi-Hat Mix"
          value={options.ride_vs_hihat_ratio}
          onChange={(v) => updateOption('ride_vs_hihat_ratio', v)}
          info="0=all hi-hat, 1=all ride"
        />
        
        <Slider
          label="Ride Bell Ratio"
          value={options.ride_bell_ratio}
          onChange={(v) => updateOption('ride_bell_ratio', v)}
          info="How often to hit the bell"
        />
      </CollapsibleSection>

      {/* Bass Line Reference (STUB) */}
      <CollapsibleSection id="bass" title="Bass Line Reference ⚠️ Coming Soon" icon="🎸">
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded p-3 mb-3">
          <p className="text-xs text-yellow-300">Bass analysis in development. These controls are stubs.</p>
        </div>
        
        <Select
          label="Bass Line Mode"
          value={options.bass_line_mode}
          options={['ignore', 'follow', 'complement', 'locked']}
          onChange={(v) => updateOption('bass_line_mode', v)}
          info="How drums interact with bass line"
        />
        
        <Slider
          label="Kick-Bass Sync"
          value={options.bass_kick_sync}
          onChange={(v) => updateOption('bass_kick_sync', v)}
          info="How closely kick follows bass notes"
        />
        
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={options.bass_lock_downbeats}
            onChange={(e) => updateOption('bass_lock_downbeats', e.target.checked)}
            className="w-4 h-4"
          />
          <label className="text-sm text-gray-300">Lock kick to bass downbeats</label>
        </div>
      </CollapsibleSection>

      {/* Additional Controls */}
      <CollapsibleSection id="additional" title="Additional Controls" icon="⚙️">
        <Slider
          label="Tom Usage"
          value={options.tom_usage}
          onChange={(v) => updateOption('tom_usage', v)}
          info="How often toms are used"
        />
        
        <Slider
          label="Crash Frequency"
          value={options.crash_frequency}
          onChange={(v) => updateOption('crash_frequency', v)}
          info="How often crashes hit"
        />
        
        <Slider
          label="Ghost Note Density"
          value={options.ghost_note_density}
          onChange={(v) => updateOption('ghost_note_density', v)}
          info="Quiet ghost notes between main hits"
        />
        
        <Slider
          label="Dynamic Range"
          value={options.dynamic_range}
          onChange={(v) => updateOption('dynamic_range', v)}
          info="Difference between soft and loud hits"
        />
      </CollapsibleSection>
    </div>
  );
}
