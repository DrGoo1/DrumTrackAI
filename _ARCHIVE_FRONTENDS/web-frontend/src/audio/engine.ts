import * as Tone from "tone";

export type TrackHandle = {
  key: string;
  url: string;
  player: Tone.Player;
  gain: Tone.Gain;
  meter: any; // Tone.Meter typings vary across versions
  muted: boolean;
  solo: boolean;
};

let started = false;
let players: Map<string, TrackHandle> = new Map();
let loopEnabled = false;
let loopStart = 0;
let loopEnd = 0;

export const Engine = {
  async ensureStarted() {
    if (started) return;
    await Tone.start();
    // @ts-ignore - latencyHint may not exist in all Tone.js versions
    if (Tone.Transport.latencyHint) Tone.Transport.latencyHint = "playback";
    started = true;
  },
  async setBpm(bpm: number) {
    await this.ensureStarted();
    Tone.Transport.bpm.value = bpm;
  },
  async loadOrGet(key: string, url: string): Promise<TrackHandle> {
    await this.ensureStarted();
    const ex = players.get(key);
    if (ex) return ex;

    const player = new Tone.Player({ url, autostart: false });
    const gain = new Tone.Gain(1);
    // @ts-ignore Tone.Meter may not have types in your version
    const meter = new (Tone as any).Meter({ normalRange: true, smoothing: 0.8 });

    player.chain(gain, meter, Tone.getContext().destination);
    player.sync();
    player.start(0);

    const h: TrackHandle = { key, url, player, gain, meter, muted: false, solo: false };
    players.set(key, h);
    return h;
  },
  async refreshTracks(tracks: { key: string; url: string }[]) {
    await this.ensureStarted();
    for (const t of tracks) await this.loadOrGet(t.key, t.url);
    for (const k of Array.from(players.keys())) {
      if (!tracks.find((t) => t.key === k)) {
        const h = players.get(k)!;
        h.player.dispose(); h.gain.dispose();
        // @ts-ignore
        h.meter.dispose?.();
        players.delete(k);
      }
    }
  },
  async play(atSeconds?: number) {
    await this.ensureStarted();
    if (typeof atSeconds === "number") Tone.Transport.seconds = atSeconds;
    Tone.Transport.start();
  },
  async pause() {
    await this.ensureStarted();
    Tone.Transport.pause();
  },
  async stop() {
    await this.ensureStarted();
    Tone.Transport.stop();
  },
  async seek(seconds: number) {
    await this.ensureStarted();
    Tone.Transport.seconds = seconds;
  },
  async setLoop(start: number, end: number, enabled: boolean) {
    await this.ensureStarted();
    loopStart = Math.max(0, Math.min(start, end));
    loopEnd = Math.max(loopStart + 0.001, Math.max(start, end));
    loopEnabled = enabled;
    Tone.Transport.setLoopPoints(loopStart, loopEnd);
    Tone.Transport.loop = loopEnabled;
  },
  setGain(key: string, value: number) {
    const h = players.get(key); if (!h) return; h.gain.gain.value = value;
  },
  setMute(key: string, m: boolean) {
    const h = players.get(key); if (!h) return; 
    h.muted = m; 
    this.updateMixerState();
  },
  setSolo(key: string, s: boolean) {
    const h = players.get(key); if (!h) return; 
    h.solo = s;
    this.updateMixerState();
  },
  updateMixerState() {
    const playerArray = Array.from(players.values());
    const hasSolo = playerArray.some(h => h.solo);
    for (const h of playerArray) {
      let shouldMute = h.muted;
      if (hasSolo && !h.solo) shouldMute = true;
      
      // Use gain value for muting since mute property doesn't exist
      h.gain.gain.value = shouldMute ? 0 : 1;
    }
  },
  getMeter(key: string) {
    const h = players.get(key); if (!h) return 0; // 0..1
    // @ts-ignore
    const v = h.meter.getValue ? h.meter.getValue() : 0; return typeof v === "number" ? (isFinite(v) ? Math.max(0, Math.min(1, v)) : 0) : 0;
  },
  state() {
    return { started, loopEnabled, loopStart, loopEnd, bpm: Tone.Transport.bpm.value };
  },
};
