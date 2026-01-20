import React, { useState } from 'react'
import { useDawStore } from '../state/dawStore'

export const ExportDialog: React.FC<{ open:boolean; onClose:()=>void }>=({ open, onClose })=>{
  const { jobId, kitMap } = useDawStore()
  const [mode, setMode] = useState<'midi'|'stems'|'stereo'>('stereo')

  const exportNow = async()=>{
    const payload = { job_id: jobId, mode, kit_map: kitMap, midi_lanes: {} }
    const res = await fetch(`/api/exports`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) })
    const j = await res.json()
    alert(`Export queued: ${j.export_id}`)
    onClose()
  }

  if(!open) return null
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-neutral-900 text-white rounded-xl p-4 w-[520px]">
        <div className="font-semibold text-lg mb-3">Export</div>
        <div className="space-y-2">
          {(['midi','stems','stereo'] as const).map(m => (
            <label key={m} className="flex items-center gap-2">
              <input type="radio" name="mode" checked={mode===m} onChange={()=>setMode(m)} />
              <span className="capitalize">{m}</span>
            </label>
          ))}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button className="px-3 py-1 bg-neutral-700 rounded" onClick={onClose}>Cancel</button>
          <button className="px-3 py-1 bg-emerald-600 rounded" onClick={exportNow}>Queue Export</button>
        </div>
      </div>
    </div>
  )
}
