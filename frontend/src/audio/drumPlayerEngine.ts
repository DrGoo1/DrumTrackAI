import { getSharedAudioContext } from "./sharedAudioContext";

export type DrumPlayerChannelId =
  | "kick"
  | "kick_sub"
  | "snare_top"
  | "snare_bottom"
  | "tom1"
  | "tom2"
  | "tom3"
  | "tom4"
  | "tom5"
  | "tom_fx"
  | "hat"
  | "ride"
  | "spot_ride"
  | "crash";

export type DrumPlayerBusId = "oh" | "room";

export type DrumPlayerChannelParams = {
  gain: number; // 0..1.5
  pan: number; // -1..1
  mute: boolean;
  solo: boolean;
  sendOh: number; // 0..1
  sendRoom: number; // 0..1
};

type ChannelState = {
  buffer: AudioBuffer | null;
  params: DrumPlayerChannelParams;
  gainNode: GainNode;
  panNode: StereoPannerNode;
  sendOhNode: GainNode;
  sendRoomNode: GainNode;
  analyser: AnalyserNode;
  activeSources: Set<AudioBufferSourceNode>;
};

export class DrumPlayerEngine {
  private ctx: AudioContext;
  private masterGain: GainNode;
  private ohBusGain: GainNode;
  private roomBusGain: GainNode;
  private analyser: AnalyserNode;
  private ohAnalyser: AnalyserNode;
  private roomAnalyser: AnalyserNode;

  private resumeHookInstalled = false;

  private channels: Map<DrumPlayerChannelId, ChannelState> = new Map();

  constructor(opts?: { latencyHint?: AudioContextLatencyCategory | number }) {
    const latencyHint = opts?.latencyHint ?? "interactive";
    this.ctx = getSharedAudioContext({ latencyHint });

    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = 1;

    this.ohBusGain = this.ctx.createGain();
    this.ohBusGain.gain.value = 1;

    this.roomBusGain = this.ctx.createGain();
    this.roomBusGain.gain.value = 1;

    this.ohAnalyser = this.ctx.createAnalyser();
    this.ohAnalyser.fftSize = 2048;

    this.roomAnalyser = this.ctx.createAnalyser();
    this.roomAnalyser.fftSize = 2048;

    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 2048;

    // Mix buses into master (via analyser taps)
    this.ohBusGain.connect(this.ohAnalyser);
    this.ohAnalyser.connect(this.masterGain);

    this.roomBusGain.connect(this.roomAnalyser);
    this.roomAnalyser.connect(this.masterGain);

    // Master -> analyser -> destination
    this.masterGain.connect(this.analyser);
    this.analyser.connect(this.ctx.destination);

    this.installResumeHook();
  }

  get audioContext() {
    return this.ctx;
  }

  private installResumeHook() {
    if (this.resumeHookInstalled) return;
    this.resumeHookInstalled = true;

    const attempt = async () => {
      try {
        if (this.ctx.state === "suspended") {
          await this.ctx.resume();
        }
      } catch {
        // ignore
      }
      if (this.ctx.state !== "suspended") {
        try {
          window.removeEventListener("pointerdown", onGesture, true);
          window.removeEventListener("touchstart", onGesture, true);
          window.removeEventListener("keydown", onGesture, true);
        } catch {
          // ignore
        }
      }
    };

    const onGesture = () => {
      void attempt();
    };

    try {
      window.addEventListener("pointerdown", onGesture, true);
      window.addEventListener("touchstart", onGesture, true);
      window.addEventListener("keydown", onGesture, true);
    } catch {
      // ignore
    }
  }

  async ensureRunning() {
    if (this.ctx.state !== "suspended") return;
    this.installResumeHook();
    try {
      await this.ctx.resume();
    } catch (e) {
      // keep hook installed; caller may retry after a gesture
      throw e;
    }
    if (this.ctx.state === "suspended") {
      throw new Error("AudioContext is not running. Click anywhere in the page, then try Play again.");
    }
  }

  close() {
    // Intentionally does NOT close the shared AudioContext.
    // The shared context is owned by the app and is reused across subsystems.
  }

  private ensureChannel(id: DrumPlayerChannelId): ChannelState {
    const existing = this.channels.get(id);
    if (existing) return existing;

    const gainNode = this.ctx.createGain();
    gainNode.gain.value = 1;

    const panNode = this.ctx.createStereoPanner();
    panNode.pan.value = 0;

    const sendOhNode = this.ctx.createGain();
    sendOhNode.gain.value = 0;

    const sendRoomNode = this.ctx.createGain();
    sendRoomNode.gain.value = 0;

    const analyser = this.ctx.createAnalyser();
    analyser.fftSize = 2048;

    // channel main -> pan -> master
    gainNode.connect(panNode);
    panNode.connect(this.masterGain);

    panNode.connect(analyser);

    // pre-pan sends (classic DAW is often post-fader; we do post-fader, pre-pan)
    gainNode.connect(sendOhNode);
    gainNode.connect(sendRoomNode);

    sendOhNode.connect(this.ohBusGain);
    sendRoomNode.connect(this.roomBusGain);

    const state: ChannelState = {
      buffer: null,
      params: {
        gain: 1,
        pan: 0,
        mute: false,
        solo: false,
        sendOh: 0,
        sendRoom: 0,
      },
      gainNode,
      panNode,
      sendOhNode,
      sendRoomNode,
      analyser,
      activeSources: new Set(),
    };

    this.channels.set(id, state);
    return state;
  }

  stopChannel(id: DrumPlayerChannelId) {
    const ch = this.ensureChannel(id);
    for (const src of Array.from(ch.activeSources)) {
      try {
        src.stop();
      } catch {
        // ignore
      }
    }
    ch.activeSources.clear();
  }

  stopAll() {
    for (const id of Array.from(this.channels.keys())) {
      this.stopChannel(id);
    }
  }

  setMasterGain(value: number) {
    this.masterGain.gain.value = Math.max(0, Math.min(1.5, value));
  }

  setBusGain(bus: DrumPlayerBusId, value: number) {
    const v = Math.max(0, Math.min(1.5, value));
    if (bus === "oh") this.ohBusGain.gain.value = v;
    if (bus === "room") this.roomBusGain.gain.value = v;
  }

  setChannelParams(id: DrumPlayerChannelId, updates: Partial<DrumPlayerChannelParams>) {
    const ch = this.ensureChannel(id);
    ch.params = { ...ch.params, ...updates };

    ch.gainNode.gain.value = Math.max(0, Math.min(1.5, ch.params.gain));
    ch.panNode.pan.value = Math.max(-1, Math.min(1, ch.params.pan));

    ch.sendOhNode.gain.value = Math.max(0, Math.min(1, ch.params.sendOh));
    ch.sendRoomNode.gain.value = Math.max(0, Math.min(1, ch.params.sendRoom));

    this.applyMuteSolo();
  }

  getChannelParams(id: DrumPlayerChannelId): DrumPlayerChannelParams {
    const ch = this.ensureChannel(id);
    return { ...ch.params };
  }

  private applyMuteSolo() {
    const channelStates = Array.from(this.channels.values());
    const hasSolo = channelStates.some((c) => c.params.solo);

    for (const ch of channelStates) {
      const shouldMute = ch.params.mute || (hasSolo && !ch.params.solo);
      // post-fader mute (simple): set gainNode to 0 but preserve slider value in params
      ch.gainNode.gain.value = shouldMute ? 0 : Math.max(0, Math.min(1.5, ch.params.gain));
    }
  }

  async loadSampleForChannel(id: DrumPlayerChannelId, audioUrl: string) {
    await this.ensureRunning();

    const res = await fetch(audioUrl);
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`Failed to load audio: ${res.status} ${res.statusText} ${txt}`);
    }

    const arr = await res.arrayBuffer();
    const buffer = await this.ctx.decodeAudioData(arr.slice(0));

    const ch = this.ensureChannel(id);
    ch.buffer = buffer;
  }

  playChannelOneShot(id: DrumPlayerChannelId, opts?: { whenSec?: number; gain?: number }) {
    // Some browsers require a user gesture to start audio. If samples were preloaded before a
    // gesture, the AudioContext can remain suspended and playback will be silent.
    // Resume opportunistically on play.
    try {
      if (this.ctx.state === "suspended") {
        void this.ctx.resume();
      }
    } catch {
      // ignore
    }

    const ch = this.ensureChannel(id);
    if (!ch.buffer) return;

    const src = this.ctx.createBufferSource();
    src.buffer = ch.buffer;

    const oneShotGain = this.ctx.createGain();
    oneShotGain.gain.value = typeof opts?.gain === "number" ? Math.max(0, Math.min(2, opts.gain)) : 1;

    src.connect(oneShotGain);
    oneShotGain.connect(ch.gainNode);

    ch.activeSources.add(src);
    src.onended = () => {
      ch.activeSources.delete(src);
      try {
        oneShotGain.disconnect();
      } catch {
        // ignore
      }
      try {
        src.disconnect();
      } catch {
        // ignore
      }
    };

    const when = typeof opts?.whenSec === "number" ? opts.whenSec : this.ctx.currentTime;
    src.start(when);
  }

  getMasterLevel01(): number {
    return this.analyserToLevel01(this.analyser);
  }

  private analyserToLevel01(analyser: AnalyserNode): number {
    const data = new Float32Array(analyser.fftSize);
    analyser.getFloatTimeDomainData(data);

    let sum = 0;
    let peak = 0;
    for (let i = 0; i < data.length; i++) {
      const v = data[i];
      sum += v * v;
      const a = Math.abs(v);
      if (a > peak) peak = a;
    }
    const rms = Math.sqrt(sum / data.length);

    // Make meters feel more responsive for transient material.
    // (We intentionally compress the dynamic range, but with higher sensitivity.)
    const combined = Math.max(rms * 4.5, peak * 2.2);
    const boosted = 1 - Math.exp(-combined * 3.4);
    return Math.max(0, Math.min(1, boosted));
  }

  getChannelLevel01(id: DrumPlayerChannelId): number {
    const ch = this.ensureChannel(id);
    return this.analyserToLevel01(ch.analyser);
  }

  getBusLevel01(bus: DrumPlayerBusId): number {
    return this.analyserToLevel01(bus === "oh" ? this.ohAnalyser : this.roomAnalyser);
  }
}

declare global {
  // eslint-disable-next-line no-var
  var __dtk_sharedDrumEngine: DrumPlayerEngine | undefined;
}

export function getSharedDrumPlayerEngine() {
  if (!globalThis.__dtk_sharedDrumEngine) {
    globalThis.__dtk_sharedDrumEngine = new DrumPlayerEngine({ latencyHint: "interactive" });
  }
  return globalThis.__dtk_sharedDrumEngine;
}
