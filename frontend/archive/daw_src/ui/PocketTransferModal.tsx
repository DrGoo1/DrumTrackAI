import React, { useEffect, useState } from 'react'
import { useDawStore } from '../state/dawStore'

export const PocketTransferModal: React.FC<{ open:boolean; onClose:()=>void }>=({ open, onClose })=>{
  const { setRefLoops } = useDawStore()
  const [loops, setLoops] = useState<any[]>([])
  const [q, setQ] = useState({ bpm:'', style:'', bars:'' })

  useEffect(()=>{ if(open){ setLoops([]) } }, [open])

  const search = async()=>{
    const url = new URL('/api/reference_loops', window.location.origin)
    if (q.bpm) url.searchParams.set('bpm', q.bpm)
    if (q.style) url.searchParams.set('style', q.style)
    if (q.bars) url.searchParams.set('bars', q.bars)
    const res = await fetch(url.toString())
    const j = await res.json(); setLoops(j.items||[]); setRefLoops(j.items||[])
  }

  const transfer = async(loop:any)=>{
    await fetch('/api/groove/transfer', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ loop_id: loop.id }) })
    alert('Transferred feel to current drums (server-side placeholder).')
    onClose()
  }

  if(!open) return null
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-neutral-900 text-white rounded-xl p-4 w-[780px]">
        <div className="font-semibold text-lg mb-3">Pocket Transfer</div>
        <div className="flex gap-2 mb-3">
          <input className="bg-neutral-800 px-2 py-1 rounded" placeholder="BPM" value={q.bpm} onChange={e=>setQ({...q,bpm:e.target.value})}/>
          <input className="bg-neutral-800 px-2 py-1 rounded" placeholder="Style" value={q.style} onChange={e=>setQ({...q,style:e.target.value})}/>
          <input className="bg-neutral-800 px-2 py-1 rounded" placeholder="Bars" value={q.bars} onChange={e=>setQ({...q,bars:e.target.value})}/>
          <button className="px-3 py-1 bg-neutral-700 rounded" onClick={search}>Search</button>
        </div>
        <div className="max-h-[50vh] overflow-y-auto divide-y divide-neutral-800">
          {loops.map((l:any)=>(
            <div key={l.id} className="py-2 flex items-center justify-between">
              <div>
                <div className="font-medium">{l.name||l.id}</div>
                <div className="text-xs opacity-70">{l.style} · {l.bpm} BPM · {l.bars} bars</div>
              </div>
              <button className="px-3 py-1 bg-emerald-600 rounded" onClick={()=>transfer(l)}>Transfer</button>
            </div>
          ))}
          {loops.length===0 && <div className="py-8 text-center opacity-60">No results yet. Try a search.</div>}
        </div>
        <div className="mt-4 text-right"><button className="px-3 py-1 bg-neutral-700 rounded" onClick={onClose}>Close</button></div>
      </div>
    </div>
  )
}
