import React, { useMemo } from "react";
import Timeline from "../Timeline";
import { useV3Store } from "../../state/v3/store";
import type { ArrangementSection } from "../../midi/types";
import { beatFloatToBarBeat, beatFloatToTimeSec, barBeatToBeatFloat, timeSecToBeatFloat } from "../../time/v3TimelineKernel";

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

function formatBBT(args: {
  tSec: number;
  timeSig: [number, number];
  beatTimes?: number[];
  beatZeroOffsetSec?: number;
  tempoMap?: Array<{ tSec: number; bpm: number }>;
  fallbackBpm: number;
}): string {
  const beatsPerBar = Number(args.timeSig?.[0] || 4) || 4;
  const ppq = 960;
  let beats = 0;
  if (Array.isArray(args.beatTimes) && args.beatTimes.length >= 2) {
    // beatTimes are already in the audio timeline (seconds). Do not shift by beatZeroOffsetSec.
    void args.beatZeroOffsetSec;
    beats = timeSecToBeatFloat(args.beatTimes, Number(args.tSec) || 0);
  } else {
    beats = beatsAtTimeFromTempoMap(args.tempoMap || [], args.fallbackBpm, args.tSec);
  }

  const b = Math.max(0, Number.isFinite(beats) ? beats : 0);
  const wholeBeats = Math.floor(b);
  const frac = Math.max(0, Math.min(0.999999, b - wholeBeats));
  const bar = Math.floor(wholeBeats / beatsPerBar) + 1;
  const beatInBar = (wholeBeats % beatsPerBar) + 1;
  const tick = Math.floor(frac * ppq);
  return `${bar}:${beatInBar}:${tick}`;
}

export function V3AudioTimeline(props: { scrollSyncRef?: React.RefObject<HTMLDivElement | null>; pixelsPerBeat: number }) {
  const importState = useV3Store((s) => s.importState);
  const arrangement = useV3Store((s) => s.arrangement);
  const playheadSec = useV3Store((s) => s.playheadSec);
  const setPlayheadSec = useV3Store((s) => s.setPlayheadSec);
  const setSections = useV3Store((s) => s.setSections);
  const setSectionsBB = useV3Store((s) => s.setSectionsBB);
  const selectedSectionId = useV3Store((s) => s.selection.selectedSectionId);
  const setSelectedSectionId = useV3Store((s) => s.setSelectedSectionId);
  const snapSectionsToBeat = useV3Store((s) => s.ui.snapSectionsToBeat);
  const setSnapSectionsToBeat = useV3Store((s) => s.setSnapSectionsToBeat);

  const tracks = useMemo(() => {
    if (!importState.fileKey || !importState.waveform?.duration) return [];
    return [
      {
        key: importState.fileKey,
        peaks: importState.waveform?.peaks || [],
        peaksL: importState.waveform?.peaksL,
        peaksR: importState.waveform?.peaksR,
        sr: Number(importState.waveform?.sr || 44100),
        seconds: Number(importState.waveform.duration || 0),
        color: "#38bdf8",
        name: importState.fileName || "Audio",
      },
    ];
  }, [importState.fileKey, importState.fileName, importState.waveform?.duration, importState.waveform?.peaks, importState.waveform?.peaksL, importState.waveform?.peaksR, importState.waveform?.sr]);

  const sections = useMemo(() => {
    const beatTimes = arrangement.beatTimes;
    const off = Number(arrangement.beatZeroOffsetSec) || 0;
    const meterMap = arrangement.meterMap;

    const bb = arrangement.sectionsBB;
    if (Array.isArray(bb) && bb.length && Array.isArray(beatTimes) && beatTimes.length >= 2) {
      return bb.map((s) => {
        const startBeat = barBeatToBeatFloat(meterMap, s.start);
        const endBeat = barBeatToBeatFloat(meterMap, s.end);
        // beatTimes are already in the audio timeline (seconds). Do not shift by beatZeroOffsetSec.
        void off;
        const startSec = beatFloatToTimeSec(beatTimes, startBeat);
        const endSec = beatFloatToTimeSec(beatTimes, endBeat);
        return {
          id: String(s.id),
          start: startSec,
          end: endSec,
          density: 0.7,
          fillIn: false,
          fillOut: false,
          label: s.label,
          confidence: typeof (s as any).conf === "number" ? (s as any).conf : undefined,
        };
      });
    }

    return (arrangement.sections || []).map((s, idx) => ({
      id: `v3-${idx}-${s.startSec.toFixed(3)}-${s.endSec.toFixed(3)}`,
      start: s.startSec,
      end: s.endSec,
      density: 0.7,
      fillIn: false,
      fillOut: false,
      label: s.label,
      confidence: typeof (s as any).conf === "number" ? (s as any).conf : undefined,
    }));
  }, [arrangement.beatTimes, arrangement.beatZeroOffsetSec, arrangement.meterMap, arrangement.sections, arrangement.sectionsBB]);

  const bpm = arrangement.tempoMap?.[0]?.bpm || 120;

  const bbt = useMemo(() => {
    return formatBBT({
      tSec: playheadSec,
      timeSig: arrangement.timeSig,
      beatTimes: arrangement.beatTimes,
      beatZeroOffsetSec: arrangement.beatZeroOffsetSec,
      tempoMap: arrangement.tempoMap,
      fallbackBpm: bpm,
    });
  }, [arrangement.beatTimes, arrangement.beatZeroOffsetSec, arrangement.tempoMap, arrangement.timeSig, bpm, playheadSec]);

  if (!importState.waveform?.duration) {
    return (
      <div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-6 text-[11px] text-slate-500">
        Load audio to view timeline.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden">
      <div className="px-3 py-1 border-b border-slate-800 bg-slate-950 text-[11px] text-slate-300 flex items-center justify-between gap-3">
        <div>
          Playhead: {playheadSec.toFixed(2)}s • {bbt}
        </div>
        <label className="flex items-center gap-2 text-[11px] text-slate-200">
          <input type="checkbox" checked={!!snapSectionsToBeat} onChange={(e) => setSnapSectionsToBeat(e.target.checked)} />
          Snap sections to beat
        </label>
      </div>
      <Timeline
        bpm={bpm}
        tempoMap={arrangement.tempoMap}
        beatTimes={arrangement.beatTimes}
        beatZeroOffsetSec={arrangement.beatZeroOffsetSec}
        tracks={tracks as any}
        sections={sections as any}
        selectedSectionIds={selectedSectionId ? new Set([selectedSectionId]) : new Set()}
        onSelectSection={(sectionId) => {
          setSelectedSectionId(sectionId ? sectionId : null);
        }}
        onSectionsChange={(next) => {
          const mapped: ArrangementSection[] = (next || [])
            .map((sec: any, i: number) => ({
              label: String(sec?.label || `Section ${i + 1}`),
              startSec: Number(sec?.start) || 0,
              endSec: Number(sec?.end) || 0,
              conf: sec?.confidence,
            }))
            .filter((s) => Number.isFinite(s.startSec) && Number.isFinite(s.endSec) && s.endSec > s.startSec);
          setSections(mapped);

          const beatTimes = arrangement.beatTimes;
          const off = Number(arrangement.beatZeroOffsetSec) || 0;
          if (Array.isArray(beatTimes) && beatTimes.length >= 2) {
            const meterMap = arrangement.meterMap;
            const bb = (next || [])
              .map((sec: any, i: number) => {
                const startSec = Number(sec?.start) || 0;
                const endSec = Number(sec?.end) || 0;
                if (!Number.isFinite(startSec) || !Number.isFinite(endSec) || endSec <= startSec) return null;

                // beatTimes are already in the audio timeline (seconds). Do not shift by beatZeroOffsetSec.
                void off;
                const rawStartBeat = timeSecToBeatFloat(beatTimes, startSec);
                const rawEndBeat = timeSecToBeatFloat(beatTimes, endSec);
                const startBeatFloat = snapSectionsToBeat ? Math.round(rawStartBeat) : rawStartBeat;
                const endBeatFloat = snapSectionsToBeat ? Math.round(rawEndBeat) : rawEndBeat;
                const start = beatFloatToBarBeat(meterMap, startBeatFloat);
                const end = beatFloatToBarBeat(meterMap, endBeatFloat);

                return {
                  id: String(sec?.id || `sec-${i}`),
                  label: String(sec?.label || `Section ${i + 1}`),
                  start,
                  end,
                  conf: sec?.confidence,
                };
              })
              .filter(Boolean) as any;
            setSectionsBB(bb);
          }
        }}
        playhead={playheadSec}
        setPlayhead={setPlayheadSec}
        playing={false}
        onDropFiles={() => {}}
        loop={{ enabled: false, start: 0, end: importState.waveform.duration }}
        setLoop={() => {}}
        gridSec={0.25}
        pixelsPerBeat={props.pixelsPerBeat}
        timeSignature={arrangement.timeSig}
        scrollSyncRef={props.scrollSyncRef}
      />
    </div>
  );
}
