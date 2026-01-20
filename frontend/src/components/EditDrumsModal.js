import React, { useState, useRef, useEffect } from 'react';
import * as Tone from 'tone';
import { Play, Square, Volume2, Settings, X } from 'lucide-react';

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const DragSlider = ({
  value,
  onChange,
  min = 0,
  max = 1,
  step = 0.01,
}) => {
  const ref = useRef(null);
  const draggingRef = useRef(false);

  const updateFromClientX = (clientX) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    const ratio = clamp((clientX - rect.left) / rect.width, 0, 1);
    const raw = min + ratio * (max - min);
    const snapped = Math.round(raw / step) * step;
    onChange(Number(clamp(snapped, min, max).toFixed(6)));
  };

  useEffect(() => {
    const handleMouseMove = (event) => {
      if (!draggingRef.current) return;
      event.preventDefault();
      updateFromClientX(event.clientX);
    };

    const handleMouseUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
    };

    const handleTouchMove = (event) => {
      if (!draggingRef.current) return;
      if (!event.touches?.length) return;
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
  }, []);

  const startDragging = (clientX) => {
    draggingRef.current = true;
    updateFromClientX(clientX);
  };

  const handleMouseDown = (event) => {
    event.preventDefault();
    startDragging(event.clientX);
  };

  const handleTouchStart = (event) => {
    if (!event.touches?.length) return;
    event.preventDefault();
    startDragging(event.touches[0].clientX);
  };

  const percent = clamp((value - min) / (max - min), 0, 1) * 100;

  return (
    <div
      ref={ref}
      role="slider"
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
      className="relative w-full h-2 bg-gray-700 rounded cursor-pointer select-none"
      style={{ touchAction: 'none' }}
      onMouseDownCapture={handleMouseDown}
      onTouchStartCapture={handleTouchStart}
      onMouseDown={handleMouseDown}
      onTouchStart={handleTouchStart}
    >
      <div
        className="absolute left-0 top-0 bottom-0 bg-blue-500 rounded pointer-events-none"
        style={{ width: `${percent}%` }}
      />
      <div
        className="absolute top-1/2 h-4 w-4 rounded-full bg-white border border-blue-500 pointer-events-none"
        style={{ left: `calc(${percent}% - 8px)`, transform: 'translateY(-50%)' }}
      />
    </div>
  );
};

const EditDrumsModal = ({ 
  isOpen, 
  onClose, 
  jobId, 
  sectionId, 
  currentNotes = {}, 
  onApply 
}) => {
  const [form, setForm] = useState({
    drummer_id: '',
    source: 'mix',
    style: 'default',
    complexity: 0.5,
    energy: 0.5,
    swing: 0.0,
    humanize: 0.2,
    fill_in: 'none',
    fill_out: 'none',
    fill_every_bars: null
  });

  const [suggestedNotes, setSuggestedNotes] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [drummers, setDrummers] = useState([]);
  
  const samplerRef = useRef(null);
  const playbackRef = useRef(null);

  // Initialize Tone.js sampler for audition
  useEffect(() => {
    if (!samplerRef.current) {
      samplerRef.current = new Tone.Sampler({
        urls: {
          C1: 'kick.wav',
          D1: 'snare.wav',
          'F#1': 'hihat.wav',
          A1: 'tom.wav',
          'C#2': 'ride.wav',
          'D#2': 'crash.wav'
        },
        baseUrl: '/samples/drums/', // Static path served by Nginx
      }).toDestination();
    }

    return () => {
      if (playbackRef.current) {
        Tone.Transport.cancel();
        setIsPlaying(false);
      }
    };
  }, []);

  // Load curated drummers
  useEffect(() => {
    if (isOpen && jobId) {
      loadDrummers();
    }
  }, [isOpen, jobId]);

  const loadDrummers = async () => {
    try {
      const response = await fetch(`/api/drummers?job_id=${jobId}`);
      if (response.ok) {
        const data = await response.json();
        setDrummers(data.drummers || []);
      }
    } catch (error) {
      console.error('Failed to load drummers:', error);
    }
  };

  const handleSuggest = async () => {
    setIsLoading(true);
    try {
      const body = {
        job_id: jobId,
        section_id: sectionId,
        drummer_id: form.drummer_id || null,
        source: form.source,
        params: {
          style: form.style,
          complexity: form.complexity,
          energy: form.energy,
          swing: form.swing,
          humanize: form.humanize,
          fill_in: form.fill_in,
          fill_out: form.fill_out,
          fill_every_bars: form.fill_every_bars
        }
      };

      const response = await fetch('/api/drums/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (response.ok) {
        const data = await response.json();
        setSuggestedNotes(data.notes);
      } else {
        console.error('Suggest failed:', await response.text());
      }
    } catch (error) {
      console.error('Suggest error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePreview = async () => {
    if (!samplerRef.current || !suggestedNotes) return;

    if (isPlaying) {
      // Stop playback
      Tone.Transport.stop();
      Tone.Transport.cancel();
      setIsPlaying(false);
      return;
    }

    // Start Tone.js if not already started
    if (Tone.context.state !== 'running') {
      await Tone.start();
    }

    setIsPlaying(true);

    // Map drum types to MIDI notes
    const drumMap = {
      kick: 'C1',
      snare: 'D1',
      hihat: 'F#1',
      tom: 'A1',
      ride: 'C#2',
      crash: 'D#2'
    };

    // Schedule all notes
    const allEvents = [];
    Object.entries(suggestedNotes).forEach(([drum, notes]) => {
      if (drumMap[drum]) {
        notes.forEach(note => {
          allEvents.push({
            time: note.seconds,
            note: drumMap[drum],
            velocity: (note.velocity || 100) / 127
          });
        });
      }
    });

    // Sort by time
    allEvents.sort((a, b) => a.time - b.time);

    // Schedule events
    allEvents.forEach(event => {
      Tone.Transport.schedule((time) => {
        samplerRef.current.triggerAttackRelease(event.note, '8n', time, event.velocity);
      }, event.time);
    });

    // Auto-stop after pattern duration (estimate 4 bars at 120 BPM = 8 seconds)
    const duration = Math.max(8, Math.max(...allEvents.map(e => e.time)) + 1);
    Tone.Transport.schedule(() => {
      setIsPlaying(false);
      Tone.Transport.stop();
      Tone.Transport.cancel();
    }, duration);

    Tone.Transport.start();
  };

  const handleApply = async () => {
    if (!suggestedNotes) return;

    try {
      const body = {
        job_id: jobId,
        section_id: sectionId,
        notes: suggestedNotes
      };

      const response = await fetch('/api/drums/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (response.ok) {
        onApply && onApply(suggestedNotes);
        onClose();
      } else {
        console.error('Apply failed:', await response.text());
      }
    } catch (error) {
      console.error('Apply error:', error);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-white">Edit Drums</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <X size={24} />
          </button>
        </div>

        <div className="space-y-6">
          {/* Drummer Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Drummer Style
            </label>
            <select
              value={form.drummer_id}
              onChange={(e) => setForm(f => ({ ...f, drummer_id: e.target.value }))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="">Auto-select</option>
              {drummers.map(drummer => (
                <option key={drummer.id} value={drummer.id}>
                  {drummer.name} - {drummer.style}
                </option>
              ))}
            </select>
          </div>

          {/* Source Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Source Track
            </label>
            <select
              value={form.source}
              onChange={(e) => setForm(f => ({ ...f, source: e.target.value }))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="mix">Full Mix</option>
              <option value="bass">Bass Track</option>
              <option value="none">Generate Free</option>
            </select>
          </div>

          {/* Style and Parameters */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Complexity
              </label>
              <DragSlider
                value={form.complexity}
                min={0}
                max={1}
                step={0.1}
                onChange={(next) => setForm((f) => ({ ...f, complexity: next }))}
              />
              <span className="text-xs text-gray-400">{Math.round(form.complexity * 100)}%</span>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Energy
              </label>
              <DragSlider
                value={form.energy}
                min={0}
                max={1}
                step={0.1}
                onChange={(next) => setForm((f) => ({ ...f, energy: next }))}
              />
              <span className="text-xs text-gray-400">{Math.round(form.energy * 100)}%</span>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Swing
              </label>
              <DragSlider
                value={form.swing}
                min={0}
                max={1}
                step={0.1}
                onChange={(next) => setForm((f) => ({ ...f, swing: next }))}
              />
              <span className="text-xs text-gray-400">{Math.round(form.swing * 100)}%</span>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Humanize
              </label>
              <DragSlider
                value={form.humanize}
                min={0}
                max={1}
                step={0.1}
                onChange={(next) => setForm((f) => ({ ...f, humanize: next }))}
              />
              <span className="text-xs text-gray-400">{Math.round(form.humanize * 100)}%</span>
            </div>
          </div>

          {/* Fill Options */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Fill In
              </label>
              <select
                value={form.fill_in}
                onChange={(e) => setForm(f => ({ ...f, fill_in: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                <option value="none">None</option>
                <option value="short">Short</option>
                <option value="long">Long</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Fill Out
              </label>
              <select
                value={form.fill_out}
                onChange={(e) => setForm(f => ({ ...f, fill_out: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                <option value="none">None</option>
                <option value="short">Short</option>
                <option value="long">Long</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Fill Cadence (every N bars)
              </label>
              <input
                type="number"
                min="0"
                placeholder="0 or empty"
                value={form.fill_every_bars ?? ''}
                onChange={(e) => setForm(f => ({ 
                  ...f, 
                  fill_every_bars: e.target.value ? parseInt(e.target.value, 10) : null 
                }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-4">
            <button
              onClick={handleSuggest}
              disabled={isLoading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-2 rounded font-medium"
            >
              {isLoading ? 'Generating...' : 'Suggest Pattern'}
            </button>

            {suggestedNotes && (
              <>
                <button
                  onClick={handlePreview}
                  className={`px-4 py-2 rounded font-medium flex items-center space-x-2 ${
                    isPlaying 
                      ? 'bg-red-600 hover:bg-red-700 text-white' 
                      : 'bg-green-600 hover:bg-green-700 text-white'
                  }`}
                >
                  {isPlaying ? <Square size={16} /> : <Play size={16} />}
                  <span>{isPlaying ? 'Stop' : 'Preview'}</span>
                </button>

                <button
                  onClick={handleApply}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium"
                >
                  Apply
                </button>
              </>
            )}
          </div>

          {/* Pattern Preview */}
          {suggestedNotes && (
            <div className="bg-gray-700 rounded p-4">
              <h3 className="text-lg font-medium text-white mb-3">Generated Pattern</h3>
              <div className="space-y-2">
                {Object.entries(suggestedNotes).map(([drum, notes]) => (
                  <div key={drum} className="flex items-center space-x-3">
                    <span className="w-16 text-sm font-medium text-gray-300 capitalize">
                      {drum}:
                    </span>
                    <span className="text-sm text-gray-400">
                      {notes.length} hits
                    </span>
                    <div className="flex-1 bg-gray-800 h-2 rounded overflow-hidden">
                      {notes.map((note, i) => (
                        <div
                          key={i}
                          className="h-full bg-blue-500 inline-block"
                          style={{
                            width: '2px',
                            marginLeft: `${(note.seconds / 8) * 100}%`
                          }}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EditDrumsModal;
