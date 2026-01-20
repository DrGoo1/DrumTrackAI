import React from 'react'

export type ImpactChain = {
  low:{ drive_type:'analog'|'tape'|'poly'; drive_amount:number; snap:number; blend:number }
  high:{ drive_type:'analog'|'tape'|'poly'; drive_amount:number; snap:number; blend:number }
  space:{ on:boolean; type:'algo'|'conv'; predelay_ms:number; duck:number; ir?:string }
}

const knob = 'bg-neutral-800 rounded px-2 py-1 w-20'

export const ImpactDrumsPanel: React.FC<{ value:ImpactChain; onChange:(v:ImpactChain)=>void }>=({ value, onChange })=>{
  const set=(path:string,val:any)=>{
    const v = JSON.parse(JSON.stringify(value))
    const [a,b] = path.split('.')
    ;(v as any)[a][b] = val
    onChange(v)
  }
  return (
    <div className="bg-neutral-900 text-white rounded p-3 space-y-3">
      <div className="font-semibold">Impact Drums</div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="opacity-80 mb-1">Low Band</div>
          <div className="flex items-center gap-2">
            <select className={knob} value={value.low.drive_type} onChange={e=>set('low.drive_type', e.target.value)}>
              <option value="analog">Analog</option>
              <option value="tape">Tape</option>
              <option value="poly">Poly</option>
            </select>
            <label>Drive</label>
            <input className={knob} type="number" step={0.01} min={0} max={1} value={value.low.drive_amount} onChange={e=>set('low.drive_amount', parseFloat(e.target.value))}/>
            <label>Snap</label>
            <input className={knob} type="number" step={0.01} min={0} max={1} value={value.low.snap} onChange={e=>set('low.snap', parseFloat(e.target.value))}/>
            <label>Blend</label>
            <input className={knob} type="number" step={0.01} min={0} max={1} value={value.low.blend} onChange={e=>set('low.blend', parseFloat(e.target.value))}/>
          </div>
        </div>
        <div>
          <div className="opacity-80 mb-1">High Band</div>
          <div className="flex items-center gap-2">
            <select className={knob} value={value.high.drive_type} onChange={e=>set('high.drive_type', e.target.value)}>
              <option value="analog">Analog</option>
              <option value="tape">Tape</option>
              <option value="poly">Poly</option>
            </select>
            <label>Drive</label>
            <input className={knob} type="number" step={0.01} min={0} max={1} value={value.high.drive_amount} onChange={e=>set('high.drive_amount', parseFloat(e.target.value))}/>
            <label>Snap</label>
            <input className={knob} type="number" step={0.01} min={0} max={1} value={value.high.snap} onChange={e=>set('high.snap', parseFloat(e.target.value))}/>
            <label>Blend</label>
            <input className={knob} type="number" step={0.01} min={0} max={1} value={value.high.blend} onChange={e=>set('high.blend', parseFloat(e.target.value))}/>
          </div>
        </div>
      </div>
      <div>
        <div className="opacity-80 mb-1">Space</div>
        <div className="flex items-center gap-2 flex-wrap">
          <label>Enable</label>
          <input type="checkbox" checked={value.space.on} onChange={e=>set('space.on', e.target.checked)} />
          <select className={knob} value={value.space.type} onChange={e=>set('space.type', e.target.value)}>
            <option value="algo">Algorithmic</option>
            <option value="conv">Convolution</option>
          </select>
          <label>Pre</label>
          <input className={knob} type="number" value={value.space.predelay_ms} onChange={e=>set('space.predelay_ms', parseFloat(e.target.value))}/>
          <label>Duck</label>
          <input className={knob} type="number" step={0.01} min={0} max={1} value={value.space.duck} onChange={e=>set('space.duck', parseFloat(e.target.value))}/>
          {value.space.type==='conv' && (
            <input className="bg-neutral-800 rounded px-2 py-1 w-72" placeholder="/samples/irs/room.wav" value={value.space.ir||''} onChange={e=>set('space.ir', e.target.value)} />
          )}
        </div>
      </div>
    </div>
  )
}
