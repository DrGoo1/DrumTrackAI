// Minimal mixer that pulls float32 frames from a SAB ring buffer.
// Message protocol: { type: 'init', sab, channels, blockSize }

class RingBuffer {
  constructor(sab) {
    this._sab = sab;
    this._i32 = new Int32Array(sab, 0, 2); // head, tail in frames
    this._buf = new Float32Array(sab, 8);  // data after 8 bytes
  }
  // pop into target (Float32Array)
  pop(frames, target) {
    const channels = 1; // interleaving handled by host if needed
    const head = Atomics.load(this._i32, 0);
    const tail = Atomics.load(this._i32, 1);
    const available = head - tail;
    const needed = frames * channels;
    const take = Math.min(available, needed);
    if (take <= 0) return 0;
    const start = tail % this._buf.length;
    const end = (start + take) % this._buf.length;
    if (start < end) {
      target.set(this._buf.subarray(start, start + take), 0);
    } else {
      const part1 = this._buf.length - start;
      target.set(this._buf.subarray(start), 0);
      target.set(this._buf.subarray(0, end), part1);
    }
    Atomics.store(this._i32, 1, tail + take);
    return take;
  }
}

class EngineProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.blockSize = 128; // render quantum
    this._rb = null;
    this._tmp = null;
    this._underruns = 0;
    this.port.onmessage = (e) => {
      const msg = e.data;
      if (msg?.type === "init") {
        this._rb = new RingBuffer(msg.sab);
        this.blockSize = msg.blockSize ?? 128;
        this._tmp = new Float32Array(this.blockSize);
      }
    };
    this._lastTime = currentTime;
  }

  process(inputs, outputs /*, parameters */) {
    if (!this._rb || !this._tmp) return true;
    const out = outputs[0];
    const ch0 = out[0];
    const n = ch0.length; // usually 128

    const taken = this._rb.pop(n, this._tmp);
    if (taken < n) {
      // zero-fill remainder
      for (let i = taken; i < n; i++) this._tmp[i] = 0;
      this._underruns++;
      if ((this._underruns & 0x0f) === 0) {
        this.port.postMessage({ type: "underrun", count: this._underruns });
      }
    }

    // copy mono -> all output channels
    for (let c = 0; c < out.length; c++) {
      out[c].set(this._tmp);
    }

    // crude render latency estimate
    const dt = (currentTime - this._lastTime) * 1000;
    this._lastTime = currentTime;
    if ((Math.random() * 8) < 1) {
      this.port.postMessage({ type: "latency", ms: dt });
    }
    return true;
  }
}

registerProcessor("engine-processor", EngineProcessor);
