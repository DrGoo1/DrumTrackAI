import { useEngineStore } from "../../state/useEngineStore";
import { features } from "../../config/features";

import { getSharedAudioContext } from "../sharedAudioContext";

export class AudioEngine {
  private ctx: AudioContext | null = null;
  private node: AudioWorkletNode | null = null;
  private sab: SharedArrayBuffer | null = null;
  private i32: Int32Array | null = null;
  private f32: Float32Array | null = null;

  // simple ring buffer helpers
  private capacityFrames = 48000; // ~1s @ 48k mono
  private blockSize = 128;

  async init() {
    if (this.ctx) return;
    this.ctx = getSharedAudioContext({ latencyHint: "interactive" });
    // Load worklet
    await this.ctx.audioWorklet.addModule("/worklet/engine-processor.js");
    this.node = new AudioWorkletNode(this.ctx, "engine-processor", { numberOfOutputs: 1, outputChannelCount: [2] });

    // SAB needs cross-origin isolation (COOP/COEP set via dev server/proxy)
    const bytes = 8 + Float32Array.BYTES_PER_ELEMENT * this.capacityFrames;
    this.sab = new SharedArrayBuffer(bytes);
    this.i32 = new Int32Array(this.sab, 0, 2);
    this.f32 = new Float32Array(this.sab, 8);

    this.node.port.onmessage = (e) => {
      const { type, count, ms } = e.data || {};
      if (type === "underrun") useEngineStore.getState().setUnderruns(count);
      if (type === "latency") useEngineStore.getState().setRenderLatencyMs(ms);
    };

    this.node.port.postMessage({ type: "init", sab: this.sab, channels: 2, blockSize: this.blockSize });
    this.node.connect(this.ctx.destination);
  }

  async resume() { await this.ctx?.resume(); }
  async suspend() { await this.ctx?.suspend(); }

  /** Push mono frames into the ring buffer (interleaving handled elsewhere) */
  pushFrames(frames: Float32Array) {
    if (!this.sab || !this.i32 || !this.f32) return;
    const head = Atomics.load(this.i32, 0);
    const tail = Atomics.load(this.i32, 1);
    const free = this.f32.length - (head - tail);
    if (free < frames.length) {
      // drop oldest to keep up
      Atomics.store(this.i32, 1, head - (this.f32.length - frames.length));
    }
    const start = head % this.f32.length;
    const end = (start + frames.length) % this.f32.length;
    if (start < end) {
      this.f32.set(frames, start);
    } else {
      const part1 = this.f32.length - start;
      this.f32.set(frames.subarray(0, part1), start);
      this.f32.set(frames.subarray(part1), 0);
    }
    Atomics.store(this.i32, 0, head + frames.length);
  }

  /** Host-side look-ahead scheduler; call on a 25ms interval */
  scheduleLoop(getBlock: (t0: number, t1: number, sampleRate: number) => Float32Array | null) {
    if (!this.ctx) return;
    const sr = this.ctx.sampleRate;
    const lookahead = 0.100; // 100ms
    const interval = 0.025;  // 25ms
    const tick = () => {
      if (!this.ctx) return;
      const tNow = this.ctx.currentTime;
      const t0 = tNow + 0.010;          // small safety
      const t1 = tNow + lookahead;
      const block = getBlock(t0, t1, sr);
      if (block) this.pushFrames(block);
      this._timer = setTimeout(tick, interval * 1000) as unknown as number;
    };
    this._timer && clearTimeout(this._timer);
    this._timer = setTimeout(tick, 0) as unknown as number;
  }

  private _timer: number | null = null;
  stopScheduler() { if (this._timer) { clearTimeout(this._timer); this._timer = null; } }
}
