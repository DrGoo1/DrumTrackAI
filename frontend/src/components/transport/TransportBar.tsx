import React, { useEffect } from 'react'
import { useDawStore } from '../../state/dawStore'
import { useEngine } from '../../audio/useEngine'
import { Engine } from '../../audio/engine'
import { Tooltip } from '../Tooltip'

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

  // Cursor follow from the audible audio clock (Engine) while playing.
  useEffect(() => { 
    let id: number
    const update = () => { 
      if (!useDawStore.getState().playing) return
      const t = Engine.getCurrentTimeSeconds()
      if (typeof t === 'number' && Number.isFinite(t)) {
        useDawStore.getState().setCursor(t)
      }
    }
    id = window.setInterval(update, 50)
    return () => window.clearInterval(id) 
  }, [])

  const rewind0 = () => { 
    try {
      void Engine.seek(0)
    } catch {
      // ignore
    }
    setCursor(0)
  }
  
  const prevBar = () => { 
    const [n, d] = ts
    const spb = (60 / bpm) * (4 / d)
    const spbar = spb * n
    const sec = Math.max(0, cursorSec - spbar)
    try {
      void Engine.seek(sec)
    } catch {
      // ignore
    }
    setCursor(sec) 
  }
  
  const nextBar = () => { 
    const [n, d] = ts
    const spb = (60 / bpm) * (4 / d)
    const spbar = spb * n
    const sec = Math.min(project?.lengthSec || 1e9, cursorSec + spbar)
    try {
      void Engine.seek(sec)
    } catch {
      // ignore
    }
    setCursor(sec) 
  }

  return (
    <div className="flex items-center gap-2 p-2 bg-slate-900 border-b border-slate-800 text-slate-100">
      <button className="px-2 py-1 rounded bg-slate-700" onClick={rewind0}>⏮</button>
      <button className="px-2 py-1 rounded bg-slate-700" onClick={prevBar}>⏪</button>
      {!playing ? (
        <button className="px-3 py-1 rounded bg-emerald-600" onClick={async () => { await Engine.play(useDawStore.getState().cursorSec); play() }}>▶</button>
      ) : (
        <button className="px-3 py-1 rounded bg-rose-600" onClick={async () => { await Engine.pause(); pause() }}>⏸</button>
      )}
      <button className="px-2 py-1 rounded bg-slate-700" onClick={async () => { await Engine.stop(); stop() }}>⏹</button>
      <Tooltip content="Toggle Loop" placement="top" maxWidthClassName="w-28">
        <button className={`px-2 py-1 rounded ${loopEnabled ? 'bg-amber-500' : 'bg-slate-700'}`} onClick={() => toggleLoop()}>🔁</button>
      </Tooltip>
      <div className="ml-3 font-mono text-sm">{fmtBBT(cursorSec, bpm, ts)}</div>
      <div className="ml-auto text-slate-400">BPM {bpm} • {ts[0]}/{ts[1]}</div>
    </div>
  )
}
