use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use serde::Serialize;
use std::path::PathBuf;
use generator::Style;
use base64::{engine::general_purpose::STANDARD as B64, Engine as _};

mod decoder;
mod dsp;
mod generator;
mod midi;
mod sectionize;
mod sectionize_smart;
mod bar;
mod meter;

#[derive(Parser)]
#[command(name="audio-core", version, about="DrumTracKAI DSP core (CLI)")]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}
#[derive(Subcommand)]
enum Cmd {
    /// Downsampled amplitude peaks for fast waveforms
    Peaks {
        file: PathBuf,
        #[arg(long, default_value_t = 3000)]
        max_points: usize,
    },
    /// Tempo/beat/onset analysis
    Analyze {
        file: PathBuf,
        #[arg(long, default_value_t = 50.0)]
        min_bpm: f32,
        #[arg(long, default_value_t = 200.0)]
        max_bpm: f32,
    },
    /// Audio section detection
    Sectionize {
        file: PathBuf,
        #[arg(long, default_value_t = 2.0)]
        min_section_sec: f32,
    },
    /// Smart audio section detection with beat alignment
    SectionizeSmart {
        file: PathBuf,
        #[arg(long, default_value_t = 120.0)]
        bpm: f32,
        #[arg(long, default_value_t = 4)]
        min_bars: u32,
        #[arg(long, default_value_t = 16)]
        max_bars: u32,
    },
    /// Analyze tempo for multiple sections
    AnalyzeSections {
        file: PathBuf,
        #[arg(long, value_delimiter = ',')]
        starts: Vec<f32>,
        #[arg(long, value_delimiter = ',')]
        ends: Vec<f32>,
        #[arg(long, default_value_t = 50.0)]
        min_bpm: f32,
        #[arg(long, default_value_t = 200.0)]
        max_bpm: f32,
    },
    /// Generate drum pattern with style and MIDI export
    Generate {
        #[arg(long)] style: String,
        #[arg(long)] label: String,
        #[arg(long)] bars: usize,
        #[arg(long)] bpm: f32,
        #[arg(long, default_value_t = 42)] seed: u64,
        #[arg(long, default_value_t = 0.6)] density: f32,
        #[arg(long, default_value_t = 0.10)] swing: f32,
        #[arg(long, default_value_t = 0.15)] humanize: f32,
        #[arg(long, default_value = "off")] swing_preset: String,
        #[arg(long, default_value = "flat")] vel_preset: String,
        #[arg(long, default_value = "random")] fill_preset: String,
    },
    /// Full analysis: beats, bars, meter, tempo, sections (SongMap)
    AnalyzeFull {
        file: PathBuf,
    },
}

#[derive(Serialize)]
struct PeaksOut {
    sr: u32,
    duration: f32,
    peaks: Vec<f32>,
    #[serde(rename = "peaksL")]
    peaks_l: Vec<f32>,
    #[serde(rename = "peaksR")]
    peaks_r: Vec<f32>,
}
#[derive(Serialize)]
struct AnalyzeOut {
    tempo: f32,
    beats: Vec<f32>,
    onsets: Vec<f32>,
}
#[derive(Serialize)]
struct SectionTempoResult {
    start: f32,
    end: f32,
    tempo: f32,
    confidence: f32,
    candidates: Vec<f32>,
}
#[derive(Serialize)]
struct AnalyzeSectionsOut {
    results: Vec<SectionTempoResult>,
}

#[derive(Serialize)]
struct SectionizeOut {
    sections: Vec<sectionize::Section>,
}

#[derive(Serialize)]
struct SmartOut { 
    sections: Vec<sectionize_smart::SmartSection> 
}

#[derive(Serialize)]
struct GenerateOut {
    notes: Vec<generator::Note>,
    midi_base64: String,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Peaks { file, max_points } => {
            let ((l, r), sr) = decoder::decode_to_stereo_f32(&file)?;
            let duration = l.len() as f32 / sr as f32;
            let peaks_l = dsp::downsample_peaks(&l, max_points);
            let peaks_r = dsp::downsample_peaks(&r, max_points);

            let mut mono = Vec::<f32>::with_capacity(l.len().min(r.len()));
            for (a, b) in l.iter().zip(r.iter()) {
                mono.push((a + b) * 0.5);
            }
            let peaks = dsp::downsample_peaks(&mono, max_points);

            serde_json::to_writer(
                std::io::stdout(),
                &PeaksOut {
                    sr,
                    duration,
                    peaks,
                    peaks_l,
                    peaks_r,
                },
            )?;
        }
        Cmd::Analyze { file, min_bpm, max_bpm } => {
            let (pcm, sr) = decoder::decode_to_mono_f32(&file)?;
            let cfg = dsp::AnalysisConfig { win: 1024, hop: 512, min_bpm, max_bpm };
            let (tempo, beats, onsets) = dsp::analyze(&pcm, sr, cfg);
            serde_json::to_writer(std::io::stdout(), &AnalyzeOut { tempo, beats, onsets })?;
        }
        Cmd::Sectionize { file, min_section_sec } => {
            let (pcm, sr) = decoder::decode_to_mono_f32(&file)?;
            let sections = sectionize::sectionize_audio(&pcm, sr, min_section_sec);
            serde_json::to_writer(std::io::stdout(), &SectionizeOut { sections })?;
        }
        Cmd::SectionizeSmart { file, bpm, min_bars, max_bars } => {
            let (pcm, sr) = decoder::decode_to_mono_f32(&file)?;
            let sections = sectionize_smart::sectionize_smart(&pcm, sr, bpm, min_bars, max_bars);
            let output = SmartOut { sections };
            serde_json::to_writer(std::io::stdout(), &output)?;
        }
        Cmd::AnalyzeSections { file, starts, ends, min_bpm, max_bpm } => {
            let (pcm, sr) = decoder::decode_to_mono_f32(&file)?;
            
            if starts.len() != ends.len() {
                anyhow::bail!("starts and ends must have the same length");
            }
            
            let cfg = dsp::AnalysisConfig {
                win: 1024,
                hop: 512,
                min_bpm,
                max_bpm,
            };
            
            let results: Vec<SectionTempoResult> = starts
                .iter()
                .zip(ends.iter())
                .map(|(&start, &end)| {
                    let (tempo, confidence, candidates) = dsp::analyze_segment(&pcm, sr, start, end, cfg);
                    SectionTempoResult {
                        start,
                        end,
                        tempo,
                        confidence,
                        candidates,
                    }
                })
                .collect();
            
            let output = AnalyzeSectionsOut { results };
            serde_json::to_writer(std::io::stdout(), &output)?;
        }
        Cmd::Generate { style, label, bars, bpm, seed, density, swing, humanize, swing_preset, vel_preset, fill_preset } => {
            let grid_sec = (60.0 / bpm) / 16.0; // 1/64 note grid
            let duration = bars as f32 * (60.0 / bpm) * 4.0; // bars to seconds
            let params = generator::GenParams {
                bpm, density, swing, humanize, grid_sec, seed,
                style: generator::Style::from_str(&style),
                label: generator::SectionLabel::from_str(&label),
                swing_preset: generator::SwingPreset::from_str(&swing_preset),
                vel_preset: generator::VelPreset::from_str(&vel_preset),
                fill_preset: generator::FillPreset::from_str(&fill_preset),
                
                // Velocity controls - reasonable defaults
                drum_velocity: 0.8,
                cymbal_velocity: 0.7,
                kick_velocity: 0.9,
                snare_velocity: 0.85,
                tom_velocity: 0.8,
                hihat_velocity: 0.7,
                crash_velocity: 0.8,
                ride_velocity: 0.7,
                
                // Density controls
                drum_density: 0.5,
                cymbal_density: 0.5,
                hihat_density: 0.7,
                ride_density: 0.3,
                crash_density: 0.2,
                
                // Fill controls
                fill_density: 0.6,
                fill_location: generator::FillLocation::Auto,
                fill_frequency: 4,
                
                // Hi-hat complexity
                hihat_complexity: 0.5,
                hihat_pattern: generator::HiHatPattern::Standard,
                hihat_open_ratio: 0.2,
                hihat_ghost_notes: 0.3,
                
                // Ride cymbal
                ride_complexity: 0.5,
                ride_pattern: generator::RidePattern::Rock,
                ride_vs_hihat_ratio: 0.3,
                ride_bell_ratio: 0.1,
                
                // Bass line reference
                bass_line_mode: generator::BassLineMode::Ignore,
                bass_kick_sync: 0.5,
                bass_lock_downbeats: true,
                
                // Additional controls
                tom_usage: 0.3,
                crash_frequency: 0.2,
                ghost_note_density: 0.2,
                dynamic_range: 0.5,
            };
            let notes = generator::generate_section(0.0, duration, true, true, params);
            let midi = midi::notes_to_midi(&notes, bpm, grid_sec);
            let b64 = B64.encode(midi);
            serde_json::to_writer(std::io::stdout(), &serde_json::json!({
                "notes": notes, 
                "midi": b64
            }))?;
        }
        Cmd::AnalyzeFull { file } => {
            let (pcm, sr) = decoder::decode_to_mono_f32(&file)?;
            
            // Use the new analyze_full function from lib
            use bar::{Bar, group_beats_into_bars};
            use meter::detect_meter;
            use sectionize_smart::SmartSection;
            
            let duration_sec = pcm.len() as f32 / sr as f32;
            
            // 1) Basic beat/tempo/onset analysis
            let cfg = dsp::AnalysisConfig {
                win: 1024,
                hop: 512,
                min_bpm: 60.0,
                max_bpm: 200.0,
            };
            let (tempo_global, beats, _onsets) = dsp::analyze(&pcm, sr, cfg);
            
            // 2) Compute per-beat energy for meter detection
            let beat_energy = dsp::estimate_beat_energy(&pcm, sr, &beats);
            
            let meter_segments = detect_meter(&beat_energy, beats.len());
            let meter = meter_segments.first().map(|m| m.meter).unwrap_or((4, 4));
            
            // 3) Group beats into bars
            let bars = group_beats_into_bars(&beats, &meter_segments);
            
            // 4) Sectionize using existing enhanced sectionization
            let sections = sectionize_smart::sectionize_smart(&pcm, sr, tempo_global, 4, 16);
            
            // Build SongMap
            #[derive(Serialize)]
            struct SongMapOutput {
                duration: f32,
                global_bpm_estimate: f32,
                meter: (u32, u32),
                bars: Vec<Bar>,
                sections: Vec<SmartSection>,
                beat_times: Vec<f32>,
            }
            
            let song_map = SongMapOutput {
                duration: duration_sec,
                global_bpm_estimate: tempo_global,
                meter,
                bars,
                sections,
                beat_times: beats,
            };
            
            serde_json::to_writer(std::io::stdout(), &song_map)?;
        }
    }
    Ok(())
}
