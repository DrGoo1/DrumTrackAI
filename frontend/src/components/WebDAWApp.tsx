import React, { useEffect, useMemo, useRef, useState } from "react";
import webdawApi, { alignSections, loadSession, saveSession, sectionizeAudio, dcsmSectionizeSmart, generateDrumPattern } from "../services/api";
import Timeline from "./Timeline";
import { Engine } from "../audio/engine";
import Mixer from "./Mixer";
import PianoRoll, { MidiNote } from "./PianoRoll";
import { SectionControls } from "./SectionControls";
import { DrummerSelector, Drummer } from "./DrummerSelector";
import DrumOptionsPanel, { DrumOptions } from "./DrumOptionsPanel";
import { ManualArrangementModal, ManualArrangement } from "./ManualArrangementModal";
import { InternetSongLookupModal, SongInfo } from "./InternetSongLookupModal";
import DrumBuilderPanel, { DrumGenerationConfig } from "./DrumBuilderPanel";

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
  label?: string;                 // intro/verse/chorus/bridge/outro/break/solo
  confidence?: number;             // 0.0-1.0 confidence in section label
  energy?: number;                 // 0.0-1.0 RMS energy (loudness)
  spectral_centroid?: number;      // 0.0-1.0 spectral centroid (brightness)
  repetition_group?: number;       // Group ID for similar sections
  tempo?: number;                  // Detected tempo for this section
  tempoConfidence?: number;        // 0.0-1.0 confidence in tempo detection
  tempoLocked?: boolean;           // User has manually set tempo
};

export type MeasureRange = {
  sectionId: string;
  sectionLabel: string;
  startMeasure: number;
  endMeasure: number;
  measureCount: number;
  tempos: number[];
  avgTempo: number;
  timeSignature: [number, number];
};

function secToBarsBeats(sec: number, bpm: number, [num, den]: [number, number]) {
  const secPerBeat = (60 / bpm) * (4 / den);
  const secPerBar = secPerBeat * num;
  const bar = Math.floor(sec / secPerBar) + 1;
  const beat = Math.floor((sec % secPerBar) / secPerBeat) + 1;
  const frac = ((sec % secPerBeat) / secPerBeat);
  return `${bar}.${beat}${frac >= 0.5 ? "+" : ""}`;
}

// Convert section to measure range for drum builder
function sectionToMeasureRange(section: Section, bpm: number, timeSig: [number, number]): MeasureRange {
  const beatsPerMeasure = timeSig[0];
  const secPerBeat = 60 / bpm;
  const secPerMeasure = secPerBeat * beatsPerMeasure;
  
  const startMeasure = Math.floor(section.start / secPerMeasure);
  const endMeasure = Math.ceil(section.end / secPerMeasure);
  const measureCount = endMeasure - startMeasure;
  
  // Create array of tempos (use section tempo or global bpm)
  const tempo = section.tempo || bpm;
  const tempos = Array(measureCount).fill(tempo);
  
  return {
    sectionId: section.id,
    sectionLabel: section.label ? section.label.charAt(0).toUpperCase() + section.label.slice(1) : 'Section',
    startMeasure,
    endMeasure,
    measureCount,
    tempos,
    avgTempo: tempo,
    timeSignature: timeSig
  };
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
  const [selectedDrummer, setSelectedDrummer] = useState<Drummer | null>(null);
  
  // NEW: Selected sections for generation
  const [selectedSectionIds, setSelectedSectionIds] = useState<Set<string>>(new Set());
  
  // NEW: Full SongMap with bars, meter, enhanced sections
  const [songMap, setSongMap] = useState<any | null>(null);
  
  // NEW: Arrangement entry modals
  const [showManualModal, setShowManualModal] = useState(false);
  const [showLookupModal, setShowLookupModal] = useState(false);
  
  // NEW: Track arrangement source for conflict handling
  const [arrangementSource, setArrangementSource] = useState<string | null>(null);
  
  // NEW: Drum Builder - measure range selection
  const [selectedMeasureRange, setSelectedMeasureRange] = useState<MeasureRange | null>(null);
  const [generatingDrums, setGeneratingDrums] = useState(false);
  
  // Comprehensive drum options
  const [drumOptions, setDrumOptions] = useState<DrumOptions>({
    bpm: 120, bars: 8, density: 0.7, swing: 0, humanize: 0.3,
    style: 'rock', label: 'verse', swing_preset: 'off', vel_preset: 'accent24', fill_preset: 'random',
    drum_velocity: 0.85, cymbal_velocity: 0.70, kick_velocity: 0.90, snare_velocity: 0.85,
    tom_velocity: 0.80, hihat_velocity: 0.65, crash_velocity: 0.90, ride_velocity: 0.70,
    drum_density: 0.7, cymbal_density: 0.6, hihat_density: 0.8, ride_density: 0.4, crash_density: 0.2,
    fill_density: 0.7, fill_location: 'end', fill_frequency: 0.25,
    hihat_complexity: 0.5, hihat_pattern: 'eighths', hihat_open_ratio: 0.2, hihat_ghost_notes: 0.3,
    ride_complexity: 0.4, ride_pattern: 'quarters', ride_vs_hihat_ratio: 0.3, ride_bell_ratio: 0.1,
    bass_line_mode: 'auto', bass_kick_sync: 0.7, bass_lock_downbeats: true,
    tom_usage: 0.3, crash_frequency: 0.2, ghost_note_density: 0.2, dynamic_range: 0.5
  });
  
  // Read URL parameters from Professional Tier page
  const [sourceInfo, setSourceInfo] = useState<{source?: string; filename?: string; drummer?: string; fileKey?: string}>({});
  const autoLoadAttemptedRef = useRef(false);
  
  useEffect(() => {
    // Prevent duplicate auto-load in React StrictMode using ref
    if (autoLoadAttemptedRef.current) {
      console.log('⏭️ Auto-load already attempted, skipping');
      return;
    }
    autoLoadAttemptedRef.current = true;
    
    const urlParams = new URLSearchParams(window.location.search);
    const source = urlParams.get('source');
    const filename = urlParams.get('filename');
    const drummer = urlParams.get('drummer');
    const fileKey = urlParams.get('fileKey');
    
    console.log('WebDAWApp URL params:', { source, filename, drummer, fileKey });
    
    if (source || filename || drummer || fileKey) {
      setSourceInfo({ source: source || undefined, filename: filename || undefined, drummer: drummer || undefined, fileKey: fileKey || undefined });
      console.log('✅ Source info set:', { source, filename, drummer, fileKey });
      
      // Auto-load file if fileKey is present
      if (fileKey && filename) {
        console.log('🚀 Starting auto-load for fileKey:', fileKey);
        
        const loadFileFromKeyAsync = async (key: string, name: string) => {
          console.log('📂 loadFileFromKeyAsync called with:', key, name);
          await loadFileFromKey(key, name);
        };
        
        setTimeout(() => loadFileFromKeyAsync(fileKey, filename), 100);
      }
    }
  }, []);

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
  
  // CRITICAL FIX: Only seek when NOT playing (manual seek only)
  // Don't seek during playback - it causes audio distortion!
  useEffect(() => { 
    if (!playing) {
      Engine.seek(playhead); 
    }
  }, [playhead, playing]);

  async function addFile(file: File) {
    setBusy(true); setErr(null);
    try {
      // Upload file and get waveform
      const { waveform } = await webdawApi.fullWorkflow(file);
      const colorPool = ["#60a5fa", "#22d3ee", "#a78bfa", "#34d399", "#f59e0b", "#ef4444"];
      const color = colorPool[tracks.length % colorPool.length];
      const seconds = (waveform as any).duration ?? Math.max(1, waveform.peaks.length / 44_100);
      
      // Add track to display with stereo data if available
      const trackData: any = { 
        key: waveform.key, 
        peaks: waveform.peaks, 
        sr: waveform.sr, 
        seconds, 
        color, 
        name: file.name 
      };
      
      // Add stereo data if present
      if (waveform.peaksL && waveform.peaksR) {
        trackData.peaksL = waveform.peaksL;
        trackData.peaksR = waveform.peaksR;
      } else {
        console.warn('⚠️ No stereo data in waveform response:', Object.keys(waveform));
      }
      
      setTracks((t) => [...t, trackData]);
      
      // Analyze tempo automatically
      try {
        const { analyzeTempo } = await import('../services/api');
        const tempoResult = await analyzeTempo(waveform.key);
        if (tempoResult.tempo && tempoResult.tempo > 0) {
          setBpm(Math.round(tempoResult.tempo));
          console.log(`Detected tempo: ${tempoResult.tempo} BPM`);
        }
      } catch (tempoError: any) {
        console.warn('Tempo detection failed:', tempoError);
        setErr(`Waveform loaded, but tempo detection failed. Using default 120 BPM.`);
      }
      
      // Auto-sectionize after tempo is detected
      if (waveform.key) {
        // Give tempo detection a moment to complete
        setTimeout(() => handleAutoSectionize(waveform.key), 500);
      }
    } catch (e: any) { setErr(e?.message || "Upload failed"); } finally { setBusy(false); }
  }
  
  const loadingFilesRef = useRef<Set<string>>(new Set());
  
  async function loadFileFromKey(fileKey: string, filename: string) {
    // Prevent duplicate loading using ref-based lock
    if (loadingFilesRef.current.has(fileKey)) {
      return;
    }
    
    // Check if track already exists
    if (tracks.some(t => t.key === fileKey)) {
      console.log('Track already loaded, skipping');
      return;
    }
    
    // Lock this file key
    loadingFilesRef.current.add(fileKey);
    setBusy(true); setErr(null);
    
    try {
      console.log('Loading file from key:', fileKey);
      
      // Fetch waveform data from backend using the file key
      const API_BASE = (window as any).__API_BASE__ || process.env.REACT_APP_API_BASE || "http://localhost:8000";
      const response = await fetch(`${API_BASE}/waveform?key=${encodeURIComponent(fileKey)}`);
      
      if (!response.ok) {
        throw new Error('Failed to load waveform');
      }
      
      const waveform = await response.json();
      const colorPool = ["#60a5fa", "#22d3ee", "#a78bfa", "#34d399", "#f59e0b", "#ef4444"];
      const color = colorPool[tracks.length % colorPool.length];
      const seconds = (waveform as any).duration ?? Math.max(1, waveform.peaks.length / 44_100);
      
      // Add track to display - check again to prevent race condition
      setTracks((t) => {
        if (t.some(track => track.key === fileKey)) {
          console.log('Track already in list, not adding');
          return t;
        }
        // Include stereo peaks if available
        const trackData: any = { 
          key: fileKey, 
          peaks: waveform.peaks, 
          sr: waveform.sr, 
          seconds, 
          color, 
          name: filename 
        };
        
        // Add stereo data if present
        if (waveform.peaksL && waveform.peaksR) {
          trackData.peaksL = waveform.peaksL;
          trackData.peaksR = waveform.peaksR;
        } else {
          console.warn('⚠️ No stereo data in waveform response:', Object.keys(waveform));
        }
        
        
        return [...t, trackData];
      });
      
      // Analyze tempo automatically
      try {
        const { analyzeTempo } = await import('../services/api');
        const tempoResult = await analyzeTempo(fileKey);
        if (tempoResult.tempo && tempoResult.tempo > 0) {
          setBpm(Math.round(tempoResult.tempo));
          console.log(`Detected tempo: ${tempoResult.tempo} BPM`);
        }
      } catch (tempoError: any) {
        console.warn('Tempo detection failed:', tempoError);
      }
      
      // Auto-sectionize
      if (fileKey) {
        setTimeout(() => handleAutoSectionize(fileKey), 500);
      }
    } catch (e: any) { 
      setErr(e?.message || "Failed to load file");
      console.error('Load file error:', e);
    } finally { 
      setBusy(false);
      // Release the lock so file can be loaded again if needed
      loadingFilesRef.current.delete(fileKey);
    }
  }
  
  function onDropFiles(list: FileList) { Array.from(list).forEach((f) => addFile(f)); }

  // Generate drum patterns using new DCSM backend with Rust integration
  async function handleGenerate(s: Section) {
    setBusy(true);
    try {
      // If drummer is selected, use drummer-specific generation
      if (selectedDrummer) {
        const response = await fetch('/api/generate_with_drummer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            drummer_id: selectedDrummer.id,
            bpm,
            sections: [{
              start: s.start,
              end: s.end,
              fill_in: s.fillIn,
              fill_out: s.fillOut,
              label: s.label || 'verse',
              density: s.density
            }],
            song_analysis: {}
          })
        });
        
        if (!response.ok) {
          throw new Error('Drummer generation failed');
        }
        
        const result = await response.json();
        
        // Convert backend notes to MidiNote format
        const newNotes: MidiNote[] = result.notes.map((note: any) => ({
          time: note.time,
          lane: note.lane,
          vel: note.vel
        }));
        
        setNotes(n => [...n, ...newNotes]);
        console.log(`Generated with ${selectedDrummer.display_name}:`, result.params_used);
      } else {
        // Fallback to generic generation
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
          vel: note.vel
        }));
        
        setNotes(n => [...n, ...newNotes]);
        
        // Optional: Handle MIDI export
        if (result.midi_base64) {
          console.log("Generated MIDI (Base64):", result.midi_base64);
        }
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

  // NEW: Full analysis with bars, meter, and enhanced sections
  async function handleAnalyzeFull(trackKey: string) {
    setBusy(true);
    try {
      const response = await fetch(
        `/dcsm/analyze_full?key=${encodeURIComponent(trackKey)}`
      );
      
      if (!response.ok) {
        throw new Error(`Full analysis failed: ${response.statusText}`);
      }
      
      const json = await response.json();
      
      // Build SongMap
      const map: any = {
        duration: json.duration,
        globalBpmEstimate: json.global_bpm_estimate ?? 120,
        meter: json.meter,
        bars: json.bars,
        sections: json.sections,
        beatTimes: json.beat_times ?? [],
      };
      
      setSongMap(map);
      
      console.log("🎯 SongMap loaded!");
      console.log(`  Global BPM: ${map.globalBpmEstimate}`);
      console.log(`  Meter: ${map.meter[0]}/${map.meter[1]}`);
      console.log(`  Bars: ${map.bars.length}`);
      console.log(`  Sections: ${map.sections.length}`);
      console.log(`  Section labels:`, map.sections.map((s: any) => s.label));
      
      // Update BPM
      setBpm(Math.round(map.globalBpmEstimate));
      
      // Convert sections to UI format with bar indices and micro tempo
      const uiSections: Section[] = map.sections.map((s: any, i: number) => {
        // Calculate per-section tempo from bars
        let sectionTempo = map.globalBpmEstimate;
        if (map.bars && map.bars.length > 0 && s.start_bar_index !== undefined && s.end_bar_index !== undefined) {
          const sectionBars = map.bars.slice(s.start_bar_index, s.end_bar_index + 1);
          if (sectionBars.length > 0) {
            const tempos = sectionBars.map((b: any) => b.tempo_bpm);
            sectionTempo = tempos.reduce((a: number, b: number) => a + b, 0) / tempos.length;
          }
        }
        
        return {
          id: `section-${Date.now()}-${i}`,
          start: s.start,
          end: s.end,
          label: s.label || `Section ${i + 1}`,
          confidence: s.confidence || 0.75,
          energy: s.energy || 0.5,
          spectral_centroid: s.spectral_centroid || 0.5,
          repetition_group: s.repetition_group,
          startBarIndex: s.start_bar_index,
          endBarIndex: s.end_bar_index,
          barCount: s.bar_count,
          tempo: sectionTempo, // ← Per-section micro tempo!
          density: 0.5 + (s.energy || 0.5) * 0.4,
          fillIn: i > 0,
          fillOut: i < map.sections.length - 1,
        };
      });
      
      console.log(`✅ Created ${uiSections.length} UI sections with tempo data`);
      
      // Apply with conflict handling
      const avgTempo = map.bars.length > 0 
        ? map.bars.reduce((sum: number, b: any) => sum + b.tempo_bpm, 0) / map.bars.length 
        : 120;
      applyArrangement(uiSections, 'Auto-Analyze (AI)', avgTempo);
      
      // Log bar tempo variations for debugging
      if (map.bars.length > 0) {
        const tempos = map.bars.map((b: any) => b.tempo_bpm);
        const minTempo = Math.min(...tempos);
        const maxTempo = Math.max(...tempos);
        const avgTempo = tempos.reduce((a: number, b: number) => a + b, 0) / tempos.length;
        console.log(`  Per-bar tempo: min=${minTempo.toFixed(1)}, max=${maxTempo.toFixed(1)}, avg=${avgTempo.toFixed(1)}`);
      }
      
    } catch (e: any) {
      console.error("Full analysis error:", e);
      setErr(`Full analysis failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  // Helper: Apply arrangement with conflict handling
  function applyArrangement(newSections: Section[], sourceName: string, newBpm?: number) {
    // Warn if replacing existing arrangement
    if (sections.length > 0 && arrangementSource) {
      const confirmed = window.confirm(
        `⚠️ Replace ${arrangementSource} (${sections.length} sections) with ${sourceName} (${newSections.length} sections)?`
      );
      if (!confirmed) {
        console.log('❌ User cancelled arrangement replacement');
        return false;
      }
    }
    
    setSections(newSections);
    setArrangementSource(sourceName);
    if (newBpm) setBpm(newBpm);
    setErr(null);
    
    console.log(`✅ Applied ${sourceName}: ${newSections.length} sections`);
    return true;
  }
  
  // Clear arrangement
  function clearArrangement() {
    const confirmed = window.confirm('Clear all sections and start over?');
    if (!confirmed) return;
    
    setSections([]);
    setArrangementSource(null);
    setSongMap(null);
    console.log('🗑️ Arrangement cleared');
  }
  
  // Auto-detect musical arrangement sections with beat layer
  async function handleAutoSectionize(trackKey: string) {
    setBusy(true);
    try {
      // Use NEW full analysis endpoint with bar layer
      await handleAnalyzeFull(trackKey);
    } catch (e: any) {
      console.error("Section detection error:", e);
      setErr(`Auto-sectionization failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }
  
  // Handle manual arrangement entry
  function handleManualArrangement(arrangement: ManualArrangement) {
    console.log('📝 Manual arrangement applied:', arrangement);
    
    // Convert measures to time
    const beatsPerMeasure = arrangement.timeSignature[0];
    const secondsPerBeat = 60.0 / arrangement.globalTempo;
    const secondsPerMeasure = secondsPerBeat * beatsPerMeasure;
    
    // Convert manual sections to UI sections
    const uiSections: Section[] = arrangement.sections.map((s, i) => {
      const startTime = (s.startMeasure - 1) * secondsPerMeasure;
      const endTime = startTime + (s.numMeasures * secondsPerMeasure);
      
      return {
        id: `manual-${Date.now()}-${i}`,
        start: startTime,
        end: endTime,
        label: s.label,
        tempo: s.tempo || arrangement.globalTempo,
        density: 0.7,
        fillIn: i > 0,
        fillOut: i < arrangement.sections.length - 1,
        confidence: 1.0,
        energy: 0.5,
      };
    });
    
    const totalMeasures = arrangement.sections.reduce((sum, s) => sum + s.numMeasures, 0);
    applyArrangement(uiSections, `Manual Entry (${totalMeasures} measures)`, arrangement.globalTempo);
  }
  
  // Handle internet song lookup
  function handleSongLookup(songInfo: SongInfo) {
    console.log('🌐 Song info from internet:', songInfo);
    
    // Apply song info if sections available
    if (songInfo.sections && songInfo.sections.length > 0) {
      const uiSections: Section[] = songInfo.sections.map((s, i) => ({
        id: `lookup-${Date.now()}-${i}`,
        start: s.startTime,
        end: s.endTime,
        label: s.label,
        tempo: songInfo.tempo,
        density: 0.7,
        fillIn: i > 0,
        fillOut: i < songInfo.sections.length - 1,
        confidence: 1.0,
        energy: 0.5,
      }));
      
      applyArrangement(uiSections, `"${songInfo.title}" by ${songInfo.artist}`, songInfo.tempo);
    } else {
      // No sections, just apply tempo
      setBpm(songInfo.tempo);
      console.log(`✅ Applied tempo from ${songInfo.title}: ${songInfo.tempo} BPM`);
    }
  }

  // NEW: Generate drums for selected measure range
  async function handleGenerateDrums(config: DrumGenerationConfig) {
    setGeneratingDrums(true);
    try {
      console.log('🥁 Generating drums:', config);
      
      const response = await fetch('/api/generate-drums', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Generation failed');
      }
      
      const result = await response.json();
      console.log(`✅ Drums generated in ${result.metadata.generation_time_ms}ms`);
      
      // Add generated MIDI notes to piano roll
      const newNotes: MidiNote[] = result.midi_notes.map((note: any) => ({
        id: note.id,
        time: note.time,
        duration: note.duration || 0.1,
        note: note.note,
        velocity: note.velocity,
        channel: 9 // Drum channel
      }));
      
      setNotes(prevNotes => [...prevNotes, ...newNotes]);
      
      console.log(`🎵 Added ${newNotes.length} drum notes to piano roll`);
      
    } catch (e: any) {
      console.error('❌ Drum generation failed:', e);
      setErr(`Drum generation failed: ${e.message}`);
    } finally {
      setGeneratingDrums(false);
    }
  }

  // Analyze tempo for all sections
  async function analyzeSectionTempos(trackKey: string, sectionsToAnalyze: Section[]) {
    try {
      const { analyzeTempoSections } = await import('../services/api');
      const result = await analyzeTempoSections(
        trackKey,
        sectionsToAnalyze.map(s => ({ start: s.start, end: s.end }))
      );
      
      // Update sections with tempo data
      setSections(prev => prev.map((section, i) => {
        const tempoData = result.results[i];
        if (tempoData && !section.tempoLocked) {
          return {
            ...section,
            tempo: Math.round(tempoData.tempo * 10) / 10, // Round to 1 decimal
            tempoConfidence: tempoData.confidence,
          };
        }
        return section;
      }));
      
      console.log(`✅ Analyzed tempo for ${result.results.length} sections`);
    } catch (e: any) {
      console.warn('Tempo analysis failed:', e);
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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <div className="flex-1 min-w-0 flex flex-col">
        <div className="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3">
          <div className="font-semibold">DrumTracKAI v1.1.16 – Enhanced DCSM</div>
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

        <div className="flex-1 overflow-hidden flex">
          {/* Left Column: Mixer + Drummer Selection + Drum Creation Module */}
          <div className="flex flex-col">
            {/* Mixer - Drum volume and meters */}
            <Mixer tracks={[...tracks.map(t=>({ key:t.key, name:t.name||t.key.split("/").pop()!, color:t.color })), { key:"__drums__", name:"Drums", color:"#f59e0b" }]} />
            
            {/* Drum Track Creation Module */}
            <div className="w-80 bg-slate-900 border-r border-slate-800 overflow-y-auto flex-1">
              {/* Drummer Selector - MOVED from right sidebar */}
              <div className="p-4 border-b border-slate-800">
                <h3 className="text-sm font-semibold text-slate-300 mb-3">Select Drummer</h3>
                <DrummerSelector
                  onSelect={(drummer) => {
                    setSelectedDrummer(drummer);
                    console.log('Selected drummer:', drummer.display_name);
                  }}
                  selectedDrummer={selectedDrummer}
                />
              </div>
              
              <div className="p-4 border-b border-slate-800">
                <h2 className="text-lg font-bold text-white mb-1">🥁 Drum Track Creation Module</h2>
                <p className="text-xs text-slate-400">Configure all drum generation parameters</p>
              </div>
              <DrumOptionsPanel 
                options={drumOptions} 
                onChange={setDrumOptions}
                drummerType={drumOptions.style}
              />
            </div>
          </div>
          
          {/* Center Column: Timeline + Piano Roll */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Timeline & Musical Arrangement - Unified Container */}
            <div className="border-b border-slate-800 bg-slate-900">
              {/* Timeline / Waveform */}
              <div className="p-4">
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
                  selectedSectionIds={selectedSectionIds}
                  onSelectSection={(sectionId: string, multi: boolean) => {
                    if (!sectionId) {
                      // Empty string clears selection
                      setSelectedSectionIds(new Set());
                      setSelectedMeasureRange(null);
                      return;
                    }
                    if (multi) {
                      // Multi-select with Ctrl/Cmd key
                      const newSelected = new Set(selectedSectionIds);
                      if (newSelected.has(sectionId)) {
                        newSelected.delete(sectionId);
                      } else {
                        newSelected.add(sectionId);
                      }
                      setSelectedSectionIds(newSelected);
                      // Clear measure range for multi-select (drum builder needs single section)
                      setSelectedMeasureRange(null);
                    } else {
                      // Single select
                      setSelectedSectionIds(new Set([sectionId]));
                      
                      // Set measure range for drum builder
                      const section = sections.find(s => s.id === sectionId);
                      if (section) {
                        const measureRange = sectionToMeasureRange(section, bpm, timeSig);
                        setSelectedMeasureRange(measureRange);
                        console.log('🎯 Selected measure range:', measureRange);
                      }
                    }
                  }}
                />
              </div>

              {/* Musical Arrangement - Nested Below Waveform */}
              {tracks.length > 0 && (
                <div className="border-t border-slate-800">
                  <SectionControls
                    sections={selectedSectionIds.size > 0 
                      ? sections.filter(s => selectedSectionIds.has(s.id))
                      : sections
                    }
                    onSectionsChange={setSections}
                    bpm={bpm}
                    currentTime={playhead}
                    trackKey={tracks[0]?.key}
                    onAnalyzeTempos={(sections) => analyzeSectionTempos(tracks[0]?.key, sections)}
                  />
                </div>
              )}
            </div>
            
            {/* Piano Roll */}
            <div className="flex-1 overflow-y-auto p-4">
              <PianoRoll bpm={bpm} gridSec={gridSec} notes={notes} onChange={setNotes} />
            </div>
          </div>

          {/* Musical Arrangement Manager - Right Sidebar */}
          <div className="w-80 bg-slate-900 border-l border-slate-800 overflow-y-auto">
              {/* Header */}
              <div className="p-4 border-b border-slate-800 bg-indigo-900/20">
                <h2 className="text-lg font-bold text-white mb-1">🎼 Musical Arrangement Manager</h2>
                <p className="text-xs text-slate-400">Section detection and bar-level analysis</p>
              </div>
              
              {/* Source Info from Professional Tier */}
              {sourceInfo.source && (
                <div className="p-4 bg-blue-900/20 border-b border-blue-500/30">
                  <div className="text-xs text-blue-300 mb-1">Source: {sourceInfo.source}</div>
                  {sourceInfo.filename && (
                    <div className="text-sm text-white font-semibold">📁 {sourceInfo.filename}</div>
                  )}
                  {sourceInfo.drummer && (
                    <div className="text-sm text-white">🥁 {sourceInfo.drummer}</div>
                  )}
                </div>
              )}
              
              {/* Analysis Options */}
              {tracks.length > 0 && (
                <div className="p-4 border-b border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">Arrangement Analysis</h3>
                  
                  {/* Current Arrangement Indicator */}
                  {arrangementSource && sections.length > 0 && (
                    <div className="mb-3 p-2 bg-blue-900/20 border border-blue-700/50 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="text-xs font-semibold text-blue-300">📊 Current Arrangement:</div>
                          <div className="text-xs text-white mt-0.5">{arrangementSource}</div>
                          <div className="text-xs text-slate-400 mt-0.5">{sections.length} sections</div>
                        </div>
                        <button
                          onClick={clearArrangement}
                          className="ml-2 px-2 py-1 bg-red-600/30 hover:bg-red-600/50 text-red-300 text-xs rounded transition-colors"
                          title="Clear all sections"
                        >
                          🗑️ Clear
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {/* Option 1: Auto-Analyze */}
                  <button 
                    className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 font-semibold text-white shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed mb-2"
                    onClick={() => handleAutoSectionize(tracks[0]?.key)}
                    disabled={busy}
                  >
                    {busy ? '⏳ Analyzing...' : '🎯 Auto-Analyze (AI)'}
                  </button>
                  <p className="text-xs text-slate-400 mb-3">Automatic detection of sections, bars, meter, and tempo</p>
                  
                  {/* Option 2: Manual Entry */}
                  <button 
                    className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 font-semibold text-white shadow-lg transition-all mb-2"
                    onClick={() => setShowManualModal(true)}
                  >
                    📝 Manual Entry
                  </button>
                  <p className="text-xs text-slate-400 mb-3">Define sections by measure count for your own songs</p>
                  
                  {/* Option 3: Well Known Song */}
                  <button 
                    className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 font-semibold text-white shadow-lg transition-all mb-2"
                    onClick={() => setShowLookupModal(true)}
                  >
                    🌐 Well Known Song
                  </button>
                  <p className="text-xs text-slate-400 mb-3">Search internet for tempo, time signature, and arrangement</p>
                  
                  {/* Manual Tempo Adjustment */}
                  {sections.length > 0 && songMap && (
                    <div className="mt-3 p-3 bg-slate-900/50 rounded-lg border border-slate-700">
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-xs text-slate-300 font-semibold">Detected Tempo</label>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            min="60"
                            max="200"
                            value={Math.round(bpm)}
                            onChange={(e) => setBpm(Math.max(60, Math.min(200, Number(e.target.value) || 120)))}
                            className="w-16 px-2 py-1 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-indigo-500 focus:outline-none"
                          />
                          <span className="text-xs text-slate-400">BPM</span>
                        </div>
                      </div>
                      <div className="text-xs text-slate-500">
                        Auto-detected: {songMap.globalBpmEstimate?.toFixed(1)} BPM
                      </div>
                      <div className="text-xs text-amber-400 mt-1">
                        ⚠️ Adjust if tempo seems incorrect
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {/* NEW: Drum Builder Panel */}
              {tracks.length > 0 && sections.length > 0 && (
                <div className="p-4 border-b border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">🥁 Drum Track Builder</h3>
                  <DrumBuilderPanel
                    selectedRange={selectedMeasureRange}
                    onGenerate={handleGenerateDrums}
                    busy={generatingDrums}
                  />
                </div>
              )}
              
              {/* Upload prompt if no tracks */}
              {tracks.length === 0 && (
                <div className="p-4 bg-yellow-900/20 border-b border-yellow-500/30">
                  <div className="text-sm text-yellow-300 mb-2">⚠️ No audio loaded</div>
                  <div className="text-xs text-yellow-200/70 mb-3">
                    Click "Upload Audio" button above to load your track
                  </div>
                  {sourceInfo.filename && (
                    <div className="text-xs text-yellow-400">
                      Expected file: {sourceInfo.filename}
                    </div>
                  )}
                </div>
              )}
              
              
              {tracks.length > 0 && (
                <div>
                  {/* Selection Info & Actions */}
                  {selectedSectionIds.size > 0 ? (
                    <div className="p-4 bg-gradient-to-r from-indigo-900/40 to-purple-900/40 border-b border-indigo-500/30">
                      <div className="text-sm text-indigo-200 font-semibold mb-3">
                        ✨ {selectedSectionIds.size} section{selectedSectionIds.size > 1 ? 's' : ''} selected
                      </div>
                      <div className="flex flex-col gap-2">
                        <button
                          className="w-full px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white font-semibold rounded-lg shadow-lg transition-all"
                          onClick={() => {
                            // Generate for all selected sections
                            const selected = sections.filter(s => selectedSectionIds.has(s.id));
                            selected.forEach(section => handleGenerate(section));
                          }}
                        >
                          🥁 Generate Drums for Selected
                        </button>
                        <button
                          className="text-xs text-indigo-300 hover:text-indigo-200 underline"
                          onClick={() => setSelectedSectionIds(new Set())}
                        >
                          Clear selection (show all)
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 bg-yellow-900/20 border-b border-yellow-500/30">
                      <div className="text-xs text-yellow-300">
                        💡 Click sections on timeline to select them
                      </div>
                    </div>
                  )}
                  
                  {/* SectionControls moved to be nested under waveform in center column */}
                </div>
              )}
            </div>
        </div>
      </div>
      
      {/* Modals */}
      <ManualArrangementModal
        isOpen={showManualModal}
        onClose={() => setShowManualModal(false)}
        onSubmit={handleManualArrangement}
        duration={tracks[0]?.seconds || 240}
      />
      
      <InternetSongLookupModal
        isOpen={showLookupModal}
        onClose={() => setShowLookupModal(false)}
        onSelect={handleSongLookup}
      />
    </div>
  );
}
