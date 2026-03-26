import React, { useEffect, useMemo, useRef, useState } from "react";
import webdawApi, { alignSections, loadSession, saveSession, sectionizeAudio, generateDrumPattern } from "../services/api";
import Timeline from "./Timeline";
import { Engine } from "../audio/engine";
import Mixer from "./Mixer";
import PianoRoll, { MidiNote } from "./PianoRoll";

export type UploadedTrack = {
  key: string;
  peaks: number[];
  sr: number;
  seconds: number;
  color: string;
  name: string;
};

export type Section = {
  id: string;
  start: number;
  end: number;
  density: number;
  fillIn: boolean;
  fillOut: boolean;
  label?: string;
  confidence?: number;
};

function secToBarsBeats(sec: number, bpm: number, [num, den]: [number, number]) {
  const secPerBeat = (60 / bpm) * (4 / den);
  const secPerBar = secPerBeat * num;
  const bar = Math.floor(sec / secPerBar) + 1;
  const beat = Math.floor((sec % secPerBar) / secPerBeat) + 1;
  const frac = ((sec % secPerBeat) / secPerBeat);
  return `${bar}.${beat}${frac >= 0.5 ? "+" : ""}`;
}

export default function WebDAWApp() {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [tracks, setTracks] = useState<UploadedTrack[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [notes, setNotes] = useState<MidiNote[]>([]);

  const [bpm, setBpm] = useState(120);
  const timeSig: [number, number] = [4,4];
  const [playhead, setPlayhead] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [loop, setLoop] = useState({ enabled: false, start: 0, end: 4 });

  const gridSec = useMemo(() => (60 / bpm) * (4 / timeSig[1]) / 16, [bpm, timeSig]); // 1/64

  useEffect(() => {
    let raf = 0; let last = performance.now();
    function tick(now: number) { const dt=(now-last)/1000; last=now; if (playing) setPlayhead(p=>p+dt); raf=requestAnimationFrame(tick);} 
    raf = requestAnimationFrame(tick); return ()=>cancelAnimationFrame(raf);
  }, [playing]);

  useEffect(() => { Engine.setBpm(bpm); }, [bpm]);
  useEffect(() => { Engine.setLoop(loop.start, loop.end, loop.enabled); }, [loop]);
  useEffect(() => {
    const API_BASE = (window as any).__API_BASE__ || process.env.REACT_APP_API_BASE || "http://localhost:8000";
    const urls = tracks.map(t => ({ key: t.key, url: `${String(API_BASE).replace(/\/$/, "")}/files/audio?key=${encodeURIComponent(t.key)}` }));
    Engine.refreshTracks(urls);
  }, [tracks]);
  useEffect(() => { Engine.seek(playhead); }, [playhead]);

  async function addFile(file: File) {
    setBusy(true); setErr(null);
    try {
      const { waveform } = await webdawApi.fullWorkflow(file);
      const colorPool = ["#60a5fa", "#22d3ee", "#a78bfa", "#34d399", "#f59e0b", "#ef4444"];
      const color = colorPool[tracks.length % colorPool.length];
      const seconds = (waveform as any).duration ?? Math.max(1, waveform.peaks.length / 44_100);
      setTracks((t) => [...t, { key: waveform.key, peaks: waveform.peaks, sr: waveform.sr, seconds, color, name: file.name }]);
    } catch (e: any) { setErr(e?.message || "Upload failed"); } finally { setBusy(false); }
  }
  function onDropFiles(list: FileList) { Array.from(list).forEach((f) => addFile(f)); }

  // Generate drum patterns using new DCSM backend with Rust integration
  async function handleGenerate(s: Section) {
    setBusy(true);
    try {
      const result = await generateDrumPattern({
        bpm,
        density: s.density,
        swing: 0.0,
        humanize: 0.1,
        seed: Math.floor(Math.random() * 10000),
        sections: [{
          start: s.start,
          end: s.end,
          fill_in: s.fillIn,
          fill_out: s.fillOut,
          density: s.density
        }]
      });
      
      // Convert backend notes to MidiNote format
      const newNotes: MidiNote[] = result.notes.map(note => ({
        time: note.time,
        lane: note.lane,
        vel: note.vel,
        articulationId: note.articulationId,
      }));
      
      setNotes(n => [...n, ...newNotes]);
      
      // Optional: Handle MIDI export
      if (result.midi_base64) {
        console.log("Generated MIDI (Base64):", result.midi_base64);
      }
    } catch (e: any) {
      setErr(`Generation failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  // Align selected sections to a track's beats
  async function alignTo(trackKey: string) {
    try {
      const { sections: aligned } = await alignSections(trackKey, sections.map(s=>({start:s.start,end:s.end})));
      setSections(sections.map((s,i)=>({ ...s, start: aligned[i].start, end: aligned[i].end })));
    } catch (e) { console.warn("align failed", e); }
  }

  // Auto-detect musical arrangement sections
  async function handleAutoSectionize(trackKey: string) {
    setBusy(true);
    try {
      const result = await sectionizeAudio(trackKey, 2.0);
      const detectedSections: Section[] = result.sections.map((s: any, i: number) => ({
        id: `auto-section-${Date.now()}-${i}`,
        start: s.start,
        end: s.end,
        density: 0.7,
        fillIn: false,
        fillOut: false,
        label: s.label || 'section',
        confidence: s.confidence || 0.8
      }));
      setSections(detectedSections);
    } catch (e: any) {
      setErr(`Auto-sectionization failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  // Save/Load session
  const SID = "dev";
  async function save(){
    try{ await saveSession(SID, { bpm, loop, tracks, sections, notes }); alert("Session saved"); } catch(e){ alert("Save failed"); }
  }
  async function load(){
    try{ 
      const s = await loadSession(SID) as any; 
      setTracks(s.tracks||[]); 
      setSections(s.sections||[]); 
      setNotes(s.notes||[]); 
      setBpm(s.bpm||120); 
      setLoop(s.loop||{enabled:false,start:0,end:4}); 
    } catch(e){ 
      alert("No saved session"); 
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <Mixer tracks={[...tracks.map(t=>({ key:t.key, name:t.name||t.key.split("/").pop()!, color:t.color })), { key:"__drums__", name:"Drums", color:"#f59e0b" }]} />

      <div className="flex-1 min-w-0">
        <div className="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3">
          <div className="font-semibold">DrumTracKAI v1.1.17 – Legacy DCSM/WebDAW</div>
          <div className="flex items-center gap-3">
            <button className="px-2 py-1 rounded bg-emerald-600" onClick={async()=>{ await Engine.play(playhead); setPlaying(true); }}>Play</button>
            <button className="px-2 py-1 rounded bg-slate-700" onClick={async()=>{ await Engine.pause(); setPlaying(false); }}>Pause</button>
            <button className="px-2 py-1 rounded bg-slate-700" onClick={async()=>{ await Engine.stop(); setPlaying(false); setPlayhead(0); }}>Stop</button>
            <div className="flex items-center gap-1">
              <span className="text-slate-400 text-sm">BPM</span>
              <input className="w-16 bg-slate-800 rounded px-2 py-1" type="number" value={bpm} onChange={(e)=>setBpm(Math.max(20, Math.min(300, Number(e.target.value)||120)))} />
            </div>
            <label className="flex items-center gap-1 ml-4">
              <input type="checkbox" checked={loop.enabled} onChange={(e)=>setLoop({ ...loop, enabled: e.target.checked })} /> Loop
            </label>
            <div className="text-sm text-slate-300 w-20 text-right">{secToBarsBeats(playhead, bpm, timeSig)}</div>
            <button className="px-3 py-1 rounded bg-indigo-600" onClick={() => fileRef.current?.click()} disabled={busy}>{busy?"Uploading…":"Upload Audio"}</button>
            <input ref={fileRef} type="file" accept="audio/*" className="hidden" onChange={(e)=>{ const f=e.target.files?.[0]; if (f) addFile(f); e.currentTarget.value=""; }} />
            <button className="px-3 py-1 rounded bg-slate-700" onClick={save}>Save</button>
            <button className="px-3 py-1 rounded bg-slate-700" onClick={load}>Load</button>
            {tracks.length>0 && <button className="px-3 py-1 rounded bg-slate-700" onClick={()=>alignTo(tracks[0].key)}>Align to {tracks[0].name?.split("/").pop()}</button>}
          </div>
        </div>

        <div className="p-4 space-y-4">
          {err && <div className="mb-3 text-rose-400 text-sm">Error: {err}</div>}
          <Timeline
            bpm={bpm}
            tracks={tracks}
            sections={sections}
            onSectionsChange={setSections}
            playhead={playhead}
            setPlayhead={setPlayhead}
            playing={playing}
            onDropFiles={(fs)=>onDropFiles(fs)}
            onGenerate={handleGenerate}
            loop={loop}
            setLoop={setLoop}
            gridSec={gridSec}
            onAutoSectionize={handleAutoSectionize}
          />

          <PianoRoll bpm={bpm} gridSec={gridSec} notes={notes} onChange={setNotes} />
        </div>
      </div>
    </div>
  );
}
