import React from "react";
import { useEngineStore } from "../state/useEngineStore";
import { useTransportStore } from "../state/useTransportStore";

export function DebugPanel() {
  const { underruns, renderLatencyMs } = useEngineStore();
  const { bpm, currentTime, playing } = useTransportStore();
  return (
    <div style={{ position:"fixed", right:12, bottom:12, padding:10, background:"#111", color:"#eee", borderRadius:8, fontSize:12, opacity:0.9 }}>
      <div><b>Playing:</b> {String(playing)} | <b>BPM:</b> {bpm}</div>
      <div><b>t:</b> {currentTime.toFixed(2)}s</div>
      <div><b>Latency:</b> {renderLatencyMs.toFixed(2)} ms | <b>Underruns:</b> {underruns}</div>
    </div>
  );
}
