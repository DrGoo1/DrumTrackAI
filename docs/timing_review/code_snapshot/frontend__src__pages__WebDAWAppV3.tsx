import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import WebDAWApp from '../components/WebDAWApp';
import { useV3Store } from '../state/v3/store';
import { useMidi } from '../midi/midiStore';
import { Engine } from '../audio/engine';
import { getSharedDrumPlayerEngine, type DrumPlayerChannelId } from '../audio/drumPlayerEngine';
import { V3ImportAnalysisHeader } from '../components/v3/V3ImportAnalysisHeader';
import { V3GlobalDefaultsPanel } from '../components/v3/V3GlobalDefaultsPanel';
import { V3DrumEditorPane } from '../components/v3/V3DrumEditorPane';
import { V3AudioTimeline } from '../components/v3/V3AudioTimeline';
import { V3SectionInspector } from '../components/v3/V3SectionInspector';
import { V3DrummerPickerModal } from '../components/v3/V3DrummerPickerModal';

type EditorTab = 'bar_tools' | 'piano_roll' | 'mixer' | 'groove_library' | 'metrics';

type ViewMode = 'v3' | 'split' | 'legacy';

function beatsAtTimeFromBeatTimes(beatTimes: number[], tSec: number): number {
  if (!Array.isArray(beatTimes) || beatTimes.length < 2) return 0;
  const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);
  if (t <= beatTimes[0]) return 0;

  let lo = 0;
  let hi = beatTimes.length - 1;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (beatTimes[mid] < t) lo = mid + 1;
    else hi = mid;
  }
  const idx = lo;
  if (idx <= 0) return 0;
  if (idx >= beatTimes.length) return beatTimes.length - 1;
  const prev = idx - 1;
  const t0 = beatTimes[prev];
  const t1 = beatTimes[idx];
  if (!Number.isFinite(t0) || !Number.isFinite(t1) || t1 <= t0) return prev;
  const frac = Math.max(0, Math.min(1, (t - t0) / (t1 - t0)));
  return prev + frac;
}

function beatsAtTimeFromTempoMap(tempoMap: Array<{ tSec: number; bpm: number }>, fallbackBpm: number, tSec: number): number {
  const pts = Array.isArray(tempoMap)
    ? tempoMap
        .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
        .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
        .sort((a, b) => a.tSec - b.tSec)
    : [];

  const bpm0 = Number.isFinite(fallbackBpm) && fallbackBpm > 0 ? fallbackBpm : 120;
  const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);

  if (!pts.length) {
    return (t * bpm0) / 60;
  }
  if (pts.length === 1) {
    return (t * pts[0].bpm) / 60;
  }

  let beats = 0;
  let prevT = pts[0].tSec;
  let prevBpm = pts[0].bpm;
  if (t <= prevT) return 0;
  for (let i = 1; i < pts.length; i++) {
    const cur = pts[i];
    if (t <= cur.tSec) {
      beats += ((t - prevT) * prevBpm) / 60;
      return beats;
    }
    beats += ((cur.tSec - prevT) * prevBpm) / 60;
    prevT = cur.tSec;
    prevBpm = cur.bpm;
  }
  beats += ((t - prevT) * prevBpm) / 60;
  return beats;
}

function playheadToXPx(args: { tSec: number; pixelsPerBeat: number; beatTimes?: number[]; tempoMap?: Array<{ tSec: number; bpm: number }>; fallbackBpm: number }): number {
  const pxPerBeat = Math.max(1, Number(args.pixelsPerBeat) || 0);
  const beats = Array.isArray(args.beatTimes) && args.beatTimes.length >= 2
    ? beatsAtTimeFromBeatTimes(args.beatTimes, args.tSec)
    : beatsAtTimeFromTempoMap(args.tempoMap || [], args.fallbackBpm, args.tSec);
  if (!Number.isFinite(beats) || beats < 0) return 0;
  return beats * pxPerBeat;
}

function timeAtBeatsFromBeatTimes(beatTimes: number[], beatsIn: number): number {
  if (!Array.isArray(beatTimes) || beatTimes.length < 2) return 0;
  const beats = Math.max(0, Number.isFinite(beatsIn) ? beatsIn : 0);
  const maxIdx = beatTimes.length - 1;
  const idx0 = Math.max(0, Math.min(maxIdx, Math.floor(beats)));
  const idx1 = Math.max(0, Math.min(maxIdx, idx0 + 1));
  const t0 = beatTimes[idx0] ?? 0;
  const t1 = beatTimes[idx1] ?? t0;
  const frac = Math.max(0, Math.min(1, beats - idx0));
  if (idx0 === idx1) return Number.isFinite(t0) ? t0 : 0;
  if (!Number.isFinite(t0) || !Number.isFinite(t1)) return Number.isFinite(t0) ? t0 : 0;
  return t0 + (t1 - t0) * frac;
}

function timeAtBeatsFromTempoMap(tempoMap: Array<{ tSec: number; bpm: number }>, fallbackBpm: number, beatsIn: number): number {
  const pts = Array.isArray(tempoMap)
    ? tempoMap
        .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
        .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
        .sort((a, b) => a.tSec - b.tSec)
    : [];

  const bpm0 = Number.isFinite(fallbackBpm) && fallbackBpm > 0 ? fallbackBpm : 120;
  const beats = Math.max(0, Number.isFinite(beatsIn) ? beatsIn : 0);
  if (!pts.length) return (beats * 60) / bpm0;
  if (pts.length === 1) return (beats * 60) / pts[0].bpm;

  const beatsAtPoint: number[] = new Array(pts.length);
  beatsAtPoint[0] = 0;
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1];
    const cur = pts[i];
    const dt = Math.max(0, cur.tSec - prev.tSec);
    beatsAtPoint[i] = beatsAtPoint[i - 1] + (dt * prev.bpm) / 60;
  }

  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1];
    const b0 = beatsAtPoint[i - 1];
    const b1 = beatsAtPoint[i];
    if (beats <= b1) {
      const db = Math.max(0, beats - b0);
      return prev.tSec + (db * 60) / prev.bpm;
    }
  }

  const last = pts[pts.length - 1];
  const bLast = beatsAtPoint[beatsAtPoint.length - 1];
  const db = Math.max(0, beats - bLast);
  return last.tSec + (db * 60) / last.bpm;
}

function mapInstrumentToChannel(instIdRaw: any): DrumPlayerChannelId | null {
  const instId = String(instIdRaw || '').toLowerCase();
  switch (instId) {
    case 'kick':
      return 'kick';
    case 'snare_center':
    case 'snare_ghost':
    case 'snare_rim':
    case 'snare':
      return 'snare_top';
    case 'hihat_closed':
    case 'hihat_open':
    case 'hihat_pedal':
    case 'hat':
      return 'hat';
    case 'ride_bow':
    case 'ride_bell':
    case 'ride_edge':
    case 'ride':
      return 'ride';
    case 'crash_1':
    case 'crash_2':
    case 'crash':
      return 'crash';
    case 'tom_high':
      return 'tom1';
    case 'tom_mid':
      return 'tom3';
    case 'tom_floor':
      return 'tom5';
    default:
      return null;
  }
}

async function getDownloadUrlSameOrigin(key: string): Promise<string> {
  const res = await fetch(`/files/download-url?key=${encodeURIComponent(key)}`);
  if (!res.ok) {
    throw new Error(`Failed to get download URL (${res.status} ${res.statusText})`);
  }
  const json: any = await res.json();
  const url = String(json?.url || "");
  if (!url) throw new Error("Download URL response missing url");
  return url;
}

export default function WebDAWAppV3() {
  const [viewMode, setViewMode] = useState<ViewMode>('v3');
  const [v3Playing, setV3Playing] = useState(false);
  const [followPlayhead, setFollowPlayhead] = useState(true);
  const [pixelsPerBeat, setPixelsPerBeat] = useState(64);
  const [drumOffsetMs, setDrumOffsetMs] = useState(0);
  const [drumBeatShift, setDrumBeatShift] = useState(0);
  const [conformStrength, setConformStrength] = useState(0.5);
  const [mvsepJobId, setMvsepJobId] = useState<string | null>(null);
  const [coachGoalsOpen, setCoachGoalsOpen] = useState(false);
  const activeTab = useV3Store((s) => s.ui.editorTab) as EditorTab;
  const setActiveTab = useV3Store((s) => s.setEditorTab) as (tab: EditorTab) => void;
  const showLegacyParity = useV3Store((s) => s.ui.showLegacyParity);
  const setShowLegacyParity = useV3Store((s) => s.setShowLegacyParity);
  const inspectorView = useV3Store((s) => s.ui.inspectorView);
  const setInspectorView = useV3Store((s) => s.setInspectorView);
  const arrangement = useV3Store((s) => s.arrangement);
  const playheadSec = useV3Store((s) => s.playheadSec);
  const setPlayheadSec = useV3Store((s) => s.setPlayheadSec);
  const importState = useV3Store((s) => s.importState);
  const generatedDrumTrack = useV3Store((s) => s.generatedDrumTrack);
  const auditionRequest = useV3Store((s) => s.auditionRequest);
  const coach = useV3Store((s) => s.coach);
  const fetchCoachGoals = useV3Store((s) => s.fetchCoachGoals);
  const runGrooveCoach = useV3Store((s) => s.runGrooveCoach);
  const applyCoachPatch = useV3Store((s) => s.applyCoachPatch);
  const setCoachSelectedGoalIds = useV3Store((s) => s.setCoachSelectedGoalIds);

  const audioTimelineScrollRef = useRef<HTMLDivElement | null>(null);
  const drumEditorScrollRef = useRef<HTMLDivElement | null>(null);
  const scrollSyncSourceRef = useRef<'audio' | 'drum' | null>(null);
  const scrollSyncCleanupRef = useRef<null | (() => void)>(null);
  const lastManualScrollMsRef = useRef<number>(0);
  const rafPlayRef = useRef<number | null>(null);
  const lastPlayheadTickRef = useRef<number | null>(null);
  const stalledPlayheadFramesRef = useRef<number>(0);
  const engineReadyKeyRef = useRef<string | null>(null);
  const drumEngineRef = useRef<ReturnType<typeof getSharedDrumPlayerEngine> | null>(null);
  const drumKitReadyRef = useRef(false);
  const drumSchedTimerRef = useRef<number | null>(null);
  const auditionStopTimerRef = useRef<number | null>(null);
  const lastDrumScheduledToRef = useRef<number>(0);
  const drumOnlyStartCtxTimeRef = useRef<number | null>(null);
  const drumOnlyStartPlayheadSecRef = useRef<number>(0);
  const engineToCtxOffsetRef = useRef<number | null>(null);
  const drumBarIndexBaseRef = useRef<number | null>(null);
  const drumBeatShiftManualRef = useRef<boolean>(false);
  const lastBeatShiftTrackIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!generatedDrumTrack) {
      setDrumBeatShift(0);
      drumBeatShiftManualRef.current = false;
      lastBeatShiftTrackIdRef.current = null;
      return;
    }

    const trackId = String((generatedDrumTrack as any)?.track_id || (generatedDrumTrack as any)?.trackId || '') || null;
    if (trackId && lastBeatShiftTrackIdRef.current !== trackId) {
      // New generation: allow auto-detect again.
      drumBeatShiftManualRef.current = false;
      lastBeatShiftTrackIdRef.current = trackId;
    }

    if (drumBeatShiftManualRef.current) {
      return;
    }

    const notes = Array.isArray((generatedDrumTrack as any)?.notes) ? (generatedDrumTrack as any).notes : [];
    if (!notes.length) {
      setDrumBeatShift(0);
      return;
    }

    let minBar = Number.POSITIVE_INFINITY;
    for (let i = 0; i < notes.length && i < 512; i++) {
      const v = Number((notes[i] as any)?.barIndex);
      if (Number.isFinite(v)) minBar = Math.min(minBar, v);
    }
    const barBase = Number.isFinite(minBar) && minBar >= 1 ? 1 : 0;

    const beatsPerBar = Number(arrangement.timeSig?.[0] || 4) || 4;
    const ticksPerBeat = Number((generatedDrumTrack as any)?.resolution_ppq || 960) || 960;
    const ticksPerBar = ticksPerBeat * beatsPerBar;

    let earliestTick = Number.POSITIVE_INFINITY;
    for (let i = 0; i < notes.length && i < 2048; i++) {
      const n: any = notes[i];
      const barRaw = Number(n?.barIndex ?? 0) || 0;
      const bar = Math.max(0, barRaw - barBase);
      if (bar !== 0) continue;
      const tickInBar = Number(n?.tickInBar ?? 0) || 0;
      if (tickInBar < earliestTick) earliestTick = tickInBar;
    }

    if (!Number.isFinite(earliestTick)) {
      setDrumBeatShift(0);
      return;
    }

    const beatInBar = earliestTick / Math.max(1, ticksPerBeat);
    const inferred = Math.max(0, Math.min(beatsPerBar - 1, Math.round(beatInBar)));
    const inferredTicks = inferred * ticksPerBeat;
    // Use an error tolerance measured in BEATS, not as a fraction of the full bar.
    // Shuffles / laid-back grooves can put the first hit a little late/early.
    const inferredErrorBeats = Math.abs(earliestTick - inferredTicks) / Math.max(1, ticksPerBeat);

    // Accept up to ~1/3 beat timing error when snapping to beat 1/2/3.
    // If we can't confidently infer a beat shift, fall back to 0.
    setDrumBeatShift(inferredErrorBeats <= 0.34 ? inferred : 0);
  }, [arrangement.timeSig, generatedDrumTrack]);

  useEffect(() => {
    if (!coachGoalsOpen) return;
    if (viewMode === 'legacy') return;
    if (importState.busyStage !== 'idle') return;
    void fetchCoachGoals();
  }, [coachGoalsOpen, fetchCoachGoals, importState.busyStage, viewMode]);

  const onConformBass = useCallback(async () => {
    const apiBase = useV3Store.getState().env.apiBase || '';
    const key = useV3Store.getState().importState.fileKey;
    const track = useV3Store.getState().generatedDrumTrack;
    if (!key || !track) return;
    try {
      const res = await fetch(`${apiBase}/api/conform-to-instrument`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          key,
          instrument: 'bass',
          strength: conformStrength,
          drum_track: track,
          mvsep_job_id: mvsepJobId,
        }),
      });
      const j = await res.json();
      const next = (j as any)?.drum_track;
      if (next && typeof next === 'object') {
        useV3Store.getState().setGeneratedDrumTrack(next as any);
      }
    } catch {
      // ignore
    }
  }, [conformStrength, mvsepJobId]);

  const onStartMvsep = useCallback(async () => {
    const apiBase = useV3Store.getState().env.apiBase || '';
    const key = useV3Store.getState().importState.fileKey;
    if (!key) return;
    try {
      const res = await fetch(`${apiBase}/api/mvsep/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, mode: 'A' }),
      });
      const j = await res.json();
      const jid = String((j as any)?.job_id || '');
      if (jid) setMvsepJobId(jid);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    useV3Store.setState((s) => ({ ui: { ...s.ui, arrangementOwner: viewMode === 'legacy' ? 'legacy' : 'v3' } }));
  }, [viewMode]);

  useEffect(() => {
    if (viewMode === 'legacy') return;
    if (!followPlayhead) return;
    const audioEl = audioTimelineScrollRef.current;
    const drumEl = drumEditorScrollRef.current;
    if (!audioEl || !drumEl) return;

    // While playing, the DrumPianoRoll handles smooth follow internally.
    // The outer scroll-sync follow can fight it and cause jumpy snapping.
    if (v3Playing) return;

    const now = performance.now();
    // Back off for a moment after manual scroll so we don't fight the user.
    if (!v3Playing && now - lastManualScrollMsRef.current < 500) return;

    const fallbackBpm = arrangement.tempoMap?.[0]?.bpm || 120;
    const xPx = playheadToXPx({
      tSec: playheadSec,
      pixelsPerBeat,
      beatTimes: arrangement.beatTimes,
      tempoMap: arrangement.tempoMap,
      fallbackBpm,
    });

    const viewLeft = drumEl.scrollLeft;
    const viewRight = viewLeft + drumEl.clientWidth;
    const margin = Math.max(80, drumEl.clientWidth * 0.25);

    if (xPx < viewLeft + margin || xPx > viewRight - margin) {
      const target = Math.max(0, xPx - drumEl.clientWidth * 0.5);
      try {
        drumEl.scrollTo({ left: target, behavior: 'smooth' });
        audioEl.scrollTo({ left: target, behavior: 'smooth' });
      } catch {
        drumEl.scrollLeft = target;
        audioEl.scrollLeft = target;
      }
    }
  }, [arrangement.beatTimes, arrangement.tempoMap, followPlayhead, pixelsPerBeat, playheadSec, v3Playing, viewMode]);

  useEffect(() => {
    if (rafPlayRef.current !== null) {
      window.cancelAnimationFrame(rafPlayRef.current);
      rafPlayRef.current = null;
    }
    if (viewMode === 'legacy') return;
    if (!v3Playing) return;

    lastPlayheadTickRef.current = null;
    stalledPlayheadFramesRef.current = 0;

    const duration = Number(importState.waveform?.duration || 0);
    const hasDuration = Number.isFinite(duration) && duration > 0;

    const tick = () => {
      const hasAudio = Boolean(importState.fileKey && importState.waveform?.duration);
      const duration = Number(importState.waveform?.duration || 0);
      const hasDuration = Number.isFinite(duration) && duration > 0;
      let t: number | null = null;

      if (hasAudio) {
        // When audio is loaded, the cursor must follow the transport timebase.
        // Using AudioContext.currentTime - offset can drift/lead depending on resync timing.
        const v = Engine.getCurrentTimeSeconds();
        if (typeof v === 'number' && Number.isFinite(v)) t = v;
      } else {
        const ctx = drumEngineRef.current?.audioContext;
        const startCtx = drumOnlyStartCtxTimeRef.current;
        if (ctx && typeof ctx.currentTime === 'number' && Number.isFinite(ctx.currentTime) && typeof startCtx === 'number') {
          t = drumOnlyStartPlayheadSecRef.current + Math.max(0, ctx.currentTime - startCtx);
        }
      }

      if (typeof t === 'number' && Number.isFinite(t)) {
        if (hasAudio) {
          const prev = lastPlayheadTickRef.current;
          if (typeof prev === 'number' && Number.isFinite(prev)) {
            // If the audio element stops advancing (ended/stalled), stop v3 playback.
            if (t <= prev + 0.0005) {
              stalledPlayheadFramesRef.current += 1;
            } else {
              stalledPlayheadFramesRef.current = 0;
            }
            if (stalledPlayheadFramesRef.current > 20) {
              stalledPlayheadFramesRef.current = 0;
              lastPlayheadTickRef.current = null;
              setV3Playing(false);
              try {
                Engine.pause();
              } catch {
                // ignore
              }
              rafPlayRef.current = null;
              return;
            }
          }
          lastPlayheadTickRef.current = t;
        }
        const clamped = hasDuration ? Math.min(Math.max(0, t), duration) : Math.max(0, t);
        setPlayheadSec(clamped);
        if (hasDuration && clamped >= duration) {
          setV3Playing(false);
          rafPlayRef.current = null;
          return;
        }
      }

      rafPlayRef.current = window.requestAnimationFrame(tick);
    };

    rafPlayRef.current = window.requestAnimationFrame(tick);
    return () => {
      if (rafPlayRef.current !== null) {
        window.cancelAnimationFrame(rafPlayRef.current);
        rafPlayRef.current = null;
      }
    };
  }, [importState.waveform?.duration, setPlayheadSec, v3Playing, viewMode]);

  useEffect(() => {
    if (viewMode === 'legacy') return;
    const key = importState.fileKey;
    if (!key) {
      engineReadyKeyRef.current = null;
      return;
    }
    if (engineReadyKeyRef.current === key) return;

    let canceled = false;
    (async () => {
      const url = await getDownloadUrlSameOrigin(key);
      if (canceled) return;
      await Engine.refreshTracks([{ key, url }]);
      if (canceled) return;
      engineReadyKeyRef.current = key;
    })().catch((e) => {
      // loud: surface the error in UI
      useV3Store.getState().setImportState({ error: e?.message || String(e) });
    });
    return () => {
      canceled = true;
    };
  }, [importState.fileKey, viewMode]);

  useEffect(() => {
    if (viewMode === 'legacy') return;
    if (drumKitReadyRef.current) return;

    let cancelled = false;
    (async () => {
      const eng = getSharedDrumPlayerEngine();
      drumEngineRef.current = eng;
      await eng.ensureRunning();
      await Promise.all([
        eng.loadSampleForChannel('kick', '/samples/drums/kick.wav'),
        eng.loadSampleForChannel('snare_top', '/samples/drums/snare.wav'),
        eng.loadSampleForChannel('hat', '/samples/drums/hihat.wav'),
        eng.loadSampleForChannel('tom1', '/samples/drums/tom.wav'),
        eng.loadSampleForChannel('tom2', '/samples/drums/tom.wav'),
        eng.loadSampleForChannel('tom3', '/samples/drums/tom.wav'),
        eng.loadSampleForChannel('tom4', '/samples/drums/tom.wav'),
        eng.loadSampleForChannel('tom5', '/samples/drums/tom.wav'),
        eng.loadSampleForChannel('ride', '/samples/drums/ride.wav'),
        eng.loadSampleForChannel('crash', '/samples/drums/crash.wav'),
      ]);
      if (cancelled) return;
      drumKitReadyRef.current = true;
    })().catch((e) => {
      useV3Store.getState().setImportState({ error: e?.message || String(e) });
    });

    return () => {
      cancelled = true;
    };
  }, [viewMode]);

  useEffect(() => {
    if (drumSchedTimerRef.current !== null) {
      window.clearInterval(drumSchedTimerRef.current);
      drumSchedTimerRef.current = null;
    }
    if (viewMode === 'legacy') return;
    if (!v3Playing) return;
    if (!generatedDrumTrack) return;
    if (!drumKitReadyRef.current) return;
    const eng = drumEngineRef.current;
    if (!eng) return;

    try {
      // Ensure AudioContext is running; this effect is triggered by a user play action.
      void eng.ensureRunning();
    } catch {
      // ignore
    }

    const getNowSec = () => {
      const hasAudio = Boolean(importState.fileKey && importState.waveform?.duration);
      if (hasAudio) {
        return Engine.getCurrentTimeSeconds();
      }
      const ctx = eng.audioContext;
      const startCtx = drumOnlyStartCtxTimeRef.current;
      if (ctx && typeof ctx.currentTime === 'number' && Number.isFinite(ctx.currentTime) && typeof startCtx === 'number') {
        return drumOnlyStartPlayheadSecRef.current + Math.max(0, ctx.currentTime - startCtx);
      }
      return null;
    };

    // Align initial scheduling window to active timebase.
    const initNow = getNowSec();
    if (typeof initNow !== 'number' || !Number.isFinite(initNow)) return;
    lastDrumScheduledToRef.current = Math.max(lastDrumScheduledToRef.current, initNow);

    const lookaheadSec = 0.25;
    const scheduleIntervalMs = 50;

    const scheduleWindow = () => {
      const engineNow = getNowSec();
      if (typeof engineNow !== 'number' || !Number.isFinite(engineNow)) return;
      const fromSec = lastDrumScheduledToRef.current;
      const toSec = Math.max(fromSec, engineNow + lookaheadSec);
      if (toSec <= fromSec + 1e-6) return;

      const ctx = eng.audioContext;
      const ctxNow = ctx?.currentTime ?? 0;
      const hasAudio = Boolean(importState.fileKey && importState.waveform?.duration);
      let engineToCtxOffset = engineToCtxOffsetRef.current;
      if (hasAudio && typeof ctxNow === 'number' && Number.isFinite(ctxNow)) {
        // Keep resyncing: HTML5 audio clock and AudioContext clock can drift.
        engineToCtxOffset = ctxNow - engineNow;
        engineToCtxOffsetRef.current = engineToCtxOffset;
      }

      const drumOffsetSec = (Number(drumOffsetMs) || 0) / 1000;

      const notes = Array.isArray((generatedDrumTrack as any)?.notes) ? (generatedDrumTrack as any).notes : [];
      if (drumBarIndexBaseRef.current === null) {
        let minBar = Number.POSITIVE_INFINITY;
        for (let i = 0; i < notes.length && i < 512; i++) {
          const v = Number((notes[i] as any)?.barIndex);
          if (Number.isFinite(v)) minBar = Math.min(minBar, v);
        }
        drumBarIndexBaseRef.current = Number.isFinite(minBar) && minBar >= 1 ? 1 : 0;
      }
      const barBase = drumBarIndexBaseRef.current || 0;
      const beatsPerBar = arrangement.timeSig?.[0] || 4;
      const ticksPerBeat = (generatedDrumTrack as any)?.resolution_ppq || 960;
      const ticksPerBar = ticksPerBeat * beatsPerBar;
      const beatShift = Number.isFinite(Number(drumBeatShift)) ? (Number(drumBeatShift) || 0) : 0;

      for (const n of notes) {
        const barRaw = Number((n as any)?.barIndex ?? 0) || 0;
        const bar = Math.max(0, barRaw - barBase);
        const tickInBar = Number((n as any)?.tickInBar ?? 0) || 0;
        const totalTicks = bar * ticksPerBar + tickInBar;
        const beats = Math.max(0, (totalTicks / Math.max(1, ticksPerBeat)) - beatShift);

        const tSec = Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2
          ? timeAtBeatsFromBeatTimes(arrangement.beatTimes, beats)
          : timeAtBeatsFromTempoMap(arrangement.tempoMap || [], arrangement.tempoMap?.[0]?.bpm || 120, beats);

        if (!Number.isFinite(tSec)) continue;
        if (tSec < fromSec || tSec >= toSec) continue;

        const ch = mapInstrumentToChannel((n as any)?.instrumentId);
        if (!ch) continue;

        const whenSec = hasAudio && typeof engineToCtxOffset === 'number' && Number.isFinite(engineToCtxOffset)
          ? (engineToCtxOffset + tSec + drumOffsetSec)
          : ctxNow + (tSec - engineNow);
        // Schedule slightly ahead to avoid jitter; also account for output latency so heard hits line up.
        const safeWhen = Math.max(ctxNow + 0.01, whenSec);

        eng.playChannelOneShot(ch, {
          whenSec: safeWhen,
          gain: Math.max(0.2, Math.min(1.5, (Number((n as any)?.velocity ?? 100) || 100) / 100)),
        });
      }

      lastDrumScheduledToRef.current = toSec;
    };

    drumSchedTimerRef.current = window.setInterval(scheduleWindow, scheduleIntervalMs);
    return () => {
      if (drumSchedTimerRef.current !== null) {
        window.clearInterval(drumSchedTimerRef.current);
        drumSchedTimerRef.current = null;
      }
      try {
        eng.stopAll();
      } catch {
        // ignore
      }
    };
  }, [arrangement.beatTimes, arrangement.tempoMap, arrangement.timeSig, generatedDrumTrack, importState.fileKey, importState.waveform?.duration, v3Playing, viewMode]);

  useEffect(() => {
    drumBarIndexBaseRef.current = null;
  }, [generatedDrumTrack]);

  useEffect(() => {
    if (auditionStopTimerRef.current !== null) {
      window.clearTimeout(auditionStopTimerRef.current);
      auditionStopTimerRef.current = null;
    }
    if (!auditionRequest) return;
    if (viewMode === 'legacy') return;

    const eng = drumEngineRef.current;
    if (!eng) return;
    if (!drumKitReadyRef.current) return;

    try {
      eng.stopAll();
    } catch {
      // ignore
    }

    if ((auditionRequest as any).mode === 'stop') {
      return;
    }

    const req: any = auditionRequest;
    const startSec = Number(req.startSec);
    const endSec = Number(req.endSec);
    const notes = Array.isArray(req.notes) ? req.notes : [];
    if (!Number.isFinite(startSec) || !Number.isFinite(endSec) || endSec <= startSec) return;

    const ctx = eng.audioContext;
    const ctxNow = ctx?.currentTime ?? 0;

    const beatsPerBar = arrangement.timeSig?.[0] || 4;
    const ticksPerBeat = Number((generatedDrumTrack as any)?.resolution_ppq || 960) || 960;
    const ticksPerBar = ticksPerBeat * beatsPerBar;
    const beatShift = Number.isFinite(Number(drumBeatShift)) ? (Number(drumBeatShift) || 0) : 0;

    let minBar = Number.POSITIVE_INFINITY;
    for (let i = 0; i < notes.length && i < 512; i++) {
      const v = Number((notes[i] as any)?.barIndex);
      if (Number.isFinite(v)) minBar = Math.min(minBar, v);
    }
    const barBase = Number.isFinite(minBar) && minBar >= 1 ? 1 : 0;

    for (const n of notes) {
      const barRaw = Number((n as any)?.barIndex ?? 0) || 0;
      const bar = Math.max(0, barRaw - barBase);
      const tickInBar = Number((n as any)?.tickInBar ?? 0) || 0;

      const totalTicks = bar * ticksPerBar + tickInBar;
      const beats = Math.max(0, (totalTicks / Math.max(1, ticksPerBeat)) - beatShift);

      const tSec = Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2
        ? timeAtBeatsFromBeatTimes(arrangement.beatTimes, beats)
        : timeAtBeatsFromTempoMap(arrangement.tempoMap || [], arrangement.tempoMap?.[0]?.bpm || 120, beats);

      if (!Number.isFinite(tSec)) continue;
      if (tSec < startSec || tSec >= endSec) continue;

      const ch = mapInstrumentToChannel((n as any)?.instrumentId);
      if (!ch) continue;

      const whenSec = ctxNow + Math.max(0, tSec - startSec);
      const safeWhen = Math.max(ctxNow + 0.002, whenSec);
      eng.playChannelOneShot(ch, {
        whenSec: safeWhen,
        gain: Math.max(0.2, Math.min(1.5, (Number((n as any)?.velocity ?? 100) || 100) / 100)),
      });
    }

    auditionStopTimerRef.current = window.setTimeout(() => {
      try {
        eng.stopAll();
      } catch {
        // ignore
      }
    }, Math.max(50, Math.round((endSec - startSec) * 1000)));
  }, [arrangement.beatTimes, arrangement.tempoMap, arrangement.timeSig, auditionRequest, generatedDrumTrack, viewMode]);

  useEffect(() => {
    const midi = useMidi.getState();
    midi.setTempoMap(arrangement.tempoMap);
    midi.setTimeSig(arrangement.timeSig[0], arrangement.timeSig[1]);
    midi.setSections(arrangement.sections);
  }, [arrangement.tempoMap, arrangement.timeSig, arrangement.sections]);

  useEffect(() => {
    scrollSyncCleanupRef.current?.();
    scrollSyncCleanupRef.current = null;
    if (viewMode === 'legacy') {
      return;
    }

    let rafId: number | null = null;

    const tryAttach = () => {
      const audioEl = audioTimelineScrollRef.current;
      const drumEl = drumEditorScrollRef.current;
      if (!audioEl || !drumEl) {
        rafId = window.requestAnimationFrame(tryAttach);
        return;
      }

      // Initial sync: prefer keeping drum editor position (user likely scrolls there more).
      audioEl.scrollLeft = drumEl.scrollLeft;

      const markManual = () => {
        lastManualScrollMsRef.current = performance.now();
      };

      const syncFromAudio = () => {
        if (v3Playing) return;
        if (!audioTimelineScrollRef.current || !drumEditorScrollRef.current) return;
        if (scrollSyncSourceRef.current === 'drum') return;
        scrollSyncSourceRef.current = 'audio';
        drumEditorScrollRef.current.scrollLeft = audioTimelineScrollRef.current.scrollLeft;
        window.requestAnimationFrame(() => {
          if (scrollSyncSourceRef.current === 'audio') scrollSyncSourceRef.current = null;
        });
      };

      const syncFromDrum = () => {
        if (!audioTimelineScrollRef.current || !drumEditorScrollRef.current) return;
        if (scrollSyncSourceRef.current === 'audio') return;
        scrollSyncSourceRef.current = 'drum';
        audioTimelineScrollRef.current.scrollLeft = drumEditorScrollRef.current.scrollLeft;
        window.requestAnimationFrame(() => {
          if (scrollSyncSourceRef.current === 'drum') scrollSyncSourceRef.current = null;
        });
      };

      audioEl.addEventListener('scroll', syncFromAudio, { passive: true });
      drumEl.addEventListener('scroll', syncFromDrum, { passive: true });

      // Only treat direct user interaction as "manual" scrolling. Programmatic scroll sync should not disable playhead-follow.
      audioEl.addEventListener('wheel', markManual, { passive: true });
      drumEl.addEventListener('wheel', markManual, { passive: true });
      audioEl.addEventListener('touchstart', markManual, { passive: true });
      drumEl.addEventListener('touchstart', markManual, { passive: true });
      audioEl.addEventListener('pointerdown', markManual, { passive: true });
      drumEl.addEventListener('pointerdown', markManual, { passive: true });

      scrollSyncCleanupRef.current = () => {
        audioEl.removeEventListener('scroll', syncFromAudio);
        drumEl.removeEventListener('scroll', syncFromDrum);
        audioEl.removeEventListener('wheel', markManual);
        drumEl.removeEventListener('wheel', markManual);
        audioEl.removeEventListener('touchstart', markManual);
        drumEl.removeEventListener('touchstart', markManual);
        audioEl.removeEventListener('pointerdown', markManual);
        drumEl.removeEventListener('pointerdown', markManual);
      };
    };

    tryAttach();
    return () => {
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId);
      }
      scrollSyncCleanupRef.current?.();
      scrollSyncCleanupRef.current = null;
    };
  }, [viewMode, v3Playing]);

  const tabLabel = useMemo(() => {
    switch (activeTab) {
      case 'bar_tools':
        return 'Bar Tools';
      case 'piano_roll':
        return 'Piano Roll + Note Inspector';
      case 'mixer':
        return 'Mixer';
      case 'groove_library':
        return 'Groove Library';
      case 'metrics':
        return 'Metrics / Debug';
      default:
        return 'Editor';
    }
  }, [activeTab]);

  const showFullWidthEditor = activeTab === 'piano_roll';

  return (
    <div className="min-h-[calc(100vh-48px)] text-slate-100">
      <V3DrummerPickerModal />
      <div className="border-b border-slate-800 bg-slate-950/60">
        <div className="max-w-[1600px] mx-auto px-4 py-3">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="text-sm font-semibold tracking-wide">WebDAW v3 (Rebuild)</div>
              <div className="text-xs text-slate-400 mt-0.5">
                Parallel UI shell. Legacy remains available for parity.
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-xs text-slate-400">View</div>
              <select
                className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
                value={viewMode}
                onChange={(e) => setViewMode(e.target.value as ViewMode)}
              >
                <option value="split">Split (v3 + legacy)</option>
                <option value="v3">v3 only</option>
                <option value="legacy">Legacy only</option>
              </select>

              <label className="flex items-center gap-2 text-xs text-slate-300 select-none">
                <input
                  type="checkbox"
                  checked={showLegacyParity}
                  onChange={(e) => setShowLegacyParity(e.target.checked)}
                />
                Legacy parity
              </label>
            </div>
          </div>
        </div>
      </div>

      {viewMode === 'legacy' ? (
        <WebDAWApp />
      ) : (
        <div className={showFullWidthEditor ? 'w-full px-2 py-4' : 'max-w-[1600px] mx-auto px-4 py-4'}>
          <div className={viewMode === 'split' ? 'grid grid-cols-2 gap-4' : ''}>
            <div className="min-w-0">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden">
                <div className="px-3 py-2 border-b border-slate-800 flex items-center justify-between">
                  <div className="text-xs font-semibold text-slate-200 tracking-wide">v3 Layout Shell</div>
                  <div className="text-[11px] text-slate-400">Active tab: {tabLabel}</div>
                </div>

                <div className="p-3">
                  <V3ImportAnalysisHeader />
                </div>

                <div className="grid grid-cols-12 gap-3 p-3 pt-0">
                  <div className={(showFullWidthEditor ? 'col-span-12' : 'col-span-12') + ' space-y-3'}>
                    <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden">
                      <div className="px-2 py-2 border-b border-slate-800 flex items-center justify-between">
                        <div className="text-xs font-semibold text-slate-200 tracking-wide">Coach + Conform</div>
                        <div className="text-[11px] text-slate-500">
                          {mvsepJobId ? `MVSEP: ${mvsepJobId}` : 'MVSEP: not started'}
                        </div>
                      </div>
                      <div className="p-2 flex flex-wrap items-center gap-2">
                        <div className="flex items-center gap-2 px-2 py-1 rounded border border-slate-800 bg-slate-950">
                          <div className="text-[11px] text-slate-400">Coach</div>
                          <button
                            type="button"
                            className="px-2 py-0.5 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 disabled:opacity-50"
                            onClick={() => {
                              setCoachGoalsOpen((v) => !v);
                              if (!coachGoalsOpen) void fetchCoachGoals();
                            }}
                            disabled={importState.busyStage !== 'idle'}
                          >
                            Goals
                          </button>
                          <button
                            type="button"
                            className="px-2 py-0.5 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 disabled:opacity-50"
                            onClick={() => void runGrooveCoach()}
                            disabled={importState.busyStage !== 'idle'}
                          >
                            Analyze
                          </button>
                          <button
                            type="button"
                            className="px-2 py-0.5 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 disabled:opacity-50"
                            onClick={() => void applyCoachPatch()}
                            disabled={importState.busyStage !== 'idle' || !(coach?.lastAnalysis as any)?.config_patch}
                          >
                            Apply
                          </button>
                        </div>

                        <div className="flex items-center gap-2">
                          <div className="text-[11px] text-slate-500">Conform (Bass)</div>
                          <input
                            type="range"
                            min={0}
                            max={1}
                            step={0.05}
                            value={conformStrength}
                            onChange={(e) => setConformStrength(Number(e.target.value))}
                            className="w-28"
                          />
                          <div className="text-[11px] text-slate-500 w-10">{Math.round(conformStrength * 100)}%</div>
                          <button
                            type="button"
                            className="px-2 py-0.5 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 disabled:opacity-50"
                            onClick={() => void onConformBass()}
                            disabled={importState.busyStage !== 'idle' || !importState.fileKey || !generatedDrumTrack}
                          >
                            Apply
                          </button>
                          <button
                            type="button"
                            className="px-2 py-0.5 rounded bg-slate-950 text-slate-200 text-[11px] border border-slate-800 disabled:opacity-50"
                            onClick={() => void onStartMvsep()}
                            disabled={importState.busyStage !== 'idle' || !importState.fileKey}
                            title={mvsepJobId ? `MVSEP job: ${mvsepJobId}` : 'Start stem separation (MVSEP)'}
                          >
                            {mvsepJobId ? 'MVSEP started' : 'Start MVSEP'}
                          </button>
                        </div>
                      </div>

                      {coachGoalsOpen && coach?.availableGoals ? (
                        <div className="px-2 pb-2">
                          <div className="flex items-start gap-3 px-2 py-2 rounded border border-slate-800 bg-slate-950">
                            <div className="text-[11px] text-slate-400 pt-0.5">Goals</div>
                            <div className="flex items-start gap-4">
                              <div className="space-y-1">
                                <div className="text-[10px] text-slate-500">Sound</div>
                                <div className="max-h-20 overflow-auto pr-1 space-y-0.5">
                                  {(coach.availableGoals.sound_first || []).map((g: any) => {
                                    const id = String(g?.id || '');
                                    if (!id) return null;
                                    const checked = Array.isArray(coach.selectedGoalIds) && coach.selectedGoalIds.includes(id);
                                    return (
                                      <label
                                        key={id}
                                        className="flex items-start gap-1 text-[11px] text-slate-200"
                                      >
                                        <input
                                          type="checkbox"
                                          checked={checked}
                                          onChange={() => {
                                            const prev = Array.isArray(coach.selectedGoalIds) ? coach.selectedGoalIds : [];
                                            const next = checked ? prev.filter((x) => x !== id) : [...prev, id];
                                            setCoachSelectedGoalIds(next);
                                          }}
                                          disabled={importState.busyStage !== 'idle'}
                                        />
                                        <span className="leading-tight">{String(g?.label || g?.id || '')}</span>
                                      </label>
                                    );
                                  })}
                                </div>
                              </div>
                              <div className="space-y-1">
                                <div className="text-[10px] text-slate-500">Technique</div>
                                <div className="max-h-20 overflow-auto pr-1 space-y-0.5">
                                  {(coach.availableGoals.technique_first || []).map((g: any) => {
                                    const id = String(g?.id || '');
                                    if (!id) return null;
                                    const checked = Array.isArray(coach.selectedGoalIds) && coach.selectedGoalIds.includes(id);
                                    return (
                                      <label key={id} className="flex items-start gap-1 text-[11px] text-slate-200">
                                        <input
                                          type="checkbox"
                                          checked={checked}
                                          onChange={() => {
                                            const prev = Array.isArray(coach.selectedGoalIds) ? coach.selectedGoalIds : [];
                                            const next = checked ? prev.filter((x) => x !== id) : [...prev, id];
                                            setCoachSelectedGoalIds(next);
                                          }}
                                          disabled={importState.busyStage !== 'idle'}
                                        />
                                        <span className="leading-tight">{String(g?.label || g?.id || '')}</span>
                                      </label>
                                    );
                                  })}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </div>

                    <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden">
                      <div className="px-2 py-2 border-b border-slate-800 flex items-center justify-between">
                        <div className="text-xs font-semibold text-emerald-200 tracking-wide">v3 Transport</div>
                        <div className="text-[11px] text-slate-400">Playhead {playheadSec.toFixed(2)}s</div>
                      </div>
                      <div className="p-2 flex items-center gap-2">
                        <button
                          type="button"
                          className={
                            'px-3 py-1.5 rounded text-xs border ' +
                            (v3Playing
                              ? 'bg-amber-600/20 text-amber-100 border-amber-500/40'
                              : 'bg-emerald-600/20 text-emerald-100 border-emerald-500/40')
                          }
                          onClick={() => {
                            const duration = Number(importState.waveform?.duration || 0);
                            const hasDuration = Number.isFinite(duration) && duration > 0;
                            if (hasDuration && playheadSec >= duration) {
                              setPlayheadSec(0);
                            }
                            const next = !v3Playing;
                            if (next) {
                              const hasAudio = Boolean(importState.fileKey && importState.waveform?.duration);
                              if (hasAudio) {
                                (async () => {
                                  try {
                                    const eng = drumEngineRef.current;
                                    await Engine.play(playheadSec);
                                    if (eng) {
                                      await eng.ensureRunning();
                                      const ctx = eng.audioContext;
                                      const tEng = Engine.getCurrentTimeSeconds();
                                      if (ctx && typeof ctx.currentTime === 'number' && Number.isFinite(ctx.currentTime) && Number.isFinite(tEng)) {
                                        engineToCtxOffsetRef.current = ctx.currentTime - tEng;
                                      }
                                    }

                                    lastDrumScheduledToRef.current = Engine.getCurrentTimeSeconds();
                                    setV3Playing(true);
                                  } catch (e: any) {
                                    useV3Store.getState().setImportState({ error: e?.message || String(e) });
                                    setV3Playing(false);
                                  }
                                })();
                                return;
                              } else {
                                if (!generatedDrumTrack) {
                                  useV3Store.getState().setImportState({ error: 'No audio loaded and no drums generated; cannot play' });
                                  throw new Error('No audio loaded and no drums generated; cannot play');
                                }
                                drumEngineRef.current?.ensureRunning().catch(() => {
                                  // ignore
                                });
                                // Drum-only transport clock: driven by AudioContext time.
                                const ctx = drumEngineRef.current?.audioContext;
                                if (!ctx) {
                                  useV3Store.getState().setImportState({ error: 'Drum engine not ready; cannot play' });
                                  throw new Error('Drum engine not ready; cannot play');
                                }
                                drumOnlyStartCtxTimeRef.current = ctx.currentTime;
                                drumOnlyStartPlayheadSecRef.current = playheadSec;
                              }
                              lastDrumScheduledToRef.current = playheadSec;
                              setV3Playing(true);
                              return;
                            }
                            if (importState.fileKey && importState.waveform?.duration) {
                              Engine.pause().catch((e) => {
                                useV3Store.getState().setImportState({ error: e?.message || String(e) });
                              });
                            }
                            drumOnlyStartCtxTimeRef.current = null;
                            engineToCtxOffsetRef.current = null;
                            try {
                              drumEngineRef.current?.stopAll();
                            } catch {
                              // ignore
                            }
                            setV3Playing(false);
                          }}
                        >
                          {v3Playing ? 'Pause' : 'Play'}
                        </button>
                        <button
                          type="button"
                          className="px-3 py-1.5 rounded text-xs border bg-slate-900 text-slate-200 border-slate-700 hover:border-slate-500"
                          onClick={() => {
                            setV3Playing(false);
                            Engine.stop().catch((e) => {
                              useV3Store.getState().setImportState({ error: e?.message || String(e) });
                            });
                            engineToCtxOffsetRef.current = null;
                            try {
                              drumEngineRef.current?.stopAll();
                            } catch {
                              // ignore
                            }
                            setPlayheadSec(0);
                          }}
                        >
                          Return to Start
                        </button>
                        <label className="ml-2 flex items-center gap-2 text-xs text-slate-300 select-none">
                          <input
                            type="checkbox"
                            checked={followPlayhead}
                            onChange={(e) => setFollowPlayhead(e.target.checked)}
                          />
                          Follow playhead
                        </label>
                        <div className="ml-2 flex items-center gap-2 text-[11px] text-slate-300">
                          <span className="text-slate-500">Drum offset</span>
                          <input
                            className="w-16 bg-slate-900 border border-slate-700 rounded px-1 py-0.5 text-[11px] text-slate-100"
                            value={String(drumOffsetMs)}
                            onChange={(e) => setDrumOffsetMs(Number(e.target.value) || 0)}
                            inputMode="numeric"
                          />
                          <span className="text-slate-500">ms</span>
                        </div>
                        <div className="ml-2 flex items-center gap-2 text-[11px] text-slate-300">
                          <span className="text-slate-500">Drum beat shift</span>
                          <input
                            className="w-12 bg-slate-900 border border-slate-700 rounded px-1 py-0.5 text-[11px] text-slate-100"
                            value={String(drumBeatShift)}
                            onChange={(e) => {
                              drumBeatShiftManualRef.current = true;
                              setDrumBeatShift(Number(e.target.value) || 0);
                            }}
                            inputMode="numeric"
                          />
                          <span className="text-slate-500">beats</span>
                        </div>
                        <div className="ml-2 flex items-center gap-1 text-[11px] text-slate-300">
                          <span className="text-slate-500">Zoom</span>
                          <button
                            type="button"
                            className="px-2 py-1 rounded border bg-slate-900 text-slate-200 border-slate-700 hover:border-slate-500"
                            onClick={() => setPixelsPerBeat((v) => Math.max(16, Math.round(v / 1.25)))}
                          >
                            -
                          </button>
                          <button
                            type="button"
                            className="px-2 py-1 rounded border bg-slate-900 text-slate-200 border-slate-700 hover:border-slate-500"
                            onClick={() => setPixelsPerBeat(64)}
                          >
                            1:1
                          </button>
                          <button
                            type="button"
                            className="px-2 py-1 rounded border bg-slate-900 text-slate-200 border-slate-700 hover:border-slate-500"
                            onClick={() => setPixelsPerBeat((v) => Math.min(256, Math.round(v * 1.25)))}
                          >
                            +
                          </button>
                        </div>
                        <div className="ml-auto text-[11px] text-slate-500">
                          {importState.waveform?.duration ? `Duration ${importState.waveform.duration.toFixed(2)}s` : 'No audio loaded'}
                        </div>
                      </div>
                    </div>

                    <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden">
                      <div className="px-2 py-2 border-b border-slate-800 flex items-center justify-between">
                        <div className="text-xs font-semibold text-slate-200 tracking-wide">Audio Timeline</div>
                        <div className="text-[11px] text-slate-400">Waveform • tempo curve • sections</div>
                      </div>
                      <div className="p-2">
                        <V3AudioTimeline scrollSyncRef={audioTimelineScrollRef} pixelsPerBeat={pixelsPerBeat} />
                      </div>
                    </div>

                    {!showFullWidthEditor && (
                      <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                        <div className="text-xs font-semibold text-emerald-300 tracking-wide">Transport / Analysis Header</div>
                        <div className="text-[11px] text-slate-500 mt-1">
                          Pending: import, tempo/time signature, sectionization, align-to-grid, playback, export.
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="p-3 pt-0">
                  <div className="rounded-lg border border-slate-800 bg-slate-950">
                    <div className="flex items-center gap-2 px-2 py-2 border-b border-slate-800">
                      <TabButton id="bar_tools" active={activeTab} onClick={setActiveTab} label="Bar" />
                      <TabButton id="piano_roll" active={activeTab} onClick={setActiveTab} label="Piano" />
                      <TabButton id="mixer" active={activeTab} onClick={setActiveTab} label="Mixer" />
                      <TabButton id="groove_library" active={activeTab} onClick={setActiveTab} label="Grooves" />
                      <TabButton id="metrics" active={activeTab} onClick={setActiveTab} label="Metrics" />
                    </div>
                    <div className="p-3">
                      <div className="text-sm font-semibold text-slate-200">{tabLabel}</div>
                      <div className="mt-2">
                        <V3DrumEditorPane
                          pianoRollScrollRef={drumEditorScrollRef}
                          pixelsPerBeat={pixelsPerBeat}
                          drumEngine={drumEngineRef.current}
                          playing={v3Playing}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-3 pt-0">
                  <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden">
                    <div className="flex items-center justify-between gap-3 px-3 py-2 border-b border-slate-800">
                      <div className="text-xs font-semibold text-slate-200 tracking-wide">Inspectors</div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          className={
                            'px-2 py-1 rounded text-[11px] border ' +
                            (inspectorView === 'both'
                              ? 'bg-slate-100 text-slate-950 border-slate-200'
                              : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-500')
                          }
                          onClick={() => setInspectorView('both')}
                        >
                          Both
                        </button>
                        <button
                          type="button"
                          className={
                            'px-2 py-1 rounded text-[11px] border ' +
                            (inspectorView === 'global'
                              ? 'bg-slate-100 text-slate-950 border-slate-200'
                              : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-500')
                          }
                          onClick={() => setInspectorView('global')}
                        >
                          Global
                        </button>
                        <button
                          type="button"
                          className={
                            'px-2 py-1 rounded text-[11px] border ' +
                            (inspectorView === 'section'
                              ? 'bg-slate-100 text-slate-950 border-slate-200'
                              : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-500')
                          }
                          onClick={() => setInspectorView('section')}
                        >
                          Section
                        </button>
                      </div>
                    </div>

                    <div className="p-3">
                      <div className="grid grid-cols-12 gap-3">
                        {(inspectorView === 'both' || inspectorView === 'global') && (
                          <div className={(inspectorView === 'both' ? 'col-span-6' : 'col-span-12') + ' space-y-3'}>
                            <V3GlobalDefaultsPanel />
                          </div>
                        )}

                        {(inspectorView === 'both' || inspectorView === 'section') && (
                          <div className={(inspectorView === 'both' ? 'col-span-6' : 'col-span-12') + ' space-y-3'}>
                            <V3SectionInspector />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {viewMode === 'split' && showLegacyParity && (
              <div className="min-w-0">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden">
                  <div className="px-3 py-2 border-b border-slate-800 flex items-center justify-between">
                    <div className="text-xs font-semibold text-slate-200 tracking-wide">Legacy (Parity)</div>
                    <div className="text-[11px] text-slate-400">Route: /</div>
                  </div>
                  <div className="h-[calc(100vh-170px)] overflow-auto">
                    <WebDAWApp />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TabButton(props: {
  id: EditorTab;
  active: EditorTab;
  onClick: (id: EditorTab) => void;
  label: string;
}) {
  const isActive = props.active === props.id;
  return (
    <button
      type="button"
      className={
        'px-2 py-1 rounded text-[11px] border ' +
        (isActive
          ? 'bg-slate-100 text-slate-950 border-slate-200'
          : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-500')
      }
      onClick={() => props.onClick(props.id)}
    >
      {props.label}
    </button>
  );
}
