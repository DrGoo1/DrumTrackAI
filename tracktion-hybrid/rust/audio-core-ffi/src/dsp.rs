use realfft::RealFftPlanner;
use serde::Serialize;
use std::f32::consts::PI;

#[derive(Clone, Copy)]
pub struct AnalysisConfig {
    pub win: usize,
    pub hop: usize,
    pub min_bpm: f32,
    pub max_bpm: f32,
}

#[derive(Serialize, Clone)]
pub struct Note {
    pub lane: String,
    pub time: f32,
    pub len: f32,
    pub vel: u8,
}

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

/// Return (tempo_bpm, beats_sec[], onsets_sec[])
pub fn analyze(pcm: &[f32], sr: u32, cfg: AnalysisConfig) -> (f32, Vec<f32>, Vec<f32>) {
    let (flux, frame_times) = spectral_flux(pcm, sr, cfg.win, cfg.hop);
    let onsets = pick_peaks(&flux, &frame_times);
    let tempo = estimate_tempo(&flux, sr, cfg.hop, cfg.min_bpm, cfg.max_bpm);
    let beats = render_beats(tempo, pcm.len() as f32 / sr as f32, onsets.first().cloned().unwrap_or(0.0));
    (tempo, beats, onsets)
}

pub fn spectral_flux_for_ui(pcm: &[f32], sr: u32, win: usize, hop: usize) -> (Vec<f32>, Vec<f32>) {
    spectral_flux(pcm, sr, win, hop)
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
    (60.0 / sec_per_beat).clamp(min_bpm, max_bpm)
}

fn render_beats(bpm: f32, duration: f32, seed_start: f32) -> Vec<f32> {
    if bpm <= 0.0 { return vec![]; }
    let spb = 60.0 / bpm;
    let mut t0 = (seed_start / spb).round() * spb;
    if t0 < 0.0 { t0 = 0.0; }
    let mut beats = Vec::new();
    let mut t = t0;
    while t <= duration { beats.push(t); t += spb; }
    beats
}

// Advanced drum generation with style/label awareness
pub fn generate_drums(
    bpm: f32,
    start: f32,
    end: f32,
    style: &str,
    label: &str,
    density: f32,
    swing_amt: f32,
    humanize: f32,
    seed: u64,
    swing_preset: &str,
    vel_preset: &str,
    fill_preset: &str,
) -> Vec<Note> {
    
    let mut rng = SimpleRng::new(seed);
    let mut notes = Vec::new();
    
    let duration = end - start;
    let spb = 60.0 / bpm; // seconds per beat
    let num_beats = (duration / spb) as usize;
    
    // Style-specific patterns
    let kick_pattern = match style {
        "rock" => vec![true, false, false, false, true, false, false, false],
        "funk" => vec![true, false, true, false, false, true, false, false],
        "jazz" => vec![true, false, false, true, false, false, true, false],
        "latin" => vec![true, false, true, false, true, false, false, false],
        _ => vec![true, false, false, false, true, false, false, false], // default rock
    };
    
    let snare_pattern = match style {
        "rock" => vec![false, false, true, false, false, false, true, false],
        "funk" => vec![false, true, false, true, false, true, false, false],
        "jazz" => vec![false, true, false, false, true, false, false, true],
        "latin" => vec![false, false, true, false, false, false, true, false],
        _ => vec![false, false, true, false, false, false, true, false],
    };
    
    let hihat_pattern = match style {
        "rock" => vec![true, true, true, true, true, true, true, true],
        "funk" => vec![true, false, true, true, false, true, true, false],
        "jazz" => vec![true, false, true, false, true, false, true, false],
        "latin" => vec![true, true, false, true, true, false, true, true],
        _ => vec![true, true, true, true, true, true, true, true],
    };
    
    // Velocity curves based on preset
    let base_velocity = match vel_preset {
        "flat" => 80,
        "accent24" => 90,
        "funk16" => 85,
        _ => 80,
    };
    
    // Apply swing based on preset
    let swing_factor = match swing_preset {
        "off" => 0.0,
        "light" => 0.1,
        "heavy" => 0.2,
        _ => swing_amt,
    };
    
    // Generate basic pattern
    for beat in 0..num_beats {
        let beat_time = start + (beat as f32 * spb);
        let pattern_idx = beat % 8;
        
        // Apply density filter
        if rng.next_f32() > density {
            continue;
        }
        
        // Kick drum
        if kick_pattern[pattern_idx] {
            let mut time = beat_time;
            if beat % 2 == 1 { time += swing_factor * spb * 0.5; } // swing on off-beats
            time += rng.next_f32() * humanize * 0.1; // humanization
            
            let vel = apply_velocity_curve(base_velocity, vel_preset, beat, &mut rng);
            notes.push(Note {
                lane: "kick".to_string(),
                time,
                len: 0.1,
                vel: vel as u8,
            });
        }
        
        // Snare drum
        if snare_pattern[pattern_idx] {
            let mut time = beat_time;
            if beat % 2 == 1 { time += swing_factor * spb * 0.5; }
            time += rng.next_f32() * humanize * 0.1;
            
            let vel = apply_velocity_curve(base_velocity + 10, vel_preset, beat, &mut rng);
            notes.push(Note {
                lane: "snare".to_string(),
                time,
                len: 0.1,
                vel: vel as u8,
            });
        }
        
        // Hi-hat
        if hihat_pattern[pattern_idx] {
            let mut time = beat_time;
            if beat % 2 == 1 { time += swing_factor * spb * 0.5; }
            time += rng.next_f32() * humanize * 0.05;
            
            let vel = apply_velocity_curve(base_velocity - 20, vel_preset, beat, &mut rng);
            notes.push(Note {
                lane: "hihat".to_string(),
                time,
                len: 0.05,
                vel: (vel as u8).max(40),
            });
        }
    }
    
    // Add fills based on label and preset
    if label == "chorus" || label == "bridge" {
        apply_fills(&mut notes, start, end, bpm, fill_preset, &mut rng);
    }
    
    notes
}

fn apply_velocity_curve(base_vel: i32, preset: &str, beat: usize, rng: &mut SimpleRng) -> i32 {
    let variation = (rng.next_f32() - 0.5) * 20.0; // ±10 velocity variation
    
    let vel = match preset {
        "accent24" => {
            if beat % 4 == 0 { base_vel + 15 } // accent on downbeats
            else if beat % 2 == 0 { base_vel + 5 } // lighter accent on beats 2,4
            else { base_vel - 10 }
        },
        "funk16" => {
            if beat % 4 == 0 { base_vel + 20 }
            else if beat % 2 == 1 { base_vel + 10 } // accent off-beats
            else { base_vel - 5 }
        },
        _ => base_vel, // flat
    };
    
    (vel as f32 + variation).clamp(1.0, 127.0) as i32
}

pub fn apply_fills(notes: &mut Vec<Note>, _start: f32, end: f32, bpm: f32, preset: &str, rng: &mut SimpleRng) {
    let spb = 60.0 / bpm;
    let fill_start = end - spb; // last beat of section
    
    match preset {
        "tomrun" => {
            // Tom roll descending
            for i in 0..4 {
                let time = fill_start + (i as f32 * spb * 0.25);
                notes.push(Note {
                    lane: "tom".to_string(),
                    time,
                    len: 0.1,
                    vel: (100 - i * 5) as u8,
                });
            }
        },
        "snarebuzz" => {
            // Snare buzz roll
            for i in 0..8 {
                let time = fill_start + (i as f32 * spb * 0.125);
                notes.push(Note {
                    lane: "snare".to_string(),
                    time,
                    len: 0.05,
                    vel: (80 + (rng.next_f32() * 20.0) as i32) as u8,
                });
            }
        },
        "edmriser" => {
            // Crash with reverse cymbal effect
            notes.push(Note {
                lane: "crash".to_string(),
                time: fill_start,
                len: spb,
                vel: 127,
            });
        },
        "random" => {
            // Random tom/snare combination
            for i in 0..4 {
                let time = fill_start + (i as f32 * spb * 0.25);
                let lane = if rng.next_f32() > 0.5 { "tom" } else { "snare" };
                notes.push(Note {
                    lane: lane.to_string(),
                    time,
                    len: 0.1,
                    vel: (90 + (rng.next_f32() * 20.0) as i32) as u8,
                });
            }
        },
        _ => {} // none
    }
}

// Simple MIDI Type-1 export
pub fn notes_to_type1_midi(notes: &[Note], bpm: f64) -> Vec<u8> {
    let mut midi = Vec::new();
    
    // MIDI header chunk
    midi.extend_from_slice(b"MThd");
    midi.extend_from_slice(&6u32.to_be_bytes()); // header length
    midi.extend_from_slice(&1u16.to_be_bytes()); // format 1 (multi-track)
    midi.extend_from_slice(&9u16.to_be_bytes()); // 9 tracks (8 drum lanes + tempo)
    midi.extend_from_slice(&480u16.to_be_bytes()); // ticks per quarter note
    
    // Track 0: Tempo track
    let mut tempo_track = Vec::new();
    tempo_track.extend_from_slice(&0u32.to_be_bytes()); // delta time
    tempo_track.push(0xFF); tempo_track.push(0x51); tempo_track.push(0x03); // tempo meta event
    let microseconds_per_quarter = (60_000_000.0 / bpm) as u32;
    tempo_track.extend_from_slice(&microseconds_per_quarter.to_be_bytes()[1..4]);
    tempo_track.extend_from_slice(&0u32.to_be_bytes()); // delta time
    tempo_track.push(0xFF); tempo_track.push(0x2F); tempo_track.push(0x00); // end of track
    
    midi.extend_from_slice(b"MTrk");
    midi.extend_from_slice(&(tempo_track.len() as u32).to_be_bytes());
    midi.extend_from_slice(&tempo_track);
    
    // Tracks 1-8: Drum lanes
    let lanes = ["kick", "snare", "hihat", "ohat", "ride", "tom", "crash", "clap"];
    let midi_notes = [36, 38, 42, 46, 51, 45, 49, 39]; // GM drum map
    
    for (lane_idx, lane_name) in lanes.iter().enumerate() {
        let mut track = Vec::new();
        let lane_notes: Vec<_> = notes.iter().filter(|n| n.lane == *lane_name).collect();
        
        let mut last_time = 0u32;
        for note in lane_notes {
            let ticks = (note.time * 480.0) as u32; // convert to MIDI ticks
            let delta = ticks - last_time;
            
            // Note on
            write_variable_length(&mut track, delta);
            track.push(0x90); // note on, channel 0
            track.push(midi_notes[lane_idx]);
            track.push(note.vel);
            
            // Note off
            let note_length_ticks = (note.len * 480.0) as u32;
            write_variable_length(&mut track, note_length_ticks);
            track.push(0x80); // note off, channel 0
            track.push(midi_notes[lane_idx]);
            track.push(0x40);
            
            last_time = ticks + note_length_ticks;
        }
        
        // End of track
        track.extend_from_slice(&0u32.to_be_bytes()); // delta time
        track.push(0xFF); track.push(0x2F); track.push(0x00);
        
        midi.extend_from_slice(b"MTrk");
        midi.extend_from_slice(&(track.len() as u32).to_be_bytes());
        midi.extend_from_slice(&track);
    }
    
    midi
}

fn write_variable_length(buf: &mut Vec<u8>, mut value: u32) {
    let mut bytes = Vec::new();
    bytes.push((value & 0x7F) as u8);
    value >>= 7;
    
    while value > 0 {
        bytes.push(((value & 0x7F) | 0x80) as u8);
        value >>= 7;
    }
    
    for byte in bytes.iter().rev() {
        buf.push(*byte);
    }
}

// Simple RNG for deterministic generation
struct SimpleRng {
    state: u64,
}

impl SimpleRng {
    fn new(seed: u64) -> Self {
        Self { state: seed }
    }
    
    fn next_u32(&mut self) -> u32 {
        self.state = self.state.wrapping_mul(1103515245).wrapping_add(12345);
        (self.state >> 16) as u32
    }
    
    fn next_f32(&mut self) -> f32 {
        self.next_u32() as f32 / u32::MAX as f32
    }
}
