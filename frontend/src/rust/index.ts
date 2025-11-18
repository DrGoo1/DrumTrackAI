// DrumTracKAI Rust-WASM Integration
// This module provides TypeScript bindings for Rust WASM functions

// WASM module is optional - fallback to JavaScript implementations
let init: any = null;
let DrumTracKAIWasm: any = null;
let AudioProcessor: any = null;
let PatternGeneratorWasm: any = null;
let Utils: any = null;

try {
  const wasmModule = require('../wasm/drumtrackai_wasm.js');
  init = wasmModule.default;
  DrumTracKAIWasm = wasmModule.DrumTracKAIWasm;
  AudioProcessor = wasmModule.AudioProcessor;
  PatternGeneratorWasm = wasmModule.PatternGeneratorWasm;
  Utils = wasmModule.Utils;
} catch (error) {
  console.warn('WASM module not available, using JavaScript fallbacks:', error);
}

let wasmInitialized = false;
let wasmModule: any = null;

// Initialize WASM module
export async function initializeRustWasm(): Promise<void> {
  if (wasmInitialized) return;
  
  try {
    if (init) {
      wasmModule = await init();
      wasmInitialized = true;
      console.log('DrumTracKAI Rust WASM module initialized');
    } else {
      console.warn('WASM module not available, skipping initialization');
    }
  } catch (error) {
    console.error('Failed to initialize Rust WASM module:', error);
    // Don't throw error, just continue without WASM
  }
}

// Rust-powered audio analyzer
export class RustAudioAnalyzer {
  private analyzer: any;

  constructor(sampleRate: number = 44100, hopLength: number = 512, frameSize: number = 2048) {
    if (!wasmInitialized || !DrumTracKAIWasm) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    this.analyzer = new DrumTracKAIWasm(sampleRate, hopLength, frameSize);
  }

  async analyzeAudio(audioData: Float32Array): Promise<any> {
    try {
      return this.analyzer.analyze_audio(audioData);
    } catch (error) {
      console.error('Rust audio analysis failed:', error);
      throw error;
    }
  }

  async detectOnsets(audioData: Float32Array): Promise<number[]> {
    try {
      const onsets = this.analyzer.detect_onsets(audioData);
      return Array.from(onsets);
    } catch (error) {
      console.error('Rust onset detection failed:', error);
      throw error;
    }
  }

  async estimateTempo(audioData: Float32Array): Promise<number> {
    try {
      return this.analyzer.estimate_tempo(audioData);
    } catch (error) {
      console.error('Rust tempo estimation failed:', error);
      throw error;
    }
  }
}

// Rust-powered pattern generator
export class RustPatternGenerator {
  private generator: any;

  constructor(tempo: number = 120) {
    if (!wasmInitialized || !PatternGeneratorWasm) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    this.generator = new PatternGeneratorWasm(tempo);
  }

  generateRockPattern(bars: number = 1): any {
    try {
      return this.generator.generate_rock_pattern(bars);
    } catch (error) {
      console.error('Rust rock pattern generation failed:', error);
      throw error;
    }
  }

  generateJazzPattern(bars: number = 1): any {
    try {
      return this.generator.generate_jazz_pattern(bars);
    } catch (error) {
      console.error('Rust jazz pattern generation failed:', error);
      throw error;
    }
  }

  setSwing(swing: number): void {
    this.generator.set_swing(swing);
  }
}

// Rust-powered audio processing utilities
export class RustAudioUtils {
  static stereoToMono(stereoData: Float32Array): Float32Array {
    if (!wasmInitialized) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    return AudioProcessor.stereo_to_mono(stereoData);
  }

  static normalizeAudio(audioData: Float32Array, targetPeak: number = 1.0): void {
    if (!wasmInitialized) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    AudioProcessor.normalize_audio(audioData, targetPeak);
  }

  static highPassFilter(audioData: Float32Array, cutoffFreq: number, sampleRate: number): void {
    if (!wasmInitialized) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    AudioProcessor.high_pass_filter(audioData, cutoffFreq, sampleRate);
  }

  static calculateRms(audioData: Float32Array): number {
    if (!wasmInitialized) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    return AudioProcessor.calculate_rms(audioData);
  }
}

// Rust utility functions
export class RustUtils {
  static dbToLinear(db: number): number {
    if (!wasmInitialized) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    return Utils.db_to_linear(db);
  }

  static linearToDb(linear: number): number {
    if (!wasmInitialized) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    return Utils.linear_to_db(linear);
  }

  static beatsToSeconds(beats: number, tempo: number): number {
    if (!wasmInitialized) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    return Utils.beats_to_seconds(beats, tempo);
  }

  static secondsToBeats(seconds: number, tempo: number): number {
    if (!wasmInitialized) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    return Utils.seconds_to_beats(seconds, tempo);
  }

  static lerp(a: number, b: number, t: number): number {
    if (!wasmInitialized) {
      throw new Error('WASM module not initialized. Call initializeRustWasm() first.');
    }
    return Utils.lerp(a, b, t);
  }
}

// Export initialization status
export function isRustWasmInitialized(): boolean {
  return wasmInitialized;
}
