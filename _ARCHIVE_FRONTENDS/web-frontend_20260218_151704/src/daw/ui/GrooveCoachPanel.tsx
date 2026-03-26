import React, { useEffect, useMemo, useState } from 'react'
import { useDawStore } from '../state/dawStore'

type Goal = { id: string; label?: string; description?: string; tags?: string[] }

export const GrooveCoachPanel: React.FC = () => {
  const { jobId, grooveMetrics, setGrooveMetrics } = useDawStore()
  const [loading, setLoading] = useState(false)
  const [goalsLoading, setGoalsLoading] = useState(false)
  const [soundGoals, setSoundGoals] = useState<Goal[]>([])
  const [techGoals, setTechGoals] = useState<Goal[]>([])
  const [selectedGoalIds, setSelectedGoalIds] = useState<string[]>([])

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      setGoalsLoading(true)
      try {
        const res = await fetch('/api/groove/goals')
        const j = await res.json()
        if (cancelled) return
        setSoundGoals(Array.isArray(j.sound_first) ? j.sound_first : [])
        setTechGoals(Array.isArray(j.technique_first) ? j.technique_first : [])
      } finally {
        if (!cancelled) setGoalsLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [])

  const toggleGoal = (id: string) => {
    setSelectedGoalIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const selectedCount = selectedGoalIds.length
  const selectedLabel = useMemo(() => {
    if (!selectedCount) return 'None'
    return `${selectedCount} selected`
  }, [selectedCount])

  const analyze = async()=>{
    setLoading(true)
    const res = await fetch('/api/groove/analyze', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, section_id: 'all', goals: selectedGoalIds }) })
    const j = await res.json(); setGrooveMetrics(j); setLoading(false)
  }

  return (
    <div className="bg-neutral-900 text-white rounded p-3 space-y-2">
      <div className="font-semibold">Groove Coach</div>
      <div className="text-xs opacity-80">Goals: {goalsLoading ? 'Loading…' : selectedLabel}</div>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="space-y-1">
          <div className="opacity-80">Sound-first</div>
          <div className="space-y-1 max-h-32 overflow-auto pr-1">
            {(soundGoals || []).map((g) => (
              <label key={g.id} className="flex gap-2 items-start">
                <input type="checkbox" checked={selectedGoalIds.includes(g.id)} onChange={() => toggleGoal(g.id)} />
                <span>
                  <div className="font-medium">{g.label || g.id}</div>
                  {g.description && <div className="opacity-70">{g.description}</div>}
                </span>
              </label>
            ))}
          </div>
        </div>
        <div className="space-y-1">
          <div className="opacity-80">Technique-first</div>
          <div className="space-y-1 max-h-32 overflow-auto pr-1">
            {(techGoals || []).map((g) => (
              <label key={g.id} className="flex gap-2 items-start">
                <input type="checkbox" checked={selectedGoalIds.includes(g.id)} onChange={() => toggleGoal(g.id)} />
                <span>
                  <div className="font-medium">{g.label || g.id}</div>
                  {g.description && <div className="opacity-70">{g.description}</div>}
                </span>
              </label>
            ))}
          </div>
        </div>
      </div>
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
          {grooveMetrics.config_patch && (
            <div className="opacity-80 mt-2">
              <div>Config Patch:</div>
              <pre className="text-xs bg-black/30 rounded p-2 overflow-auto max-h-40">{JSON.stringify(grooveMetrics.config_patch, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
