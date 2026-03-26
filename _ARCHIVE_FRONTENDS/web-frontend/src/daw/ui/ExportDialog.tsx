import React, { useState } from 'react'
import { useDawStore } from '../state/dawStore'
import { useMidi } from '../../midi/midiStore'
import type { MidiTrack } from '../../midi/types'
import { dcsmExportMidi } from '../../services/api'

type ExportMode = 'stereo' | 'stems' | 'midi_plugin'

export const ExportDialog: React.FC<{ open:boolean; onClose:()=>void }> = ({ open, onClose }) => {
  const { jobId, kitMap } = useDawStore()
  const { song } = useMidi()
  const [mode, setMode] = useState<ExportMode>('stereo')
  const [plugin, setPlugin] = useState<'jamstix' | 'sd3' | 'ssd5'>('jamstix')
  const [busy, setBusy] = useState(false)

  const exportNow = async () => {
    if (busy) return

    // Legacy export queue for audio/stems
    if (mode !== 'midi_plugin') {
      try {
        setBusy(true)
        const payload = { job_id: jobId, mode: mode === 'stereo' ? 'stereo' : 'stems', kit_map: kitMap, midi_lanes: {} }
        const res = await fetch(`/api/exports`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
        const j = await res.json()
        alert(`Export queued: ${j.export_id}`)
        onClose()
      } finally {
        setBusy(false)
      }
      return
    }

    // MIDI plugin export using articulated notes from the current drums clip
    try {
      setBusy(true)

      const drumsTrack: MidiTrack | undefined = song.tracks.find(t => t.kind === 'drums')
      const clip = drumsTrack?.clips[0]
      if (!drumsTrack || !clip) {
        alert('No drums clip found to export.')
        return
      }

      const ppq = song.ppq
      const notesPayload = clip.notes.map(n => ({
        t0: n.t0,
        t1: n.t1,
        pitch: n.pitch,
        vel: n.vel,
        chan: n.chan,
        articulationId: n.articulationId,
      }))

      const result = await dcsmExportMidi({
        plugin,
        ppq,
        notes: notesPayload,
      })

      if (!result.midi_base64) {
        alert(result.error || 'Export failed: empty MIDI')
        return
      }

      const bytes = Uint8Array.from(atob(result.midi_base64), c => c.charCodeAt(0))
      const blob = new Blob([bytes], { type: 'audio/midi' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = result.filename || `drums_${plugin}.mid`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      onClose()
    } catch (e: any) {
      alert(`MIDI export failed: ${e?.message || e}`)
    } finally {
      setBusy(false)
    }
  }

  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-neutral-900 text-white rounded-xl p-4 w-[520px]">
        <div className="font-semibold text-lg mb-3">Export</div>
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="mode"
              checked={mode === 'stereo'}
              onChange={() => setMode('stereo')}
            />
            <span>Stereo mixdown</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="mode"
              checked={mode === 'stems'}
              onChange={() => setMode('stems')}
            />
            <span>Stems (multi-track)</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="mode"
              checked={mode === 'midi_plugin'}
              onChange={() => setMode('midi_plugin')}
            />
            <span>Drums MIDI (articulated, plugin-specific)</span>
          </label>

          {mode === 'midi_plugin' && (
            <div className="mt-2 pl-6 space-y-2 text-sm text-neutral-300">
              <div>
                Target plugin:
                <select
                  className="ml-2 bg-neutral-800 border border-neutral-700 rounded px-2 py-0.5 text-sm"
                  value={plugin}
                  onChange={e => setPlugin(e.target.value as any)}
                >
                  <option value="jamstix">Jamstix</option>
                  <option value="sd3">Superior Drummer 3</option>
                  <option value="ssd5">SSD5</option>
                </select>
              </div>
              <div className="text-[11px] text-neutral-500">
                Exports the current drums clip from the MIDI editor, using its articulationId
                per note and the selected plugin's articulation map.
              </div>
            </div>
          )}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button className="px-3 py-1 bg-neutral-700 rounded" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            className="px-3 py-1 bg-emerald-600 rounded disabled:opacity-50"
            onClick={exportNow}
            disabled={busy}
          >
            {busy ? 'Exporting…' : 'Export'}
          </button>
        </div>
      </div>
    </div>
  )
}
