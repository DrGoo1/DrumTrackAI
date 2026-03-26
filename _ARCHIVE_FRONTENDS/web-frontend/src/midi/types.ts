// MIDI Types for DrumTracKAI Open Source WebDAW
// PPQ-based timing with variable tempo support

export type PPQ = 480
export type Tick = number

export type MidiNote = {
  id: string
  t0: Tick        // start tick
  t1: Tick        // end tick  
  pitch: number   // MIDI note number (0-127)
  vel: number     // velocity (0-127)
  chan: number    // MIDI channel (1-16)
  articulationId?: string
}

export type MidiClip = {
  id: string
  name: string
  startTick: Tick
  endTick: Tick
  notes: MidiNote[]
  dcsmTrack?: any
}

export type MidiTrackKind = 'drums' | 'bass' | 'melodic'

export type MidiTrack = {
  id: string
  name: string
  kind: MidiTrackKind
  chan: number
  clips: MidiClip[]
  muted: boolean
  solo: boolean
}

// Tempo and arrangement from audio analysis
export type TempoPt = {
  tSec: number    // time in seconds
  bpm: number     // beats per minute
}

export type ArrangementSection = {
  label: string
  startSec: number
  endSec: number
  conf?: number   // confidence from analysis
}

export type MidiSong = {
  ppq: PPQ
  tempoMap: TempoPt[]
  timeSig: [number, number]  // [numerator, denominator]
  sections: ArrangementSection[]
  tracks: MidiTrack[]
}

// Drum kit mapping for generation
export type DrumMap = {
  kick: number     // MIDI note for kick
  snare: number    // MIDI note for snare
  hihat: number    // MIDI note for hi-hat
  openhat: number  // MIDI note for open hi-hat
  crash: number    // MIDI note for crash
  ride: number     // MIDI note for ride
  tom1: number     // MIDI note for high tom
  tom2: number     // MIDI note for mid tom
  tom3: number     // MIDI note for floor tom
}

// Style parameters for drum generation
export type DrumStyle = {
  genre: string
  subGenre?: string
  swing: number      // 0-100, swing amount
  density: number    // 0-100, note density
  humanize: number   // 0-100, timing/velocity variation
  bassAware: boolean // use bass events for kick placement
}

// Bass events from audio analysis
export type BassEvent = {
  tSec: number
  pitch: number
  conf: number
  dur: number
}
