import { AudioEngine } from "./AudioEngine";
import { useTransportStore } from "../../state/useTransportStore";
import { features } from "../../config/features";

export const engine = new AudioEngine();

// Create workers using standard Web Worker constructor
const peaksWorker = new Worker(new URL("../workers/peaks.worker.ts", import.meta.url));
const decoderWorker = new Worker(new URL("../workers/decoder.worker.ts", import.meta.url));

export async function initEngine() {
  if (!features.realtimeWorklet) return;
  await engine.init();
}

// Example block provider that renders a mono buffer for [t0, t1)
export function startScheduler(getBlock: (t0: number, t1: number, sr: number) => Float32Array | null) {
  engine.scheduleLoop(getBlock);
}

export function stopScheduler() {
  engine.stopScheduler();
}

// Waveform tiles
export function buildPeaks(pcm: Float32Array, levels = [64, 512]): Promise<Record<string, { min: Float32Array; max: Float32Array }>> {
  return new Promise((resolve) => {
    const id = crypto.randomUUID();
    const onmessage = (e: MessageEvent<any>) => {
      if (e.data.id !== id) return;
      peaksWorker.removeEventListener("message", onmessage as any);
      resolve(e.data.tiles);
    };
    peaksWorker.addEventListener("message", onmessage as any);
    peaksWorker.postMessage({ id, pcm, levels });
  });
}
