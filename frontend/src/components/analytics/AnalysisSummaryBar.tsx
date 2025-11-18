import React from 'react'
import { useDawStore } from '../../state/dawStore'

export default function AnalysisSummaryBar() {
  const { project } = useDawStore()
  const a = project?.analytics
  
  return (
    <div className="flex items-center gap-4 px-3 py-1 text-sm bg-slate-950 text-slate-200 border-b border-slate-800">
      <span className="opacity-70">Style:</span> 
      <span className="font-medium">{a?.style?.genre || '—'}{a?.style?.sub ? ` / ${a.style.sub}` : ''}</span>
      <span className="opacity-70">Tempo:</span> 
      <span className="font-medium">{(a?.globalBpm || project?.bpm)?.toFixed(1)} BPM</span>
      <span className="opacity-70">Time Sig:</span> 
      <span className="font-medium">{(a?.timeSig || project?.timeSig)?.join('/')}</span>
      <span className="ml-auto opacity-50">Audio analytics</span>
    </div>
  )
}
