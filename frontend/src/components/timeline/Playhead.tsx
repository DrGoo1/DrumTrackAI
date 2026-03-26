import React, { useRef } from 'react'
import { useDawStore } from '../../state/dawStore'
import { Tooltip } from '../Tooltip'

export default function Playhead() {
  const { cursorSec, pxPerSecond, setCursor } = useDawStore()
  const x = Math.round(cursorSec * pxPerSecond)
  const isDragging = useRef(false)
  
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    isDragging.current = true
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return
      
      const timeline = document.querySelector('[data-timeline]') as HTMLElement
      if (!timeline) return
      
      const rect = timeline.getBoundingClientRect()
      const mouseX = e.clientX - rect.left + timeline.scrollLeft
      const newCursorSec = Math.max(0, mouseX / pxPerSecond)
      
      setCursor(newCursorSec)
    }
    
    const handleMouseUp = () => {
      isDragging.current = false
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }
  
  return (
    <div className="absolute top-0 bottom-0 z-30 cursor-ew-resize" style={{ left: x }}>
      <div className="w-[2px] h-full bg-red-500/80 pointer-events-none" />
      <Tooltip content="Drag to seek" placement="top" maxWidthClassName="w-28">
        <div 
          className="-translate-x-1 -translate-y-1 w-3 h-3 bg-red-500 rounded-full border border-white cursor-ew-resize hover:bg-red-400"
          onMouseDown={handleMouseDown}
        />
      </Tooltip>
    </div>
  )
}
