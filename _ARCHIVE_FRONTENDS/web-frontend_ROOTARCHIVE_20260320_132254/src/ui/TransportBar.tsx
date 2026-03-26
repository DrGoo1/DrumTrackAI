import React from 'react'
import * as Tone from 'tone'
import { useDawStore } from '../state/dawStore'

export default function TransportBar() {
  const { playing, project, cursorSec, play, pause, stop, setBpm } = useDawStore()
  const bpm = project?.bpm || 120

  const handlePlay = async () => {
    if (Tone.getContext().state !== "running") {
      try { 
        await Tone.start() 
        console.log('AudioContext resumed')
      } catch (e) {
        console.warn('Failed to start AudioContext:', e)
      }
    }
    play()
  }

  const handleStop = () => {
    stop()
    Tone.Transport.stop()
    Tone.Transport.position = 0
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex items-center gap-4 p-2 bg-slate-900 border-b border-slate-800">
      {/* Transport Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={handlePlay}
          disabled={playing}
          className="px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white rounded"
        >
          ▶
        </button>
        <button
          onClick={pause}
          disabled={!playing}
          className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 disabled:bg-slate-600 text-white rounded"
        >
          ⏸
        </button>
        <button
          onClick={handleStop}
          className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded"
        >
          ⏹
        </button>
      </div>

      {/* Time Display */}
      <div className="text-slate-300 font-mono">
        {formatTime(cursorSec)}
      </div>

      {/* BPM Control */}
      <div className="flex items-center gap-2">
        <span className="text-slate-400 text-sm">BPM:</span>
        <input
          type="number"
          value={bpm}
          onChange={(e) => setBpm(Number(e.target.value))}
          className="w-16 px-2 py-1 bg-slate-800 text-white rounded"
          min={60}
          max={200}
        />
      </div>

      {/* Audio Context Status */}
      {Tone.getContext().state !== "running" && (
        <div className="text-yellow-400 text-xs">
          Click Play to enable audio
        </div>
      )}
    </div>
  )
}
