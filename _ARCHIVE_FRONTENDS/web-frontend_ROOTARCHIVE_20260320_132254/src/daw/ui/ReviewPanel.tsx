import React, { useEffect, useState } from 'react'
import { useDawStore } from '../state/dawStore'

export const ReviewPanel: React.FC = ()=>{
  const { jobId, comments, setComments, cursorSec } = useDawStore()
  const [text, setText] = useState('')
  const load = async()=>{ const res = await fetch(`/api/review/comments?job_id=${jobId}`); const j = await res.json(); setComments(j.items||[]) }
  const add = async()=>{
    if (!text.trim()) return
    await fetch('/api/review/comments', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, section_id: 'all', time_sec: cursorSec, text }) })
    setText(''); load()
  }
  useEffect(()=>{ load() },[jobId])
  return (
    <div className="bg-neutral-900 text-white rounded p-3 space-y-2">
      <div className="font-semibold">Review</div>
      <div className="flex gap-2">
        <input className="flex-1 bg-neutral-800 px-2 py-1 rounded" placeholder="Leave a note at the current cursor…" value={text} onChange={e=>setText(e.target.value)} />
        <button className="px-3 py-1 bg-emerald-600 rounded" onClick={add}>Add</button>
      </div>
      <div className="max-h-64 overflow-y-auto divide-y divide-neutral-800 text-sm">
        {comments.map((c:any)=>(
          <div key={c.id} className="py-2">
            <div className="opacity-70 text-xs">{c.time_sec.toFixed(2)}s</div>
            <div>{c.text}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
