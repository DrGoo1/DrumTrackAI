import React, { useEffect, useState } from 'react'
import { useDawStore } from '../state/dawStore'

const LANES = ['kick','snare','hihat','tom','ride','crash']

export const KitBuilderModal: React.FC<{ open:boolean; onClose:()=>void }>=({ open, onClose })=>{
  const { setKit } = useDawStore()
  const [mapping, setMapping] = useState<Record<string,string>>({})

  useEffect(()=>{ if(open) setMapping({}) },[open])

  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-neutral-900 text-white rounded-xl p-4 w-[780px] shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <div className="font-semibold text-lg">Kit Builder</div>
          <button
            className="bg-neutral-800 px-2 py-1 rounded text-sm"
            onClick={async ()=>{
              const r = await fetch('/api/samples/kits/default'); 
              const j = await r.json();
              setMapping(j.kit_map||{});
            }}
          >Load Default Kit</button>
        </div>
        <div className="space-y-2 max-h-[50vh] overflow-y-auto">
          {LANES.map(l=> (
            <div key={l} className="grid grid-cols-5 gap-2 items-center">
              <div className="col-span-1 opacity-80">{l}</div>
              <input
                className="col-span-3 bg-neutral-800 px-2 py-1 rounded"
                placeholder={`/samples/kits/default/${l}.wav`}
                value={mapping[l]||''}
                onChange={(e)=> setMapping(m=>({...m,[l]:e.target.value}))}
              />
              <button className="bg-neutral-700 px-2 py-1 rounded">Browse</button>
            </div>
          ))}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button className="px-3 py-1 bg-neutral-700 rounded" onClick={onClose}>Cancel</button>
          <button className="px-3 py-1 bg-emerald-600 rounded" onClick={()=>{ setKit(mapping); onClose() }}>Save Kit</button>
        </div>
      </div>
    </div>
  )
}
