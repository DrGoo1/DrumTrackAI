// frontend/src/audio/engine.ts
// Complete audio engine code

import * as Tone from "tone";

export type TrackHandle = {
  key: string;
  url: string;
  audioElement: HTMLAudioElement;
  source: MediaElementAudioSourceNode;
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
let monitoringInterval: NodeJS.Timeout | null = null;

export const Engine = {
  async ensureStarted() {
    if (started) return;
    // SKIP Tone.start() - we're not using Web Audio API
    // await Tone.start();
    console.log('⏭️ Skipping Tone.start() - using plain HTML5 Audio');
    started = true;
  },
  async setBpm(bpm: number) {
    await this.ensureStarted();
    Tone.Transport.bpm.value = bpm;
  },
  async loadOrGet(key: string, url: string): Promise<TrackHandle> {
    await this.ensureStarted();
    
    // CRITICAL: Check if player already exists - STOP DUPLICATES
    const ex = players.get(key);
    if (ex) {
      console.log(`♻️ Reusing existing player for: ${key}`);
      return ex;
    }
    
    console.log(`🆕 Creating NEW audio element for: ${key}`);

    // CRITICAL FIX: Use HTML5 Audio - SIMPLE AS POSSIBLE
    const audioElement = document.createElement('audio');
    audioElement.preload = "auto";
    audioElement.loop = false;
    audioElement.playbackRate = 1.0; // Ensure normal speed
    audioElement.preservesPitch = true; // Ensure no pitch shifting
    // @ts-ignore - Browser-specific properties
    audioElement.mozPreservesPitch = true; // Firefox
    // @ts-ignore - Browser-specific properties
    audioElement.webkitPreservesPitch = true; // Chrome
    audioElement.src = url;
    
    console.log('🎵 Loading audio from:', url);
    console.log('Audio element settings:', {
      volume: audioElement.volume,
      playbackRate: audioElement.playbackRate,
      muted: audioElement.muted,
      preservesPitch: audioElement.preservesPitch
    });
    
    // Wait for audio to be ready
    await new Promise<void>((resolve, reject) => {
      const onLoad = () => {
        console.log('✅ Audio element loaded successfully');
        audioElement.removeEventListener('loadeddata', onLoad);
        audioElement.removeEventListener('error', onError);
        resolve();
      };
      const onError = (e: any) => {
        console.error('❌ Audio element error:', e);
        console.error('Error details:', {
          error: audioElement.error,
          errorCode: audioElement.error?.code,
          networkState: audioElement.networkState,
          readyState: audioElement.readyState,
          src: audioElement.src
        });
        audioElement.removeEventListener('loadeddata', onLoad);
        audioElement.removeEventListener('error', onError);
        reject(new Error(`Audio load failed: ${audioElement.error?.message || 'Unknown error'}`));
      };
      
      audioElement.addEventListener('loadeddata', onLoad);
      audioElement.addEventListener('error', onError);
    });
    
    // SIMPLE APPROACH: Just use audio element directly
    // NO MediaElementSource, NO Web Audio API complications
    audioElement.volume = 0.5; // Reasonable volume (50%)
    
    // Create dummy objects for compatibility
    const gain = new Tone.Gain(1.0); // Not actually used
    // @ts-ignore - Create a fake meter
    const meter = { getValue: () => -60 };
    const source = null; // No source node needed
    
    console.log(`✅ Audio element ready for: ${key} (volume: 0.1)`);

    const h: TrackHandle = { key, url, audioElement, source, gain, meter, muted: false, solo: false };
    players.set(key, h);
    console.log(`📊 Total players in memory: ${players.size}`);
    return h;
  },
  async refreshTracks(tracks: { key: string; url: string }[]) {
    await this.ensureStarted();
    
    console.log('🔄 refreshTracks called with:', tracks.map(t => t.key));
    console.log('📊 Current players:', Array.from(players.keys()));
    
    // Find tracks to remove (exist in players but not in new tracks list)
    const tracksToRemove = Array.from(players.keys()).filter(
      key => !tracks.find(t => t.key === key)
    );
    
    console.log('🗑️ Removing players:', tracksToRemove);
    
    // CRITICAL: Stop and dispose removed tracks properly
    for (const key of tracksToRemove) {
      const h = players.get(key);
      if (h) {
        console.log(`🛑 Stopping and removing: ${key}`);
        h.audioElement.pause();
        h.audioElement.currentTime = 0;
        h.audioElement.src = ''; // Clear source
        h.audioElement.load(); // Reset element
        h.audioElement.remove(); // Remove from DOM if attached
        players.delete(key);
      }
    }
    
    // Load new tracks (loadOrGet will skip if already exists)
    for (const t of tracks) {
      await this.loadOrGet(t.key, t.url);
    }
  },
  async play(atSeconds?: number) {
    await this.ensureStarted();
    if (typeof atSeconds === "number") Tone.Transport.seconds = atSeconds;
    
    // CRITICAL: First STOP all audio to prevent overlaps
    console.log('⏹️ Stopping all audio before play');
    for (const h of Array.from(players.values())) {
      h.audioElement.pause();
    }
    
    // Small delay to ensure stop is processed
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // Manually start all audio elements
    const currentTime = typeof atSeconds === "number" ? atSeconds : 0;
    console.log(`▶️ Starting ${players.size} audio tracks at ${currentTime.toFixed(2)}s`);
    
    for (const h of Array.from(players.values())) {
      h.audioElement.currentTime = currentTime;
      h.audioElement.volume = 0.5; // Ensure volume is correct (50%)
      const playPromise = h.audioElement.play();
      if (playPromise) {
        playPromise
          .then(() => console.log(`✅ Playing: ${h.key} at volume ${h.audioElement.volume}`))
          .catch(e => console.error('❌ Play failed:', h.key, e));
      }
    }
    
    // DON'T start Transport - not needed for plain HTML5 audio
    // Tone.Transport.start();
  },
  async pause() {
    await this.ensureStarted();
    
    // Pause all audio elements
    for (const h of Array.from(players.values())) {
      h.audioElement.pause();
    }
    
    // Tone.Transport.pause();
  },
  async stop() {
    await this.ensureStarted();
    
    // Stop all audio elements
    for (const h of Array.from(players.values())) {
      h.audioElement.pause();
      h.audioElement.currentTime = 0;
    }
    
    // Tone.Transport.stop();
  },
  async seek(seconds: number) {
    await this.ensureStarted();
    
    // Seek all audio elements
    for (const h of Array.from(players.values())) {
      h.audioElement.currentTime = seconds;
    }
    
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
      
      // Set gain level (0.3 is safe for HTML5 Audio)
      h.gain.gain.value = shouldMute ? 0 : 0.3;
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
