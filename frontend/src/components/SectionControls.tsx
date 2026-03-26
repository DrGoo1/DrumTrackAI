/**
 * Section Controls Panel - Edit, rename, merge, and manage musical sections
 */
import React, { useState } from 'react';
import { Section } from './WebDAWApp';
import { useRudimentBlockStore } from '../state/useRudimentBlockStore';
import { Tooltip } from './Tooltip';

interface SectionControlsProps {
  sections: Section[];
  onSectionsChange: (sections: Section[]) => void;
  bpm: number;
  timeSignature?: [number, number];
  currentTime: number;
  trackKey?: string;
  onAnalyzeTempos?: (sections: Section[]) => Promise<void>;
}

export const SectionControls: React.FC<SectionControlsProps> = ({
  sections,
  onSectionsChange,
  bpm,
  timeSignature,
  currentTime,
  trackKey,
  onAnalyzeTempos
}) => {
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState<string>('');
  const [isExpanded, setIsExpanded] = useState(false); // Default collapsed
  const blocksBySection = useRudimentBlockStore((state) => state.blocksBySection);

  const formatTime = (seconds: number) => {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

  const getBars = (section: Section) => {
    const duration = section.end - section.start;
    const beatsPerBar = timeSignature?.[0] ?? 4;
    const secPerBeat = 60 / bpm;
    return Math.round(duration / (secPerBeat * beatsPerBar));
  };

  const updateSection = (id: string, updates: Partial<Section>) => {
    onSectionsChange(sections.map(s => s.id === id ? { ...s, ...updates } : s));
  };

  const deleteSection = (id: string) => {
    if (sections.length <= 1) {
      alert('Cannot delete the last section');
      return;
    }
    if (confirm('Delete this section?')) {
      onSectionsChange(sections.filter(s => s.id !== id));
      setSelectedSectionId(null);
    }
  };

  const mergeSections = (id1: string, id2: string) => {
    const idx1 = sections.findIndex(s => s.id === id1);
    const idx2 = sections.findIndex(s => s.id === id2);
    if (idx1 === -1 || idx2 === -1) return;

    const [first, second] = idx1 < idx2 ? [sections[idx1], sections[idx2]] : [sections[idx2], sections[idx1]];
    
    const merged: Section = {
      id: `merged-${Date.now()}`,
      start: first.start,
      end: second.end,
      density: (first.density + second.density) / 2,
      fillIn: first.fillIn,
      fillOut: second.fillOut,
      label: first.label,
      confidence: Math.min(first.confidence || 0.8, second.confidence || 0.8)
    };

    const newSections = sections.filter(s => s.id !== id1 && s.id !== id2);
    newSections.splice(Math.min(idx1, idx2), 0, merged);
    onSectionsChange(newSections);
    setSelectedSectionId(merged.id);
  };

  const splitSection = (id: string, splitTime: number) => {
    const section = sections.find(s => s.id === id);
    if (!section) return;

    // Snap to nearest beat
    const secPerBeat = 60 / bpm;
    const beatNum = Math.round(splitTime / secPerBeat);
    const snappedTime = beatNum * secPerBeat;

    if (snappedTime <= section.start || snappedTime >= section.end) {
      alert('Split point must be within section boundaries');
      return;
    }

    const section1: Section = {
      id: `${section.id}-a`,
      start: section.start,
      end: snappedTime,
      density: section.density,
      fillIn: section.fillIn,
      fillOut: true,
      label: section.label,
      confidence: section.confidence
    };

    const section2: Section = {
      id: `${section.id}-b`,
      start: snappedTime,
      end: section.end,
      density: section.density,
      fillIn: true,
      fillOut: section.fillOut,
      label: section.label,
      confidence: section.confidence
    };

    const idx = sections.findIndex(s => s.id === id);
    const newSections = [...sections];
    newSections.splice(idx, 1, section1, section2);
    onSectionsChange(newSections);
    setSelectedSectionId(section2.id);
  };

  const addSection = () => {
    const newSection: Section = {
      id: `manual-${Date.now()}`,
      start: currentTime,
      end: currentTime + (60 / bpm) * 16, // 4 bars
      density: 0.7,
      fillIn: false,
      fillOut: false,
      label: 'new section',
      confidence: 1.0
    };
    onSectionsChange([...sections, newSection].sort((a, b) => a.start - b.start));
    setSelectedSectionId(newSection.id);
  };

  const startRename = (section: Section) => {
    setEditingId(section.id);
    setEditLabel(section.label || 'section');
  };

  const finishRename = () => {
    if (editingId && editLabel.trim()) {
      updateSection(editingId, { label: editLabel.trim() });
    }
    setEditingId(null);
    setEditLabel('');
  };

  return (
    <div className="bg-slate-800 rounded-lg p-3">
      {/* Collapsible Header */}
      <div 
        className="flex items-center justify-between cursor-pointer hover:bg-slate-700/50 p-2 rounded transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <span className="text-slate-400">{isExpanded ? '▼' : '▶'}</span>
          <h3 className="text-sm font-semibold text-slate-100">
            Musical Arrangement
          </h3>
          <span className="text-xs text-slate-500">({sections.length})</span>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="mt-2 space-y-2">
          {/* Add Section Button */}
          <button
            onClick={addSection}
            className="w-full px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors flex items-center justify-center gap-2"
          >
            <span>+</span> Add Section
          </button>

          {/* Section List */}
          <div className="space-y-1 max-h-64 overflow-y-auto pr-1 text-xs">
        {sections.map((section, idx) => {
          const isSelected = section.id === selectedSectionId;
          const isEditing = section.id === editingId;
          const bars = getBars(section);
          const blockCount = blocksBySection[section.id]?.length ?? 0;

          return (
            <div
              key={section.id}
              onClick={() => setSelectedSectionId(section.id)}
              className={`p-1.5 rounded border cursor-pointer transition-all ${
                isSelected 
                  ? 'border-blue-500 bg-slate-700' 
                  : 'border-slate-600 bg-slate-750 hover:border-slate-500'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                {isEditing ? (
                  <input
                    type="text"
                    value={editLabel}
                    onChange={(e) => setEditLabel(e.target.value)}
                    onBlur={finishRename}
                    onKeyPress={(e) => e.key === 'Enter' && finishRename()}
                    autoFocus
                    className="px-1 py-0.5 bg-slate-900 text-white rounded border border-blue-500 text-xs w-full"
                  />
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 text-xs">{idx + 1}.</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                      section.label === 'intro' ? 'bg-green-900/40 text-green-300' :
                      section.label === 'verse' ? 'bg-blue-900/40 text-blue-300' :
                      section.label === 'pre-chorus' ? 'bg-purple-900/40 text-purple-300' :
                      section.label === 'chorus' ? 'bg-red-900/40 text-red-300' :
                      section.label === 'bridge' ? 'bg-yellow-900/40 text-yellow-300' :
                      section.label === 'outro' ? 'bg-orange-900/40 text-orange-300' :
                      section.label === 'interlude' ? 'bg-cyan-900/40 text-cyan-300' :
                      'bg-slate-700 text-slate-300'
                    }`}>
                      {section.label?.toUpperCase() || 'SECTION'}
                    </span>
                    <span className="text-slate-500 text-xs">({bars}b)</span>
                    {blockCount > 0 && (
                      <span className="ml-1 flex items-center gap-1 rounded bg-purple-900/30 px-2 py-0.5 text-[10px] font-semibold text-purple-200">
                        🧱 {blockCount}
                      </span>
                    )}
                  </div>
                )}
                <div className="flex gap-0.5">
                  {!isEditing && (
                    <Tooltip content="Rename" placement="top" maxWidthClassName="w-24">
                      <button
                        onClick={(e) => { e.stopPropagation(); startRename(section); }}
                        className="px-1 py-0 bg-slate-600 hover:bg-slate-500 text-white text-xs rounded"
                      >
                        ✏️
                      </button>
                    </Tooltip>
                  )}
                  <Tooltip content="Delete" placement="top" maxWidthClassName="w-24">
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteSection(section.id); }}
                      className="px-1 py-0 bg-red-600 hover:bg-red-700 text-white text-xs rounded"
                    >
                      🗑️
                    </button>
                  </Tooltip>
                </div>
              </div>

              <div className="text-xs text-slate-400">
                {formatTime(section.start)} - {formatTime(section.end)}
                {section.tempo && ` • ${section.tempo.toFixed(0)} BPM`}
              </div>

              {blockCount > 0 && (
                <div className="mt-1 text-[11px] text-purple-300">
                  🎯 {blockCount} pinned rudiment block{blockCount > 1 ? 's' : ''}
                </div>
              )}

              {/* Hide expanded controls to save space - only show for selected */}
              {false && isSelected && (
                <div className="mt-3 pt-3 border-t border-slate-600 space-y-2">
                  {/* Density slider */}
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">
                      Density: {(section.density * 100).toFixed(0)}%
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={section.density * 100}
                      onChange={(e) => updateSection(section.id, { density: parseInt(e.target.value) / 100 })}
                      className="w-full"
                    />
                  </div>

                  {/* Fill options */}
                  <div className="flex gap-3 text-xs">
                    <label className="flex items-center gap-1 text-slate-300">
                      <input
                        type="checkbox"
                        checked={section.fillIn}
                        onChange={(e) => updateSection(section.id, { fillIn: e.target.checked })}
                      />
                      Fill In
                    </label>
                    <label className="flex items-center gap-1 text-slate-300">
                      <input
                        type="checkbox"
                        checked={section.fillOut}
                        onChange={(e) => updateSection(section.id, { fillOut: e.target.checked })}
                      />
                      Fill Out
                    </label>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2 pt-2">
                    <Tooltip content="Split at playhead position" placement="top" maxWidthClassName="w-56">
                      <button
                        onClick={() => splitSection(section.id, currentTime)}
                        disabled={currentTime <= section.start || currentTime >= section.end}
                        className="flex-1 px-2 py-1 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white text-xs rounded"
                      >
                        ✂️ Split Here
                      </button>
                    </Tooltip>
                    {idx < sections.length - 1 && (
                      <Tooltip content="Merge with next section" placement="top" maxWidthClassName="w-52">
                        <button
                          onClick={() => mergeSections(section.id, sections[idx + 1].id)}
                          className="flex-1 px-2 py-1 bg-orange-600 hover:bg-orange-700 text-white text-xs rounded"
                        >
                          🔗 Merge →
                        </button>
                      </Tooltip>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
          </div>

          {/* Empty State */}
          {sections.length === 0 && (
            <div className="text-center py-6 text-slate-400">
              <p className="text-sm mb-2">No sections defined</p>
              <p className="text-xs">Click "+ Add Section" above to get started</p>
            </div>
          )}

          {/* Tips */}
          <div className="pt-3 border-t border-slate-700 text-xs text-slate-400">
            <p>💡 <strong>Tips:</strong></p>
            <ul className="list-disc list-inside space-y-1 mt-1">
              <li>Click section to select and edit</li>
              <li>Split sections at playhead position</li>
              <li>Merge adjacent sections</li>
              <li>Adjust density for each section</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default SectionControls;
