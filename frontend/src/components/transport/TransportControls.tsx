// Transport Controls - Play/Pause/Stop/Loop controls for WebDAW
// Integrates with Tone.js transport and DAW store

import React from 'react'
import { Play, Pause, Square, RotateCcw, SkipBack, SkipForward } from 'lucide-react'
import { useDawStore } from '../../state/dawStore'
import * as Tone from 'tone'
import { Tooltip } from '../Tooltip'

export default function TransportControls() {
  const { 
    playing, 
    cursorSec, 
    loopEnabled, 
    loopStartSec, 
    loopEndSec,
    play,
    pause,
    setCursor,
    toggleLoop,
    setLoop
  } = useDawStore()

  const handlePlay = async () => {
    try {
      // Ensure audio context is started
      if (Tone.context.state === 'suspended') {
        await Tone.start()
      }
      
      if (playing) {
        pause()
      } else {
        play()
      }
    } catch (error) {
      console.error('Transport control error:', error)
    }
  }

  const handleStop = () => {
    pause()
    setCursor(0)
  }

  const handleRewind = () => {
    setCursor(Math.max(0, cursorSec - 10))
  }

  const handleFastForward = () => {
    setCursor(cursorSec + 10)
  }

  const handleLoopToggle = () => {
    if (!loopEnabled) {
      // Enable loop with default region
      const start = Math.max(0, cursorSec - 4)
      const end = cursorSec + 4
      setLoop(start, end)
    }
    toggleLoop(!loopEnabled)
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = (seconds % 60).toFixed(1)
    return `${mins}:${secs.padStart(4, '0')}`
  }

  return (
    <div className="flex items-center gap-4">
      {/* Main transport buttons */}
      <div className="flex items-center gap-2">
        <Tooltip content="Rewind 10s" placement="top" maxWidthClassName="w-28">
          <button
            onClick={handleRewind}
            className="p-2 bg-slate-700 hover:bg-slate-600 text-white rounded"
          >
            <SkipBack size={16} />
          </button>
        </Tooltip>

        <Tooltip content={playing ? 'Pause' : 'Play'} placement="top" maxWidthClassName="w-20">
          <button
            onClick={handlePlay}
            className={`p-3 rounded-full ${
              playing 
                ? 'bg-red-600 hover:bg-red-700' 
                : 'bg-green-600 hover:bg-green-700'
            } text-white`}
          >
            {playing ? <Pause size={20} /> : <Play size={20} />}
          </button>
        </Tooltip>

        <Tooltip content="Stop" placement="top" maxWidthClassName="w-20">
          <button
            onClick={handleStop}
            className="p-2 bg-slate-700 hover:bg-slate-600 text-white rounded"
          >
            <Square size={16} />
          </button>
        </Tooltip>

        <Tooltip content="Fast Forward 10s" placement="top" maxWidthClassName="w-36">
          <button
            onClick={handleFastForward}
            className="p-2 bg-slate-700 hover:bg-slate-600 text-white rounded"
          >
            <SkipForward size={16} />
          </button>
        </Tooltip>
      </div>

      {/* Time display */}
      <div className="bg-slate-800 px-3 py-2 rounded font-mono text-slate-300">
        {formatTime(cursorSec)}
      </div>

      {/* Loop controls */}
      <div className="flex items-center gap-2">
        <Tooltip content="Toggle Loop" placement="top" maxWidthClassName="w-28">
          <button
            onClick={handleLoopToggle}
            className={`p-2 rounded ${
              loopEnabled 
                ? 'bg-orange-600 hover:bg-orange-700 text-white' 
                : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
            }`}
          >
            <RotateCcw size={16} />
          </button>
        </Tooltip>

        {loopEnabled && (
          <div className="text-xs text-slate-400">
            Loop: {formatTime(loopStartSec)} - {formatTime(loopEndSec)}
          </div>
        )}
      </div>

      {/* Tempo display */}
      <div className="bg-slate-800 px-3 py-2 rounded">
        <span className="text-xs text-slate-400 mr-2">BPM:</span>
        <span className="text-slate-300 font-mono">
          {Math.round(Tone.Transport.bpm.value)}
        </span>
      </div>

      {/* Status indicator */}
      <div className={`w-2 h-2 rounded-full ${
        playing ? 'bg-green-500 animate-pulse' : 'bg-slate-600'
      }`} />
    </div>
  )
}
