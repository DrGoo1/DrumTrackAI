// Professional Web Audio Engine for DrumTracKAI DAW
class AudioEngine {
  constructor() {
    this.audioContext = null;
    this.tracks = new Map();
    this.masterGain = null;
    this.isInitialized = false;
    this.currentTime = 0;
    this.isPlaying = false;
    this.tempo = 120;
    this.timeSignature = [4, 4];
    this.sampleRate = 44100;
    
    // Audio processing nodes
    this.masterLimiter = null;
    this.masterEQ = null;
    this.analysers = new Map();
    
    // Playback state
    this.playbackStartTime = 0;
    this.pausedAt = 0;
    this.loopRegion = null;
    
    this.initialize();
  }

  async initialize() {
    try {
      // Create audio context with optimal settings
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: this.sampleRate,
        latencyHint: 'interactive'
      });

      // Create master gain node
      this.masterGain = this.audioContext.createGain();
      this.masterGain.gain.value = 0.8; // -2dB headroom

      // Create master limiter (simple compressor)
      this.masterLimiter = this.audioContext.createDynamicsCompressor();
      this.masterLimiter.threshold.value = -6;
      this.masterLimiter.knee.value = 5;
      this.masterLimiter.ratio.value = 10;
      this.masterLimiter.attack.value = 0.003;
      this.masterLimiter.release.value = 0.1;

      // Create master EQ (3-band)
      this.masterEQ = {
        low: this.audioContext.createBiquadFilter(),
        mid: this.audioContext.createBiquadFilter(),
        high: this.audioContext.createBiquadFilter()
      };

      this.masterEQ.low.type = 'lowshelf';
      this.masterEQ.low.frequency.value = 320;
      this.masterEQ.mid.type = 'peaking';
      this.masterEQ.mid.frequency.value = 1000;
      this.masterEQ.mid.Q.value = 0.5;
      this.masterEQ.high.type = 'highshelf';
      this.masterEQ.high.frequency.value = 3200;

      // Connect master chain
      this.masterGain
        .connect(this.masterEQ.low)
        .connect(this.masterEQ.mid)
        .connect(this.masterEQ.high)
        .connect(this.masterLimiter)
        .connect(this.audioContext.destination);

      this.isInitialized = true;
      console.log('AudioEngine initialized successfully');
    } catch (error) {
      console.error('Failed to initialize AudioEngine:', error);
    }
  }

  // Load audio file and create track
  async loadTrack(trackId, audioFile, trackName = 'Track') {
    if (!this.isInitialized) {
      await this.initialize();
    }

    try {
      let audioBuffer;
      
      if (audioFile instanceof File) {
        // Load from file
        const arrayBuffer = await audioFile.arrayBuffer();
        audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      } else if (typeof audioFile === 'string') {
        // Load from URL
        const response = await fetch(audioFile);
        const arrayBuffer = await response.arrayBuffer();
        audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      } else if (audioFile instanceof AudioBuffer) {
        // Already decoded
        audioBuffer = audioFile;
      } else {
        throw new Error('Invalid audio file format');
      }

      // Create track object
      const track = {
        id: trackId,
        name: trackName,
        buffer: audioBuffer,
        source: null,
        gainNode: this.audioContext.createGain(),
        panNode: this.audioContext.createStereoPanner(),
        analyser: this.audioContext.createAnalyser(),
        eqNodes: this.createTrackEQ(),
        isPlaying: false,
        isMuted: false,
        isSoloed: false,
        volume: 0.75,
        pan: 0,
        startTime: 0,
        duration: audioBuffer.duration,
        regions: [] // For cut/paste functionality
      };

      // Configure analyser
      track.analyser.fftSize = 2048;
      track.analyser.smoothingTimeConstant = 0.8;

      // Connect track audio chain
      track.gainNode
        .connect(track.eqNodes.low)
        .connect(track.eqNodes.mid)
        .connect(track.eqNodes.high)
        .connect(track.panNode)
        .connect(track.analyser)
        .connect(this.masterGain);

      // Store track
      this.tracks.set(trackId, track);
      this.analysers.set(trackId, track.analyser);

      console.log(`Track loaded: ${trackName} (${audioBuffer.duration.toFixed(2)}s)`);
      return track;
    } catch (error) {
      console.error(`Failed to load track ${trackId}:`, error);
      throw error;
    }
  }

  // Create 3-band EQ for track
  createTrackEQ() {
    const eq = {
      low: this.audioContext.createBiquadFilter(),
      mid: this.audioContext.createBiquadFilter(),
      high: this.audioContext.createBiquadFilter()
    };

    eq.low.type = 'lowshelf';
    eq.low.frequency.value = 320;
    eq.low.gain.value = 0;

    eq.mid.type = 'peaking';
    eq.mid.frequency.value = 1000;
    eq.mid.Q.value = 0.5;
    eq.mid.gain.value = 0;

    eq.high.type = 'highshelf';
    eq.high.frequency.value = 3200;
    eq.high.gain.value = 0;

    return eq;
  }

  // Generate waveform data for visualization
  generateWaveformData(audioBuffer, width = 1000) {
    const channelData = audioBuffer.getChannelData(0);
    const samplesPerPixel = Math.floor(channelData.length / width);
    const waveformData = [];

    for (let i = 0; i < width; i++) {
      const start = i * samplesPerPixel;
      const end = start + samplesPerPixel;
      let min = 0;
      let max = 0;

      for (let j = start; j < end && j < channelData.length; j++) {
        const sample = channelData[j];
        if (sample > max) max = sample;
        if (sample < min) min = sample;
      }

      waveformData.push({ min, max });
    }

    return waveformData;
  }

  // Transport controls
  async play(startTime = this.pausedAt) {
    if (!this.isInitialized || this.isPlaying) return;

    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    this.playbackStartTime = this.audioContext.currentTime - startTime;
    this.isPlaying = true;

    // Start all tracks
    for (const [trackId, track] of this.tracks) {
      if (!track.isMuted && track.buffer) {
        this.startTrack(trackId, startTime);
      }
    }

    // Start time update loop
    this.updateTimeLoop();
  }

  pause() {
    if (!this.isPlaying) return;

    this.isPlaying = false;
    this.pausedAt = this.audioContext.currentTime - this.playbackStartTime;

    // Stop all tracks
    for (const [trackId, track] of this.tracks) {
      this.stopTrack(trackId);
    }
  }

  stop() {
    this.pause();
    this.pausedAt = 0;
    this.currentTime = 0;
  }

  // Track playback control
  startTrack(trackId, startTime = 0) {
    const track = this.tracks.get(trackId);
    if (!track || !track.buffer) return;

    // Stop existing source if playing
    if (track.source) {
      track.source.stop();
    }

    // Create new source
    track.source = this.audioContext.createBufferSource();
    track.source.buffer = track.buffer;
    track.source.connect(track.gainNode);

    // Start playback
    track.source.start(this.audioContext.currentTime, startTime);
    track.isPlaying = true;

    // Handle track end
    track.source.onended = () => {
      track.isPlaying = false;
      track.source = null;
    };
  }

  stopTrack(trackId) {
    const track = this.tracks.get(trackId);
    if (!track || !track.source) return;

    track.source.stop();
    track.source = null;
    track.isPlaying = false;
  }

  // Track controls
  setTrackVolume(trackId, volume) {
    const track = this.tracks.get(trackId);
    if (!track) return;

    track.volume = Math.max(0, Math.min(1, volume));
    track.gainNode.gain.setValueAtTime(track.volume, this.audioContext.currentTime);
  }

  setTrackPan(trackId, pan) {
    const track = this.tracks.get(trackId);
    if (!track) return;

    track.pan = Math.max(-1, Math.min(1, pan));
    track.panNode.pan.setValueAtTime(track.pan, this.audioContext.currentTime);
  }

  muteTrack(trackId, mute = true) {
    const track = this.tracks.get(trackId);
    if (!track) return;

    track.isMuted = mute;
    const targetVolume = mute ? 0 : track.volume;
    track.gainNode.gain.setValueAtTime(targetVolume, this.audioContext.currentTime);
  }

  soloTrack(trackId, solo = true) {
    const track = this.tracks.get(trackId);
    if (!track) return;

    track.isSoloed = solo;

    // If soloing, mute all other tracks
    if (solo) {
      for (const [otherTrackId, otherTrack] of this.tracks) {
        if (otherTrackId !== trackId) {
          this.muteTrack(otherTrackId, true);
        }
      }
      this.muteTrack(trackId, false);
    } else {
      // If unsoloing, check if any other tracks are soloed
      const hasSoloedTracks = Array.from(this.tracks.values()).some(t => t.isSoloed && t.id !== trackId);
      if (!hasSoloedTracks) {
        // Unmute all tracks
        for (const [otherTrackId] of this.tracks) {
          this.muteTrack(otherTrackId, false);
        }
      }
    }
  }

  // Get audio levels for meters
  getTrackLevels(trackId) {
    const analyser = this.analysers.get(trackId);
    if (!analyser) return { peak: 0, rms: 0 };

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);

    // Calculate peak and RMS
    let peak = 0;
    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
      const value = dataArray[i] / 255;
      peak = Math.max(peak, value);
      sum += value * value;
    }
    const rms = Math.sqrt(sum / bufferLength);

    return { peak, rms };
  }

  // Time update loop
  updateTimeLoop() {
    if (!this.isPlaying) return;

    this.currentTime = this.audioContext.currentTime - this.playbackStartTime;

    // Check loop region
    if (this.loopRegion && this.currentTime >= this.loopRegion.end) {
      this.pause();
      this.play(this.loopRegion.start);
      return;
    }

    // Continue loop
    requestAnimationFrame(() => this.updateTimeLoop());
  }

  // Set tempo and time signature
  setTempo(bpm) {
    this.tempo = bpm;
  }

  setTimeSignature(numerator, denominator) {
    this.timeSignature = [numerator, denominator];
  }

  // Export functionality
  async exportMix(format = 'wav') {
    // This would implement offline rendering of the mix
    // For now, return a placeholder
    return new Blob([''], { type: `audio/${format}` });
  }

  // Cleanup
  destroy() {
    if (this.audioContext) {
      this.audioContext.close();
    }
    this.tracks.clear();
    this.analysers.clear();
  }
}

export default AudioEngine;
