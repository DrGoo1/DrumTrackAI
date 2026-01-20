import { create } from 'zustand'

export type MidiEvent = { time_sec: number; lane: string; velocity?: number }
export type LaneMap = Record<string, MidiEvent[]>
export type Marker = { t: number; cls: "kick"|"snare"|"hh"|"other"; conf?: number; dur?: number }
export type Clip = { id: string; key: string; startSec: number; durationSec: number; peaksKey?: string }
export type Track = { id: string; name: string; gainDb: number; pan: number; mute: boolean; solo: boolean; clips: Clip[]; markers?: Marker[] }
export type Project = { id: string; name: string; bpm: number; timeSig: [number, number]; lengthSec: number; tracks: Track[] }

function uid(prefix = "id") { return `${prefix}_${Math.random().toString(36).slice(2,9)}`; }

interface ZoomState { pxPerSecond: number; setZoom: (v:number)=>void }
interface TransportState { playing:boolean; cursorSec:number; setPlaying:(b:boolean)=>void; setCursor:(s:number)=>void }
interface GridState { bpm:number; timeSig:[number,number]; snap:boolean; grid:'bar'|'beat'|'1/2'|'1/4'|'off'; setBpm:(n:number)=>void; setTimeSig:(n:[number,number])=>void; setSnap:(b:boolean)=>void; setGrid:(g:'bar'|'beat'|'1/2'|'1/4'|'off')=>void }
interface KitState { kitMap: Record<string,string>; setKit:(m:Record<string,string>)=>void }
interface SessionState { jobId:string; setJobId:(s:string)=>void }
interface GrooveState { grooveMetrics: any | null; setGrooveMetrics:(g:any)=>void }
interface LoopsState { refLoops: any[]; setRefLoops:(a:any[])=>void }
interface ReviewState { comments: any[]; setComments:(a:any[])=>void }
interface ProjectState { 
  project: Project | null; 
  newProject: (name?: string) => void;
  addTrack: (name: string) => string;
  addClipToTrack: (trackId: string, key: string, startSec: number, durationSec: number) => string;
  setTrackMix: (id: string, gainDb: number, pan: number) => void;
  setTrackMarkers: (id: string, markers: Marker[]) => void;
}

export const useDawStore = create<ZoomState & TransportState & GridState & KitState & SessionState & GrooveState & LoopsState & ReviewState & ProjectState>((set, get)=>({
  pxPerSecond: 120,
  setZoom:(v)=>set({pxPerSecond: Math.max(20, Math.min(600, v))}),
  playing:false,
  cursorSec:0,
  setPlaying:(b)=>set({playing:b}),
  setCursor:(s)=>set({cursorSec:s}),
  bpm:120,
  timeSig:[4,4],
  snap:true,
  grid:'beat',
  setBpm:(n)=>set({bpm:n}),
  setTimeSig:(n)=>set({timeSig:n}),
  setSnap:(b)=>set({snap:b}),
  setGrid:(g)=>set({grid:g}),
  kitMap:{},
  setKit:(m)=>set({kitMap:m}),
  jobId: Math.random().toString(36).slice(2),
  setJobId:(s)=>set({jobId:s}),
  grooveMetrics:null,
  setGrooveMetrics:(g)=>set({grooveMetrics:g}),
  refLoops:[],
  setRefLoops:(a)=>set({refLoops:a}),
  comments:[],
  setComments:(a)=>set({comments:a}),
  // Core DAW Baseline: Multi-track project support
  project: null,
  newProject: (name = "Untitled") => set({
    project: { id: uid("p"), name, bpm: 120, timeSig: [4,4], lengthSec: 180, tracks: [] }
  }),
  addTrack: (name) => {
    const id = uid("t");
    set((s) => s.project ? { project: { ...s.project, tracks: [...s.project.tracks, { id, name, gainDb: 0, pan: 0, mute: false, solo: false, clips: [] }] } } : s);
    return id;
  },
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
  setTrackMarkers: (id, markers) => set((s) => {
    if (!s.project) return s;
    const tracks = s.project.tracks.map(t => t.id !== id ? t : { ...t, markers });
    return { project: { ...s.project, tracks } };
  }),
}))
