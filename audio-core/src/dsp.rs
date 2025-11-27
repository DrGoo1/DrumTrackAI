use rayon::prelude::*;
use realfft::{RealFftPlanner, RealToComplex};
use serde::Serialize;
use std::f32::consts::PI;

#[macro_export]
macro_rules! define_hann { () => {
    struct Hann(usize);
    impl Hann { fn collect(&self)->Vec<f32>{ use std::f32::consts::PI; (0..self.0).map(|i|(PI*2.0*i as f32/(self.0 as f32-1.0)).sin().powi(2)).collect() } }
}}

pub fn downsample_peaks(pcm: &[f32], max_points: usize) -> Vec<f32> {
    if pcm.is_empty() || max_points == 0 { return vec![]; }
    let step = (pcm.len() + max_points - 1) / max_points; // ceil
    let chunks = pcm.chunks(step);
    let mut peaks: Vec<f32> = chunks
        .map(|ch| ch.iter().map(|x| x.abs()).fold(0.0_f32, f32::max))
        .collect();
    let m = peaks.iter().cloned().fold(0.0_f32, f32::max).max(1e-8);
    for p in &mut peaks { *p = (*p / m).clamp(0.0, 1.0); }
    peaks
}

#[derive(Clone, Copy)]
pub struct AnalysisConfig {
    pub win: usize,
    pub hop: usize,
    pub min_bpm: f32,
    pub max_bpm: f32,
}

/// Return (tempo_bpm, beats_sec[], onsets_sec[])
pub fn analyze(pcm: &[f32], sr: u32, cfg: AnalysisConfig) -> (f32, Vec<f32>, Vec<f32>) {
    let (flux, frame_times) = spectral_flux(pcm, sr, cfg.win, cfg.hop);
    let onsets = pick_peaks(&flux, &frame_times);
    let tempo = estimate_tempo(&flux, sr, cfg.hop, cfg.min_bpm, cfg.max_bpm);
    let beats = render_beats(tempo, pcm.len() as f32 / sr as f32, onsets.first().cloned().unwrap_or(0.0));
    (tempo, beats, onsets)
}

/// Analyze a specific time segment of audio
/// Returns (tempo_bpm, confidence, candidate_tempos[])
pub fn analyze_segment(pcm: &[f32], sr: u32, start_sec: f32, end_sec: f32, cfg: AnalysisConfig) -> (f32, f32, Vec<f32>) {
    let start_frame = (start_sec * sr as f32) as usize;
    let end_frame = (end_sec * sr as f32) as usize;
    
    // Bounds checking
    let start_frame = start_frame.min(pcm.len());
    let end_frame = end_frame.min(pcm.len());
    
    if start_frame >= end_frame || end_frame - start_frame < sr as usize {
        // Too short, return default
        return (120.0, 0.0, vec![120.0]);
    }
    
    let segment = &pcm[start_frame..end_frame];
    let (flux, _) = spectral_flux(segment, sr, cfg.win, cfg.hop);
    
    // Get tempo and candidate tempos with confidence
    let tempo = estimate_tempo(&flux, sr, cfg.hop, cfg.min_bpm, cfg.max_bpm);
    let candidates = estimate_tempo_candidates(&flux, sr, cfg.hop, cfg.min_bpm, cfg.max_bpm, 3);
    
    // Calculate confidence based on autocorrelation peak strength
    let confidence = calculate_tempo_confidence(&flux, sr, cfg.hop, tempo);
    
    (tempo, confidence, candidates)
}

fn hann(n: usize) -> Vec<f32> {
    (0..n).map(|i| (PI * 2.0 * i as f32 / (n as f32 - 1.0)).sin().powi(2)).collect()
}

pub fn spectral_flux(pcm: &[f32], sr: u32, win: usize, hop: usize) -> (Vec<f32>, Vec<f32>) {
    let mut planner = RealFftPlanner::<f32>::new();
    let r2c = planner.plan_fft_forward(win);
    let mut input = r2c.make_input_vec();
    let mut spectrum = r2c.make_output_vec();
    let window = hann(win);

    let n_frames = if pcm.len() < win { 0 } else { 1 + (pcm.len() - win) / hop };
    let mut flux = Vec::with_capacity(n_frames);
    let mut times = Vec::with_capacity(n_frames);
    let mut prev_mag = vec![0.0f32; win/2+1];

    for f in 0..n_frames {
        let start = f*hop;
        for i in 0..win { input[i] = pcm[start + i] * window[i]; }
        r2c.process(&mut input, &mut spectrum).unwrap();

        let mut sum = 0.0f32;
        for (k, c) in spectrum.iter().enumerate() {
            let mag = (c.norm_sqr().sqrt()).max(0.0);
            let d = (mag - prev_mag[k]).max(0.0);
            sum += d;
            prev_mag[k] = mag;
        }
        flux.push(sum);
        times.push((start as f32)/ (sr as f32));
    }
    // normalize
    let maxv = flux.iter().cloned().fold(0.0_f32, f32::max).max(1e-8);
    for v in &mut flux { *v = (*v / maxv).clamp(0.0, 1.0); }
    (flux, times)
}

fn pick_peaks(flux: &[f32], times: &[f32]) -> Vec<f32> {
    if flux.is_empty() { return vec![]; }
    let mean: f32 = flux.iter().sum::<f32>() / flux.len() as f32;
    let std: f32 = (flux.iter().map(|v| (v-mean)*(v-mean)).sum::<f32>() / flux.len() as f32).sqrt();
    let thr = mean + 0.5*std;
    let mut out = Vec::new();
    for i in 1..flux.len()-1 {
        if flux[i] > thr && flux[i] > flux[i-1] && flux[i] >= flux[i+1] {
            out.push(times[i]);
        }
    }
    out
}

fn estimate_tempo(flux: &[f32], sr: u32, hop: usize, min_bpm: f32, max_bpm: f32) -> f32 {
    if flux.len() < 4 { return 120.0; }
    let hop_sec = hop as f32 / sr as f32;
    let min_lag = (60.0 / max_bpm / hop_sec).round().max(1.0) as usize;
    let max_lag = (60.0 / min_bpm / hop_sec).round().max(min_lag as f32) as usize;

    // zero-mean flux
    let mean = flux.iter().sum::<f32>() / flux.len() as f32;
    let mut z = flux.to_vec();
    for v in &mut z { *v -= mean; }

    let mut best = (0.0f32, min_lag);
    for lag in min_lag..=max_lag {
        let mut acc = 0.0f32;
        for i in 0..(z.len()-lag) {
            acc += z[i] * z[i+lag];
        }
        if acc > best.0 { best = (acc, lag); }
    }
    let sec_per_beat = best.1 as f32 * hop_sec;
    let raw_tempo = 60.0 / sec_per_beat;
    
    // Apply octave correction to bring tempo into reasonable range
    correct_tempo_octave(raw_tempo)
}

/// Correct tempo by octaves to bring into reasonable musical range (60-180 BPM)
/// This fixes issues where the algorithm detects subdivisions (8th/16th notes) as the beat
fn correct_tempo_octave(tempo: f32) -> f32 {
    let mut corrected = tempo;
    
    // If tempo too high (likely detecting subdivisions), halve it
    while corrected > 180.0 {
        corrected /= 2.0;
    }
    
    // If tempo too low (unlikely but possible), double it
    while corrected < 60.0 && corrected > 0.0 {
        corrected *= 2.0;
    }
    
    // Final safety clamp
    corrected.clamp(60.0, 200.0)
}

fn render_beats(bpm: f32, duration: f32, seed_start: f32) -> Vec<f32> {
    if bpm <= 0.0 { return vec![]; }
    let spb = 60.0 / bpm;
    let mut t0 = (seed_start / spb).round() * spb;
    if t0 < 0.0 { t0 = 0.0; }
    let mut v = Vec::new();
    let mut t = t0;
    while t <= duration {
        v.push(t);
        t += spb;
    }
    v
}

/// Get multiple tempo candidates (not just the best)
fn estimate_tempo_candidates(flux: &[f32], sr: u32, hop: usize, min_bpm: f32, max_bpm: f32, count: usize) -> Vec<f32> {
    if flux.len() < 4 { return vec![120.0]; }
    let hop_sec = hop as f32 / sr as f32;
    let min_lag = (60.0 / max_bpm / hop_sec).round().max(1.0) as usize;
    let max_lag = (60.0 / min_bpm / hop_sec).round().max(min_lag as f32) as usize;
    
    // Zero-mean flux
    let mean = flux.iter().sum::<f32>() / flux.len() as f32;
    let mut z: Vec<f32> = flux.iter().map(|v| v - mean).collect();
    
    // Autocorrelation
    let mut acf = vec![0.0f32; max_lag - min_lag + 1];
    for lag in min_lag..=max_lag {
        let mut sum = 0.0f32;
        for i in 0..(flux.len() - lag) {
            sum += z[i] * z[i + lag];
        }
        acf[lag - min_lag] = sum;
    }
    
    // Find top N peaks
    let mut peaks: Vec<(usize, f32)> = Vec::new();
    for i in 1..acf.len()-1 {
        if acf[i] > acf[i-1] && acf[i] >= acf[i+1] && acf[i] > 0.0 {
            peaks.push((i + min_lag, acf[i]));
        }
    }
    
    // Sort by strength
    peaks.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    
    // Convert to BPM and apply octave correction
    let mut candidates: Vec<f32> = peaks.iter()
        .take(count)
        .map(|(lag, _)| {
            let raw_bpm = 60.0 / (*lag as f32 * hop_sec);
            correct_tempo_octave(raw_bpm)
        })
        .collect();
    
    if candidates.is_empty() {
        candidates.push(120.0);
    }
    
    candidates
}

/// Calculate confidence based on autocorrelation peak strength
fn calculate_tempo_confidence(flux: &[f32], sr: u32, hop: usize, tempo: f32) -> f32 {
    if flux.len() < 4 { return 0.0; }
    let hop_sec = hop as f32 / sr as f32;
    let target_lag = (60.0 / tempo / hop_sec).round() as usize;
    
    if target_lag >= flux.len() { return 0.0; }
    
    // Zero-mean flux
    let mean = flux.iter().sum::<f32>() / flux.len() as f32;
    let z: Vec<f32> = flux.iter().map(|v| v - mean).collect();
    
    // Autocorrelation at target lag
    let mut sum = 0.0f32;
    let mut norm = 0.0f32;
    for i in 0..(flux.len() - target_lag) {
        sum += z[i] * z[i + target_lag];
        norm += z[i] * z[i];
    }
    
    // Normalize to 0-1 range
    if norm > 1e-8 {
        (sum / norm).max(0.0).min(1.0)
    } else {
        0.0
    }
}

/// Estimate energy for each beat (for meter detection)
pub fn estimate_beat_energy(pcm: &[f32], sr: u32, beat_times: &[f32]) -> Vec<f32> {
    if beat_times.is_empty() {
        return Vec::new();
    }

    let win = (0.08 * sr as f32) as usize; // 80 ms window around each beat
    let half_win = win / 2;
    let mut energies = Vec::with_capacity(beat_times.len());

    for &bt in beat_times {
        let center = (bt * sr as f32) as isize;
        let start = (center - half_win as isize).max(0) as usize;
        let end = (center + half_win as isize).min(pcm.len() as isize - 1) as usize;

        let mut sum_sq = 0.0;
        let mut count = 0;
        for i in start..end {
            let v = pcm[i];
            sum_sq += v * v;
            count += 1;
        }

        let rms = if count > 0 {
            (sum_sq / count as f32).sqrt()
        } else {
            0.0
        };

        energies.push(rms);
    }

    // Normalize to 0–1
    let max_val = energies
        .iter()
        .copied()
        .fold(0.0_f32, |a, b| a.max(b))
        .max(1e-6);
    for e in &mut energies {
        *e /= max_val;
    }

    energies
}
