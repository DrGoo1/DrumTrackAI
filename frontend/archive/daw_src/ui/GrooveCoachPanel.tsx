import React, { useState } from 'react'
import { useDawStore } from '../state/dawStore'

export const GrooveCoachPanel: React.FC = () => {
  const { jobId, grooveMetrics, setGrooveMetrics } = useDawStore()
  const [loading, setLoading] = useState(false)

  const analyze = async()=>{
    setLoading(true)
    const res = await fetch('/api/groove/analyze', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, section_id: 'all' }) })
    const j = await res.json(); setGrooveMetrics(j); setLoading(false)
  }

  return (
    <div className="bg-neutral-900 text-white rounded p-3 space-y-2">
      <div className="font-semibold">Groove Coach</div>
      <button className="px-3 py-1 bg-emerald-600 rounded" onClick={analyze} disabled={loading}>{loading?'Analyzing…':'Analyze Groove'}</button>
      {grooveMetrics && (
        <div className="text-sm space-y-1 mt-2">
          <div>Timing: {(grooveMetrics.timing_score*100).toFixed(0)}%</div>
          <div>Velocity: {(grooveMetrics.velocity_score*100).toFixed(0)}%</div>
          <div>Humanization: {(grooveMetrics.humanization_score*100).toFixed(0)}%</div>
          <div>Overall: {(grooveMetrics.overall_score*100).toFixed(0)}%</div>
          <div className="opacity-80">Suggestions:</div>
          <ul className="list-disc ml-5 opacity-80">
            {grooveMetrics.suggestions?.map((h:string,i:number)=>(<li key={i}>{h}</li>))}
          </ul>
        </div>
      )}
    </div>
  )
}
