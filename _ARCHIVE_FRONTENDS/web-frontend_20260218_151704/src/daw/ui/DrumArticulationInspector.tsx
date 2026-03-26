import React, { useMemo } from 'react'
import { useMidi } from '../../midi/midiStore'

interface DrumArticulationInspectorProps {
  trackId: string
  clipId: string
  selectedNoteIds: string[]
}

// Simple instrument family inference from MIDI pitch (GM-ish)
function inferInstrumentFamily(pitch: number): 'kick' | 'snare' | 'hihat' | 'ride' | 'tom' | 'crash' | 'other' {
  if (pitch === 36 || pitch === 35) return 'kick'
  if (pitch === 38 || pitch === 40 || pitch === 37 || pitch === 39) return 'snare'
  if (pitch === 42 || pitch === 44 || pitch === 46) return 'hihat'
  if (pitch === 51 || pitch === 53 || pitch === 59 || pitch === 52) return 'ride'
  if (pitch === 48 || pitch === 47 || pitch === 45 || pitch === 43 || pitch === 41) return 'tom'
  if (pitch === 49 || pitch === 57 || pitch === 55) return 'crash'
  return 'other'
}

const HAT_ARTS = [
  'hh_closed_tight',
  'hh_closed',
  'hh_slightly_open',
  'hh_half_open',
  'hh_fully_open',
  'hh_pedal_chick',
  'hh_splash',
]

const RIDE_ARTS = [
  'ride_bow_tip',
  'ride_bow_shoulder',
  'ride_bell',
  'ride_edge',
]

const SNARE_ARTS = [
  'snare_center',
  'snare_rimshot',
  'snare_sidestick',
  'snare_ghost',
]

const TOM_ARTS = [
  'tom_center',
]

const CRASH_ARTS = [
  'crash_normal',
  'crash_bell',
  'crash_choke',
]

export const DrumArticulationInspector: React.FC<DrumArticulationInspectorProps> = ({
  trackId,
  clipId,
  selectedNoteIds,
}) => {
  const { getClip, updateNote } = useMidi()

  const clip = getClip(trackId, clipId)
  const notes = clip?.notes || []

  const selectedNotes = useMemo(
    () => notes.filter(n => selectedNoteIds.includes(n.id)),
    [notes, selectedNoteIds]
  )

  const focusNote = selectedNotes[0]

  const { family, options } = useMemo(() => {
    if (!focusNote) {
      return { family: 'other' as const, options: [] as string[] }
    }
    const fam = inferInstrumentFamily(focusNote.pitch)
    if (fam === 'hihat') return { family: fam, options: HAT_ARTS }
    if (fam === 'ride') return { family: fam, options: RIDE_ARTS }
    if (fam === 'snare') return { family: fam, options: SNARE_ARTS }
    if (fam === 'tom') return { family: fam, options: TOM_ARTS }
    if (fam === 'crash') return { family: fam, options: CRASH_ARTS }
    return { family: fam, options: [] as string[] }
  }, [focusNote])

  if (!focusNote) {
    return (
      <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-3 text-sm text-neutral-400">
        No note selected
      </div>
    )
  }

  const handleArticulationChange = (value: string) => {
    const art = value || undefined
    selectedNotes.forEach(n => {
      updateNote(trackId, clipId, n.id, { articulationId: art })
    })
  }

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-3 text-xs text-neutral-200 space-y-3">
      <div className="font-semibold text-neutral-100 mb-1">Note Inspector</div>

      <div className="space-y-1">
        <div className="flex justify-between">
          <span className="text-neutral-400">Pitch</span>
          <span className="font-mono">{focusNote.pitch}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-neutral-400">Velocity</span>
          <span className="font-mono">{focusNote.vel}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-neutral-400">Channel</span>
          <span className="font-mono">{focusNote.chan}</span>
        </div>
      </div>

      <div className="pt-2 border-t border-neutral-800 mt-2">
        <label className="block text-[11px] text-neutral-400 mb-1">
          Articulation {family !== 'other' && <span className="opacity-70">({family})</span>}
        </label>
        <select
          value={focusNote.articulationId || ''}
          onChange={e => handleArticulationChange(e.target.value)}
          className="w-full bg-neutral-950 border border-neutral-700 rounded px-2 py-1 text-[11px] text-neutral-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        >
          <option value="">(auto)</option>
          {options.map(opt => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>

      <div className="text-[11px] text-neutral-500">
        Editing {selectedNotes.length} note{selectedNotes.length === 1 ? '' : 's'}
      </div>
    </div>
  )
}
