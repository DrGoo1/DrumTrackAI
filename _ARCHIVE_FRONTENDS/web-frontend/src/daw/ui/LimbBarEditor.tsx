import React, { useEffect, useMemo, useState } from "react"
import { useMidi } from "../../midi/midiStore"
import type { MidiNote } from "../../midi/types"
import { KnobCircle } from "./KnobCircle"
import { DrumIcon } from "./DrumIcon"
import { drumKindFromNote } from "./drumKindFromNote"

type Resolution = 16 | 32 | 64

type TimeSpan = "1" | "1/2" | "1/4" | "1/8" // full bar down to 1/8 of a bar

type LimbRow = "LH" | "RH" | "LF" | "RF"

const LIMB_ORDER: LimbRow[] = ["LH", "RH", "LF", "RF"]

type SlotKey = string // `${limb}:${step}`

interface SlotMeta {
  open: number
  priority: number
  timing: number
  power: number
}

interface LimbBarEditorProps {
  trackId: string
  clipId: string

  // Optional callback so the parent (AppDAW) can collect per-bar defaults and
  // per-slot overrides and forward them into the drum generation DTO.
  onBarMetaChange?: (
    barIndex: number,
    defaults: SlotMeta,
    slots: { limb: LimbRow; step: number; meta: SlotMeta }[],
  ) => void
}

function limbFromPitch(n: MidiNote): LimbRow {
  const p = n.pitch
  if (p === 35 || p === 36) return "RF"
  if (p === 38 || p === 40 || (p >= 41 && p <= 48)) return "LH"
  if (p === 42 || p === 44 || p === 46 || (p >= 49 && p <= 59)) return "RH"
  return "LH"
}

export const LimbBarEditor: React.FC<LimbBarEditorProps> = ({ trackId, clipId, onBarMetaChange }) => {
  const { song, getClip } = useMidi()
  const clip = getClip(trackId, clipId)

  const [barResolution, setBarResolution] = useState<Resolution>(16)
  const [currentBar, setCurrentBar] = useState(0)
  const [mode, setMode] = useState<'full' | 'auto' | 'bar' | 'recompose'>("full")
  const [strokeMode, setStrokeMode] = useState<'single' | 'double' | 'bounced' | 'locked'>("single")

  const [timeSpan, setTimeSpan] = useState<TimeSpan>("1")

  const [barDefaults, setBarDefaults] = useState<SlotMeta>({
    open: 0.0,
    priority: 0.5,
    timing: 0.5,
    power: 0.8,
  })
  const [slotMeta, setSlotMeta] = useState<Record<SlotKey, SlotMeta>>({})
  const [selectedSlot, setSelectedSlot] = useState<{ limb: LimbRow; step: number } | null>(null)

  const ppq = song.ppq || 480
  const barTicks = ppq * 4

  // Derive bar metrics safely even when there is no clip yet.
  const totalTicks = clip ? clip.endTick - clip.startTick : 0
  const barCount = clip ? Math.max(1, Math.ceil(totalTicks / barTicks)) : 1
  const safeBar = clip ? Math.min(currentBar, barCount - 1) : 0
  const barStartTick = clip ? clip.startTick + safeBar * barTicks : 0

  const spanFactor =
    timeSpan === "1"
      ? 1
      : timeSpan === "1/2"
      ? 0.5
      : timeSpan === "1/4"
      ? 0.25
      : 0.125

  const visibleTicks = barTicks * spanFactor
  const barEndTick = barStartTick + visibleTicks

  const steps = barResolution
  const ticksPerStep = barTicks / steps

  const grid = useMemo(() => {
    const out: Record<LimbRow, Record<number, MidiNote[]>> = {
      LH: {},
      RH: {},
      LF: {},
      RF: {},
    }

    if (!clip) return out

    for (const n of clip.notes || []) {
      if (n.t1 <= barStartTick || n.t0 >= barEndTick) continue
      const limb = limbFromPitch(n)
      const relTicks = n.t0 - barStartTick
      const step = Math.max(0, Math.min(steps - 1, Math.floor(relTicks / ticksPerStep)))
      if (!out[limb][step]) out[limb][step] = []
      out[limb][step].push(n)
    }
    return out
  }, [clip, barStartTick, barEndTick, steps, ticksPerStep])

  const selectedKey: SlotKey | null = selectedSlot
    ? `${selectedSlot.limb}:${selectedSlot.step}`
    : null

  const activeMeta: SlotMeta = selectedKey && slotMeta[selectedKey]
    ? slotMeta[selectedKey]
    : barDefaults

  // Notify parent of the current bar's defaults + per-slot overrides whenever
  // they change. The parent is responsible for storing this per bar index.
  useEffect(() => {
    if (!clip || !onBarMetaChange) return
    const slots: { limb: LimbRow; step: number; meta: SlotMeta }[] = []
    for (const [key, meta] of Object.entries(slotMeta)) {
      const [limbStr, stepStr] = key.split(":")
      const limb = limbStr as LimbRow
      const step = Number(stepStr) || 0
      slots.push({ limb, step, meta })
    }
    onBarMetaChange(safeBar, barDefaults, slots)
  }, [clip, onBarMetaChange, safeBar, barDefaults, slotMeta])

  if (!clip) {
    return <div className="text-[11px] text-neutral-500">No clip selected.</div>
  }

  return (
    <div className="w-full bg-neutral-950 border border-neutral-800 rounded p-3 text-[12px] space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button className="px-2 py-1 rounded bg-neutral-900 border border-neutral-700 text-[11px]">
            BAR
          </button>
          <select
            className="bg-neutral-950 border border-neutral-700 rounded px-1 py-0.5 text-[11px]"
            value={safeBar}
            onChange={(e) => setCurrentBar(Number(e.target.value))}
          >
            {Array.from({ length: barCount }).map((_, i) => (
              <option key={i} value={i}>
                {i + 1}
              </option>
            ))}
          </select>
          <button className="px-2 py-1 rounded bg-neutral-900 border border-neutral-700 text-[11px]">
            CLEAR
          </button>
        </div>
        <button className="px-2 py-1 rounded bg-emerald-700 border border-emerald-400 text-[11px]">
          PREVIEW
        </button>
      </div>

      <div className="flex items-center gap-1 text-[11px]">
        {(["full", "auto", "bar", "recompose"] as const).map((m) => (
          <button
            key={m}
            className={
              "px-2 py-1 rounded border " +
              (mode === m
                ? "bg-emerald-700/80 border-emerald-400 text-white"
                : "bg-neutral-900 border-neutral-700 text-neutral-300")
            }
            onClick={() => setMode(m)}
          >
            {m.toUpperCase()}
          </button>
        ))}
        <div className="flex-1" />
        <span className="mr-1 text-neutral-400">SPAN</span>
        {["1", "1/2", "1/4", "1/8"].map((s) => (
          <button
            key={s}
            className={
              "px-1.5 py-0.5 rounded border text-[10px] " +
              (timeSpan === s
                ? "bg-purple-700/80 border-purple-400 text-white"
                : "bg-neutral-900 border-neutral-700 text-neutral-300")
            }
            onClick={() => setTimeSpan(s as TimeSpan)}
          >
            {s}
          </button>
        ))}

        <span className="ml-3 mr-1 text-neutral-400">RES</span>
        {[16, 32, 64].map((r) => (
          <button
            key={r}
            className={
              "px-1.5 py-0.5 rounded border text-[10px] " +
              (barResolution === r
                ? "bg-cyan-700/80 border-cyan-400 text-white"
                : "bg-neutral-900 border-neutral-700 text-neutral-300")
            }
            onClick={() => setBarResolution(r as Resolution)}
          >
            {r}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-1 text-[10px]">
        {(["single", "double", "bounced", "locked"] as const).map((s) => (
          <button
            key={s}
            className={
              "px-1.5 py-0.5 rounded border " +
              (strokeMode === s
                ? "bg-sky-700/80 border-sky-400 text-white"
                : "bg-neutral-900 border-neutral-700 text-neutral-300")
            }
            onClick={() => setStrokeMode(s)}
          >
            {s.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-5">
        <KnobCircle
          label="OPEN"
          value={activeMeta.open}
          onChange={(v) => {
            if (selectedKey) {
              setSlotMeta((prev) => ({
                ...prev,
                [selectedKey]: {
                  ...(prev[selectedKey] ?? barDefaults),
                  open: v,
                },
              }))
            } else {
              setBarDefaults((prev) => ({ ...prev, open: v }))
            }
          }}
        />
        <KnobCircle
          label="PRIORITY"
          value={activeMeta.priority}
          onChange={(v) => {
            if (selectedKey) {
              setSlotMeta((prev) => ({
                ...prev,
                [selectedKey]: {
                  ...(prev[selectedKey] ?? barDefaults),
                  priority: v,
                },
              }))
            } else {
              setBarDefaults((prev) => ({ ...prev, priority: v }))
            }
          }}
        />
        <KnobCircle
          label="TIMING"
          value={activeMeta.timing}
          onChange={(v) => {
            if (selectedKey) {
              setSlotMeta((prev) => ({
                ...prev,
                [selectedKey]: {
                  ...(prev[selectedKey] ?? barDefaults),
                  timing: v,
                },
              }))
            } else {
              setBarDefaults((prev) => ({ ...prev, timing: v }))
            }
          }}
        />
        <KnobCircle
          label="POWER"
          value={activeMeta.power}
          onChange={(v) => {
            if (selectedKey) {
              setSlotMeta((prev) => ({
                ...prev,
                [selectedKey]: {
                  ...(prev[selectedKey] ?? barDefaults),
                  power: v,
                },
              }))
            } else {
              setBarDefaults((prev) => ({ ...prev, power: v }))
            }
          }}
        />
      </div>

      <div className="border border-neutral-800 rounded bg-neutral-900/80 overflow-hidden">
        {LIMB_ORDER.map((limb) => (
          <div
            key={limb}
            className="flex items-stretch border-t border-neutral-800 last:border-b-0"
          >
            <div className="w-12 px-2 flex items-center justify-end text-[11px] text-neutral-400">
              {limb}
            </div>
            <div className="flex-1 grid" style={{ gridTemplateColumns: `repeat(${steps}, 1fr)` }}>
              {Array.from({ length: steps }).map((_, stepIdx) => {
                const notes = grid[limb][stepIdx] || []
                const isAlt = (stepIdx % 4) < 2
                const cellBg = isAlt ? "bg-neutral-900" : "bg-neutral-800/80"

                const isSelected =
                  selectedSlot?.limb === limb && selectedSlot?.step === stepIdx

                return (
                  <div
                    key={stepIdx}
                    className={`${cellBg} relative border-l border-neutral-800/60 h-12 ${
                      isSelected ? "ring-1 ring-cyan-400" : ""
                    }`}
                    onClick={() => setSelectedSlot({ limb, step: stepIdx })}
                  >
                    {notes.map((n, i) => {
                      const velNorm = Math.min(1, Math.max(0, n.vel / 127))
                      const ghost = velNorm < 0.35
                      const accent = velNorm > 0.8
                      const barHeight = Math.max(6, velNorm * 16)

                      return (
                        <div
                          key={`${n.id}-${i}`}
                          className="absolute inset-0 flex items-center justify-center"
                        >
                          <DrumIcon
                            kind={drumKindFromNote(n)}
                            ghost={ghost}
                            accent={accent}
                            size={11}
                          />
                          <div
                            className="absolute right-[1px] bottom-[2px] w-[2px] bg-red-500"
                            style={{ height: barHeight }}
                          />
                        </div>
                      )
                    })}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
