import React, { useState, useRef, useEffect, useCallback } from 'react';
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

  const hatPresets = [
    { label: 'Tight 16ths', pattern: 'standard', openRatio: 0.05, complexity: 0.35 },
    { label: 'Shimmer', pattern: 'funk', openRatio: 0.25, complexity: 0.55 },
    { label: 'Half-Time Swell', pattern: 'latin', openRatio: 0.4, complexity: 0.7 },
  ];

  const ridePresets = [
    { label: 'Classic Rock', pattern: 'rock', bell: 0.15, mix: 0.3 },
    { label: 'Jazz Bell', pattern: 'jazz', bell: 0.55, mix: 0.75 },
    { label: 'Fusion Wash', pattern: 'fusion', bell: 0.25, mix: 0.5 },
  ];

  const bassLockPresets = [
    { label: 'Loose', mode: 'complement', sync: 0.2, lock: false },
    { label: 'Pocket', mode: 'follow', sync: 0.55, lock: true },
    { label: 'Grid-Locked', mode: 'locked', sync: 0.85, lock: true },
  ];

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const clamp = (value: number, min: number, max: number) =>
    Math.min(max, Math.max(min, value));

  const updateOptions = (partial: Partial<DrumOptions>) => {
    onChange({ ...options, ...partial });
  };

  const updateOption = <K extends keyof DrumOptions>(key: K, value: DrumOptions[K]) => {
    updateOptions({ [key]: value } as Partial<DrumOptions>);
  };

  const CircularKnob = ({
    value,
    onChange,
    min = 0,
    max = 1,
    step = 0.01,
  }: {
    value: number;
    onChange: (v: number) => void;
    min?: number;
    max?: number;
    step?: number;
  }) => {
    const pointerRef = useRef<number | null>(null);
    const dragRef = useRef<{ value: number; y: number } | null>(null);
    const knobRef = useRef<HTMLDivElement | null>(null);

    const finishDrag = () => {
      if (pointerRef.current !== null && knobRef.current) {
        try {
          knobRef.current.releasePointerCapture(pointerRef.current);
        } catch {
          // Safe to ignore release failures when pointer capture was already lost.
        }
      }
      pointerRef.current = null;
      dragRef.current = null;
    };

    const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
      if (pointerRef.current !== event.pointerId) return;
      if (!dragRef.current) return;
      event.preventDefault();
      const delta = (dragRef.current.y - event.clientY) / 150;
      const raw = dragRef.current.value + delta * (max - min);
      const snapped = Math.round(raw / step) * step;
      onChange(Number(clamp(snapped, min, max).toFixed(4)));
    };

    const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
      if (pointerRef.current !== event.pointerId) return;
      finishDrag();
    };

    const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      pointerRef.current = event.pointerId;
      dragRef.current = { value, y: event.clientY };
      knobRef.current = event.currentTarget;
      event.currentTarget.setPointerCapture(event.pointerId);
    };

    const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
      event.preventDefault();
      const direction = event.deltaY < 0 ? 1 : -1;
      const raw = value + direction * step * 2;
      onChange(Number(clamp(raw, min, max).toFixed(4)));
    };

    useEffect(() => () => finishDrag(), []);

    const percent = clamp((value - min) / (max - min), 0, 1);

    return (
      <div
        ref={knobRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onWheel={handleWheel}
        className="relative h-20 w-20 rounded-full bg-slate-950 border border-cyan-400/60 shadow-[inset_0_0_20px_rgba(34,211,238,0.35)] cursor-pointer select-none"
        style={{ touchAction: 'none' }}
      >
        <div
          className="absolute bottom-3 left-1/2 w-1 rounded-full bg-cyan-300/60 origin-bottom"
          style={{
            height: `${Math.max(12, percent * 70)}%`,
            transform: 'translateX(-50%)',
          }}
        />
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: `conic-gradient(rgba(34,211,238,0.9) ${percent * 300}deg, rgba(8,47,73,0.2) ${percent * 300}deg)`,
          }}
        />
        <div className="absolute inset-[6px] rounded-full bg-slate-900 flex items-center justify-center text-cyan-100 font-semibold">
          {Math.round(percent * 100)}%
        </div>
      </div>
    );
  };

  const RangeSlider = ({
    value,
    onChange,
    min = 0,
    max = 1,
    step = 0.01,
    ariaLabel,
  }: {
    value: number;
    onChange: (v: number) => void;
    min?: number;
    max?: number;
    step?: number;
    ariaLabel: string;
  }) => {
    const sliderRef = useRef<HTMLDivElement | null>(null);
    const draggingRef = useRef(false);

    const updateFromClientX = useCallback(
      (clientX: number) => {
        const rect = sliderRef.current?.getBoundingClientRect();
        if (!rect) return;
        const ratio = clamp((clientX - rect.left) / rect.width, 0, 1);
        const raw = min + ratio * (max - min);
        const snapped = Math.round(raw / step) * step;
        onChange(Number(clamp(snapped, min, max).toFixed(4)));
      },
      [min, max, step, onChange]
    );

    useEffect(() => {
      const handleMouseMove = (event: MouseEvent) => {
        if (!draggingRef.current) return;
        event.preventDefault();
        updateFromClientX(event.clientX);
      };

      const handleMouseUp = () => {
        if (!draggingRef.current) return;
        draggingRef.current = false;
      };

      const handleTouchMove = (event: TouchEvent) => {
        if (!draggingRef.current) return;
        if (!event.touches.length) return;
        event.preventDefault();
        updateFromClientX(event.touches[0].clientX);
      };

      const handleTouchEnd = () => {
        if (!draggingRef.current) return;
        draggingRef.current = false;
      };

      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      window.addEventListener('touchmove', handleTouchMove, { passive: false });
      window.addEventListener('touchend', handleTouchEnd);
      window.addEventListener('touchcancel', handleTouchEnd);

      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
        window.removeEventListener('touchmove', handleTouchMove);
        window.removeEventListener('touchend', handleTouchEnd);
        window.removeEventListener('touchcancel', handleTouchEnd);
      };
    }, [updateFromClientX]);

    const startDragging = (clientX: number) => {
      draggingRef.current = true;
      sliderRef.current?.focus();
      updateFromClientX(clientX);
    };

    const handleMouseDown = (event: React.MouseEvent<HTMLDivElement>) => {
      event.preventDefault();
      startDragging(event.clientX);
    };

    const handleTouchStart = (event: React.TouchEvent<HTMLDivElement>) => {
      if (!event.touches.length) return;
      event.preventDefault();
      startDragging(event.touches[0].clientX);
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      const direction = event.key === 'ArrowRight' ? 1 : -1;
      const multiplier = event.shiftKey ? 5 : event.altKey ? 0.2 : 1;
      const delta = direction * step * multiplier;
      const next = clamp(value + delta, min, max);
      onChange(Number(next.toFixed(4)));
    };

    const percent = clamp((value - min) / (max - min), 0, 1) * 100;

    return (
      <div
        ref={sliderRef}
        role="slider"
        tabIndex={0}
        aria-label={ariaLabel}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={Number(value.toFixed(3))}
        aria-valuetext={`${Math.round(percent)}%`}
        className="relative w-32 h-6 cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-cyan-400/70 rounded"
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        onKeyDown={handleKeyDown}
        style={{ touchAction: 'none' }}
      >
        <div
          className="absolute top-1/2 left-0 right-0 h-1 bg-slate-700/80 rounded-full"
          style={{ transform: 'translateY(-50%)' }}
        />
        <div
          className="absolute top-1/2 left-0 h-1 bg-cyan-400 rounded-full"
          style={{ width: `${percent}%`, transform: 'translateY(-50%)' }}
        />
        <div
          className="absolute top-1/2 h-3 w-3 rounded-full bg-white border border-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.7)]"
          style={{ left: `calc(${percent}% - 6px)`, transform: 'translateY(-50%)' }}
        />
      </div>
    );
  };

  const KnobField = ({
    label,
    value,
    onChange,
    min = 0,
    max = 1,
    step = 0.01,
    info,
  }: {
    label: string;
    value: number;
    onChange: (v: number) => void;
    min?: number;
    max?: number;
    step?: number;
    info?: string;
  }) => {
    return (
      <div className="flex flex-col items-center gap-2 text-center text-xs text-slate-300">
        <div className="flex items-center gap-1">
          <span className="font-semibold text-slate-100">{label}</span>
          {info && (
            <div className="group relative">
              <Info className="h-3 w-3 text-cyan-300 cursor-help" />
              <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-44 bg-slate-900 text-[11px] text-slate-100 p-2 rounded border border-cyan-400/40 shadow-lg">
                {info}
              </div>
            </div>
          )}
        </div>
        <CircularKnob value={value} onChange={onChange} min={min} max={max} step={step} />
        <RangeSlider
          value={value}
          onChange={onChange}
          min={min}
          max={max}
          step={step}
          ariaLabel={`${label} slider`}
        />
      </div>
    );
  };

  const Select = ({
    label,
    value,
    options: selectOptions,
    onChange,
    info,
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
        {selectOptions.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );

  const CollapsibleSection = ({
    id,
    title,
    children,
    icon,
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
          type="button"
          onClick={() => toggleSection(id)}
          className="w-full px-4 py-3 bg-gray-800 hover:bg-gray-750 flex items-center justify-between transition-colors"
        >
          <span className="text-white font-semibold flex items-center gap-2">
            {icon && <span>{icon}</span>}
            {title}
          </span>
          {isExpanded ? (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronRight className="h-5 w-5 text-gray-400" />
          )}
        </button>
        {isExpanded && <div className="p-4 bg-gray-800/50 space-y-4">{children}</div>}
      </div>
    );
  };

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-gray-700 bg-gray-900/80 p-4 shadow-inner">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-500">Global Groove Macros</p>
            <p className="text-sm text-gray-300">Quickly tune the overall drummer feel before diving into details.</p>
          </div>
          {drummerType && (
            <span className="text-[11px] px-2 py-1 rounded-full border border-gray-700 text-gray-300">
              {drummerType.toUpperCase()}
            </span>
          )}
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <KnobField
            label="Groove Intensity"
            value={options.density}
            onChange={(v) => updateOption('density', v)}
            info="Maps to pattern density & ghosting"
          />
          <KnobField
            label="Pocket & Swing"
            value={options.swing}
            onChange={(v) => updateOption('swing', v)}
            info="Push/pull feel across hats & snare"
          />
          <KnobField
            label="Humanize"
            value={options.humanize}
            onChange={(v) => updateOption('humanize', v)}
            info="Timing and velocity variation"
          />
        </div>
      </div>

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
        
        <div className="grid grid-cols-2 gap-6">
          <KnobField
            label="Overall Density"
            value={options.density}
            onChange={(v) => updateOption('density', v)}
            info="How busy/complex the overall pattern is"
          />
          <KnobField
            label="Humanize"
            value={options.humanize}
            onChange={(v) => updateOption('humanize', v)}
            info="Add human timing variations for realism"
          />
        </div>
      </CollapsibleSection>

      {/* Velocity Controls */}
      <CollapsibleSection id="velocity" title="Velocity (Volume)" icon="🔊">
        <div className="space-y-3">
          <div className="bg-blue-500/10 border border-blue-500/30 rounded p-3">
            <p className="text-xs text-blue-300 mb-2">Master Volume Controls</p>
            <div className="grid grid-cols-2 gap-3">
              <KnobField
                label="Drums"
                value={options.drum_velocity}
                onChange={(v) => updateOption('drum_velocity', v)}
                info="Overall volume for kick, snare, toms"
              />
              <KnobField
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
            <div className="mt-3 grid grid-cols-3 gap-4">
              <KnobField label="Kick" value={options.kick_velocity} onChange={(v) => updateOption('kick_velocity', v)} />
              <KnobField label="Snare" value={options.snare_velocity} onChange={(v) => updateOption('snare_velocity', v)} />
              <KnobField label="Toms" value={options.tom_velocity} onChange={(v) => updateOption('tom_velocity', v)} />
              <KnobField label="Hi-Hat" value={options.hihat_velocity} onChange={(v) => updateOption('hihat_velocity', v)} />
              <KnobField label="Crash" value={options.crash_velocity} onChange={(v) => updateOption('crash_velocity', v)} />
              <KnobField label="Ride" value={options.ride_velocity} onChange={(v) => updateOption('ride_velocity', v)} />
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
              <KnobField
                label="Drums"
                value={options.drum_density}
                onChange={(v) => updateOption('drum_density', v)}
                info="How busy kick, snare, toms are"
              />
              <KnobField
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
            <div className="mt-3 grid grid-cols-3 gap-4">
              <KnobField label="Hi-Hat" value={options.hihat_density} onChange={(v) => updateOption('hihat_density', v)} />
              <KnobField label="Ride" value={options.ride_density} onChange={(v) => updateOption('ride_density', v)} />
              <KnobField label="Crash" value={options.crash_density} onChange={(v) => updateOption('crash_density', v)} />
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
        
        <KnobField
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
        
        <KnobField
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

      {/* Hi-Hat Controls */}
      <CollapsibleSection id="hihat" title="Hi-Hat Articulation" icon="🎩">
        <div className="flex flex-wrap gap-2 mb-3">
          {hatPresets.map((preset) => (
            <button
              type="button"
              key={preset.label}
              onClick={() => {
                updateOptions({
                  hihat_pattern: preset.pattern,
                  hihat_open_ratio: preset.openRatio,
                  hihat_complexity: preset.complexity,
                });
              }}
              className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                options.hihat_pattern === preset.pattern ? 'bg-blue-500/30 border-blue-400 text-blue-200' : 'border-gray-700 text-gray-300 hover:border-blue-400'
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <KnobField
          label="Hi-Hat Complexity"
          value={options.hihat_complexity}
          onChange={(v) => updateOption('hihat_complexity', v)}
          info="Loosen to introduce additional 16th embellishments"
        />

        <Select
          label="Hi-Hat Pattern"
          value={options.hihat_pattern}
          options={['standard', 'disco', 'funk', 'latin', 'techno', 'jazz']}
          onChange={(v) => updateOption('hihat_pattern', v)}
          info="Defines sticking logic per section"
        />

        <div className="grid grid-cols-2 gap-6 mt-4">
          <KnobField
            label="Open Ratio"
            value={options.hihat_open_ratio}
            onChange={(v) => updateOption('hihat_open_ratio', v)}
            info="Blend between closed and open articulations"
          />
          <KnobField
            label="Ghost Notes"
            value={options.hihat_ghost_notes}
            onChange={(v) => updateOption('hihat_ghost_notes', v)}
            info="Adds feathered strokes between main pulses"
          />
        </div>
      </CollapsibleSection>

      {/* Ride Cymbal Controls */}
      <CollapsibleSection id="ride" title="Ride Cymbal Dynamics" icon="🔔">
        <div className="flex flex-wrap gap-2 mb-3">
          {ridePresets.map((preset) => (
            <button
              type="button"
              key={preset.label}
              onClick={() => {
                updateOptions({
                  ride_pattern: preset.pattern,
                  ride_bell_ratio: preset.bell,
                  ride_vs_hihat_ratio: preset.mix,
                });
              }}
              className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                options.ride_pattern === preset.pattern ? 'bg-amber-500/30 border-amber-300 text-amber-100' : 'border-gray-700 text-gray-300 hover:border-amber-300'
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <KnobField
          label="Ride Complexity"
          value={options.ride_complexity}
          onChange={(v) => updateOption('ride_complexity', v)}
          info="Controls syncopation and skip beats"
        />

        <Select
          label="Ride Pattern"
          value={options.ride_pattern}
          options={['rock', 'jazz', 'fusion', 'latin']}
          onChange={(v) => updateOption('ride_pattern', v)}
          info="Stylistic voicing for ride phrasing"
        />

        <div className="grid grid-cols-2 gap-6 mt-4">
          <KnobField
            label="Ride vs Hat"
            value={options.ride_vs_hihat_ratio}
            onChange={(v) => updateOption('ride_vs_hihat_ratio', v)}
            info="Crossfade between hat-driven or ride-driven time"
          />
          <KnobField
            label="Bell Ratio"
            value={options.ride_bell_ratio}
            onChange={(v) => updateOption('ride_bell_ratio', v)}
            info="Dial in bell vs bow strikes"
          />
        </div>
      </CollapsibleSection>

      {/* Bass Line Reference */}
      <CollapsibleSection id="bass" title="Low-End Lock" icon="🎸">
        <div className="flex flex-wrap gap-2 mb-3">
          {bassLockPresets.map((preset) => (
            <button
              type="button"
              key={preset.label}
              onClick={() => {
                updateOptions({
                  bass_line_mode: preset.mode,
                  bass_kick_sync: preset.sync,
                  bass_lock_downbeats: preset.lock,
                });
              }}
              className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                options.bass_line_mode === preset.mode ? 'bg-emerald-500/30 border-emerald-300 text-emerald-100' : 'border-gray-700 text-gray-300 hover:border-emerald-300'
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <Select
          label="Bass Line Mode"
          value={options.bass_line_mode}
          options={['ignore', 'follow', 'complement', 'locked']}
          onChange={(v) => updateOption('bass_line_mode', v)}
          info="Defines how aggressively the kick shadows the bass"
        />

        <KnobField
          label="Kick-Bass Sync"
          value={options.bass_kick_sync}
          onChange={(v) => updateOption('bass_kick_sync', v)}
          info="Higher values force kick hits onto bass accents"
        />

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={options.bass_lock_downbeats}
            onChange={(e) => updateOption('bass_lock_downbeats', e.target.checked)}
            className="w-4 h-4"
          />
          <label className="text-sm text-gray-300">Lock Kick to Bass Downbeats</label>
        </div>
      </CollapsibleSection>

      {/* Additional Controls */}
      <CollapsibleSection id="additional" title="Additional Controls" icon="⚙️">
        <div className="grid grid-cols-2 gap-6">
          <KnobField
            label="Tom Usage"
            value={options.tom_usage}
            onChange={(v) => updateOption('tom_usage', v)}
            info="How often toms are used"
          />
          <KnobField
            label="Crash Frequency"
            value={options.crash_frequency}
            onChange={(v) => updateOption('crash_frequency', v)}
            info="How often crashes hit"
          />
          <KnobField
            label="Ghost Note Density"
            value={options.ghost_note_density}
            onChange={(v) => updateOption('ghost_note_density', v)}
            info="Quiet ghost notes between main hits"
          />
          <KnobField
            label="Dynamic Range"
            value={options.dynamic_range}
            onChange={(v) => updateOption('dynamic_range', v)}
            info="Difference between soft and loud hits"
          />
        </div>
      </CollapsibleSection>
    </div>
  );
}
