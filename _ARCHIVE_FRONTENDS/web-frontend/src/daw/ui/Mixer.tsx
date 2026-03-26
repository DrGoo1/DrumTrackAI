import React, { useEffect, useRef } from 'react'
import { useDawStore } from '../state/dawStore'
import { useEngine } from '../audio/useEngine'

export const Mixer: React.FC = () => {
  const { project, setTrackMix } = useDawStore()
  const engine = useEngine()
  if (!project) return null

  return (
    <div className="grid grid-cols-6 gap-3 p-2 bg-slate-900 rounded-xl">
      {project?.tracks?.map(t => (
        <Strip key={t.id} id={t.id} name={t.name} gainDb={t.gainDb} pan={t.pan}
               onGain={(v)=>{ setTrackMix(t.id, v, t.pan); engine?.setLaneGainDb?.(t.id, v) }}
               onPan={(v)=>{ setTrackMix(t.id, t.gainDb, v); engine?.setLanePan?.(t.id, v) }}
               getAnalyser={()=>engine?.attachAnalyser?.(t.id) || null} />
      )) || []}
    </div>
  )
}

const Strip: React.FC<{ 
  id: string; 
  name: string; 
  gainDb: number; 
  pan: number; 
  onGain: (v: number) => void; 
  onPan: (v: number) => void; 
  getAnalyser: () => AnalyserNode | null 
}> = ({ name, gainDb, pan, onGain, onPan, getAnalyser }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  
  useEffect(() => {
    const c = canvasRef.current; if (!c) return
    const dpr = window.devicePixelRatio || 1
    c.width = Math.round(40 * dpr); c.height = Math.round(120 * dpr)
    c.style.width = '40px'; c.style.height = '120px'
    const g = c.getContext('2d')!; g.scale(dpr, dpr)
    const an = getAnalyser(); if (!an) return
    const buf = new Uint8Array(an.frequencyBinCount)
    let raf = 0
    const draw = () => {
      an.getByteFrequencyData(buf)
      const v = buf[0] / 255 // rough energy
      g.clearRect(0, 0, 40, 120)
      g.fillStyle = '#1f2937'; g.fillRect(0, 0, 40, 120)
      g.fillStyle = '#10b981';
      const h = Math.round(v * 110)
      g.fillRect(12, 110 - h, 16, h)
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [getAnalyser])

  return (
    <div className="p-2 bg-slate-800 rounded-lg">
      <div className="text-slate-100 text-sm mb-2">{name}</div>
      <canvas ref={canvasRef} />
      <div className="mt-2">
        <div className="text-xs text-slate-300">Gain (dB)</div>
        <input type="range" min={-24} max={6} step={0.1} defaultValue={gainDb}
               onChange={(e) => onGain(Number(e.target.value))} />
      </div>
      <div className="mt-2">
        <div className="text-xs text-slate-300">Pan</div>
        <input type="range" min={-1} max={1} step={0.01} defaultValue={pan}
               onChange={(e) => onPan(Number(e.target.value))} />
      </div>
    </div>
  )
}
