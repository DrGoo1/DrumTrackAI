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
import { LimbBarEditor } from './ui/LimbBarEditor'
import { KitLimbsPanel } from './ui/KitLimbsPanel'
import { useMidi } from '../midi/midiStore'
import { DrumEditorPanel } from './ui/DrumEditorPanel'
import { SourceSongPanel } from './ui/SourceSongPanel'
import { SectionsPanel, SectionRow } from './ui/SectionsPanel'
import { sectionizeAudio, dcsmExportMidi, analyzeTempo, dcsmSectionizeSmart } from '../services/api'

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
  const [impactOpen, setImpactOpen] = useState(false)

  // MIDI drum track + clip for DrumEditorPanel
  const { song, addTrack, addClip, updateNotes, getClip, setTempoMap } = useMidi()
  const [drumTrackId, setDrumTrackId] = useState<string | null>(null)
  const [drumClipId, setDrumClipId] = useState<string | null>(null)
  const [sourceSong, setSourceSong] = useState<{ key: string; durationSec: number; peaks?: number[] } | null>(null)
  const [sections, setSections] = useState<SectionRow[]>([])
  const [lastTempoBpm, setLastTempoBpm] = useState<number | null>(null)
  const [lastConfig, setLastConfig] = useState<any | null>(null)
  const [exportScope, setExportScope] = useState<'clip' | 'first_section'>('clip')
  const [editorMode, setEditorMode] = useState<'limb' | 'piano'>('limb')

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
        setLastTempoBpm(bpm)
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
      const bpm = lastTempoBpm ?? song.tempoMap[0]?.bpm ?? 120
      const result = await dcsmSectionizeSmart(sourceSong.key, bpm)
      const next: SectionRow[] = result.sections.map((s, idx) => ({
        id: `sec-${idx}`,
        start: s.start,
        end: s.end,
        density: 0.7,
        fillIn: false,
        fillOut: false,
        label: s.label || `Section ${idx + 1}`,
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

      let notes = (clip.notes || []).map((n) => ({
        t0: n.t0,
        t1: n.t1,
        pitch: n.pitch,
        vel: n.vel,
        chan: n.chan,
        articulationId: n.articulationId,
      }))

      if (exportScope === 'first_section' && sections.length > 0) {
        const tempoBpm = song.tempoMap[0]?.bpm ?? 120
        const ppq = song.ppq
        const ticksPerSecond = (tempoBpm / 60) * ppq
        const first = sections[0]
        const startTick = Math.round((first.start ?? 0) * ticksPerSecond)
        const endTick = Math.round((first.end ?? first.start ?? 0) * ticksPerSecond)
        notes = notes.filter(n => n.t0 >= startTick && n.t0 < endTick)
      }

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
    <div className="min-h-screen bg-neutral-950 text-white text-[14px] leading-snug">
      <TransportBar />
      <div className="flex items-center gap-2 p-2 border-b border-neutral-800">
        <button className="px-3 py-1 bg-neutral-800 rounded" onClick={()=> setKitOpen(true)}>Kit Builder</button>
        <button className="px-3 py-1 bg-neutral-800 rounded" onClick={()=> setExpOpen(true)}>Export</button>
        <div className="flex items-center gap-1 text-xs">
          <span>Export</span>
          <select
            className="bg-neutral-900 border border-neutral-700 rounded px-1 py-0.5"
            value={exportScope}
            onChange={(e) => setExportScope(e.target.value as any)}
          >
            <option value="clip">Clip</option>
            <option value="first_section">First Section</option>
          </select>
        </div>
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
          <div className="text-[11px] text-neutral-400">
            Debug  sections: {sections.length}, waveformPeaks: {sourceSong?.peaks?.length ?? 0}
          </div>
          {/* Ruler + sections + waveform share the same horizontal scroll space */}
          <div className="space-y-1 overflow-x-auto">
            <div style={{ minWidth: Math.max(600, totalSec * pxPerSecond) }}>
              <BarsBeatsRuler seconds={totalSec} />
              {sections.length > 0 && (
                <div className="relative h-6 bg-neutral-950 border border-neutral-800 rounded overflow-hidden text-[11px] mt-1">
                  {sections.map((s, idx) => {
                    // Fallback: if backend didn't provide sane start/end, spread sections evenly
                    const spanSec = totalSec / sections.length
                    const rawStart = typeof s.start === 'number' && isFinite(s.start) ? s.start : idx * spanSec
                    const rawEnd = typeof s.end === 'number' && isFinite(s.end) ? s.end : rawStart + spanSec
                    const safeStart = Math.max(0, Math.min(totalSec, rawStart))
                    const safeEnd = Math.max(safeStart + 0.1, Math.min(totalSec, rawEnd))
                    const startPx = safeStart * pxPerSecond
                    const width = Math.max(24, (safeEnd - safeStart) * pxPerSecond)
                    const hasFill = s.fillIn || s.fillOut
                    return (
                      <div
                        key={s.id}
                        className={"absolute top-0 bottom-0 flex items-center px-1 border-r " + (hasFill ? "bg-emerald-500/20 border-emerald-400/70" : "bg-neutral-800/40 border-neutral-700/70")}
                        style={{ left: startPx, width }}
                        title={s.label}
                      >
                        <span className="truncate text-cyan-200">{s.label}</span>
                      </div>
                    )
                  })}
                </div>
              )}
              {sourceSong?.peaks && sourceSong.peaks.length > 0 && (
                <div className="h-10 bg-neutral-900 border border-neutral-800 rounded overflow-hidden flex items-center px-1 mt-1">
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
            </div>
          </div>
          <Timeline totalSec={totalSec} onScrub={(sec)=> setCursor(sec)} />
          <div className="grid grid-cols-12 gap-3">
            <div className="col-span-8 space-y-3">
              <Mixer />
              {drumTrackId && drumClipId && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-semibold text-cyan-300 tracking-wide">Drum Editor</div>
                    <div className="text-[11px] flex items-center gap-1 text-neutral-400">
                      <span>View</span>
                      <select
                        className="bg-neutral-950 border border-neutral-700 rounded px-1 py-0.5"
                        value={editorMode}
                        onChange={(e) => setEditorMode(e.target.value as any)}
                      >
                        <option value="limb">Limb View</option>
                        <option value="piano">Piano Roll</option>
                      </select>
                    </div>
                  </div>
                  {editorMode === 'limb' ? (
                    <LimbBarEditor trackId={drumTrackId} clipId={drumClipId} />
                  ) : (
                    <DrumEditorPanel trackId={drumTrackId} clipId={drumClipId} />
                  )}
                </div>
              )}
            </div>
            <div className="col-span-4 space-y-3">
              <KitLimbsPanel />
              <DrumCreationPanel
                sourceSong={sourceSong}
                sections={sections}
                onConfigBuilt={setLastConfig}
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
              {lastConfig && (
                <div className="text-[10px] bg-neutral-950 border border-neutral-800 rounded p-2 space-y-1">
                  <div className="font-semibold text-neutral-300">Debug</div>
                  <div className="text-neutral-400">Tempo Map: {JSON.stringify(song.tempoMap)}</div>
                  <div className="text-neutral-400 overflow-x-auto max-h-32 whitespace-pre">
                    {JSON.stringify(lastConfig, null, 2)}
                  </div>
                </div>
              )}
              <div className="border border-neutral-800 rounded bg-neutral-950/60">
                <button
                  className="w-full flex items-center justify-between px-2 py-1 text-[11px] text-neutral-300 hover:bg-neutral-900"
                  onClick={() => setImpactOpen((v) => !v)}
                >
                  <span>Impact / Saturation</span>
                  <span className="text-neutral-500">{impactOpen ? 'Hide' : 'Show'}</span>
                </button>
                {impactOpen && (
                  <div className="p-2">
                    <ImpactDrumsPanel value={impact as any} onChange={setImpact as any} />
                  </div>
                )}
              </div>
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
