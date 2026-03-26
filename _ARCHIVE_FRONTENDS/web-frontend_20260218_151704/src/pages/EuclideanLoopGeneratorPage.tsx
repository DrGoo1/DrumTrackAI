import React, { useState } from "react";
import { EuclideanGrooveDesigner } from "../euclidean/EuclideanGrooveDesigner";
import { AudioEngine } from "../audio/AudioEngine";
import { EuclideanClickPlayer } from "../audio/EuclideanClickPlayer";
import { generateDrums } from "../services/api";
import type { DrumGenerationConfigDTO, EuclideanLaneConfigDTO } from "../types/drumGenerationConfig";
import type { EuclideanLaneConfig, EuclideanPatternEvent } from "../euclidean/euclidean";
import { renderEuclideanClicksToWav } from "../audio/wav";

const engine = new AudioEngine();
const player = new EuclideanClickPlayer(engine);

export const EuclideanLoopGeneratorPage: React.FC = () => {
  const [state, setState] = useState<{
    lanes: EuclideanLaneConfig[];
    bars: number;
    tempo: number;
    swing: number;
    patternEvents: EuclideanPatternEvent[];
  } | null>(null);

  const [busy, setBusy] = useState<null | "midi" | "wav">(null);
  const [error, setError] = useState<string | null>(null);

  const handlePreview = async (events: EuclideanPatternEvent[], tempo: number) => {
    await player.playPattern(events, tempo);
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportMidi = async () => {
    if (!state) return;
    setError(null);
    setBusy("midi");

    try {
      const laneDTOs: EuclideanLaneConfigDTO[] = state.lanes.map((lane) => ({
        instrumentId: lane.instrumentId,
        steps: lane.steps,
        hits: lane.hits,
        accents: lane.accents,
        rotate: lane.rotate,
        velocity: lane.velocity,
        accentVelocity: lane.accentVelocity,
      }));

      const cfg: DrumGenerationConfigDTO = {
        sectionId: "euclid_loop_generator",
        startMeasure: 0,
        endMeasure: Math.max(0, state.bars - 1),
        tempos: Array.from({ length: Math.max(1, state.bars) }, () => state.tempo),
        timeSignature: [4, 4],
        style: "Funk",
        drummer: "Purdie_AI",
        intensity: 0.7,
        variation: 0.5,
        humanize: true,
        humanizeAmount: 0.72,
        ghostNoteAmount: 0.65,
        swingAmount: state.swing,
        buildScope: "selected_section",
        fillLocations: [],
        fillType: "auto",
        generationMode: "euclidean",
        euclideanLanes: laneDTOs,
      };

      const resp = await generateDrums(cfg);
      if (!resp?.midi_base64) {
        throw new Error("Empty MIDI export from backend");
      }

      const bytes = Uint8Array.from(atob(resp.midi_base64), (c) => c.charCodeAt(0));
      const blob = new Blob([bytes], { type: "audio/midi" });
      const filename = `euclidean_loop_${state.tempo}bpm_${state.bars}bars.mid`;
      downloadBlob(blob, filename);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(null);
    }
  };

  const handleExportWav = async () => {
    if (!state) return;
    setError(null);
    setBusy("wav");

    try {
      const wav = await renderEuclideanClicksToWav(state.patternEvents, state.tempo);
      const filename = `euclidean_click_${state.tempo}bpm_${state.bars}bars.wav`;
      downloadBlob(wav, filename);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-6xl mx-auto px-4 py-4">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <div className="text-sm uppercase tracking-wider text-slate-400">DrumTracKAI</div>
            <h2 className="text-2xl font-bold text-slate-100">Euclidean Loop Generator</h2>
            <div className="text-sm text-slate-400 mt-1">
              Design a loop with the Euclidean wheel, preview it, then export as MIDI or stereo WAV.
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              className="px-3 py-2 rounded bg-slate-800 hover:bg-slate-700 text-sm disabled:opacity-50"
              onClick={handleExportMidi}
              disabled={!state || busy !== null}
              title="Exports the loop via backend MIDI generation (midi_base64)."
            >
              {busy === "midi" ? "Exporting MIDI…" : "Export MIDI"}
            </button>
            <button
              className="px-3 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-sm disabled:opacity-50"
              onClick={handleExportWav}
              disabled={!state || busy !== null}
              title="Renders the click-preview to a stereo WAV using OfflineAudioContext."
            >
              {busy === "wav" ? "Rendering WAV…" : "Export Stereo WAV"}
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-3 bg-red-950/40 border border-red-900/60 text-red-200 rounded p-2 text-sm">
            {error}
          </div>
        )}

        <EuclideanGrooveDesigner onPreviewPattern={handlePreview} onStateChange={setState} />
      </div>
    </div>
  );
};
