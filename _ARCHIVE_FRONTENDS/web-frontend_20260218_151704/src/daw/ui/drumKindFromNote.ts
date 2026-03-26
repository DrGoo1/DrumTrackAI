import type { MidiNote } from "../../midi/types"
import type { DrumKind } from "./drumKinds"

export function drumKindFromNote(n: MidiNote): DrumKind {
  const p = n.pitch
  if (p === 35 || p === 36) return "kick"
  if (p === 38 || p === 40) return "snare"
  if (p >= 41 && p <= 48) return "tom"
  if (p === 42 || p === 44) return "hat_closed"
  if (p === 46) return "hat_open"
  if (p === 51 || p === 53) return "ride"
  if (p === 49 || p === 57) return "crash"
  return "perc"
}
