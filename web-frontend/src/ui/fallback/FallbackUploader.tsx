import React, { useState } from "react";
import { uploadFileSmart, fetchWaveform } from "../../api/files";

export default function FallbackUploader() {
  const [busy, setBusy] = useState(false);
  const [pct, setPct] = useState(0);

  async function onPick(file: File) {
    setBusy(true);
    setPct(0);
    const key = `uploads/${Date.now()}-${file.name}`;
    try {
      await uploadFileSmart(file, key, (p) => setPct(Math.round(p * 100)));
      const wf = await fetchWaveform(key);
      window.dispatchEvent(new CustomEvent("wf:loaded", { detail: { key, wf } }));
      console.log("[Fallback] waveform fetched", wf?.peaks?.length);
    } catch (e: any) {
      console.error("[Fallback] upload/fetch failed:", e?.message || e);
      alert("Upload/waveform failed. See console.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="h-[260px] bg-slate-900 border border-slate-800 rounded-lg p-6 flex items-center justify-center gap-3">
      <label className="cursor-pointer px-3 py-2 rounded bg-emerald-600 text-white">
        {busy ? `Uploading… ${pct}%` : "Import audio"}
        <input
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onPick(f);
          }}
        />
      </label>
      <span className="text-slate-400 text-sm">Fallback timeline</span>
    </div>
  );
}
