// import * as Tone from "tone"; // DISABLED - using plain HTML5 Audio only

export type TrackHandle = {
  key: string;
  url: string;
  audioElement: HTMLAudioElement;
  source: MediaElementAudioSourceNode | null;
  gain: any; // Plain object, not Tone.Gain - prevents hidden Tone.js routing
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

// CRITICAL: Global lock to prevent React StrictMode double-mounting from creating duplicates
let globalAudioCreationLock = new Set<string>();

export const Engine = {
  async ensureStarted() {
    if (started) return;
    
    // CRITICAL: Clean up any ghost audio elements from StrictMode double-mounting
    const ghostAudios = document.querySelectorAll('audio');
    if (ghostAudios.length > 0) {
      console.warn(`🧹 Cleaning up ${ghostAudios.length} ghost audio elements`);
      ghostAudios.forEach(a => {
        a.pause();
        a.src = '';
        a.remove();
      });
    }
    
    // SKIP Tone.start() - we're not using Web Audio API
    // await Tone.start();
    console.log('⏭️ Skipping Tone.start() - using plain HTML5 Audio');
    started = true;
  },
  async setBpm(bpm: number) {
    await this.ensureStarted();
    // BPM not used without Tone.Transport
  },
  async loadOrGet(key: string, url: string): Promise<TrackHandle> {
    await this.ensureStarted();
    
    // CRITICAL: Global lock prevents StrictMode double-mounting duplicates
    if (globalAudioCreationLock.has(key)) {
      console.warn(`🚫 BLOCKED duplicate creation (StrictMode): ${key}`);
      const ex = players.get(key);
      if (ex) return ex;
      // If no player exists yet, wait briefly for it to be created
      await new Promise(resolve => setTimeout(resolve, 100));
      return players.get(key) || await this.loadOrGet(key, url);
    }
    
    // CRITICAL: Check if player already exists - STOP DUPLICATES
    const ex = players.get(key);
    if (ex) {
      console.log(`♻️ Reusing existing player for: ${key}`);
      return ex;
    }
    
    // Acquire lock BEFORE creating
    globalAudioCreationLock.add(key);
    console.log(`🆕 Creating NEW audio element for: ${key}`);

    // CRITICAL: Use EXACT same method as MinimalAudioTest (which works!)
    const audioElement = new Audio(url);
    audioElement.volume = 0.5;
    audioElement.preload = "auto";
    
    console.log('🎵 Loading audio from:', url);
    console.log('Audio element settings:', {
      volume: audioElement.volume,
      playbackRate: audioElement.playbackRate,
      muted: audioElement.muted
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
        audioElement.removeEventListener('loadeddata', onLoad);
        audioElement.removeEventListener('error', onError);
        reject(new Error(`Audio load failed`));
      };
      
      audioElement.addEventListener('loadeddata', onLoad);
      audioElement.addEventListener('error', onError);
    });
    
    // Create dummy objects for compatibility
    // @ts-ignore
    const gain = { gain: { value: 0.5 } };
    // @ts-ignore
    const meter = { getValue: () => -60 };
    const source = null;
    
    console.log(`✅ Audio element ready for: ${key} (volume: ${audioElement.volume})`);

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
    // Transport not used
    
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
  getCurrentTimeSeconds() {
    // Use any existing player as the time source.
    // This is the authoritative clock for DCSM playback while HTML5 audio is running.
    const first = Array.from(players.values())[0];
    if (!first || !first.audioElement) return 0;
    const t = first.audioElement.currentTime;
    return typeof t === "number" && Number.isFinite(t) ? t : 0;
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
    
    // Transport.seconds not used
  },
  async setLoop(start: number, end: number, enabled: boolean) {
    await this.ensureStarted();
    loopStart = Math.max(0, Math.min(start, end));
    loopEnd = Math.max(loopStart + 0.001, Math.max(start, end));
    loopEnabled = enabled;
    // Transport loop not used with plain HTML5 audio
  },
  setGain(key: string, value: number) {
    const h = players.get(key); if (!h) return; 
    h.audioElement.volume = value; // Use audio element directly
    h.gain.gain.value = value; // Update dummy for compatibility
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
      
      // CRITICAL: Set volume on audio element directly, not Tone.Gain
      h.audioElement.volume = shouldMute ? 0 : 0.5;
      h.gain.gain.value = shouldMute ? 0 : 0.5; // Update dummy for compatibility
    }
  },
  getMeter(key: string) {
    const h = players.get(key); if (!h) return 0; // 0..1
    // @ts-ignore
    const v = h.meter.getValue ? h.meter.getValue() : 0; return typeof v === "number" ? (isFinite(v) ? Math.max(0, Math.min(1, v)) : 0) : 0;
  },
  state() {
    return { started, loopEnabled, loopStart, loopEnd, bpm: 120 };
  },
};
