import React, { useRef, useEffect } from 'react';

export type UploadedTrack = {
  key: string;
  peaks: number[];
  sr: number;
  seconds: number;
  color: string;
  name: string;
};

export type Section = {
  id: string;
  start: number;
  end: number;
  density: number;
  fillIn: boolean;
  fillOut: boolean;
  label?: string;
  confidence?: number;
  tempo?: number;                  // Per-section micro tempo
  energy?: number;                 // Section energy/loudness
  spectral_centroid?: number;      // Section brightness
};

interface TimelineProps {
  bpm: number;
  tracks: UploadedTrack[];
  sections: Section[];
  onSectionsChange: (sections: Section[]) => void;
  playhead: number;
  setPlayhead: (time: number) => void;
  playing: boolean;
  onDropFiles: (files: FileList) => void;
  onGenerate: (section: Section) => void;
  loop: { enabled: boolean; start: number; end: number };
  setLoop: (loop: { enabled: boolean; start: number; end: number }) => void;
  gridSec: number;
  onAutoSectionize?: (trackKey: string) => void;
  selectedSectionIds?: Set<string>;
  onSelectSection?: (sectionId: string, multi: boolean) => void;
}

const Timeline: React.FC<TimelineProps> = ({
  bpm,
  tracks,
  sections,
  onSectionsChange,
  playhead,
  setPlayhead,
  playing,
  onDropFiles,
  onGenerate,
  loop,
  setLoop,
  gridSec,
  onAutoSectionize,
  selectedSectionIds = new Set(),
  onSelectSection
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Draw timeline and waveforms
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);
    
    // Debug: Log section count when rendering
    if (sections.length > 0) {
      console.log(`🎨 Timeline rendering ${sections.length} sections`);
    }

    // Reserve header area for sections
    const headerHeight = 50;
    const contentHeight = height - headerHeight;

    // Draw tracks below header
    const trackHeight = Math.max(60, contentHeight / Math.max(1, tracks.length));
    tracks.forEach((track, i) => {
      const y = headerHeight + (i * trackHeight);
      
      // Draw waveform background
      ctx.fillStyle = track.color + '20';
      ctx.fillRect(0, y, width, trackHeight - 2);
      
      // Check if stereo waveform data exists
      const peaksL = (track as any).peaksL;
      const peaksR = (track as any).peaksR;
      const hasStereoPeaks = !!(peaksL && peaksR && Array.isArray(peaksL) && Array.isArray(peaksR));
      
      if (hasStereoPeaks) {
        // Draw STEREO waveform (L on top half, R on bottom half)
        const halfHeight = (trackHeight - 2) / 2;
        const centerY = y + halfHeight;
        
        ctx.fillStyle = track.color;
        const samplesPerPixel = Math.max(1, Math.floor(peaksL.length / width));
        
        for (let x = 0; x < width; x++) {
          const startSample = x * samplesPerPixel;
          const endSample = Math.min(startSample + samplesPerPixel, peaksL.length);
          
          // L channel (top half)
          let maxL = 0;
          for (let s = startSample; s < endSample; s++) {
            maxL = Math.max(maxL, Math.abs(peaksL[s] || 0));
          }
          const barHeightL = maxL * (halfHeight - 5);
          ctx.fillRect(x, centerY - barHeightL, 1, barHeightL);
          
          // R channel (bottom half)
          let maxR = 0;
          for (let s = startSample; s < endSample; s++) {
            maxR = Math.max(maxR, Math.abs(peaksR[s] || 0));
          }
          const barHeightR = maxR * (halfHeight - 5);
          ctx.fillRect(x, centerY, 1, barHeightR);
        }
        
        // Draw center line to separate L/R channels
        ctx.strokeStyle = '#ffffff40'; // Semi-transparent white
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        ctx.lineTo(width, centerY);
        ctx.stroke();
      } else {
        // Draw MONO waveform (centered)
        ctx.fillStyle = track.color;
        const samplesPerPixel = Math.max(1, Math.floor(track.peaks.length / width));
        
        for (let x = 0; x < width; x++) {
          const startSample = x * samplesPerPixel;
          const endSample = Math.min(startSample + samplesPerPixel, track.peaks.length);
          
          let max = 0;
          for (let s = startSample; s < endSample; s++) {
            max = Math.max(max, Math.abs(track.peaks[s] || 0));
          }
          
          const barHeight = max * (trackHeight - 10);
          const barY = y + (trackHeight - barHeight) / 2;
          ctx.fillRect(x, barY, 1, barHeight);
        }
      }
      
      // Draw track label
      ctx.fillStyle = '#ffffff';
      ctx.font = '12px sans-serif';
      ctx.fillText(track.name + (hasStereoPeaks ? ' (Stereo)' : ''), 8, y + 20);
    });

    // Draw section header area background
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, width, headerHeight);

    // Draw sections in header
    const maxDuration = Math.max(...tracks.map(t => t.seconds), 10);
    
    if (sections.length > 0) {
      console.log(`📐 Canvas dimensions: ${width}x${height}, maxDuration: ${maxDuration}s`);
    }
    
    sections.forEach((section, idx) => {
      const startX = (section.start / maxDuration) * width;
      const endX = (section.end / maxDuration) * width;
      
      if (idx === 0) {
        console.log(`🎯 First section: "${section.label}" at ${startX.toFixed(1)}px to ${endX.toFixed(1)}px (width: ${(endX-startX).toFixed(1)}px), tempo: ${section.tempo}`);
      }
      
      // Color-code sections by type
      const sectionColors = {
        verse: 'rgba(59, 130, 246, 0.5)', // blue
        chorus: 'rgba(34, 197, 94, 0.5)', // green
        bridge: 'rgba(168, 85, 247, 0.5)', // purple
        intro: 'rgba(249, 115, 22, 0.5)', // orange
        outro: 'rgba(239, 68, 68, 0.5)', // red
        default: 'rgba(100, 116, 139, 0.5)' // slate
      };
      
      const strokeColors = {
        verse: '#3b82f6',
        chorus: '#22c55e', 
        bridge: '#a855f7',
        intro: '#f97316',
        outro: '#ef4444',
        default: '#64748b'
      };
      
      const sectionType = section.label?.toLowerCase() || 'default';
      const isSelected = selectedSectionIds.has(section.id);
      
      // Draw section background in header
      ctx.fillStyle = sectionColors[sectionType] || sectionColors.default;
      ctx.fillRect(startX, 0, endX - startX, headerHeight);
      
      // Highlight selected sections
      if (isSelected) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.fillRect(startX, 0, endX - startX, headerHeight);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.strokeRect(startX, 0, endX - startX, headerHeight);
      }
      
      // Draw vertical lines at section boundaries through entire timeline
      ctx.strokeStyle = strokeColors[sectionType] || strokeColors.default;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(startX, headerHeight);
      ctx.lineTo(startX, height);
      ctx.stroke();
      ctx.setLineDash([]);
      
      // Draw section border in header
      ctx.strokeStyle = strokeColors[sectionType] || strokeColors.default;
      ctx.lineWidth = 2;
      ctx.strokeRect(startX, 0, endX - startX, headerHeight);
      
      // Draw section label and tempo in header
      if (section.label && (endX - startX) > 60) {
        // Section name
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px sans-serif';
        const textWidth = ctx.measureText(section.label.toUpperCase()).width;
        const textX = startX + (endX - startX - textWidth) / 2; // Center text
        ctx.fillText(section.label.toUpperCase(), textX, 15);
        
        // Micro tempo (per-section tempo)
        const microTempo = section.tempo || bpm;
        ctx.font = 'bold 10px monospace';
        ctx.fillStyle = '#fbbf24'; // Yellow/amber for tempo
        const tempoText = `♩=${Math.round(microTempo)}`;
        const tempoTextWidth = ctx.measureText(tempoText).width;
        const tempoTextX = startX + (endX - startX - tempoTextWidth) / 2;
        ctx.fillText(tempoText, tempoTextX, 28);
        
        // Show duration in bars
        const durationSec = section.end - section.start;
        const beatsPerBar = 4;
        const secPerBeat = 60 / microTempo; // Use section tempo
        const bars = Math.round(durationSec / (secPerBeat * beatsPerBar));
        ctx.font = '9px sans-serif';
        ctx.fillStyle = '#cbd5e1';
        const barText = `${bars} bars`;
        const barTextWidth = ctx.measureText(barText).width;
        const barTextX = startX + (endX - startX - barTextWidth) / 2;
        ctx.fillText(barText, barTextX, 42);
      }
    });

    // Draw playhead
    const playheadX = (playhead / maxDuration) * width;
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playheadX, 0);
    ctx.lineTo(playheadX, height);
    ctx.stroke();

  }, [tracks, playhead, sections, bpm]);

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const maxDuration = Math.max(...tracks.map(t => t.seconds), 10);
    const clickTime = (x / canvas.width) * maxDuration;
    
    const headerHeight = 50;
    
    // Check if click was in section header area
    if (y <= headerHeight && onSelectSection) {
      // Find which section was clicked
      for (const section of sections) {
        const startX = (section.start / maxDuration) * canvas.width;
        const endX = (section.end / maxDuration) * canvas.width;
        
        if (x >= startX && x <= endX) {
          // Multi-select with Ctrl/Cmd key
          const isMulti = event.ctrlKey || event.metaKey;
          onSelectSection(section.id, isMulti);
          return;
        }
      }
      // Clicked in header but not on a section - clear selection
      if (onSelectSection) {
        onSelectSection('', false);
      }
    } else {
      // Click in waveform area - set playhead
      setPlayhead(clickTime);
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      onDropFiles(files);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  const addSection = () => {
    const newSection: Section = {
      id: `section-${Date.now()}`,
      start: playhead,
      end: playhead + 4,
      density: 0.5,
      fillIn: false,
      fillOut: false
    };
    onSectionsChange([...sections, newSection]);
  };

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-100">Timeline</h3>
        <div className="flex gap-2">
          {tracks.length > 0 && onAutoSectionize && (
            <button
              onClick={() => onAutoSectionize(tracks[0].key)}
              className="px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              Auto-Detect Sections
            </button>
          )}
          <button
            onClick={addSection}
            className="px-3 py-1 bg-emerald-600 text-white rounded hover:bg-emerald-700"
          >
            Add Section
          </button>
        </div>
      </div>

      <div 
        className="relative"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <canvas
          ref={canvasRef}
          width={800}
          height={Math.max(200, tracks.length * 60)}
          className="w-full bg-slate-900 rounded cursor-pointer"
          onClick={handleCanvasClick}
        />
      </div>

      {/* Sections list removed - now shown in collapsible "Musical Arrangement" below */}
    </div>
  );
};

export default Timeline;
