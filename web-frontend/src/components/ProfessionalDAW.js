import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, Pause, Square, SkipBack, SkipForward, Volume2, Settings,
  Upload, Download, Save, FolderOpen, Edit, Undo, Redo,
  ZoomIn, ZoomOut, Grid, Music, Headphones, ArrowLeft
} from 'lucide-react';

// Import ChatGPT-5 DAW components
import EditDrumsModal from './EditDrumsModal';
import { 
  applyQuantize, 
  applySwing, 
  applyHumanize, 
  MidiHistoryManager 
} from '../utils/midiOperations';

const ProfessionalDAW = ({ onBack, systemStatus }) => {
  // Core DAW state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(240); // 4 minutes default
  const [tempo, setTempo] = useState(120);
  const [zoom, setZoom] = useState(1.0);
  
  // Project state
  const [projectName, setProjectName] = useState('Untitled Project');
  const [tracks, setTracks] = useState([]);
  const [selectedTrack, setSelectedTrack] = useState(null);
  
  // Edit Drums Modal state
  const [showEditDrums, setShowEditDrums] = useState(false);
  const [currentSectionId, setCurrentSectionId] = useState(null);
  const [drumNotes, setDrumNotes] = useState({});
  
  // MIDI operations
  const historyManagerRef = useRef(new MidiHistoryManager());
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  
  // Audio context and playback
  const audioContextRef = useRef(null);
  const playbackRef = useRef(null);

  useEffect(() => {
    // Initialize audio context
    initializeAudioContext();
    
    // Initialize default project
    initializeDefaultProject();
    
    return () => {
      if (playbackRef.current) {
        clearInterval(playbackRef.current);
      }
    };
  }, []);

  const initializeAudioContext = async () => {
    try {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      console.log('Audio context initialized');
    } catch (error) {
      console.error('Failed to initialize audio context:', error);
    }
  };

  const initializeDefaultProject = () => {
    const defaultTracks = [
      { 
        id: 'master', 
        name: 'Master', 
        type: 'master', 
        color: '#DC2626', 
        volume: 85, 
        pan: 0, 
        muted: false, 
        solo: false,
        isMaster: true 
      },
      { 
        id: 'drums', 
        name: 'Drums', 
        type: 'drums', 
        color: '#7C3AED', 
        volume: 80, 
        pan: 0, 
        muted: false, 
        solo: false,
        hasAudio: false 
      },
      { 
        id: 'bass', 
        name: 'Bass', 
        type: 'bass', 
        color: '#DC2626', 
        volume: 75, 
        pan: 0, 
        muted: false, 
        solo: false,
        hasAudio: false 
      },
      { 
        id: 'vocals', 
        name: 'Vocals', 
        type: 'vocals', 
        color: '#059669', 
        volume: 85, 
        pan: 0, 
        muted: false, 
        solo: false,
        hasAudio: false 
      },
      { 
        id: 'other', 
        name: 'Other', 
        type: 'other', 
        color: '#D97706', 
        volume: 70, 
        pan: 0, 
        muted: false, 
        solo: false,
        hasAudio: false 
      }
    ];
    
    setTracks(defaultTracks);
  };

  // Transport controls
  const handlePlay = () => {
    if (!isPlaying) {
      setIsPlaying(true);
      playbackRef.current = setInterval(() => {
        setCurrentTime(prev => {
          const newTime = prev + 0.1;
          if (newTime >= duration) {
            handleStop();
            return duration;
          }
          return newTime;
        });
      }, 100);
    } else {
      setIsPlaying(false);
      if (playbackRef.current) {
        clearInterval(playbackRef.current);
        playbackRef.current = null;
      }
    }
  };

  const handleStop = () => {
    setIsPlaying(false);
    setCurrentTime(0);
    if (playbackRef.current) {
      clearInterval(playbackRef.current);
      playbackRef.current = null;
    }
  };

  // MIDI Operations Functions
  const pushToHistory = (notes, description) => {
    historyManagerRef.current.pushState(notes, description);
    const historyInfo = historyManagerRef.current.getHistoryInfo();
    setCanUndo(historyInfo.canUndo);
    setCanRedo(historyInfo.canRedo);
  };

  const handleUndo = () => {
    const previousState = historyManagerRef.current.undo();
    if (previousState) {
      setDrumNotes(previousState.notes);
      const historyInfo = historyManagerRef.current.getHistoryInfo();
      setCanUndo(historyInfo.canUndo);
      setCanRedo(historyInfo.canRedo);
    }
  };

  const handleRedo = () => {
    const nextState = historyManagerRef.current.redo();
    if (nextState) {
      setDrumNotes(nextState.notes);
      const historyInfo = historyManagerRef.current.getHistoryInfo();
      setCanUndo(historyInfo.canUndo);
      setCanRedo(historyInfo.canRedo);
    }
  };

  const quantize = (strength = 1.0) => {
    pushToHistory(drumNotes, `Quantize ${Math.round(strength * 100)}%`);
    setDrumNotes(prev => applyQuantize(prev, { strength }));
  };

  const swing = (amount = 0.5) => {
    pushToHistory(drumNotes, `Swing ${Math.round(amount * 100)}%`);
    setDrumNotes(prev => applySwing(prev, { amount }));
  };

  const humanize = (amount = 0.15) => {
    pushToHistory(drumNotes, `Humanize ${Math.round(amount * 100)}%`);
    setDrumNotes(prev => applyHumanize(prev, { amount }));
  };

  // Edit Drums Functions
  const openEditDrums = (sectionId) => {
    setCurrentSectionId(sectionId);
    setShowEditDrums(true);
  };

  const handleDrumNotesApply = (newNotes) => {
    pushToHistory(drumNotes, 'Apply Generated Pattern');
    setDrumNotes(prev => ({ ...prev, ...newNotes }));
  };

  // Track controls
  const updateTrack = (trackId, property, value) => {
    setTracks(prev => prev.map(track => 
      track.id === trackId ? { ...track, [property]: value } : track
    ));
  };

  const toggleMute = (trackId) => {
    updateTrack(trackId, 'muted', !tracks.find(t => t.id === trackId)?.muted);
  };

  const toggleSolo = (trackId) => {
    updateTrack(trackId, 'solo', !tracks.find(t => t.id === trackId)?.solo);
  };

  // Utility functions
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const centisecs = Math.floor((seconds % 1) * 100);
    return `${mins}:${secs.toString().padStart(2, '0')}.${centisecs.toString().padStart(2, '0')}`;
  };

  const formatBBT = (seconds) => {
    const beatsPerSecond = tempo / 60;
    const totalBeats = seconds * beatsPerSecond;
    const bars = Math.floor(totalBeats / 4) + 1;
    const beats = Math.floor(totalBeats % 4) + 1;
    const ticks = Math.floor((totalBeats % 1) * 480);
    return `${bars}.${beats}.${ticks.toString().padStart(3, '0')}`;
  };

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={onBack}
              className="flex items-center space-x-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Back</span>
            </button>
            
            <div className="flex items-center space-x-3">
              <Music className="w-6 h-6 text-purple-500" />
              <h1 className="text-xl font-bold">DrumTracKAI Professional DAW</h1>
            </div>
            
            <div className="text-sm text-gray-400">
              {projectName}
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <button className="flex items-center space-x-2 px-3 py-2 bg-gray-700 hover:bg-blue-600 rounded-lg">
              <Upload className="w-4 h-4" />
              <span className="text-sm">Import</span>
            </button>
            
            <button
              onClick={() => openEditDrums('current')}
              className="flex items-center space-x-2 px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg"
            >
              <Edit className="w-4 h-4" />
              <span className="text-sm">Edit Drums</span>
            </button>
            
            <button className="flex items-center space-x-2 px-3 py-2 bg-gray-700 hover:bg-green-600 rounded-lg">
              <Save className="w-4 h-4" />
              <span className="text-sm">Save</span>
            </button>
          </div>
        </div>
      </div>

      {/* Transport Controls */}
      <div className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button 
              onClick={handlePlay}
              className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg"
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
              <span>{isPlaying ? 'Pause' : 'Play'}</span>
            </button>
            <button onClick={handleStop} className="p-3 bg-gray-700 hover:bg-gray-600 rounded-lg">
              <Square className="w-5 h-5" />
            </button>
            
            {/* MIDI Operations */}
            <div className="flex items-center space-x-2 ml-6">
              <div className="flex items-center space-x-1">
                <button
                  onClick={handleUndo}
                  disabled={!canUndo}
                  className="p-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:opacity-50 rounded"
                  title="Undo"
                >
                  <Undo className="w-4 h-4" />
                </button>
                <button
                  onClick={handleRedo}
                  disabled={!canRedo}
                  className="p-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:opacity-50 rounded"
                  title="Redo"
                >
                  <Redo className="w-4 h-4" />
                </button>
              </div>
              
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => quantize(0.8)}
                  className="px-3 py-1 bg-gray-700 hover:bg-green-600 rounded text-xs"
                  title="Quantize 80%"
                >
                  Quantize
                </button>
                <button
                  onClick={() => swing(0.5)}
                  className="px-3 py-1 bg-gray-700 hover:bg-blue-600 rounded text-xs"
                  title="Swing 50%"
                >
                  Swing
                </button>
                <button
                  onClick={() => humanize(0.15)}
                  className="px-3 py-1 bg-gray-700 hover:bg-purple-600 rounded text-xs"
                  title="Humanize 15%"
                >
                  Humanize
                </button>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-6">
            <div className="text-lg font-mono bg-gray-700 px-4 py-2 rounded border border-gray-600">
              <div className="text-white">{formatTime(currentTime)} / {formatTime(duration)}</div>
              <div className="text-xs text-blue-300 text-center">Time</div>
            </div>
            <div className="text-lg font-mono bg-gray-700 px-4 py-2 rounded border border-gray-600">
              <div className="text-blue-300">{formatBBT(currentTime)}</div>
              <div className="text-xs text-blue-300 text-center">Bars.Beats.Ticks</div>
            </div>
          </div>
          
          <div className="flex items-center space-x-3 bg-gray-700 px-3 py-2 rounded">
            <span className="text-sm font-medium">Zoom:</span>
            <button 
              onClick={() => setZoom(Math.max(0.25, zoom - 0.25))}
              className="px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded text-xs"
            >
              <ZoomOut className="w-3 h-3" />
            </button>
            <button 
              onClick={() => setZoom(Math.min(4, zoom + 0.25))}
              className="px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded text-xs"
            >
              <ZoomIn className="w-3 h-3" />
            </button>
            <span className="text-sm font-mono w-12 text-center">{zoom.toFixed(1)}x</span>
          </div>
        </div>
      </div>

      {/* Main DAW Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Mixer Panel */}
        <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
          <div className="bg-gray-700 p-3 border-b border-gray-600">
            <h3 className="font-semibold text-white text-sm">Professional Mixer</h3>
            <div className="text-xs text-gray-400">
              {tracks.filter(t => !t.isMaster).length} Tracks + Master
            </div>
          </div>
          
          <div className="flex-1 overflow-auto p-2 space-y-2">
            {tracks.map(track => (
              <div
                key={track.id}
                className={`bg-gray-700 rounded-lg p-3 border-2 ${
                  selectedTrack === track.id ? 'border-purple-500' : 'border-transparent'
                }`}
                onClick={() => setSelectedTrack(track.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: track.color }}
                    />
                    <span className="text-sm font-medium">{track.name}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleMute(track.id);
                      }}
                      className={`px-2 py-1 text-xs rounded ${
                        track.muted ? 'bg-red-600 text-white' : 'bg-gray-600 hover:bg-red-600'
                      }`}
                    >
                      M
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSolo(track.id);
                      }}
                      className={`px-2 py-1 text-xs rounded ${
                        track.solo ? 'bg-yellow-600 text-white' : 'bg-gray-600 hover:bg-yellow-600'
                      }`}
                    >
                      S
                    </button>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Volume2 className="w-4 h-4 text-gray-400" />
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={track.volume}
                      onChange={(e) => updateTrack(track.id, 'volume', parseInt(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-xs text-gray-400 w-8">{track.volume}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-400 w-8">Pan</span>
                    <input
                      type="range"
                      min="-50"
                      max="50"
                      value={track.pan}
                      onChange={(e) => updateTrack(track.id, 'pan', parseInt(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-xs text-gray-400 w-8">
                      {track.pan > 0 ? `R${track.pan}` : track.pan < 0 ? `L${Math.abs(track.pan)}` : 'C'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Timeline Area */}
        <div className="flex-1 flex flex-col">
          <div className="bg-gray-700 p-3 border-b border-gray-600">
            <h3 className="font-semibold text-white text-sm">Timeline & Arrangement</h3>
            <div className="text-xs text-gray-400">
              Tempo: {tempo} BPM • Duration: {formatTime(duration)} • Zoom: {zoom.toFixed(1)}x
            </div>
          </div>
          
          <div className="flex-1 bg-gray-800 p-4">
            <div className="text-center py-20">
              <div className="text-6xl mb-4">🎵</div>
              <h3 className="text-2xl font-bold mb-2">Professional DAW Ready</h3>
              <p className="text-gray-400 mb-6">
                Import audio files or click "Edit Drums" to start creating with LLM-driven drum generation
              </p>
              
              <div className="flex justify-center space-x-4">
                <button className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg">
                  <Upload className="w-5 h-5" />
                  <span>Import Audio</span>
                </button>
                
                <button
                  onClick={() => openEditDrums('intro')}
                  className="flex items-center space-x-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg"
                >
                  <Edit className="w-5 h-5" />
                  <span>Generate Drums</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div className="bg-gray-800 border-t border-gray-700 p-3">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-4">
            <span className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full animate-pulse ${
                isPlaying ? 'bg-green-500' : 'bg-blue-500'
              }`} />
              <span className="font-medium">{isPlaying ? 'Playing...' : 'Ready'}</span>
            </span>
            <span className="text-gray-400">•</span>
            <span>ChatGPT-5 LLM Integration Active</span>
            <span className="text-gray-400">•</span>
            <span>Professional Mode</span>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3 bg-gray-700 px-3 py-1 rounded">
              <span className="text-xs text-green-400">
                {systemStatus?.status === 'healthy' ? 'Backend Online' : 'Backend Offline'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Edit Drums Modal */}
      <EditDrumsModal
        isOpen={showEditDrums}
        onClose={() => setShowEditDrums(false)}
        jobId="demo_project_01"
        sectionId={currentSectionId}
        currentNotes={drumNotes}
        onApply={handleDrumNotesApply}
      />
    </div>
  );
};

export default ProfessionalDAW;
