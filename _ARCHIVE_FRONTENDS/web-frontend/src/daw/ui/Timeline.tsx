import React, { useEffect, useRef, useState } from 'react'
import * as Tone from 'tone'
import { useDawStore } from '../state/dawStore'
import { drawMarkers } from './markersLayer'

export const Timeline: React.FC<{ totalSec:number; onScrub:(sec:number)=>void }>=({ totalSec, onScrub })=>{
  const { pxPerSecond, setZoom, cursorSec, setCursor, snap, bpm, timeSig, grid, project } = useDawStore()
  const ref = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [scrollLeft, setScrollLeft] = useState(0)

  // Mouse wheel zoom + scroll with anchored zoom
  useEffect(()=>{
    const el = ref.current; if(!el) return
    const onWheel = (e:WheelEvent)=>{
      if (e.ctrlKey || e.metaKey) { // zoom
        e.preventDefault()
        const mouseX = e.clientX - el.getBoundingClientRect().left + el.scrollLeft
        const anchorSec = mouseX / pxPerSecond
        const factor = e.deltaY < 0 ? 1.1 : 0.9
        const newPps = Math.min(Math.max(pxPerSecond * factor, 20), 2000)
        setZoom(newPps)
        // keep time under mouse pinned
        el.scrollLeft = anchorSec * newPps - mouseX + el.getBoundingClientRect().left
      }
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return ()=> el.removeEventListener('wheel', onWheel as any)
  }, [pxPerSecond, setZoom])

  // Snap helper function
  const snapToGrid = (sec: number, grid: 'bar'|'beat'|'1/2'|'1/4'|'off' = 'beat') => {
    if (grid === 'off' || !snap) return sec
    const spb = (60 / bpm) * (4 / timeSig[1]) // denominator-aware
    const step = grid === 'bar' ? spb * timeSig[0] : 
                 grid === 'beat' ? spb : 
                 grid === '1/2' ? spb/2 : 
                 spb/4
    return Math.round(sec / step) * step
  }

  // Scrub & snap
  const onDown:React.MouseEventHandler<HTMLDivElement> = (e)=>{
    const bounds = (e.currentTarget as HTMLDivElement).getBoundingClientRect()
    const x = e.clientX - bounds.left + e.currentTarget.scrollLeft
    let sec = x / pxPerSecond
    sec = snapToGrid(sec, grid)
    setCursor(sec)
    onScrub(sec)
  }

  // Auto-scroll when playing (reduced state churn)
  useEffect(()=>{
    let r = 0
    const loop = ()=>{
      const sec = Tone.Transport.seconds
      const prev = useDawStore.getState().cursorSec
      // Only update if visually changed (reduces React churn)
      if (Math.abs((sec - prev) * pxPerSecond) > 1) {
        useDawStore.setState({ cursorSec: sec })
      }
      if (ref.current){
        const x = sec * pxPerSecond
        const viewL = ref.current.scrollLeft
        const viewR = viewL + ref.current.clientWidth
        if (x > viewR - 80) ref.current.scrollLeft = x - ref.current.clientWidth/2
      }
      r = requestAnimationFrame(loop)
    }
    r = requestAnimationFrame(loop)
    return ()=> cancelAnimationFrame(r)
  }, [pxPerSecond])

  return (
    <div ref={ref} className="relative h-20 overflow-x-auto bg-neutral-900" onMouseDown={onDown}
         onScroll={(e)=> setScrollLeft((e.target as HTMLDivElement).scrollLeft)}>
      <div style={{ width: totalSec*pxPerSecond }} className="h-full relative">
        {/* Cursor */}
        <div className="absolute top-0 bottom-0 w-px bg-emerald-400" style={{ left: cursorSec*pxPerSecond }}/>
      </div>
    </div>
  )
}
