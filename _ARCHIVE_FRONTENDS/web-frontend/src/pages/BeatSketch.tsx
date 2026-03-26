import React, { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { BeatPadGrid } from "../components/BeatPadGrid";
import {
  BeatPadHit,
  translateBeatbox,
  translateTapPattern,
  webdawApi,
} from "../services/api";

const personaPresets = [
  { id: "neo_soul_guru", label: "Neo-Soul Pocket" },
  { id: "arena_rock_captain", label: "Arena Rock Drive" },
  { id: "alt_glitch_curator", label: "Alt / Glitch" },
];

const stylePacks = [
  { id: "neo_soul_pocket", label: "Neo-Soul Pocket" },
  { id: "pop_punk_energy", label: "Pop Punk Energy" },
  { id: "ambient_brushes", label: "Ambient Brushes" },
];

type UploadResult = { success: boolean; file_id: string; message: string };
type StatusState = "idle" | "recording" | "ready" | "uploading" | "translating" | "complete" | "error";
type PadStatus = "idle" | "sending" | "complete" | "error";
type CaptureMode = "mic" | "pads";
type EntryIntent = "mic" | "pads" | "sing" | "upload";

const entryIntentCopy: Record<EntryIntent, string> = {
  mic: "BeatSketch mode: hold to record beatboxing or percussive ideas.",
  pads: "BeatPad mode: tap the neon pads, then translate instantly.",
  sing: "BeatSing tip: hum or vocalize rhythms—the mic capture is ready.",
  upload: "Audio upload mode: capture a quick reference, then upload via Translate to analyze sections.",
};

export default function BeatSketchPage() {
  const location = useLocation();
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | undefined>(undefined);

  const [status, setStatus] = useState<StatusState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [uploadInfo, setUploadInfo] = useState<UploadResult | null>(null);
  const [translation, setTranslation] = useState<Awaited<ReturnType<typeof translateBeatbox>> | null>(null);
  const [personaId, setPersonaId] = useState(personaPresets[0].id);
  const [stylePack, setStylePack] = useState(stylePacks[0].id);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.35);
  const [swing, setSwing] = useState(0.08);
  const [quantization, setQuantization] = useState("1/16");
  const [captureMode, setCaptureMode] = useState<CaptureMode>("mic");
  const [padTempo, setPadTempo] = useState(96);
  const [padHits, setPadHits] = useState<BeatPadHit[]>([]);
  const [padStatus, setPadStatus] = useState<PadStatus>("idle");
  const [padError, setPadError] = useState<string | null>(null);
  const [entryIntent, setEntryIntent] = useState<EntryIntent>("mic");

  const supportsRecording = typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      cancelAnimationFrame(timerRef.current);
      timerRef.current = undefined;
    }
  }, []);

  const startTimer = useCallback(() => {
    stopTimer();
    const started = performance.now();
    const tick = () => {
      setElapsed((performance.now() - started) / 1000);
      timerRef.current = requestAnimationFrame(tick);
    };
    timerRef.current = requestAnimationFrame(tick);
  }, [stopTimer]);

  const stopRecorder = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder) {
      if (recorder.state !== "inactive") {
        recorder.stop();
      }
      recorder.stream.getTracks().forEach((track) => track.stop());
      recorderRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      if (audioURL) {
        URL.revokeObjectURL(audioURL);
      }
      stopTimer();
      stopRecorder();
    };
  }, [audioURL, stopRecorder, stopTimer]);

  useEffect(() => {
    if (status === "recording") {
      startTimer();
    } else {
      stopTimer();
    }
  }, [startTimer, status, stopTimer]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const rawMode = params.get("mode") || "mic";
    const allowed: EntryIntent[] = ["mic", "pads", "sing", "upload"];
    const modeParam: EntryIntent = allowed.includes(rawMode as EntryIntent) ? (rawMode as EntryIntent) : "mic";
    setEntryIntent(modeParam);
    if (modeParam === "pads") {
      setCaptureMode("pads");
    } else {
      setCaptureMode("mic");
    }
  }, [location.search]);

  const handleStartRecording = async () => {
    setError(null);
    setTranslation(null);
    setUploadInfo(null);
    setAudioBlob(null);
    setAudioURL(null);

    if (!supportsRecording) {
      setError("This browser does not support in-browser audio capture.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
        },
      });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      recorderRef.current = recorder;

      recorder.ondataavailable = (evt) => {
        if (evt.data?.size) {
          chunksRef.current.push(evt.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        setAudioBlob(blob);
        setAudioURL(url);
        setStatus("ready");
      };

      recorder.start();
      setStatus("recording");
      setElapsed(0);
    } catch (err) {
      console.error(err);
      setError((err as Error).message || "Unable to access microphone");
    }
  };

  const handleStopRecording = () => {
    stopRecorder();
    stopTimer();
  };

  const resetTake = () => {
    stopRecorder();
    stopTimer();
    setStatus("idle");
    setElapsed(0);
    if (audioURL) {
      URL.revokeObjectURL(audioURL);
      setAudioURL(null);
    }
    setAudioBlob(null);
    setUploadInfo(null);
    setTranslation(null);
  };

  const handleUploadAndTranslate = async () => {
    if (!audioBlob) {
      setError("Record a take before uploading.");
      return;
    }

    try {
      setStatus("uploading");
      setError(null);
      const file = new File([audioBlob], `beatbox-${Date.now()}.webm`, { type: audioBlob.type || "audio/webm" });
      const uploadRes = await webdawApi.uploadDirect(file);
      setUploadInfo(uploadRes);
      if (!uploadRes.success) {
        throw new Error(uploadRes.message || "Upload failed");
      }

      setStatus("translating");
      const translateRes = await translateBeatbox(uploadRes.file_id, {
        persona_id: personaId,
        style_pack: stylePack,
        options: {
          swing,
          quantization,
          confidence_threshold: confidenceThreshold,
        },
      });
      setTranslation(translateRes);
      setStatus("complete");
    } catch (err) {
      console.error(err);
      setError((err as Error).message || "Translation failed");
      setStatus("error");
    }
  };

  const handlePadHitsChange = (hits: BeatPadHit[]) => {
    setPadHits(hits);
    if (hits.length === 0) {
      setPadStatus("idle");
    }
  };

  const handlePadTranslate = async () => {
    if (!padHits.length) {
      setPadError("Tap a pattern before translating.");
      return;
    }

    try {
      setPadStatus("sending");
      setPadError(null);
      const response = await translateTapPattern({
        hits: padHits,
        tempo: padTempo,
        persona_id: personaId,
        style_pack: stylePack,
        plugin: "jamstix",
        options: {
          swing,
          quantization,
          confidence_threshold: confidenceThreshold,
          plugin: "jamstix",
        },
      });
      setTranslation(response);
      setPadStatus("complete");
    } catch (err) {
      console.error(err);
      setPadError((err as Error).message || "Pad translation failed");
      setPadStatus("error");
    }
  };

  const midiHref = translation?.preview_midi ? `data:audio/midi;base64,${translation.preview_midi}` : undefined;
  const isPadTranslateDisabled = !padHits.length || padStatus === "sending";

  const renderMicPanel = () => (
    <div className="space-y-6">
      {!supportsRecording && (
        <div className="rounded-2xl border border-yellow-700/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-100">
          MediaRecorder is not available in this browser. Try the latest Chrome, Edge, or Safari.
        </div>
      )}

      <p className="text-sm text-slate-300">
        Hold the phone close, beatbox clearly, and avoid clipping. We will sync to Jamstix automatically.
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={status === "recording" ? handleStopRecording : handleStartRecording}
          className={`px-5 py-3 rounded-2xl text-sm font-semibold tracking-wide shadow-lg transition ${
            status === "recording"
              ? "bg-gradient-to-r from-rose-500 to-orange-500 hover:brightness-110"
              : "bg-gradient-to-r from-emerald-500 to-lime-400 hover:brightness-110"
          }`}
        >
          {status === "recording" ? "Stop Recording" : "Record Beat"}
        </button>
        <button
          onClick={resetTake}
          disabled={status === "recording"}
          className="px-4 py-2 rounded-2xl text-sm font-semibold border border-white/20 hover:bg-white/10 disabled:opacity-30"
        >
          Reset Take
        </button>
        <span className="text-xs uppercase tracking-widest text-slate-400">{elapsed.toFixed(1)}s captured</span>
      </div>

      {audioURL && (
        <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
          <audio controls src={audioURL} className="w-full" />
          <p className="mt-2 text-xs text-slate-400">Preview before uploading.</p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={handleUploadAndTranslate}
          disabled={!audioBlob || status === "uploading" || status === "translating"}
          className="px-5 py-3 rounded-2xl bg-gradient-to-r from-sky-500 to-indigo-500 font-semibold tracking-wide disabled:opacity-40"
        >
          {status === "uploading" ? "Uploading…" : status === "translating" ? "Translating…" : "Upload & Translate"}
        </button>
        {uploadInfo?.file_id && <span className="text-xs text-slate-400">File ID: {uploadInfo.file_id}</span>}
        {status === "complete" && (
          <span className="text-emerald-400 text-xs uppercase tracking-widest">Translation complete</span>
        )}
      </div>

      {error && (
        <div className="rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</div>
      )}
    </div>
  );

  const renderPadPanel = () => (
    <div className="space-y-6">
      <p className="text-sm text-slate-300">
        Tap the neon pads—each press is timestamped to your custom tempo and sent straight into DrumTracKAI.
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-sm text-slate-200">
          Tempo
          <div className="mt-1 flex items-center gap-3">
            <input
              type="range"
              min={60}
              max={160}
              value={padTempo}
              onChange={(e) => setPadTempo(parseInt(e.target.value, 10) || 96)}
              className="flex-1 accent-purple-400"
            />
            <input
              type="number"
              value={padTempo}
              onChange={(e) => setPadTempo(parseInt(e.target.value, 10) || 96)}
              className="w-20 rounded-2xl border border-white/20 bg-black/30 px-2 py-1 text-right text-sm"
            />
            <span className="text-xs text-slate-400">BPM</span>
          </div>
        </label>
      </div>

      <BeatPadGrid tempo={padTempo} onHitsChange={handlePadHitsChange} />

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={handlePadTranslate}
          disabled={isPadTranslateDisabled}
          className="px-5 py-3 rounded-2xl bg-gradient-to-r from-purple-500 to-fuchsia-500 font-semibold tracking-wide disabled:opacity-30"
        >
          {padStatus === "sending" ? "Translating…" : "Translate Pad Groove"}
        </button>
        <span className="text-xs text-slate-400">{padHits.length} hits captured</span>
        {padStatus === "complete" && (
          <span className="text-emerald-400 text-xs uppercase tracking-widest">Synced</span>
        )}
      </div>

      {padError && (
        <div className="rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">{padError}</div>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-black via-slate-950 to-black text-slate-100">
      <div className="relative max-w-6xl mx-auto py-12 px-4 space-y-10">
        <div className="absolute inset-0 -z-10 opacity-60 blur-3xl" aria-hidden>
          <div className="mx-auto mt-10 h-64 max-w-3xl rounded-full bg-gradient-to-r from-purple-600/40 via-amber-500/30 to-fuchsia-500/40" />
        </div>

        <header className="rounded-3xl border border-white/10 bg-gradient-to-r from-purple-900/70 via-indigo-900/40 to-slate-900/60 p-8 shadow-2xl">
          <p className="text-xs uppercase tracking-[0.4em] text-purple-200">Beat Sketch</p>
          <h1 className="mt-3 text-4xl font-bold text-white">Sketch a Beat the DrumTracKAI Way</h1>
          <p className="mt-3 max-w-3xl text-slate-200">
            Capture a groovy idea with your voice or tap the neon pads. DrumTracKAI aligns the feel, enriches it with
            Jamstix personas, and hands you a sophisticated beat that mirrors the landing-page energy.
          </p>
          <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/30 px-4 py-2 text-xs uppercase tracking-widest text-slate-200">
            {entryIntentCopy[entryIntent]}
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-6 shadow-xl space-y-6">
            <div className="inline-flex rounded-full border border-white/15 bg-black/40 p-1 text-xs font-semibold tracking-wide">
              {(["mic", "pads"] as CaptureMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setCaptureMode(mode)}
                  className={`px-4 py-2 rounded-full transition ${
                    captureMode === mode
                      ? "bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white"
                      : "text-slate-400"
                  }`}
                >
                  {mode === "mic" ? "Microphone" : "Beat Pads"}
                </button>
              ))}
            </div>

            {captureMode === "mic" ? renderMicPanel() : renderPadPanel()}
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-6 space-y-6">
            <h2 className="text-lg font-semibold text-white">Persona & Feel</h2>
            <p className="text-sm text-slate-300">Match the landing-page gradients with the right drummer brain.</p>
            <div className="space-y-3">
              <label className="block text-sm text-slate-200">
                Persona
                <select
                  value={personaId}
                  onChange={(e) => setPersonaId(e.target.value)}
                  className="mt-1 w-full rounded-2xl bg-black/40 border border-white/15 px-3 py-2"
                >
                  {personaPresets.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block text-sm text-slate-200">
                Style Pack
                <select
                  value={stylePack}
                  onChange={(e) => setStylePack(e.target.value)}
                  className="mt-1 w-full rounded-2xl bg-black/40 border border-white/15 px-3 py-2"
                >
                  {stylePacks.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.label}
                    </option>
                  ))}
                </select>
              </label>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <label className="block text-slate-200">
                  Swing
                  <input
                    type="number"
                    step="0.01"
                    min={0}
                    max={0.3}
                    value={swing}
                    onChange={(e) => setSwing(parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-2xl bg-black/40 border border-white/15 px-2 py-1"
                  />
                </label>
                <label className="block text-slate-200">
                  Quantization
                  <select
                    value={quantization}
                    onChange={(e) => setQuantization(e.target.value)}
                    className="mt-1 w-full rounded-2xl bg-black/40 border border-white/15 px-2 py-1"
                  >
                    <option value="1/8">1/8</option>
                    <option value="1/12">1/12</option>
                    <option value="1/16">1/16</option>
                    <option value="1/32">1/32</option>
                  </select>
                </label>
                <label className="block text-slate-200 col-span-2">
                  Confidence Threshold
                  <input
                    type="number"
                    step="0.05"
                    min={0.1}
                    max={0.9}
                    value={confidenceThreshold}
                    onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value) || 0.35)}
                    className="mt-1 w-full rounded-2xl bg-black/40 border border-white/15 px-2 py-1"
                  />
                </label>
              </div>
            </div>
          </div>
        </section>

        {translation && (
          <section className="rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900/80 via-black/80 to-purple-950/60 p-6 space-y-4 shadow-2xl">
            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-200">
              <span>
                Tempo: <strong>{translation.tempo.toFixed(1)} BPM</strong>
              </span>
              <span>
                Hits detected: <strong>{translation.hits.length}</strong>
              </span>
              {translation.summary && (
                <span>
                  {Object.entries(translation.summary)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ")}
                </span>
              )}
              {midiHref && (
                <a
                  href={midiHref}
                  download={`beatbox-${uploadInfo?.file_id || "translation"}.mid`}
                  className="text-sky-300 underline"
                >
                  Download MIDI
                </a>
              )}
            </div>

            <div className="max-h-64 overflow-auto rounded-2xl border border-white/10 bg-black/30 text-sm">
              <table className="w-full text-left">
                <thead className="bg-white/5 text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Hit</th>
                    <th className="px-3 py-2">Beat</th>
                    <th className="px-3 py-2">Time (s)</th>
                    <th className="px-3 py-2">Velocity</th>
                    <th className="px-3 py-2">Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {translation.hits.map((hit, idx) => (
                    <tr key={`${hit.instrument}-${idx}`} className="odd:bg-white/5">
                      <td className="px-3 py-2 capitalize">{hit.instrument}</td>
                      <td className="px-3 py-2">{hit.beat_position.toFixed(3)}</td>
                      <td className="px-3 py-2">{hit.time.toFixed(3)}</td>
                      <td className="px-3 py-2">{hit.velocity}</td>
                      <td className="px-3 py-2">{hit.confidence.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
