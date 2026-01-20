import React from 'react'
import PanKnob from './PanKnob'
import Meter from './Meter'
import { Tooltip } from '../Tooltip'

export default function Strip({ 
  id, name, gainDb, pan, mute, solo, onGain, onPan, onMute, onSolo, getAnalyser 
}: {
  id: string; 
  name: string; 
  gainDb: number; 
  pan: number; 
  mute: boolean; 
  solo: boolean; 
  onGain: (v: number) => void; 
  onPan: (v: number) => void; 
  onMute: () => void; 
  onSolo: () => void; 
  getAnalyser: () => AnalyserNode | null
}) {
  return (
    <div className="p-2 bg-slate-700 rounded-xl text-slate-50 w-[260px]">
      <div className="flex items-center justify-between mb-2 text-sm">
        <Tooltip content={name} placement="top" maxWidthClassName="w-56">
          <span className="truncate">{name}</span>
        </Tooltip>
        <div className="flex gap-1">
          <button onClick={onMute} className={`px-2 py-0.5 rounded ${mute ? 'bg-rose-600' : 'bg-slate-600'}`}>M</button>
          <button onClick={onSolo} className={`px-2 py-0.5 rounded ${solo ? 'bg-amber-500' : 'bg-slate-600'}`}>S</button>
        </div>
      </div>
      <div className="flex gap-3 items-center">
        <Meter getNode={getAnalyser} />
        <div className="flex-1">
          <div className="text-xs opacity-80">Gain (dB)</div>
          <input 
            type="range" 
            min={-24} 
            max={6} 
            step={0.1} 
            value={gainDb} 
            onChange={e => onGain(parseFloat(e.target.value))} 
            className="w-full" 
          />
          <div className="mt-2 flex items-center justify-between">
            <div className="text-xs opacity-80">Pan</div>
            <PanKnob value={pan} onChange={onPan} />
          </div>
        </div>
      </div>
    </div>
  )
}
