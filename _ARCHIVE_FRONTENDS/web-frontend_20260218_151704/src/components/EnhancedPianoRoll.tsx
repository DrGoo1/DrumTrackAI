import React, { useRef, useEffect, useState, useCallback } from 'react';
import { WebDAWProject, PatternGrid, KIT_PIECES, GRID_RESOLUTIONS } from '../types/api';
import * as Tone from 'tone';

interface EnhancedPianoRollProps {
  project: WebDAWProject;
  onPatternUpdate: (sectionId: string, pattern: PatternGrid, humanize?: number, humanizePerLane?: Record<string, number>, quantize?: {grid: string, strength: number}, laneSettings?: Record<string, any>) => void;
}

interface Note {
  tick: number;
  velocity: number;
  kitPiece: string;
  id: string;
}

interface SelectionRect {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
}

// Default velocities per kit piece
const DEFAULT_VELOCITIES: Record<string, number> = {
  kick: 110,
  snare: 96,
  hh_closed: 75,
  hh_open: 80,
  ride: 85,
  tom_hi: 90,
  tom_mid: 92,
  tom_low: 95,
  crash: 100
};

// Audio engine for auditioning
class DrumAudioEngine {
  private synths: Record<string, any> = {};
  private initialized = false;

  async init() {
    if (this.initialized) return;
    
    try {
      await Tone.start();
      
      // Create synths for each kit piece
      this.synths.kick = new Tone.MembraneSynth({
        pitchDecay: 0.05,
        octaves: 10,
        oscillator: { type: 'sine' },
        envelope: { attack: 0.001, decay: 0.4, sustain: 0.01, release: 1.4 }
      }).toDestination();
      
      this.synths.snare = new Tone.NoiseSynth({
        noise: { type: 'white' },
        envelope: { attack: 0.005, decay: 0.1, sustain: 0.0 }
      }).toDestination();
      
      this.synths.hh_closed = new Tone.MetalSynth({
        envelope: { attack: 0.001, decay: 0.1, release: 0.01 },
        harmonicity: 5.1,
        modulationIndex: 32,
        resonance: 4000
      }).toDestination();
      
      this.synths.hh_open = new Tone.MetalSynth({
        envelope: { attack: 0.001, decay: 0.5, release: 0.1 },
        harmonicity: 5.1,
        modulationIndex: 32,
        resonance: 4000
      }).toDestination();
      
      // Copy for other pieces
      this.synths.ride = this.synths.hh_open;
      this.synths.tom_hi = this.synths.kick;
      this.synths.tom_mid = this.synths.kick;
      this.synths.tom_low = this.synths.kick;
      this.synths.crash = this.synths.hh_open;
      
      this.initialized = true;
    } catch (error) {
      console.warn('Audio engine init failed:', error);
    }
  }

  audition(kitPiece: string, velocity: number = 80) {
    if (!this.initialized) return;
    
    const synth = this.synths[kitPiece];
    if (!synth) return;
    
    const volume = Tone.gainToDb(velocity / 127);
    
    try {
      if (kitPiece === 'kick' || kitPiece.includes('tom')) {
        const freq = kitPiece === 'kick' ? 60 : kitPiece === 'tom_hi' ? 200 : kitPiece === 'tom_mid' ? 120 : 80;
        synth.triggerAttackRelease(freq, '8n', undefined, volume);
      } else {
        synth.triggerAttackRelease('8n', undefined, volume);
      }
    } catch (error) {
      console.warn('Audition failed:', error);
    }
  }
}

const audioEngine = new DrumAudioEngine();

export const EnhancedPianoRoll: React.FC<EnhancedPianoRollProps> = ({ project, onPatternUpdate }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selectedSection, setSelectedSection] = useState<string>('');
  const [gridResolution, setGridResolution] = useState<number>(64);
  const [velocityMode, setVelocityMode] = useState(false);
  const [pattern, setPattern] = useState<PatternGrid | null>(null);
  const [selectedNotes, setSelectedNotes] = useState<Set<string>>(new Set());
  const [selectionRect, setSelectionRect] = useState<SelectionRect | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [stepMode, setStepMode] = useState(false);
  const [caretPosition, setCaretPosition] = useState(0);
  const [clipboard, setClipboard] = useState<Note[]>([]);
  const [humanize, setHumanize] = useState(0);
  const [humanizePerLane, setHumanizePerLane] = useState<Record<string, number>>({});
  const [quantizeGrid, setQuantizeGrid] = useState('1/64');
  const [quantizeStrength, setQuantizeStrength] = useState(0);
  const [laneSettings, setLaneSettings] = useState<Record<string, {mute: boolean, solo: boolean, volume: number}>>({});

  // Initialize audio engine
  useEffect(() => {
    audioEngine.init();
  }, []);

  // Initialize with first section
  useEffect(() => {
    if (project.smap?.sections.length && !selectedSection) {
      setSelectedSection(project.smap.sections[0].id);
    }
  }, [project.smap, selectedSection]);

  // Initialize lane settings
  useEffect(() => {
    const defaultLaneSettings: Record<string, {mute: boolean, solo: boolean, volume: number}> = {};
    KIT_PIECES.forEach(piece => {
      defaultLaneSettings[piece] = { mute: false, solo: false, volume: 1.0 };
    });
    setLaneSettings(defaultLaneSettings);
  }, []);

  // Load pattern for selected section
  useEffect(() => {
    if (!selectedSection || !project.dgraph) return;

    const section = project.dgraph.sections.find(s => s.section_id === selectedSection);
    if (section) {
      setPattern(section.pattern);
      setHumanize(section.humanize || 0);
      setHumanizePerLane(section.humanize_per_lane || {});
      const quantize = section.quantize || { grid: '1/64', strength: 0 };
      setQuantizeGrid(quantize.grid || '1/64');
      setQuantizeStrength(quantize.strength || 0);
      setLaneSettings(section.lane_settings || {});
    } else {
      // Create empty pattern
      const emptyPattern: PatternGrid = {
        ppq: 480,
        bars: 4,
        kick: [],
        snare: [],
        hh_closed: [],
        hh_open: [],
        ride: [],
        tom_hi: [],
        tom_mid: [],
        tom_low: [],
        crash: [],
        vel: {}
      };
      setPattern(emptyPattern);
    }
  }, [selectedSection, project.dgraph]);

  // Convert pattern to notes array for easier manipulation
  const patternToNotes = useCallback((pat: PatternGrid): Note[] => {
    const notes: Note[] = [];
    KIT_PIECES.forEach(kitPiece => {
      const hits = pat[kitPiece] || [];
      const vels = pat.vel?.[kitPiece] || [];
      hits.forEach((tick, index) => {
        notes.push({
          tick,
          velocity: vels[index] || DEFAULT_VELOCITIES[kitPiece] || 80,
          kitPiece,
          id: `${kitPiece}_${tick}_${index}`
        });
      });
    });
    return notes;
  }, []);

  // Convert notes array back to pattern
  const notesToPattern = useCallback((notes: Note[], pat: PatternGrid): PatternGrid => {
    const newPattern = { ...pat };
    
    // Clear existing data
    KIT_PIECES.forEach(piece => {
      newPattern[piece] = [];
      if (!newPattern.vel) newPattern.vel = {};
      newPattern.vel[piece] = [];
    });
    
    // Group notes by kit piece
    const grouped = notes.reduce((acc, note) => {
      if (!acc[note.kitPiece]) acc[note.kitPiece] = [];
      acc[note.kitPiece].push(note);
      return acc;
    }, {} as Record<string, Note[]>);
    
    // Convert back to pattern format
    Object.entries(grouped).forEach(([kitPiece, pieceNotes]) => {
      const sorted = pieceNotes.sort((a, b) => a.tick - b.tick);
      newPattern[kitPiece as keyof PatternGrid] = sorted.map(n => n.tick);
      if (!newPattern.vel![kitPiece]) newPattern.vel![kitPiece] = [];
      newPattern.vel![kitPiece] = sorted.map(n => n.velocity);
    });
    
    return newPattern;
  }, []);

  return (
    <div className="h-full bg-gray-900 flex flex-col">
      {/* Enhanced Piano Roll Controls */}
      <div className="h-16 bg-gray-800 border-b border-gray-700 flex items-center px-4 space-x-4 overflow-x-auto">
        <div className="text-sm text-gray-400">Enhanced Piano Roll</div>

        {/* Section Selector */}
        <select
          value={selectedSection}
          onChange={(e) => setSelectedSection(e.target.value)}
          className="bg-gray-700 text-white text-sm rounded px-2 py-1"
        >
          {project.smap?.sections.map(section => (
            <option key={section.id} value={section.id}>
              {section.label} ({section.id})
            </option>
          ))}
        </select>

        {/* Grid Resolution */}
        <select
          value={gridResolution}
          onChange={(e) => setGridResolution(Number(e.target.value))}
          className="bg-gray-700 text-white text-sm rounded px-2 py-1"
        >
          {GRID_RESOLUTIONS.map(res => (
            <option key={res} value={res}>1/{res}</option>
          ))}
        </select>

        {/* Step Input Mode */}
        <button
          onClick={() => setStepMode(!stepMode)}
          className={`px-3 py-1 text-sm rounded ${
            stepMode ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
          }`}
        >
          Step Input
        </button>

        {/* Velocity Mode */}
        <button
          onClick={() => setVelocityMode(!velocityMode)}
          className={`px-3 py-1 text-sm rounded ${
            velocityMode ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
          }`}
        >
          Velocity
        </button>

        {/* Selection Controls */}
        <div className="flex space-x-2">
          <button
            onClick={() => {
              if (pattern) {
                const notes = patternToNotes(pattern);
                setSelectedNotes(new Set(notes.map(n => n.id)));
              }
            }}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded"
          >
            Select All
          </button>
          <button
            onClick={() => {
              if (pattern) {
                const notes = patternToNotes(pattern);
                const allIds = new Set(notes.map(n => n.id));
                const newSelection = new Set<string>();
                allIds.forEach(id => {
                  if (!selectedNotes.has(id)) newSelection.add(id);
                });
                setSelectedNotes(newSelection);
              }
            }}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded"
          >
            Invert
          </button>
          <button
            onClick={() => setSelectedNotes(new Set())}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded"
          >
            Clear
          </button>
        </div>

        {/* Quantize Controls */}
        <div className="flex items-center space-x-2">
          <select
            value={quantizeGrid}
            onChange={(e) => setQuantizeGrid(e.target.value)}
            className="bg-gray-700 text-white text-sm rounded px-2 py-1"
          >
            <option value="1/16">1/16</option>
            <option value="1/32">1/32</option>
            <option value="1/64">1/64</option>
            <option value="1/128">1/128</option>
          </select>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={quantizeStrength}
            onChange={(e) => setQuantizeStrength(parseFloat(e.target.value))}
            className="w-16"
          />
          <span className="text-xs text-gray-400">{Math.round(quantizeStrength * 100)}%</span>
          <button
            onClick={() => {
              if (!pattern || selectedNotes.size === 0) return;
              const notes = patternToNotes(pattern);
              const subdivision = pattern.ppq / (parseInt(quantizeGrid.split('/')[1]) / 4);
              const quantizedNotes = notes.map(note => {
                if (selectedNotes.has(note.id)) {
                  const quantizedTick = Math.round(note.tick / subdivision) * subdivision;
                  return { ...note, tick: quantizedTick };
                }
                return note;
              });
              const newPattern = notesToPattern(quantizedNotes, pattern);
              setPattern(newPattern);
              onPatternUpdate(selectedSection, newPattern, humanize, humanizePerLane, 
                { grid: quantizeGrid, strength: quantizeStrength }, laneSettings);
            }}
            className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded"
          >
            Quantize Sel
          </button>
        </div>

        {/* Humanize Controls */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-400">Humanize:</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={humanize}
            onChange={(e) => setHumanize(parseFloat(e.target.value))}
            className="w-16"
          />
          <span className="text-xs text-gray-400">{Math.round(humanize * 100)}%</span>
        </div>
      </div>

      {/* Enhanced Piano Roll Canvas */}
      <div className="flex-1 relative">
        <canvas
          ref={canvasRef}
          width={1400}
          height={360}
          className="w-full h-full cursor-crosshair"
          onMouseDown={(e) => {
            // Enhanced mouse handling will be implemented here
            console.log('Enhanced piano roll interaction');
          }}
        />
      </div>

      {/* Pattern Info */}
      <div className="h-10 bg-gray-800 border-t border-gray-700 flex items-center px-4 text-xs text-gray-400">
        {pattern && (
          <div className="flex space-x-4">
            <span>PPQ: {pattern.ppq}</span>
            <span>Bars: {pattern.bars}</span>
            <span>Grid: 1/{gridResolution}</span>
            <span>Selected: {selectedNotes.size}</span>
            {Object.entries(pattern).filter(([key, value]) => 
              key !== 'ppq' && key !== 'bars' && key !== 'vel' && Array.isArray(value) && value.length > 0
            ).map(([key, value]) => (
              <span key={key}>{key}: {(value as number[]).length} hits</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
