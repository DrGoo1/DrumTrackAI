import React, { useMemo, useState } from 'react'
import { useDawStore } from '../../state/dawStore'

export default function TempoLane() {
  const { project, setTempoMap, pxPerSecond } = useDawStore()
  const points = useMemo(() => (
    project?.analytics?.tempoMap?.length ? 
    project.analytics!.tempoMap! : 
    [{ tSec: 0, bpm: project?.bpm || 120 }]
  ), [project])
  
  const [drag, setDrag] = useState<{ i: number; y: number; bpm: number } | null>(null)
  const min = 50, max = 220, h = 52
  const yOf = (b: number) => h - (b - min) / (max - min) * h
  
  const onDown = (i: number, e: React.MouseEvent) => setDrag({ i, y: e.clientY, bpm: points[i].bpm })
  const onMove = (e: React.MouseEvent) => { 
    if (!drag) return
    const dy = e.clientY - drag.y
    const bpm = Math.max(min, Math.min(max, drag.bpm - dy * 0.5))
    const next = points.map((p, ix) => ix === drag.i ? { ...p, bpm } : p)
    setTempoMap(next) 
  }
  const onUp = () => setDrag(null)
  
  return (
    <div className="relative h-[52px] bg-slate-900 border-b border-slate-800 select-none" onMouseMove={onMove} onMouseUp={onUp}>
      {points.map((p, i) => { 
        const x = p.tSec * pxPerSecond
        return (
          <div key={i} className="absolute" style={{ left: x }}>
            <div 
              className="w-2 h-2 bg-emerald-400 rounded-full translate-x-[-4px] translate-y-[-4px] cursor-ns-resize" 
              style={{ top: yOf(p.bpm) }} 
              onMouseDown={(e) => onDown(i, e)} 
            />
          </div>
        )
      })}
    </div>
  )
}
