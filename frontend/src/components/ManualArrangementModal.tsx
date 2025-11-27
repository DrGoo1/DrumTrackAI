/**
 * Manual Arrangement Entry Modal
 * For user's own songs - manually specify tempo, time sig, sections, and tempo changes
 */
import React, { useState } from 'react';

export interface ManualSection {
  id: string;
  label: string;
  startMeasure: number; // measure number
  numMeasures: number;  // how many measures
  tempo?: number;       // optional per-section tempo
}

export interface ManualArrangement {
  globalTempo: number;
  timeSignature: [number, number];
  sections: ManualSection[];
  tempoChanges: { time: number; newTempo: number }[];
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (arrangement: ManualArrangement) => void;
  duration: number; // audio duration
}

export const ManualArrangementModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSubmit,
  duration
}) => {
  const [tempo, setTempo] = useState(120);
  const [timeSig, setTimeSig] = useState<[number, number]>([4, 4]);
  const [sections, setSections] = useState<ManualSection[]>([
    { id: '1', label: 'intro', startMeasure: 1, numMeasures: 4, tempo: undefined }
  ]);
  const [tempoChanges, setTempoChanges] = useState<{ time: number; newTempo: number }[]>([]);

  if (!isOpen) return null;

  const addSection = () => {
    const lastSection = sections[sections.length - 1];
    const newStart = lastSection ? lastSection.startMeasure + lastSection.numMeasures : 1;
    setSections([...sections, {
      id: Date.now().toString(),
      label: 'section',
      startMeasure: newStart,
      numMeasures: 4,
      tempo: undefined
    }]);
  };

  const updateSection = (id: string, updates: Partial<ManualSection>) => {
    setSections(sections.map(s => s.id === id ? { ...s, ...updates } : s));
  };

  const deleteSection = (id: string) => {
    setSections(sections.filter(s => s.id !== id));
  };

  const addTempoChange = () => {
    setTempoChanges([...tempoChanges, { time: 0, newTempo: tempo }]);
  };

  const handleSubmit = () => {
    onSubmit({
      globalTempo: tempo,
      timeSignature: timeSig,
      sections,
      tempoChanges
    });
    onClose();
  };

  const calculateTime = (measure: number, numMeasures: number) => {
    const beatsPerMeasure = timeSig[0];
    const totalBeats = (measure - 1 + numMeasures) * beatsPerMeasure;
    const totalSeconds = (totalBeats / tempo) * 60;
    const min = Math.floor(totalSeconds / 60);
    const sec = Math.floor(totalSeconds % 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

  const sectionTypes = ['intro', 'verse', 'pre-chorus', 'chorus', 'bridge', 'solo', 'breakdown', 'outro'];

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-700 bg-gradient-to-r from-indigo-900/40 to-purple-900/40">
          <h2 className="text-xl font-bold text-white">📝 Manual Arrangement Entry</h2>
          <p className="text-sm text-slate-300 mt-1">Define your song's structure manually</p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Global Settings */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">
                Global Tempo (BPM)
              </label>
              <input
                type="number"
                min="40"
                max="240"
                value={tempo}
                onChange={(e) => setTempo(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-900 text-white rounded border border-slate-600 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">
                Time Signature
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="1"
                  max="16"
                  value={timeSig[0]}
                  onChange={(e) => setTimeSig([Number(e.target.value), timeSig[1]])}
                  className="w-20 px-3 py-2 bg-slate-900 text-white rounded border border-slate-600 focus:border-indigo-500 focus:outline-none text-center"
                />
                <span className="text-white text-2xl">/</span>
                <select
                  value={timeSig[1]}
                  onChange={(e) => setTimeSig([timeSig[0], Number(e.target.value)])}
                  className="w-20 px-3 py-2 bg-slate-900 text-white rounded border border-slate-600 focus:border-indigo-500 focus:outline-none"
                >
                  <option value="2">2</option>
                  <option value="4">4</option>
                  <option value="8">8</option>
                  <option value="16">16</option>
                </select>
              </div>
            </div>
          </div>

          {/* Sections */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-white">Song Sections</h3>
              <button
                onClick={addSection}
                className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors"
              >
                + Add Section
              </button>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
              {sections.map((section, idx) => (
                <div key={section.id} className="p-3 bg-slate-900 rounded border border-slate-700">
                  <div className="grid grid-cols-12 gap-3 items-center">
                    <div className="col-span-1 text-slate-400 font-semibold">#{idx + 1}</div>
                    
                    <div className="col-span-3">
                      <select
                        value={section.label}
                        onChange={(e) => updateSection(section.id, { label: e.target.value })}
                        className="w-full px-2 py-1 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-indigo-500 focus:outline-none"
                      >
                        {sectionTypes.map(type => (
                          <option key={type} value={type}>{type.toUpperCase()}</option>
                        ))}
                      </select>
                    </div>

                    <div className="col-span-3">
                      <label className="text-xs text-slate-400">Start Measure</label>
                      <input
                        type="number"
                        min="1"
                        step="1"
                        value={section.startMeasure}
                        onChange={(e) => updateSection(section.id, { startMeasure: Number(e.target.value) })}
                        className="w-full px-2 py-1 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-indigo-500 focus:outline-none"
                      />
                      <span className="text-xs text-slate-500">~{calculateTime(section.startMeasure, 0)}</span>
                    </div>

                    <div className="col-span-3">
                      <label className="text-xs text-slate-400"># Measures</label>
                      <input
                        type="number"
                        min="1"
                        step="1"
                        value={section.numMeasures}
                        onChange={(e) => updateSection(section.id, { numMeasures: Number(e.target.value) })}
                        className="w-full px-2 py-1 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-indigo-500 focus:outline-none"
                      />
                      <span className="text-xs text-slate-500">~{calculateTime(section.startMeasure, section.numMeasures)}</span>
                    </div>

                    <div className="col-span-2 flex gap-1">
                      <button
                        onClick={() => deleteSection(section.id)}
                        className="px-2 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded"
                        disabled={sections.length === 1}
                      >
                        🗑️
                      </button>
                    </div>
                  </div>

                  {/* Optional per-section tempo */}
                  <div className="mt-2">
                    <label className="flex items-center gap-2 text-xs text-slate-400">
                      <input
                        type="checkbox"
                        checked={section.tempo !== undefined}
                        onChange={(e) => updateSection(section.id, { 
                          tempo: e.target.checked ? tempo : undefined 
                        })}
                      />
                      Different tempo for this section
                    </label>
                    {section.tempo !== undefined && (
                      <input
                        type="number"
                        min="40"
                        max="240"
                        value={section.tempo}
                        onChange={(e) => updateSection(section.id, { tempo: Number(e.target.value) })}
                        className="mt-1 w-24 px-2 py-1 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-indigo-500 focus:outline-none"
                        placeholder="BPM"
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* MIDI Tempo Map Upload */}
          <div className="border border-slate-700 rounded p-4 bg-slate-900/50">
            <h3 className="text-sm font-semibold text-white mb-2">📄 Import MIDI Tempo Map (Optional)</h3>
            <p className="text-xs text-slate-400 mb-2">
              Upload a MIDI file with tempo map to automatically set tempo changes
            </p>
            <input
              type="file"
              accept=".mid,.midi"
              className="text-sm text-slate-300"
              onChange={(e) => {
                // TODO: Parse MIDI tempo map
                console.log('MIDI file selected:', e.target.files?.[0]);
              }}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700 bg-slate-900 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded transition-colors"
          >
            Apply Arrangement
          </button>
        </div>
      </div>
    </div>
  );
};
