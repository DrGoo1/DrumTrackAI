/**
 * AudioEngine.js
 * Web Audio API wrapper for section-based playback with loop support
 * Handles audio loading, decoding, and precise time-based playback
 */

class AudioEngine {
  constructor() {
    this.audioContext = null;
    this.audioBuffer = null;
    this.sourceNode = null;
    this.gainNode = null;
    this.isPlaying = false;
    this.isLooping = false;
    this.currentSection = null;
    this.startTime = 0;
    this.pausedAt = 0;
    this.loopTimeout = null;
    this.onPlaybackEnd = null;
    this.onTimeUpdate = null;
    this.updateInterval = null;
  }

  /**
   * Initialize audio context (must be called after user interaction)
   */
  async initialize() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.gainNode = this.audioContext.createGain();
      this.gainNode.connect(this.audioContext.destination);
    }

    // Resume context if suspended (browser autoplay policy)
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }
  }

  /**
   * Load and decode audio file from URL
   * @param {string} url - Audio file URL
   */
  async loadAudio(url) {
    try {
      await this.initialize();

      const response = await fetch(url);
      const arrayBuffer = await response.arrayBuffer();
      this.audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

      console.log(`Audio loaded: ${this.audioBuffer.duration.toFixed(2)}s, ${this.audioBuffer.sampleRate}Hz`);
      return this.audioBuffer;
    } catch (error) {
      console.error('Failed to load audio:', error);
      throw error;
    }
  }

  /**
   * Play a specific section with optional loop
   * @param {Object} section - Section object with start, end, label
   * @param {boolean} loop - Enable looping
   */
  async playSection(section, loop = false) {
    if (!this.audioBuffer) {
      throw new Error('No audio loaded');
    }

    await this.initialize();

    // Stop current playback
    this.stop();

    this.currentSection = section;
    this.isLooping = loop;
    this.pausedAt = 0;

    // Start playback
    this._startPlayback(section.start, section.end - section.start);
  }

  /**
   * Internal method to start/restart playback
   */
  _startPlayback(offset, duration) {
    // Create new source node
    this.sourceNode = this.audioContext.createBufferSource();
    this.sourceNode.buffer = this.audioBuffer;
    this.sourceNode.connect(this.gainNode);

    // Store timing info
    this.startTime = this.audioContext.currentTime - this.pausedAt;
    this.isPlaying = true;

    // Handle playback end
    this.sourceNode.onended = () => {
      this.isPlaying = false;
      this.pausedAt = 0;

      if (this.isLooping && this.currentSection) {
        // Loop: restart section playback
        this._startPlayback(this.currentSection.start, this.currentSection.end - this.currentSection.start);
      } else {
        // Not looping: clean up
        this.sourceNode = null;
        if (this.onPlaybackEnd) {
          this.onPlaybackEnd();
        }
      }
    };

    // Start playback at offset with duration
    this.sourceNode.start(0, offset, duration);

    // Start time updates
    this._startTimeUpdates();
  }

  /**
   * Pause playback (can be resumed)
   */
  pause() {
    if (!this.isPlaying || !this.sourceNode) return;

    const elapsed = this.audioContext.currentTime - this.startTime;
    this.pausedAt = elapsed;

    this.sourceNode.stop();
    this.sourceNode = null;
    this.isPlaying = false;

    this._stopTimeUpdates();
  }

  /**
   * Resume playback from pause
   */
  async resume() {
    if (!this.currentSection || this.isPlaying) return;

    await this.initialize();

    const remainingDuration = (this.currentSection.end - this.currentSection.start) - this.pausedAt;
    const currentOffset = this.currentSection.start + this.pausedAt;

    this._startPlayback(currentOffset, remainingDuration);
  }

  /**
   * Stop playback completely
   */
  stop() {
    if (this.sourceNode) {
      try {
        this.sourceNode.stop();
      } catch (e) {
        // Already stopped
      }
      this.sourceNode = null;
    }

    this.isPlaying = false;
    this.isLooping = false;
    this.pausedAt = 0;
    this.currentSection = null;

    if (this.loopTimeout) {
      clearTimeout(this.loopTimeout);
      this.loopTimeout = null;
    }

    this._stopTimeUpdates();
  }

  /**
   * Toggle loop mode
   */
  toggleLoop() {
    this.isLooping = !this.isLooping;
    return this.isLooping;
  }

  /**
   * Set volume (0.0 to 1.0)
   */
  setVolume(volume) {
    if (this.gainNode) {
      this.gainNode.gain.value = Math.max(0, Math.min(1, volume));
    }
  }

  /**
   * Get current playback position relative to section
   */
  getCurrentPosition() {
    if (!this.isPlaying || !this.currentSection) return 0;

    const elapsed = this.audioContext.currentTime - this.startTime;
    const sectionDuration = this.currentSection.end - this.currentSection.start;
    return Math.min(elapsed, sectionDuration);
  }

  /**
   * Get current playback progress (0 to 1)
   */
  getProgress() {
    if (!this.currentSection) return 0;

    const position = this.getCurrentPosition();
    const duration = this.currentSection.end - this.currentSection.start;
    return Math.min(position / duration, 1);
  }

  /**
   * Start periodic time updates
   */
  _startTimeUpdates() {
    this._stopTimeUpdates();

    this.updateInterval = setInterval(() => {
      if (this.onTimeUpdate && this.isPlaying) {
        const position = this.getCurrentPosition();
        const progress = this.getProgress();
        this.onTimeUpdate({ position, progress, section: this.currentSection });
      }
    }, 100); // Update every 100ms
  }

  /**
   * Stop time updates
   */
  _stopTimeUpdates() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
  }

  /**
   * Clean up resources
   */
  dispose() {
    this.stop();

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.audioBuffer = null;
    this.gainNode = null;
  }

  /**
   * Get audio info
   */
  getAudioInfo() {
    if (!this.audioBuffer) return null;

    return {
      duration: this.audioBuffer.duration,
      sampleRate: this.audioBuffer.sampleRate,
      numberOfChannels: this.audioBuffer.numberOfChannels,
      length: this.audioBuffer.length,
    };
  }
}

export default AudioEngine;
