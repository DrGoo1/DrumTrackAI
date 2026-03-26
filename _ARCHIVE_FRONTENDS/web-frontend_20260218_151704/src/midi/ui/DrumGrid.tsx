// Drum Grid Editor - Canvas-based MIDI drum sequencer
// High-performance grid for editing drum patterns with velocity lanes

import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useMidi } from '../midiStore'
import { useDawStore } from '../../state/dawStore'
import { secondsToTicks, ticksToSeconds, quantizeTicks } from '../tempo'
import { MidiNote } from '../types'
import { GM_DRUM_MAP } from '../players'

interface DrumGridProps {
  trackId: string
  clipId: string
  className?: string
  onSelectionChange?: (noteIds: string[]) => void
}

interface DrumRow {
  name: string
  pitch: number
  color: string
  shortcut: string
}

const DRUM_ROWS: DrumRow[] = [
  { name: 'KICK', pitch: GM_DRUM_MAP.kick, color: '#ef4444', shortcut: 'K' },
  { name: 'SNARE', pitch: GM_DRUM_MAP.snare, color: '#f97316', shortcut: 'S' },
  { name: 'HIHAT', pitch: GM_DRUM_MAP.hihat, color: '#eab308', shortcut: 'H' },
  { name: 'OPEN HAT', pitch: GM_DRUM_MAP.openhat, color: '#84cc16', shortcut: 'O' },
  { name: 'CRASH', pitch: GM_DRUM_MAP.crash, color: '#06b6d4', shortcut: 'C' },
  { name: 'RIDE', pitch: GM_DRUM_MAP.ride, color: '#8b5cf6', shortcut: 'R' },
  { name: 'TOM 1', pitch: GM_DRUM_MAP.tom1, color: '#ec4899', shortcut: '1' },
  { name: 'TOM 2', pitch: GM_DRUM_MAP.tom2, color: '#f43f5e', shortcut: '2' },
]

const GRID_WIDTH = 1200
const GRID_HEIGHT = 320
const ROW_HEIGHT = GRID_HEIGHT / DRUM_ROWS.length
const STEPS_PER_BAR = 16
const VELOCITY_HEIGHT = 60

export default function DrumGrid({ trackId, clipId, className = '', onSelectionChange }: DrumGridProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const velocityCanvasRef = useRef<HTMLCanvasElement>(null)
  const [selectedNotes, setSelectedNotes] = useState<Set<string>>(new Set())
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null)
  const [quantization, setQuantization] = useState(16) // 16th notes
  const [showVelocity, setShowVelocity] = useState(true)
  
  // Store hooks
  const { song, updateNotes, addNote, removeNote } = useMidi()
  const { cursorSec, pxPerSecond } = useDawStore()
  
  // Get current clip
  const track = song.tracks.find(t => t.id === trackId)
  const clip = track?.clips.find(c => c.id === clipId)
  const notes = clip?.notes || []
  
  // Calculate grid metrics
  const ppq = song.ppq
  const tempoMap = song.tempoMap
  const beatsPerBar = song.timeSig[0]
  const stepsPerBeat = STEPS_PER_BAR / beatsPerBar
  const stepWidth = GRID_WIDTH / STEPS_PER_BAR
  
  // Draw main grid
  const drawGrid = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')!
    const dpr = window.devicePixelRatio || 1
    
    // Set canvas size for high DPI
    canvas.width = GRID_WIDTH * dpr
    canvas.height = GRID_HEIGHT * dpr
    canvas.style.width = `${GRID_WIDTH}px`
    canvas.style.height = `${GRID_HEIGHT}px`
    ctx.scale(dpr, dpr)
    
    // Clear canvas
    ctx.fillStyle = '#0f172a' // slate-900
    ctx.fillRect(0, 0, GRID_WIDTH, GRID_HEIGHT)
    
    // Draw vertical grid lines (steps)
    for (let i = 0; i <= STEPS_PER_BAR; i++) {
      const x = i * stepWidth
      const isBeat = i % stepsPerBeat === 0
      const isBar = i % STEPS_PER_BAR === 0
      
      ctx.strokeStyle = isBar ? '#475569' : isBeat ? '#334155' : '#1e293b' // slate variants
      ctx.lineWidth = isBar ? 2 : 1
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, GRID_HEIGHT)
      ctx.stroke()
    }
    
    // Draw horizontal grid lines (drum rows)
    DRUM_ROWS.forEach((row, index) => {
      const y = index * ROW_HEIGHT
      
      // Row background (alternating)
      ctx.fillStyle = index % 2 === 0 ? '#1e293b' : '#0f172a'
      ctx.fillRect(0, y, GRID_WIDTH, ROW_HEIGHT)
      
      // Row separator
      ctx.strokeStyle = '#334155'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(GRID_WIDTH, y)
      ctx.stroke()
      
      // Row label
      ctx.fillStyle = '#94a3b8'
      ctx.font = '12px monospace'
      ctx.textAlign = 'left'
      ctx.fillText(row.name, 8, y + ROW_HEIGHT / 2 + 4)
      
      // Shortcut key
      ctx.fillStyle = '#64748b'
      ctx.font = '10px monospace'
      ctx.fillText(`[${row.shortcut}]`, 8, y + ROW_HEIGHT - 8)
    })
    
    // Draw notes
    notes.forEach(note => {
      const rowIndex = DRUM_ROWS.findIndex(row => row.pitch === note.pitch)
      if (rowIndex === -1) return
      
      const row = DRUM_ROWS[rowIndex]
      const y = rowIndex * ROW_HEIGHT
      
      // Convert ticks to grid position
      const startStep = Math.floor((note.t0 / ppq) * stepsPerBeat)
      const endStep = Math.ceil((note.t1 / ppq) * stepsPerBeat)
      const x = startStep * stepWidth
      const width = Math.max((endStep - startStep) * stepWidth, 4)
      
      // Note color based on velocity and selection (and optional articulation cue)
      const isSelected = selectedNotes.has(note.id)
      const alpha = note.vel / 127
      const baseColor = row.color
      
      if (isSelected) {
        ctx.fillStyle = '#3b82f6' // blue for selection
        ctx.strokeStyle = '#1d4ed8'
        ctx.lineWidth = 2
      } else {
        ctx.fillStyle = baseColor + Math.floor(alpha * 255).toString(16).padStart(2, '0')
        ctx.strokeStyle = baseColor
        ctx.lineWidth = 1
      }
      
      // Draw note rectangle
      ctx.fillRect(x + 2, y + 4, width - 4, ROW_HEIGHT - 8)
      ctx.strokeRect(x + 2, y + 4, width - 4, ROW_HEIGHT - 8)

      // Optional articulation label (tiny code in bottom-right corner)
      const art = (note as any).articulationId as string | undefined
      if (art) {
        let label = ''
        if (art.startsWith('hh_')) label = 'H'
        else if (art.startsWith('ride')) label = 'R'
        else if (art.startsWith('snare')) label = 'S'
        else if (art.startsWith('tom')) label = 'T'
        else if (art.startsWith('crash')) label = 'C'

        if (label) {
          ctx.fillStyle = '#0f172a'
          ctx.font = '9px monospace'
          ctx.textAlign = 'right'
          ctx.fillText(label, x + width - 4, y + ROW_HEIGHT - 6)
        }
      }
      
      // Draw velocity indicator
      const velHeight = (note.vel / 127) * (ROW_HEIGHT - 12)
      ctx.fillStyle = baseColor + '80' // Semi-transparent
      ctx.fillRect(x + 2, y + ROW_HEIGHT - 4 - velHeight, 3, velHeight)
    })
    
    // Draw playhead cursor
    if (cursorSec > 0) {
      const cursorTicks = secondsToTicks(tempoMap, cursorSec, ppq)
      const cursorStep = (cursorTicks / ppq) * stepsPerBeat
      const cursorX = cursorStep * stepWidth
      
      if (cursorX >= 0 && cursorX <= GRID_WIDTH) {
        ctx.strokeStyle = '#3b82f6'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(cursorX, 0)
        ctx.lineTo(cursorX, GRID_HEIGHT)
        ctx.stroke()
      }
    }
    
  }, [notes, selectedNotes, cursorSec, tempoMap, ppq, stepsPerBeat, stepWidth])
  
  // Draw velocity lane
  const drawVelocityLane = useCallback(() => {
    if (!showVelocity) return
    
    const canvas = velocityCanvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')!
    const dpr = window.devicePixelRatio || 1
    
    canvas.width = GRID_WIDTH * dpr
    canvas.height = VELOCITY_HEIGHT * dpr
    canvas.style.width = `${GRID_WIDTH}px`
    canvas.style.height = `${VELOCITY_HEIGHT}px`
    ctx.scale(dpr, dpr)
    
    // Clear canvas
    ctx.fillStyle = '#1e293b'
    ctx.fillRect(0, 0, GRID_WIDTH, VELOCITY_HEIGHT)
    
    // Draw velocity bars for selected notes
    const selectedNotesList = notes.filter(note => selectedNotes.has(note.id))
    
    selectedNotesList.forEach(note => {
      const startStep = Math.floor((note.t0 / ppq) * stepsPerBeat)
      const x = startStep * stepWidth
      const height = (note.vel / 127) * (VELOCITY_HEIGHT - 10)
      
      const rowIndex = DRUM_ROWS.findIndex(row => row.pitch === note.pitch)
      const color = rowIndex !== -1 ? DRUM_ROWS[rowIndex].color : '#64748b'
      
      ctx.fillStyle = color
      ctx.fillRect(x + 2, VELOCITY_HEIGHT - height - 5, stepWidth - 4, height)
    })
    
    // Draw velocity grid lines
    for (let i = 0; i <= 4; i++) {
      const y = (i / 4) * VELOCITY_HEIGHT
      ctx.strokeStyle = '#334155'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(GRID_WIDTH, y)
      ctx.stroke()
      
      // Velocity labels
      ctx.fillStyle = '#64748b'
      ctx.font = '10px monospace'
      ctx.textAlign = 'right'
      ctx.fillText(`${127 - Math.floor((i / 4) * 127)}`, GRID_WIDTH - 5, y + 12)
    }
    
  }, [notes, selectedNotes, showVelocity, ppq, stepsPerBeat, stepWidth])
  
  // Handle mouse events
  const handleMouseDown = (event: React.MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const rect = canvas.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    
    const step = Math.floor(x / stepWidth)
    const rowIndex = Math.floor(y / ROW_HEIGHT)
    
    if (rowIndex < 0 || rowIndex >= DRUM_ROWS.length) return
    
    const row = DRUM_ROWS[rowIndex]
    const ticks = quantizeTicks(step * (ppq / stepsPerBeat), ppq, quantization)
    
    // Check if clicking on existing note
    const existingNote = notes.find(note => 
      note.pitch === row.pitch && 
      Math.abs(note.t0 - ticks) < (ppq / quantization)
    )
    
    if (existingNote) {
      // Toggle selection or delete
      if (event.shiftKey) {
        setSelectedNotes(prev => {
          const newSet = new Set(prev)
          if (newSet.has(existingNote.id)) {
            newSet.delete(existingNote.id)
          } else {
            newSet.add(existingNote.id)
          }
          return newSet
        })
      } else if (event.altKey) {
        // Delete note
        removeNote(trackId, clipId, existingNote.id)
      } else {
        // Select single note
        setSelectedNotes(new Set([existingNote.id]))
      }
    } else {
      // Add new note
      const noteLength = ppq / quantization // Default to quantization length
      const velocity = 100 // Default velocity
      
      addNote(trackId, clipId, {
        t0: ticks,
        t1: ticks + noteLength,
        pitch: row.pitch,
        vel: velocity,
        chan: 1
      })
    }
    
    setIsDragging(true)
    setDragStart({ x, y })
  }
  
  const handleMouseMove = (event: React.MouseEvent) => {
    if (!isDragging || !dragStart) return
    
    // Handle note dragging logic here
    // For now, just track mouse movement
  }
  
  const handleMouseUp = () => {
    setIsDragging(false)
    setDragStart(null)
  }

  // Notify parent of selection changes
  useEffect(() => {
    if (onSelectionChange) {
      onSelectionChange(Array.from(selectedNotes))
    }
  }, [selectedNotes, onSelectionChange])
  
  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle if grid is focused
      if (!canvasRef.current?.matches(':focus-within')) return
      
      // Drum row shortcuts
      const row = DRUM_ROWS.find(r => r.shortcut.toLowerCase() === event.key.toLowerCase())
      if (row && cursorSec >= 0) {
        const cursorTicks = secondsToTicks(tempoMap, cursorSec, ppq)
        const quantizedTicks = quantizeTicks(cursorTicks, ppq, quantization)
        const noteLength = ppq / quantization
        
        addNote(trackId, clipId, {
          t0: quantizedTicks,
          t1: quantizedTicks + noteLength,
          pitch: row.pitch,
          vel: 100,
          chan: 1
        })
        
        event.preventDefault()
      }
      
      // Delete selected notes
      if (event.key === 'Delete' || event.key === 'Backspace') {
        selectedNotes.forEach(noteId => {
          removeNote(trackId, clipId, noteId)
        })
        setSelectedNotes(new Set())
        event.preventDefault()
      }
      
      // Select all
      if (event.key === 'a' && (event.ctrlKey || event.metaKey)) {
        setSelectedNotes(new Set(notes.map(n => n.id)))
        event.preventDefault()
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedNotes, notes, cursorSec, tempoMap, ppq, quantization, trackId, clipId, addNote, removeNote])
  
  // Redraw on changes
  useEffect(() => {
    drawGrid()
  }, [drawGrid])
  
  useEffect(() => {
    drawVelocityLane()
  }, [drawVelocityLane])
  
  return (
    <div className={`drum-grid bg-slate-900 rounded-lg border border-slate-700 ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-slate-700">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-slate-300">Drum Grid</span>
          
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400">Quantize:</label>
            <select 
              value={quantization}
              onChange={(e) => setQuantization(Number(e.target.value))}
              className="bg-slate-800 text-slate-300 text-xs px-2 py-1 rounded border border-slate-600"
            >
              <option value={4}>1/4</option>
              <option value={8}>1/8</option>
              <option value={16}>1/16</option>
              <option value={32}>1/32</option>
            </select>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowVelocity(!showVelocity)}
            className={`text-xs px-2 py-1 rounded ${
              showVelocity 
                ? 'bg-blue-600 text-white' 
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            Velocity
          </button>
          
          <button
            onClick={() => setSelectedNotes(new Set())}
            className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600"
          >
            Clear Selection
          </button>
        </div>
      </div>
      
      {/* Main grid */}
      <div className="relative">
        <canvas
          ref={canvasRef}
          className="block cursor-crosshair"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          tabIndex={0}
        />
      </div>
      
      {/* Velocity lane */}
      {showVelocity && (
        <div className="border-t border-slate-700">
          <canvas
            ref={velocityCanvasRef}
            className="block"
          />
        </div>
      )}
      
      {/* Status bar */}
      <div className="flex items-center justify-between p-2 border-t border-slate-700 text-xs text-slate-400">
        <span>{notes.length} notes</span>
        <span>{selectedNotes.size} selected</span>
        <span>Click to add • Shift+Click to select • Alt+Click to delete</span>
      </div>
    </div>
  )
}
