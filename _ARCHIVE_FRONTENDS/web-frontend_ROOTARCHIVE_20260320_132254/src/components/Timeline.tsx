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
  onAutoSectionize
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

    // Draw tracks
    const trackHeight = Math.max(60, height / Math.max(1, tracks.length));
    tracks.forEach((track, i) => {
      const y = i * trackHeight;
      
      // Draw waveform background
      ctx.fillStyle = track.color + '20';
      ctx.fillRect(0, y, width, trackHeight - 2);
      
      // Draw waveform peaks
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
      
      // Draw track label
      ctx.fillStyle = '#ffffff';
      ctx.font = '12px sans-serif';
      ctx.fillText(track.name, 8, y + 20);
    });

    // Draw playhead
    const maxDuration = Math.max(...tracks.map(t => t.seconds), 10);
    const playheadX = (playhead / maxDuration) * width;
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playheadX, 0);
    ctx.lineTo(playheadX, height);
    ctx.stroke();

    // Draw sections with labels
    sections.forEach(section => {
      const startX = (section.start / maxDuration) * width;
      const endX = (section.end / maxDuration) * width;
      
      // Color-code sections by type
      const sectionColors = {
        verse: 'rgba(59, 130, 246, 0.3)', // blue
        chorus: 'rgba(34, 197, 94, 0.3)', // green
        bridge: 'rgba(168, 85, 247, 0.3)', // purple
        intro: 'rgba(249, 115, 22, 0.3)', // orange
        outro: 'rgba(239, 68, 68, 0.3)', // red
        default: 'rgba(34, 197, 94, 0.3)' // green
      };
      
      const strokeColors = {
        verse: '#3b82f6',
        chorus: '#22c55e', 
        bridge: '#a855f7',
        intro: '#f97316',
        outro: '#ef4444',
        default: '#22c55e'
      };
      
      const sectionType = section.label?.toLowerCase() || 'default';
      ctx.fillStyle = sectionColors[sectionType] || sectionColors.default;
      ctx.fillRect(startX, 0, endX - startX, height);
      
      ctx.strokeStyle = strokeColors[sectionType] || strokeColors.default;
      ctx.lineWidth = 2;
      ctx.strokeRect(startX, 0, endX - startX, height);
      
      // Draw section label
      if (section.label) {
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText(section.label.toUpperCase(), startX + 4, 20);
        
        if (section.confidence) {
          ctx.font = '10px sans-serif';
          ctx.fillStyle = '#e2e8f0';
          ctx.fillText(`${(section.confidence * 100).toFixed(0)}%`, startX + 4, 35);
        }
      }
    });

  }, [tracks, playhead, sections]);

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const maxDuration = Math.max(...tracks.map(t => t.seconds), 10);
    const clickTime = (x / canvas.width) * maxDuration;
    
    setPlayhead(clickTime);
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

      {/* Sections list */}
      {sections.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-slate-300 mb-2">Sections</h4>
          <div className="space-y-2">
            {sections.map((section) => (
              <div
                key={section.id}
                className="flex items-center justify-between bg-slate-700 rounded p-2"
              >
                <div className="flex items-center gap-3">
                  <div className="text-sm text-slate-200">
                    {section.start.toFixed(1)}s - {section.end.toFixed(1)}s
                  </div>
                  {section.label && (
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      section.label.toLowerCase() === 'verse' ? 'bg-blue-600 text-white' :
                      section.label.toLowerCase() === 'chorus' ? 'bg-green-600 text-white' :
                      section.label.toLowerCase() === 'bridge' ? 'bg-purple-600 text-white' :
                      section.label.toLowerCase() === 'intro' ? 'bg-orange-600 text-white' :
                      section.label.toLowerCase() === 'outro' ? 'bg-red-600 text-white' :
                      'bg-slate-600 text-white'
                    }`}>
                      {section.label.toUpperCase()}
                    </span>
                  )}
                  {section.confidence && (
                    <span className="text-xs text-slate-400">
                      {(section.confidence * 100).toFixed(0)}% confidence
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => onGenerate(section)}
                    className="px-2 py-1 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700"
                  >
                    Generate
                  </button>
                  <button
                    onClick={() => {
                      const newSection = { ...section, id: `section-${Date.now()}` };
                      onSectionsChange([...sections, newSection]);
                    }}
                    className="px-2 py-1 bg-emerald-600 text-white rounded text-xs hover:bg-emerald-700"
                  >
                    Duplicate
                  </button>
                  <button
                    onClick={() => onSectionsChange(sections.filter(s => s.id !== section.id))}
                    className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Timeline;
