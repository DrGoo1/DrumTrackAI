import { create } from "zustand";

export type Marker = { t: number; cls: string; conf?: number; dur?: number };
export type Section = { label: string; startSec: number; endSec: number; conf?: number };
export type TempoPoint = { tSec: number; bpm: number };
export type Analytics = {
  style?: { genre?: string; sub?: string; conf?: number };
  globalBpm?: number;
  timeSig?: [number, number];
  tempoMap?: TempoPoint[];
  sections?: Section[];
  key?: string;
};

export type Clip = { id: string; key: string; startSec: number; durationSec: number; peaksKey?: string };
export type Track = { 
  id: string; 
  name: string; 
  gainDb: number; 
  pan: number; // -1..1
  mute: boolean; 
  solo: boolean; 
  isBass?: boolean;
  clips: Clip[]; 
  markers?: Marker[];
  waveform?: { sr: number; peaks: number[]; samples?: number };
  fileKey?: string;
};
export type Project = { 
  id: string; 
  name: string; 
  bpm: number; 
  timeSig: [number, number]; 
  lengthSec: number; 
  tracks: Track[];
  analytics?: Analytics;
  originalBpm?: number; // bpm at import time (for tempo ratio)
};

function uid(prefix = "id") { return `${prefix}_${Math.random().toString(36).slice(2,9)}`; }

interface DAWState {
  project: Project | null;
  pxPerSecond: number;
  cursorSec: number;
  playing: boolean;
  // loop & follow
  loopEnabled: boolean;
  loopStartSec: number;
  loopEndSec: number;
  followPlayhead: boolean;
  // setters
  setZoom: (z: number) => void;
  newProject: (name?: string) => void;
  setBpm: (bpm: number) => void;
  addTrack: (name: string) => string; // returns trackId
  removeTrack: (id: string) => void;
  addClipToTrack: (trackId: string, key: string, startSec: number, durationSec: number) => string; // clipId
  setTrackMix: (id: string, gainDb: number, pan: number) => void;
  toggleMute: (id: string) => void;
  toggleSoloExclusive: (id: string) => void;
  // analytics setters
  setAnalytics: (a: Analytics) => void;
  setTempoMap: (points: TempoPoint[]) => void;
  setTrackIsBass: (id: string, on: boolean) => void;
  setTrackWaveform: (id: string, waveform: { sr: number; peaks: number[]; samples?: number }) => void;
  setTrackFileKey: (id: string, fileKey: string) => void;
  // transport setters
  setCursor: (sec: number) => void;
  play: () => void;
  pause: () => void;
  stop: () => void;
  setLoop: (start: number, end: number) => void;
  toggleLoop: (on?: boolean) => void;
  setFollow: (on: boolean) => void;
}

export const useDawStore = create<DAWState>((set, get) => ({
  project: null,
  pxPerSecond: 120,
  cursorSec: 0,
  playing: false,
  loopEnabled: false,
  loopStartSec: 0,
  loopEndSec: 8,
  followPlayhead: true,
  
  setZoom: (z) => set({ pxPerSecond: Math.max(30, Math.min(600, z)) }),
  newProject: (name = "Untitled") => set({
    project: { id: uid("p"), name, bpm: 120, timeSig: [4,4], lengthSec: 180, tracks: [] }
  }),
  setBpm: (bpm) => set((s) => s.project ? { project: { ...s.project, bpm } } : s),
  addTrack: (name) => {
    const id = uid("t");
    set((s) => s.project ? { project: { ...s.project, tracks: [...s.project.tracks, { id, name, gainDb: 0, pan: 0, mute: false, solo: false, clips: [] }] } } : s);
    return id;
  },
  removeTrack: (id) => set((s) => {
    if (!s.project) return s;
    const tracks = s.project.tracks.filter(t => t.id !== id);
    return { project: { ...s.project, tracks } };
  }),
  addClipToTrack: (trackId, key, startSec, durationSec) => {
    const cid = uid("c");
    set((s) => {
      if (!s.project) return s;
      const tracks = s.project.tracks.map(t => t.id !== trackId ? t : { ...t, clips: [...t.clips, { id: cid, key, startSec, durationSec }] });
      return { project: { ...s.project, tracks } };
    });
    return cid;
  },
  setTrackMix: (id, gainDb, pan) => set((s) => {
    if (!s.project) return s;
    const tracks = s.project.tracks.map(t => t.id !== id ? t : { ...t, gainDb, pan });
    return { project: { ...s.project, tracks } };
  }),
  toggleMute: (id) => set((s) => {
    if (!s.project) return s;
    const tracks = s.project.tracks.map(t => t.id !== id ? t : { ...t, mute: !t.mute });
    return { project: { ...s.project, tracks } };
  }),
  toggleSoloExclusive: (id) => set((s) => {
    if (!s.project) return s;
    const tracks = s.project.tracks.map(t => t.id !== id ? { ...t, solo: false } : { ...t, solo: !t.solo });
    return { project: { ...s.project, tracks } };
  }),
  
  // analytics
  setAnalytics: (a) => set((s) => s.project ? { project: { ...s.project, analytics: { ...(s.project.analytics || {}), ...a } } } : s),
  setTempoMap: (points) => set((s) => {
    if (!s.project) return s;
    const analytics = { ...(s.project.analytics || {}), tempoMap: points };
    return { project: { ...s.project, analytics } };
  }),
  setTrackIsBass: (id, on) => set((s) => {
    if (!s.project) return s;
    const tracks = s.project.tracks.map(t => t.id === id ? { ...t, isBass: on } : t);
    return { project: { ...s.project, tracks } };
  }),
  setTrackWaveform: (id, waveform) => set((s) => {
    if (!s.project) return s;
    const tracks = s.project.tracks.map(t => t.id === id ? { ...t, waveform } : t);
    return { project: { ...s.project, tracks } };
  }),
  setTrackFileKey: (id, fileKey) => set((s) => {
    if (!s.project) return s;
    const tracks = s.project.tracks.map(t => t.id === id ? { ...t, fileKey } : t);
    return { project: { ...s.project, tracks } };
  }),
  
  // transport
  setCursor: (sec) => set({ cursorSec: Math.max(0, sec) }),
  play: () => set({ playing: true }),
  pause: () => set({ playing: false }),
  stop: () => set({ playing: false, cursorSec: 0 }),
  setLoop: (start, end) => set({ loopStartSec: Math.max(0, Math.min(start, end)), loopEndSec: Math.max(start, end) }),
  toggleLoop: (on) => set((s) => ({ loopEnabled: on ?? !s.loopEnabled })),
  setFollow: (on) => set({ followPlayhead: on }),
}));
