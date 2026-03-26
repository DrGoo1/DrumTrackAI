import React, { useEffect, useRef } from 'react'

const toDb = (x: number) => 20 * Math.log10(Math.max(1e-9, x))

export default function Meter({ getNode, width = 18, height = 112 }: { getNode: () => AnalyserNode | null; width?: number; height?: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  
  useEffect(() => {
    const c = ref.current, an = getNode?.()
    if (!c || !an) return
    
    const dpr = window.devicePixelRatio || 1
    c.width = Math.round(width * dpr)
    c.height = Math.round(height * dpr)
    c.style.width = width + 'px'
    c.style.height = height + 'px'
    
    const g = c.getContext('2d')!
    g.scale(dpr, dpr)
    const buf = new Float32Array(an.fftSize)
    let peakHold = -120, rmsDb = -120, raf = 0
    
    const draw = () => {
      an.getFloatTimeDomainData(buf)
      let sum = 0, pk = 0
      for (let i = 0; i < buf.length; i++) {
        const v = buf[i]
        sum += v * v
        if (Math.abs(v) > pk) pk = Math.abs(v)
      }
      const rms = Math.sqrt(sum / buf.length)
      const pkDb = toDb(pk)
      const tRms = toDb(rms)
      rmsDb = Math.max(tRms, rmsDb - 0.6)
      peakHold = Math.max(pkDb, peakHold - 0.9)
      
      g.clearRect(0, 0, width, height)
      const y = (db: number) => height - Math.max(0, Math.min(1, (db + 60) / 60)) * height
      
      g.fillStyle = '#0b1220'
      g.fillRect(0, 0, width, height)
      g.fillStyle = '#10b981'
      g.fillRect(2, y(rmsDb), width - 4, height - y(rmsDb))
      if (rmsDb > -6) {
        g.fillStyle = '#f59e0b'
        g.fillRect(2, y(-6), width - 4, height - y(-6))
      }
      if (rmsDb > -1) {
        g.fillStyle = '#ef4444'
        g.fillRect(2, y(-1), width - 4, height - y(-1))
      }
      g.fillStyle = '#eab308'
      g.fillRect(2, y(peakHold) - 2, width - 4, 2)
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [getNode, width, height])
  
  return <canvas ref={ref} />
}
