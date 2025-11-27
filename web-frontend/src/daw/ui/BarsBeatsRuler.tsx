import React, { useEffect, useRef } from 'react'
import { useDawStore } from '../state/dawStore'

export const BarsBeatsRuler: React.FC<{ seconds: number }> = ({ seconds }) => {
  const { bpm, timeSig, pxPerSecond } = useDawStore()
  const [num, den] = timeSig
  const secPerBeat = (60 / bpm) * (4 / den)
  const secPerBar  = secPerBeat * num
  const width = Math.max(1, Math.ceil(seconds * pxPerSecond))
  const ref = useRef<HTMLCanvasElement | null>(null)
  const minorBeats = pxPerSecond >= 220 ? 2 : pxPerSecond >= 140 ? 1 : 0.5

  useEffect(() => {
    const c = ref.current; if (!c) return
    const dpr = window.devicePixelRatio || 1
    c.width = Math.round(width * dpr)
    c.height = Math.round(28 * dpr)
    c.style.width = width + 'px'
    c.style.height = '28px'
    const g = c.getContext('2d')!
    g.scale(dpr, dpr)
    g.fillStyle = '#0f172a'; g.fillRect(0,0,width,28)
    g.strokeStyle = '#334155'; g.fillStyle = '#94a3b8'
    const px = pxPerSecond
    const step = secPerBeat * minorBeats
    for (let t=0, bar=1; t <= seconds + 1e-6; t += step) {
      const x = Math.round(t*px) + 0.5
      const isBar = Math.abs((t / secPerBar) - Math.round(t / secPerBar)) < 1e-6
      g.beginPath(); g.moveTo(x, 0); g.lineTo(x, isBar ? 20 : 14); g.stroke()
      if (isBar) { g.fillText(String(bar++), x+3, 24) }
    }
    g.fillText('Bars/Beats', width-80, 12)
  }, [width, seconds, pxPerSecond, secPerBeat, secPerBar, minorBeats])

  return <div className="overflow-x-auto"><canvas ref={ref} /></div>
}
