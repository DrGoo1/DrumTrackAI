// MIDI Store using Zustand for DrumTracKAI Open Source WebDAW
// Manages MIDI tracks, clips, notes, and synchronization with audio timeline

import { create } from 'zustand'
import { MidiSong, MidiTrack, MidiClip, MidiNote, TempoPt, ArrangementSection, MidiTrackKind } from './types'
import { createDefaultTempoMap } from './tempo'

interface MidiState {
  song: MidiSong
  
  // Tempo and arrangement sync
  setTempoMap: (tempoMap: TempoPt[]) => void
  setSections: (sections: ArrangementSection[]) => void
  setTimeSig: (numerator: number, denominator: number) => void
  
  // Track management
  addTrack: (track: Omit<MidiTrack, 'id' | 'clips' | 'muted' | 'solo'>) => string
  removeTrack: (trackId: string) => void
  updateTrack: (trackId: string, updates: Partial<MidiTrack>) => void
  toggleMute: (trackId: string) => void
  toggleSoloExclusive: (trackId: string) => void
  
  // Clip management
  addClip: (trackId: string, clip: Omit<MidiClip, 'id'>) => string
  removeClip: (trackId: string, clipId: string) => void
  updateClip: (trackId: string, clipId: string, updates: Partial<MidiClip>) => void
  
  // Note management
  updateNotes: (trackId: string, clipId: string, notes: MidiNote[]) => void
  addNote: (trackId: string, clipId: string, note: Omit<MidiNote, 'id'>) => string
  removeNote: (trackId: string, clipId: string, noteId: string) => void
  updateNote: (trackId: string, clipId: string, noteId: string, updates: Partial<MidiNote>) => void
  
  // Utility functions
  getTrack: (trackId: string) => MidiTrack | undefined
  getClip: (trackId: string, clipId: string) => MidiClip | undefined
  getAllNotes: () => { trackId: string; clipId: string; note: MidiNote }[]
  clearAll: () => void
  
  // Import/Export state
  importSong: (song: MidiSong) => void
  exportSong: () => MidiSong
}

const createDefaultSong = (): MidiSong => ({
  ppq: 480,
  tempoMap: createDefaultTempoMap(120),
  timeSig: [4, 4],
  sections: [],
  tracks: []
})

export const useMidi = create<MidiState>((set, get) => ({
  song: createDefaultSong(),
  
  // Tempo and arrangement sync
  setTempoMap: (tempoMap) => 
    set(state => ({ 
      song: { ...state.song, tempoMap: [...tempoMap] } 
    })),
    
  setSections: (sections) =>
    set(state => ({
      song: { ...state.song, sections: [...sections] }
    })),
    
  setTimeSig: (numerator, denominator) =>
    set(state => ({
      song: { ...state.song, timeSig: [numerator, denominator] }
    })),
  
  // Track management
  addTrack: (trackData) => {
    const id = `mtrk_${crypto.randomUUID()}`
    set(state => ({
      song: {
        ...state.song,
        tracks: [
          ...state.song.tracks,
          {
            id,
            clips: [],
            muted: false,
            solo: false,
            ...trackData
          }
        ]
      }
    }))
    return id
  },
  
  removeTrack: (trackId) =>
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.filter(t => t.id !== trackId)
      }
    })),
    
  updateTrack: (trackId, updates) =>
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => 
          t.id === trackId ? { ...t, ...updates } : t
        )
      }
    })),
  
  toggleMute: (trackId) =>
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => 
          t.id === trackId ? { ...t, muted: !t.muted } : t
        )
      }
    })),
  
  toggleSoloExclusive: (trackId) =>
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => ({
          ...t,
          solo: t.id === trackId ? !t.solo : false
        }))
      }
    })),
  
  // Clip management
  addClip: (trackId, clipData) => {
    const id = `clip_${crypto.randomUUID()}`
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => 
          t.id === trackId 
            ? { ...t, clips: [...t.clips, { id, ...clipData }] }
            : t
        )
      }
    }))
    return id
  },
  
  removeClip: (trackId, clipId) =>
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => 
          t.id === trackId 
            ? { ...t, clips: t.clips.filter(c => c.id !== clipId) }
            : t
        )
      }
    })),
    
  updateClip: (trackId, clipId, updates) =>
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => 
          t.id === trackId 
            ? { 
                ...t, 
                clips: t.clips.map(c => 
                  c.id === clipId ? { ...c, ...updates } : c
                )
              }
            : t
        )
      }
    })),
  
  // Note management
  updateNotes: (trackId, clipId, notes) =>
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => 
          t.id === trackId 
            ? { 
                ...t, 
                clips: t.clips.map(c => 
                  c.id === clipId ? { ...c, notes } : c
                )
              }
            : t
        )
      }
    })),
    
  addNote: (trackId, clipId, noteData) => {
    const id = `note_${crypto.randomUUID()}`
    const note = { id, ...noteData }
    
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => 
          t.id === trackId 
            ? { 
                ...t, 
                clips: t.clips.map(c => 
                  c.id === clipId 
                    ? { ...c, notes: [...c.notes, note] }
                    : c
                )
              }
            : t
        )
      }
    }))
    return id
  },
  
  removeNote: (trackId, clipId, noteId) =>
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => 
          t.id === trackId 
            ? { 
                ...t, 
                clips: t.clips.map(c => 
                  c.id === clipId 
                    ? { ...c, notes: c.notes.filter(n => n.id !== noteId) }
                    : c
                )
              }
            : t
        )
      }
    })),
    
  updateNote: (trackId, clipId, noteId, updates) =>
    set(state => ({
      song: {
        ...state.song,
        tracks: state.song.tracks.map(t => 
          t.id === trackId 
            ? { 
                ...t, 
                clips: t.clips.map(c => 
                  c.id === clipId 
                    ? { 
                        ...c, 
                        notes: c.notes.map(n => 
                          n.id === noteId ? { ...n, ...updates } : n
                        )
                      }
                    : c
                )
              }
            : t
        )
      }
    })),
  
  // Utility functions
  getTrack: (trackId) => {
    const { song } = get()
    return song.tracks.find(t => t.id === trackId)
  },
  
  getClip: (trackId, clipId) => {
    const track = get().getTrack(trackId)
    return track?.clips.find(c => c.id === clipId)
  },
  
  getAllNotes: () => {
    const { song } = get()
    const allNotes: { trackId: string; clipId: string; note: MidiNote }[] = []
    
    song.tracks.forEach(track => {
      track.clips.forEach(clip => {
        clip.notes.forEach(note => {
          allNotes.push({ trackId: track.id, clipId: clip.id, note })
        })
      })
    })
    
    return allNotes
  },
  
  clearAll: () => set({ song: createDefaultSong() }),
  
  // Import/Export
  importSong: (song) => set({ song: { ...song } }),
  
  exportSong: () => {
    const { song } = get()
    return { ...song }
  }
}))

// Helper hooks for common operations
export const useMidiTracks = () => useMidi(state => state.song.tracks)
export const useMidiTrack = (trackId: string) => useMidi(state => 
  state.song.tracks.find(t => t.id === trackId)
)
export const useMidiTempoMap = () => useMidi(state => state.song.tempoMap)
export const useMidiSections = () => useMidi(state => state.song.sections)
