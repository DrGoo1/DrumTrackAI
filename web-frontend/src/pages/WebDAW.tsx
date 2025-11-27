import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AudioEngine } from '../audio/AudioEngine';
import { Scheduler } from '../audio/Scheduler';
import { TempoMap } from '../time/TempoMap';
import { WaveformView } from '../components/WaveformView';
import { SectionEditor, Section } from '../components/SectionEditor';
import { analyzeTempo, fetchWaveform, uploadFile, alignSections, analyzeTempoSections, generateMidiSections, ping, getApiBases } from '../api/api';

export const WebDAW: React.FC = () => {
  const engineRef = useRef(new AudioEngine());
  const [currentTime, setCurrentTime] = useState(0);
  const [peaks, setPeaks] = useState<number[] | undefined>(undefined);
  const [peaksL, setPeaksL] = useState<number[] | undefined>(undefined);
  const [peaksR, setPeaksR] = useState<number[] | undefined>(undefined);
  const [durationSec, setDurationSec] = useState<number | undefined>(undefined);
  const [beatLanes, setBeatLanes] = useState<Array<{ start: number; end: number; beats: number[]; confidence?: number }>>([]);
  const [barLanes, setBarLanes] = useState<Array<{ start: number; end: number; bars: number[] }>>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [fileKey, setFileKey] = useState<string | null>(null);
  const [bpm, setBpm] = useState<number | null>(null);
  const [sectionBpm, setSectionBpm] = useState<Record<string, number>>({});
  const [tempoDetails, setTempoDetails] = useState<Record<string, { tempo: number|null; confidence: number; candidates: number[] }>>({});
  const [swing, setSwing] = useState<number>(0.0); // 0.0 .. 0.6
  const [velocityProfile, setVelocityProfile] = useState<'flat' | 'accent24'>('flat');
  const [useRide, setUseRide] = useState<boolean>(false);
  const [useCrash, setUseCrash] = useState<boolean>(true);
  const [fillType, setFillType] = useState<'none'|'random'|'tomrun'|'snarebuzz'|'edmriser'>('none');
  const [fillBars, setFillBars] = useState<1 | 2>(1);
  const [kickVel, setKickVel] = useState<'flat' | 'punchy'>('flat');
  const [snareVel, setSnareVel] = useState<'flat' | 'accent24' | 'ghost'>('flat');
  const [hhVel, setHhVel] = useState<'flat' | 'accent24'>('flat');
  const [rideVel, setRideVel] = useState<'flat' | 'washy'>('flat');
  const [showBeats, setShowBeats] = useState<boolean>(true);
  const [showBars, setShowBars] = useState<boolean>(true);
  const tempoMap = useMemo(() => new TempoMap(), []);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      setCurrentTime(engineRef.current.getCurrentTimeSeconds());
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  useEffect(() => { engineRef.current.init(); }, []);

  const schedulerRef = useRef<Scheduler | null>(null);
  useEffect(() => {
    schedulerRef.current = new Scheduler(
      () => engineRef.current.getCurrentTimeSeconds(),
      () => { /* schedule window hook; integrate drum notes later */ }
    );
    return () => schedulerRef.current?.stop();
  }, []);

  const onLoadAudio = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.wav,.mp3,.flac,.aac';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (file) {
        // Load into Web Audio for playback
        await engineRef.current.loadTrack(file);
        engineRef.current.play(0);

        // Upload to backend to get a file key and server-side peaks
        try {
          const up = await uploadFile(file);
          if (up?.key) {
            setFileKey(up.key);
            if (up.waveform?.peaks?.length) {
              setPeaks(up.waveform.peaks);
              // stereo if available
              const anyWf: any = up.waveform;
              if (anyWf?.peaksL && anyWf?.peaksR) {
                setPeaksL(anyWf.peaksL);
                setPeaksR(anyWf.peaksR);
              } else {
                setPeaksL(undefined);
                setPeaksR(undefined);
              }
              if (typeof anyWf?.duration === 'number') setDurationSec(anyWf.duration);
            } else {
              const wf = await fetchWaveform(up.key, 3000);
              const anyWf: any = wf;
              if (anyWf?.peaks) setPeaks(anyWf.peaks);
              if (anyWf?.peaksL && anyWf?.peaksR) {
                setPeaksL(anyWf.peaksL);
                setPeaksR(anyWf.peaksR);
              } else {
                setPeaksL(undefined);
                setPeaksR(undefined);
              }
              if (typeof anyWf?.duration === 'number') setDurationSec(anyWf.duration);
            }
          }
        } catch (e) {
          console.warn('Upload/waveform failed, using client-side peaks', e);
          // Fallback: simple client-side peaks
          const buf = engineRef.current.getBuffer();
          if (buf) {
            const ch = buf.getChannelData(0);
            const target = 2000;
            const block = Math.max(1, Math.floor(ch.length / target));
            const out: number[] = new Array(Math.min(target, Math.ceil(ch.length / block))).fill(0);
            for (let i = 0; i < out.length; i++) {
              let sum = 0;
              const start = i * block;
              const end = Math.min(ch.length, start + block);
              for (let j = start; j < end; j++) sum += ch[j] * ch[j];
              const rms = Math.sqrt(sum / Math.max(1, end - start));
              out[i] = Math.max(-1, Math.min(1, rms * 2 - 1));
            }
            setPeaks(out);
          }
        }
      }
    };
    input.click();
  };

  const onAnalyzeTempo = async () => {
    if (!fileKey) {
      alert('Load a file first');
      return;
    }
    try {
      const res = await analyzeTempo(fileKey);
      // Backend returns { tempo, beats, onsets }
      if ((res as any).tempo) {
        setBpm((res as any).tempo as number);
      }
      // TODO: update TempoMap with a single-segment or curve if provided
    } catch (e) {
      alert('Tempo analysis failed');
      console.error(e);
    }
  };

  const onAuditionBeats = () => {
    const ctx = engineRef.current.getContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const current = engineRef.current.getCurrentTimeSeconds();
    const horizon = current + 8.0; // seconds ahead
    const freqStrong = 1400;
    const freqWeak = 1000;
    beatLanes.forEach(lane => {
      (lane.beats || []).forEach((t, idx) => {
        if (t >= current && t <= horizon) {
          const when = now + (t - current);
          const isDownbeat = idx % 4 === 0; // heuristic until downbeat detection
          engineRef.current.scheduleClick(when, isDownbeat ? freqStrong : freqWeak, 0.03);
        }
      });
    });
  };

  const onAnalyzeSections = async () => {
    if (!fileKey) { alert('Load a file first'); return; }
    try {
      const payload = sections.map(s => ({ start: s.start, end: s.end }));
      const res = await analyzeTempoSections(fileKey, payload);
      const bpmMap: Record<string, number> = {};
      const detMap: Record<string, { tempo: number|null; confidence: number; candidates: number[] }> = {};
      res.results.forEach((r, idx) => {
        const id = sections[idx]?.id;
        if (!id) return;
        if (typeof r.tempo === 'number' && !isNaN(r.tempo)) bpmMap[id] = r.tempo;
        detMap[id] = { tempo: r.tempo, confidence: r.confidence, candidates: r.candidates || [] };
      });
      setSectionBpm(bpmMap);
      setTempoDetails(detMap);
    } catch (e) {
      console.error('Tempo sections analysis failed', e);
      alert('Tempo sections analysis failed');
    }
  };

  const onAlignSections = async () => {
    if (!fileKey) { alert('Load a file first'); return; }
    try {
      const payload = sections.map(s => ({ start: s.start, end: s.end }));
      const res = await alignSections(fileKey, payload);
      if (res?.sections?.length) {
        // Merge aligned times back into current labeled sections by index
        const updated = sections.map((s, i) => ({ ...s, start: res.sections[i]?.start ?? s.start, end: res.sections[i]?.end ?? s.end }));
        setSections(updated);
        if (typeof res.tempo === 'number') setBpm(res.tempo);
        // Build beat lanes from details if present
        const lanes: Array<{ start: number; end: number; beats: number[]; confidence?: number }> = [];
        const barOut: Array<{ start: number; end: number; bars: number[] }> = [];
        const anyRes: any = res as any;
        if (Array.isArray(anyRes.details)) {
          anyRes.details.forEach((d: any) => {
            if (Array.isArray(d?.beats)) {
              lanes.push({ start: Number(d.start)||0, end: Number(d.end)||0, confidence: Number(d.confidence), beats: d.beats.map((x: any)=>Number(x)).filter((x: number)=>!isNaN(x)) });
            }
            if (Array.isArray(d?.bars)) {
              barOut.push({ start: Number(d.start)||0, end: Number(d.end)||0, bars: d.bars.map((x: any)=>Number(x)).filter((x: number)=>!isNaN(x)) });
            }
          });
        }
        setBeatLanes(lanes);
        setBarLanes(barOut);
      }
    } catch (e) {
      console.error('Align sections failed', e);
      alert('Align sections failed');
    }
  };

  const onExportMidi = async () => {
    if (!fileKey) { alert('Load a file first'); return; }
    try {
      const payload = sections.map(s => ({ start: s.start, end: s.end }));
      const res = await generateMidiSections(fileKey, payload, {
        swing,
        velocity: velocityProfile,
        ride: useRide,
        crash: useCrash,
        fill: fillType,
        fillBars,
        velocityLanes: {
          kick: kickVel,
          snare: snareVel,
          hihat: hhVel,
          ride: rideVel,
        },
      });
      if (res?.base64) {
        const a = document.createElement('a');
        a.href = `data:audio/midi;base64,${res.base64}`;
        a.download = res.filename || 'drumtrack.mid';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
    } catch (e) {
      console.error('MIDI export failed', e);
      alert('MIDI export failed');
    }
  };

  const onPingApi = async () => {
    try {
      const bases = getApiBases();
      const res = await ping();
      alert(`API bases tried:\n${bases.join('\n')}\n\nHealth: ${res.ok ? 'OK' : 'FAILED'}`);
    } catch (e) {
      alert('Ping failed');
    }
  };

  return (
    <div style={{ padding: 12 }}>
      <h2>DrumTracKAI WebDAW (Scaffold)</h2>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button onClick={onLoadAudio}>Load Audio</button>
        <button onClick={() => engineRef.current.play(currentTime)}>Play</button>
        <button onClick={() => engineRef.current.stop()}>Stop</button>
        <div>
          Time: {currentTime.toFixed(2)}s | Next Downbeat: {tempoMap.nextDownbeatAfter(currentTime).toFixed(2)}s
          {bpm ? ` | BPM: ${bpm.toFixed(1)}` : ''}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
          <label><input type="checkbox" checked={showBeats} onChange={e=> setShowBeats(e.target.checked)} /> Show Beats</label>
          <label><input type="checkbox" checked={showBars} onChange={e=> setShowBars(e.target.checked)} /> Show Bars</label>
        </div>
        <button onClick={onPingApi}>Ping API</button>
        <button onClick={onAnalyzeTempo}>Analyze Tempo</button>
        <button onClick={onAnalyzeSections}>Analyze Sections</button>
        <button onClick={onAlignSections}>Align Sections to Grid</button>
        <button onClick={onAuditionBeats}>Audition Beats</button>
        <button onClick={onExportMidi}>Export MIDI (Prototype)</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 12 }}>
          <label> Swing: <input type="range" min={0} max={60} value={Math.round(swing*100)} onChange={e=> setSwing(Number(e.target.value)/100)} /></label>
          <select value={velocityProfile} onChange={e=> setVelocityProfile(e.target.value as any)}>
            <option value="flat">Velocity: Flat</option>
            <option value="accent24">Velocity: Accent 2/4</option>
          </select>
          <label><input type="checkbox" checked={useRide} onChange={e=> setUseRide(e.target.checked)} /> Ride</label>
          <label><input type="checkbox" checked={useCrash} onChange={e=> setUseCrash(e.target.checked)} /> Crash</label>
          <select value={fillType} onChange={e=> setFillType(e.target.value as any)}>
            <option value="none">Fill: None</option>
            <option value="random">Fill: Random</option>
            <option value="tomrun">Fill: Tom Run</option>
            <option value="snarebuzz">Fill: Snare Buzz</option>
            <option value="edmriser">Fill: EDM Riser</option>
          </select>
          <label> Fill bars:
            <select value={fillBars} onChange={e=> setFillBars(Number(e.target.value) === 2 ? 2 : 1)}>
              <option value={1 as any}>1</option>
              <option value={2 as any}>2</option>
            </select>
          </label>
          <label> Kick vel:
            <select value={kickVel} onChange={e=> setKickVel(e.target.value as any)}>
              <option value="flat">Flat</option>
              <option value="punchy">Punchy</option>
            </select>
          </label>
          <label> Snare vel:
            <select value={snareVel} onChange={e=> setSnareVel(e.target.value as any)}>
              <option value="flat">Flat</option>
              <option value="accent24">Accent 2/4</option>
              <option value="ghost">Ghost</option>
            </select>
          </label>
          <label> Hat vel:
            <select value={hhVel} onChange={e=> setHhVel(e.target.value as any)}>
              <option value="flat">Flat</option>
              <option value="accent24">Accent 2/4</option>
            </select>
          </label>
          <label> Ride vel:
            <select value={rideVel} onChange={e=> setRideVel(e.target.value as any)}>
              <option value="flat">Flat</option>
              <option value="washy">Washy</option>
            </select>
          </label>
        </div>
      </div>
      <div style={{ marginTop: 12 }}>
        <WaveformView
          peaks={peaks}
          peaksL={peaksL}
          peaksR={peaksR}
          durationSec={durationSec}
          beatLanes={showBeats ? beatLanes : []}
          barLanes={showBars ? barLanes : []}
        />
      </div>
      <div style={{ marginTop: 12 }}>
        <SectionEditor sections={sections} onChange={setSections} />
        {sections.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#bbb' }}>
            {sections.map(s => (
              <div key={s.id} style={{ marginBottom: 6 }}>
                <div><strong>{s.label}</strong> [{s.start.toFixed(2)} - {s.end.toFixed(2)}]s</div>
                <div>
                  BPM: {sectionBpm[s.id]?.toFixed?.(1) || '—'}
                  {tempoDetails[s.id] ? ` | Confidence: ${tempoDetails[s.id].confidence.toFixed(2)} | Candidates: ${(tempoDetails[s.id].candidates||[]).slice(0,5).map(c=>c.toFixed(1)).join(', ')}` : ''}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
