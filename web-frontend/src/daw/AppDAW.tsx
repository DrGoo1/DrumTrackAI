import React, { useEffect, useMemo, useState } from 'react'
import * as Tone from 'tone'
import { useDawStore } from './state/dawStore'
import { DrumEngine } from './audio/engine'
import { TransportBar } from './ui/TransportBar'
import { BarsBeatsRuler } from './ui/BarsBeatsRuler'
import { Timeline } from './ui/Timeline'
import { Mixer } from './ui/Mixer'
import { KitBuilderModal } from './ui/KitBuilderModal'
import { ExportDialog } from './ui/ExportDialog'
import { ImpactDrumsPanel } from './ui/ImpactDrumsPanel'
import { GrooveCoachPanel } from './ui/GrooveCoachPanel'
import { PocketTransferModal } from './ui/PocketTransferModal'
import { ReviewPanel } from './ui/ReviewPanel'
import { DrumCreationPanel } from './ui/DrumCreationPanel'
import { useMidi } from '../midi/midiStore'
import { DrumEditorPanel } from './ui/DrumEditorPanel'
import { SourceSongPanel } from './ui/SourceSongPanel'
import { SectionsPanel, SectionRow } from './ui/SectionsPanel'
import { sectionizeAudio, dcsmExportMidi, analyzeTempo } from '../services/api'

export const AppDAW: React.FC = () => {
  const { kitMap, setCursor, project, pxPerSecond } = useDawStore()
  const [engine, setEngine] = useState<DrumEngine|null>(null)
  const [kitOpen, setKitOpen] = useState(false)
  const [expOpen, setExpOpen] = useState(false)
  const [pocketOpen, setPocketOpen] = useState(false)
  const [impact, setImpact] = useState({
    low:{drive_type:'analog',drive_amount:0.2,snap:0.15,blend:0.5},
    high:{drive_type:'tape',drive_amount:0.12,snap:0.1,blend:0.35},
    space:{on:false,type:'algo',predelay_ms:15,duck:0.25}
  })

  // MIDI drum track + clip for DrumEditorPanel
  const { song, addTrack, addClip, updateNotes, getClip, setTempoMap } = useMidi()
  const [drumTrackId, setDrumTrackId] = useState<string | null>(null)
  const [drumClipId, setDrumClipId] = useState<string | null>(null)
  const [sourceSong, setSourceSong] = useState<{ key: string; durationSec: number; peaks?: number[] } | null>(null)
  const [sections, setSections] = useState<SectionRow[]>([])

  useEffect(()=>{ setEngine(new DrumEngine(kitMap)) }, [kitMap])
  
  // Replace dummy heartbeat with a cursor updater
  useEffect(() => {
    let raf = 0
    const tick = () => {
      const sec = Tone.Transport.seconds
      // write only if visually changed (reduces churn)
      const currentCursor = useDawStore.getState().cursorSec ?? -1
      if (Math.abs((sec - currentCursor) * (pxPerSecond ?? 100)) > 1) {
        useDawStore.setState({ cursorSec: sec })
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [pxPerSecond])

  // Ensure a default drums track/clip exists for the MIDI editor
  useEffect(() => {
    if (drumTrackId && drumClipId) return

    // Try to find an existing drums track/clip first
    const drumsTrack = song.tracks.find(t => t.kind === 'drums')
    if (drumsTrack && drumsTrack.clips.length > 0) {
      setDrumTrackId(drumsTrack.id)
      setDrumClipId(drumsTrack.clips[0].id)
      return
    }

    // Otherwise, create a basic drums track and clip
    const newTrackId = drumsTrack ? drumsTrack.id : addTrack({ name: 'Drums', kind: 'drums', chan: 10 })
    const newClipId = addClip(newTrackId, {
      name: 'Main Groove',
      startTick: 0,
      endTick: 4 * 4 * 480, // 4 bars of 4/4 at PPQ 480
      notes: [],
    })
    setDrumTrackId(newTrackId)
    setDrumClipId(newClipId)
  }, [song.tracks, addTrack, addClip, drumTrackId, drumClipId])

  // Derive timeline length from project or fallback to sourceSong duration or 180s
  const totalSec = useMemo(() => {
    if (sourceSong) return Math.max(60, Math.ceil(sourceSong.durationSec || 180))
    if (!project) return 180
    const maxEnd = project.tracks?.flatMap(t => t.clips ?? [])
      .reduce((m,c) => Math.max(m, (c.startSec ?? 0) + (c.durationSec ?? 0)), 0)
    return Math.max(60, Math.ceil(maxEnd || 180))
  }, [project])

  // When a source song is loaded, try to analyze its tempo and update the MIDI tempo map
  useEffect(() => {
    async function syncTempo() {
      if (!sourceSong) return
      try {
        const result = await analyzeTempo(sourceSong.key)
        const bpm = result.tempo || 120
        setTempoMap([{ tSec: 0, bpm }])
      } catch (e) {
        console.warn('analyzeTempo failed, keeping default tempo map', e)
      }
    }
    void syncTempo()
  }, [sourceSong?.key])

  async function handleAutoSectionize() {
    if (!sourceSong) return
    try {
      const result = await sectionizeAudio(sourceSong.key, 2.0)
      const next: SectionRow[] = result.sections.map((s, idx) => ({
        id: `sec-${idx}`,
        start: s.start,
        end: s.end,
        density: 0.7,
        fillIn: false,
        fillOut: false,
        label: `Section ${idx + 1}`,
      }))
      setSections(next)
    } catch (e) {
      console.warn('Auto-sectionize failed', e)
    }
  }

  async function handleExportDrumsMidi() {
    try {
      if (!drumTrackId || !drumClipId) return
      const clip = getClip(drumTrackId, drumClipId)
      if (!clip) return

      const notes = (clip.notes || []).map((n) => ({
        t0: n.t0,
        t1: n.t1,
        pitch: n.pitch,
        vel: n.vel,
        chan: n.chan,
        articulationId: n.articulationId,
      }))

      if (notes.length === 0) return

      const resp = await dcsmExportMidi({
        plugin: 'jamstix',
        ppq: song.ppq,
        notes,
      })

      if (!resp || resp.error) {
        console.warn('dcsmExportMidi failed', resp?.error)
        return
      }

      const base64 = resp.midi_base64
      const byteString = atob(base64)
      const buf = new Uint8Array(byteString.length)
      for (let i = 0; i < byteString.length; i++) {
        buf[i] = byteString.charCodeAt(i)
      }
      const blob = new Blob([buf], { type: 'audio/midi' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = resp.filename || 'drumtrack.mid'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.warn('Export drums MIDI failed', e)
    }
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <TransportBar />
      <div className="flex items-center gap-2 p-2 border-b border-neutral-800">
        <button className="px-3 py-1 bg-neutral-800 rounded" onClick={()=> setKitOpen(true)}>Kit Builder</button>
        <button className="px-3 py-1 bg-neutral-800 rounded" onClick={()=> setExpOpen(true)}>Export</button>
        <button className="px-3 py-1 bg-neutral-800 rounded" onClick={handleExportDrumsMidi}>Export Drums MIDI</button>
        <button className="px-3 py-1 bg-neutral-800 rounded" onClick={()=> setPocketOpen(true)}>Pocket Transfer</button>
        <div className="ml-auto text-xs opacity-70">Mousewheel + Ctrl/⌘ to Zoom</div>
      </div>

      <div className="grid grid-cols-12 gap-3 p-3">
        <div className="col-span-3 space-y-3">
          <SourceSongPanel onSongLoaded={setSourceSong} />
          <SectionsPanel sections={sections} onChange={setSections} onAutoSectionize={handleAutoSectionize} />
        </div>
        <div className="col-span-9 space-y-3">
          <BarsBeatsRuler seconds={totalSec} />
          {sourceSong?.peaks && sourceSong.peaks.length > 0 && (
            <div className="h-10 w-full bg-neutral-900 border border-neutral-800 rounded overflow-hidden flex items-center px-1">
              <div className="flex w-full h-8 gap-[1px] opacity-70">
                {sourceSong.peaks.slice(0, 400).map((p, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-emerald-500/40"
                    style={{ height: `${Math.max(4, Math.min(32, Math.abs(p))) }px`, alignSelf: 'center' }}
                  />
                ))}
              </div>
            </div>
          )}
          <Timeline totalSec={totalSec} onScrub={(sec)=> setCursor(sec)} />
          <div className="grid grid-cols-12 gap-3">
            <div className="col-span-8 space-y-3">
              <Mixer />
              {drumTrackId && drumClipId && (
                <DrumEditorPanel trackId={drumTrackId} clipId={drumClipId} />
              )}
              <DrumCreationPanel
                sourceSong={sourceSong}
                sections={sections}
                onApplyDrums={(payload) => {
                  if (!drumTrackId || !drumClipId) return

                  const ppq = song.ppq
                  const firstTempo = song.tempoMap[0]?.bpm ?? 120
                  const ticksPerSecond = (firstTempo / 60) * ppq

                  const newNotes = (payload.midi_notes || []).map((n: any, idx: number) => {
                    const t0 = Math.round(n.time * ticksPerSecond)
                    const lengthSec = n.length ?? 0.25
                    const t1 = t0 + Math.round(lengthSec * ticksPerSecond)
                    return {
                      id: `gen_${idx}`,
                      t0,
                      t1,
                      pitch: n.note,
                      vel: n.velocity,
                      chan: 10,
                      articulationId: n.articulationId,
                    }
                  })

                  updateNotes(drumTrackId, drumClipId, newNotes)
                }}
              />
              <ImpactDrumsPanel value={impact as any} onChange={setImpact as any} />
            </div>
            <div className="col-span-4 space-y-3">
              <GrooveCoachPanel />
              <ReviewPanel />
            </div>
          </div>
        </div>
      </div>

      <KitBuilderModal open={kitOpen} onClose={()=> setKitOpen(false)} />
      <ExportDialog open={expOpen} onClose={()=> setExpOpen(false)} />
      <PocketTransferModal open={pocketOpen} onClose={()=> setPocketOpen(false)} />
    </div>
  )
}
