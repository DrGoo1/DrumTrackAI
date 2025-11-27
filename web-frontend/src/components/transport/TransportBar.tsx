import React, { useEffect } from 'react'
import * as Tone from 'tone'
import { useDawStore } from '../../state/dawStore'
import { useEngine } from '../../audio/useEngine'

function fmtBBT(sec: number, bpm: number, ts: [number, number]) {
  const [num, den] = ts
  const spb = (60 / bpm) * (4 / den)
  const spbar = spb * num
  const bar = Math.floor(sec / spbar) + 1
  const beat = Math.floor((sec % spbar) / spb) + 1
  const tick = Math.round((((sec % spbar) % spb) / spb) * 480)
  return `${bar}:${beat}:${tick}`
}

export default function TransportBar() {
  const { project, cursorSec, playing, loopEnabled, loopStartSec, loopEndSec, setCursor, play, pause, stop, toggleLoop } = useDawStore()
  const engine = useEngine()
  const bpm = project?.bpm || 120
  const ts = project?.timeSig || [4, 4]

  // Apply play/pause/loop to Tone
  useEffect(() => { 
    if (playing) { 
      Tone.start(); 
      Tone.Transport.start('+0.01') 
    } else { 
      Tone.Transport.pause() 
    } 
  }, [playing])
  
  useEffect(() => { 
    if (loopEnabled) { 
      Tone.Transport.setLoopPoints(loopStartSec, loopEndSec); 
      Tone.Transport.loop = true 
    } else { 
      Tone.Transport.loop = false 
    } 
  }, [loopEnabled, loopStartSec, loopEndSec])

  // Cursor follow from Tone.Transport while playing
  useEffect(() => { 
    let id: number
    const update = () => { 
      useDawStore.getState().setCursor(Tone.Transport.seconds) 
    }
    id = window.setInterval(update, 50)
    return () => window.clearInterval(id) 
  }, [])

  const rewind0 = () => { 
    Tone.Transport.seconds = 0; 
    setCursor(0) 
  }
  
  const prevBar = () => { 
    const [n, d] = ts
    const spb = (60 / bpm) * (4 / d)
    const spbar = spb * n
    const sec = Math.max(0, cursorSec - spbar)
    Tone.Transport.seconds = sec
    setCursor(sec) 
  }
  
  const nextBar = () => { 
    const [n, d] = ts
    const spb = (60 / bpm) * (4 / d)
    const spbar = spb * n
    const sec = Math.min(project?.lengthSec || 1e9, cursorSec + spbar)
    Tone.Transport.seconds = sec
    setCursor(sec) 
  }

  return (
    <div className="flex items-center gap-2 p-2 bg-slate-900 border-b border-slate-800 text-slate-100">
      <button className="px-2 py-1 rounded bg-slate-700" onClick={rewind0}>⏮</button>
      <button className="px-2 py-1 rounded bg-slate-700" onClick={prevBar}>⏪</button>
      {!playing ? (
        <button className="px-3 py-1 rounded bg-emerald-600" onClick={() => play()}>▶</button>
      ) : (
        <button className="px-3 py-1 rounded bg-rose-600" onClick={() => pause()}>⏸</button>
      )}
      <button className="px-2 py-1 rounded bg-slate-700" onClick={() => { Tone.Transport.stop(); stop() }}>⏹</button>
      <button className={`px-2 py-1 rounded ${loopEnabled ? 'bg-amber-500' : 'bg-slate-700'}`} onClick={() => toggleLoop()} title="Toggle Loop">🔁</button>
      <div className="ml-3 font-mono text-sm">{fmtBBT(cursorSec, bpm, ts)}</div>
      <div className="ml-auto text-slate-400">BPM {bpm} • {ts[0]}/{ts[1]}</div>
    </div>
  )
}
