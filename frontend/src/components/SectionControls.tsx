/**
 * Section Controls Panel - Edit, rename, merge, and manage musical sections
 */
import React, { useState } from 'react';
import { Section } from './WebDAWApp';

interface SectionControlsProps {
  sections: Section[];
  onSectionsChange: (sections: Section[]) => void;
  bpm: number;
  currentTime: number;
  trackKey?: string;
  onAnalyzeTempos?: (sections: Section[]) => Promise<void>;
}

export const SectionControls: React.FC<SectionControlsProps> = ({
  sections,
  onSectionsChange,
  bpm,
  currentTime,
  trackKey,
  onAnalyzeTempos
}) => {
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState('');

  const selectedSection = sections.find(s => s.id === selectedSectionId);

  const formatTime = (seconds: number) => {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

  const getBars = (section: Section) => {
    const duration = section.end - section.start;
    const beatsPerBar = 4;
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
    <div className="bg-slate-800 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-slate-100">Section Manager</h3>
        <button
          onClick={addSection}
          className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors"
        >
          + Add Section
        </button>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {sections.map((section, idx) => {
          const isSelected = section.id === selectedSectionId;
          const isEditing = section.id === editingId;
          const bars = getBars(section);

          return (
            <div
              key={section.id}
              onClick={() => setSelectedSectionId(section.id)}
              className={`p-3 rounded border-2 cursor-pointer transition-all ${
                isSelected 
                  ? 'border-blue-500 bg-slate-700' 
                  : 'border-slate-600 bg-slate-750 hover:border-slate-500'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                {isEditing ? (
                  <input
                    type="text"
                    value={editLabel}
                    onChange={(e) => setEditLabel(e.target.value)}
                    onBlur={finishRename}
                    onKeyPress={(e) => e.key === 'Enter' && finishRename()}
                    autoFocus
                    className="px-2 py-1 bg-slate-900 text-white rounded border border-blue-500 text-sm"
                  />
                ) : (
                  <span className="font-semibold text-slate-100">
                    {idx + 1}. {section.label?.toUpperCase() || 'SECTION'}
                  </span>
                )}
                <div className="flex gap-1">
                  {!isEditing && (
                    <button
                      onClick={(e) => { e.stopPropagation(); startRename(section); }}
                      className="px-2 py-0.5 bg-slate-600 hover:bg-slate-500 text-white text-xs rounded"
                      title="Rename"
                    >
                      ✏️
                    </button>
                  )}
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteSection(section.id); }}
                    className="px-2 py-0.5 bg-red-600 hover:bg-red-700 text-white text-xs rounded"
                    title="Delete"
                  >
                    🗑️
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                <div>
                  <span className="text-slate-400">Start:</span> {formatTime(section.start)}
                </div>
                <div>
                  <span className="text-slate-400">End:</span> {formatTime(section.end)}
                </div>
                <div>
                  <span className="text-slate-400">Duration:</span> {bars} bars
                </div>
                <div>
                  <span className="text-slate-400">Density:</span> {(section.density * 100).toFixed(0)}%
                </div>
              </div>

              {/* Tempo Display */}
              {section.tempo && (
                <div className="mt-2 pt-2 border-t border-slate-700">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">Tempo:</span>
                      <span className={`font-bold ${
                        (section.tempoConfidence || 0) > 0.85 ? 'text-green-400' :
                        (section.tempoConfidence || 0) > 0.6 ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>
                        {section.tempo.toFixed(1)} BPM
                      </span>
                      {section.tempoConfidence && (
                        <span className="text-slate-500">
                          ({(section.tempoConfidence * 100).toFixed(0)}%)
                        </span>
                      )}
                      {section.tempoLocked && (
                        <span className="text-blue-400" title="Tempo locked">
                          🔒
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {isSelected && (
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
                    <button
                      onClick={() => splitSection(section.id, currentTime)}
                      disabled={currentTime <= section.start || currentTime >= section.end}
                      className="flex-1 px-2 py-1 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white text-xs rounded"
                      title="Split at playhead position"
                    >
                      ✂️ Split Here
                    </button>
                    {idx < sections.length - 1 && (
                      <button
                        onClick={() => mergeSections(section.id, sections[idx + 1].id)}
                        className="flex-1 px-2 py-1 bg-orange-600 hover:bg-orange-700 text-white text-xs rounded"
                        title="Merge with next section"
                      >
                        🔗 Merge →
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {sections.length === 0 && (
        <div className="text-center py-8 text-slate-400">
          <p className="mb-2">No sections defined</p>
          <button
            onClick={addSection}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded"
          >
            Create First Section
          </button>
        </div>
      )}

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
  );
};

export default SectionControls;
