import { useEffect } from 'react'
import { useDawStore } from '../../state/dawStore'
import * as Tone from 'tone'

export default function Shortcuts() {
  const { playing, play, pause, toggleLoop } = useDawStore()
  
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === 'Space') { 
        e.preventDefault(); 
        playing ? pause() : play() 
      }
      if (e.key === 'l' || e.key === 'L') { 
        toggleLoop() 
      }
      if (e.key === '0') { 
        Tone.Transport.seconds = 0; 
        useDawStore.getState().setCursor(0) 
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [playing, play, pause, toggleLoop])
  
  return null
}
