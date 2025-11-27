import React from 'react'
import { useDawStore } from '../../state/dawStore'
import { useEngine } from '../../audio/useEngine'
import Strip from './Strip'

export default function MixerPanel() {
  const { project, setTrackMix, toggleMute, toggleSoloExclusive } = useDawStore()
  const engine = useEngine()
  
  if (!project) return null
  
  function applyMutes() { 
    if (!project?.tracks) return
    const someSolo = !!project.tracks.some(t => t.solo)
    project.tracks.forEach(t => { 
      const eff = t.mute || (someSolo && !t.solo)
      engine?.setLaneMuted?.(t.id, !!eff) 
    }) 
  }
  
  return (
    <div className="space-y-3 w-[300px]">
      {project.tracks?.map(t => (
        <Strip 
          key={t.id} 
          id={t.id} 
          name={t.name} 
          gainDb={t.gainDb} 
          pan={t.pan} 
          mute={!!t.mute} 
          solo={!!t.solo}
          onGain={(v) => { setTrackMix(t.id, v, t.pan); engine?.setLaneGainDb?.(t.id, v) }}
          onPan={(v) => { setTrackMix(t.id, t.gainDb, v); engine?.setLanePan?.(t.id, v) }}
          onMute={() => { toggleMute(t.id); applyMutes() }} 
          onSolo={() => { toggleSoloExclusive(t.id); applyMutes() }}
          getAnalyser={() => engine?.attachAnalyser?.(t.id) || null}
        />
      ))}
    </div>
  )
}
