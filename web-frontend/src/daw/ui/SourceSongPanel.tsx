import React, { useRef, useState } from "react";
import { webdawApi } from "../../services/api";

interface SourceSongPanelProps {
  onSongLoaded?: (payload: { key: string; durationSec: number; peaks?: number[] }) => void;
}

export const SourceSongPanel: React.FC<SourceSongPanelProps> = ({ onSongLoaded }) => {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  async function handleFile(file: File) {
    setBusy(true);
    setErr(null);
    try {
      const { key, waveform } = await webdawApi.fullWorkflow(file);
      const anyWf: any = waveform;
      const seconds = anyWf.duration ?? Math.max(1, (anyWf.peaks?.length || 0) / 44_100);
      setFileName(file.name);
      onSongLoaded?.({ key, durationSec: seconds, peaks: anyWf.peaks });
    } catch (e: any) {
      setErr(e?.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) {
      void handleFile(f);
      e.currentTarget.value = "";
    }
  }

  function onDrop(ev: React.DragEvent<HTMLDivElement>) {
    ev.preventDefault();
    const f = ev.dataTransfer.files?.[0];
    if (f) void handleFile(f);
  }

  return (
    <div className="space-y-2 p-2 bg-neutral-900 rounded border border-neutral-800">
      <div className="text-xs font-semibold text-neutral-200">Source Song</div>
      <div
        className="flex flex-col items-center justify-center border border-dashed border-neutral-700 rounded bg-neutral-950/60 py-6 text-xs text-neutral-400 cursor-pointer hover:border-emerald-500 hover:text-neutral-200 transition-colors"
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
      >
        {busy ? (
          <span>Uploading &amp; analyzing…</span>
        ) : (
          <>
            <span>{fileName ?? "Click or drop an audio file (no drums)"}</span>
            <span className="mt-1 text-[10px] opacity-70">File is sent to backend for arrangement &amp; tempo analysis</span>
          </>
        )}
      </div>
      {err && <div className="text-[11px] text-rose-400">Error: {err}</div>}
      <input
        ref={fileRef}
        type="file"
        className="hidden"
        accept="audio/*"
        onChange={onFileChange}
      />
    </div>
  );
}
