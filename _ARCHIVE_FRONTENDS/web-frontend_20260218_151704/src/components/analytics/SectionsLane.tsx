import React from 'react'
import { useDawStore } from '../../state/dawStore'

export default function SectionsLane() {
  const { project, pxPerSecond } = useDawStore()
  const secs = project?.analytics?.sections || []
  
  return (
    <div className="relative h-6 bg-slate-900 border-b border-slate-800 text-xs text-slate-100">
      {secs.map((s, i) => (
        <div 
          key={i} 
          className="absolute top-0 bottom-0 px-2 flex items-center bg-emerald-600/10 border-r border-emerald-500/40" 
          style={{ 
            left: s.startSec * pxPerSecond, 
            width: Math.max(2, (s.endSec - s.startSec) * pxPerSecond) 
          }}
        >
          <span className="opacity-90">{s.label}</span>
        </div>
      ))}
    </div>
  )
}
