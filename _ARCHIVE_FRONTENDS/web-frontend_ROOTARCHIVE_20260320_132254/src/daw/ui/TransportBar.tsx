import React from 'react'
import * as Tone from 'tone'
import { useDawStore } from '../state/dawStore'

export const TransportBar: React.FC = () => {
  const { playing, setPlaying, cursorSec, setCursor, bpm, setBpm, timeSig, setZoom } = useDawStore()

  const toggle = async () => {
    await Tone.start()
    if (!playing) {
      Tone.Transport.start('+0.05', cursorSec)
      setPlaying(true)
    } else {
      Tone.Transport.pause()
      setPlaying(false)
      useDawStore.setState({ cursorSec: Tone.Transport.seconds })
    }
  }

  const stop = () => {
    Tone.Transport.stop()
    setPlaying(false)
    setCursor(0)
  }

  const onBpm = (e:React.ChangeEvent<HTMLInputElement>)=>{
    const v = parseFloat(e.target.value||'120')
    Tone.Transport.bpm.rampTo(v, 0.05)
    setBpm(v)
  }

  return (
    <div className="flex items-center gap-3 p-2 bg-neutral-900 text-white border-b border-neutral-800">
      <button className="px-3 py-1 rounded bg-emerald-600" onClick={toggle}>{playing?'Pause':'Play'}</button>
      <button className="px-3 py-1 bg-neutral-800 rounded" onClick={()=> setZoom(100)}>100%</button>
      <button
        className="px-3 py-1 bg-indigo-600 rounded"
        onClick={async ()=>{
          const { jobId, bpm, kitMap } = useDawStore.getState() as any;
          const r = await fetch('/api/preview/render', { 
            method:'POST', 
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ job_id: jobId, bpm, bars: 4, kit_map: kitMap, midi_lanes: {} })
          });
          const j = await r.json();
          if (j.url) window.open(j.url, '_blank');
        }}
      >QA 4-bar Preview</button>
      <div className="flex items-center gap-1">
        <label>BPM</label>
        <input className="w-20 bg-neutral-800 px-2 py-1 rounded" type="number" min={30} max={300} value={bpm}
               onChange={onBpm}/>
      </div>
      <div className="opacity-70">Time Sig: {timeSig[0]}/{timeSig[1]}</div>
      <div className="ml-auto opacity-70">Cursor: {cursorSec.toFixed(2)}s</div>
    </div>
  )
}
