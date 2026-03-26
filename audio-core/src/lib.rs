pub mod decoder;
pub mod dsp;
pub mod generator;
pub mod midi;
pub mod sectionize_smart;
pub mod bar;
pub mod meter;

#[cfg(feature = "python")]
pub mod pyo3_bindings;

#[cfg(feature = "python")]
pub use pyo3_bindings::*;

use serde::Serialize;
use bar::{Bar, group_beats_into_bars};
use meter::detect_meter;
use sectionize_smart::SmartSection;

#[derive(Serialize, Clone, Debug)]
pub struct SongMap {
    pub duration: f32,
    pub global_bpm_estimate: f32,
    pub meter: (u32, u32),
    pub bars: Vec<Bar>,
    pub sections: Vec<SmartSection>,
    pub beat_times: Vec<f32>,
}

/// Full analysis: tempo, beats, bars, meter, sections
pub fn analyze_full(
    pcm: &[f32],
    sr: u32,
) -> SongMap {
    let duration_sec = pcm.len() as f32 / sr as f32;
    
    // 1) Basic beat/tempo/onset analysis
    let cfg = dsp::AnalysisConfig {
        win: 1024,
        hop: 512,
        min_bpm: 60.0,
        max_bpm: 200.0,
    };
    let (tempo_global, beats, _onsets) = dsp::analyze(pcm, sr, cfg);

    // 2) Compute per-beat energy for meter detection
    let beat_energy = dsp::estimate_beat_energy(pcm, sr, &beats);

    let meter_segments = detect_meter(&beat_energy, beats.len());
    let meter = meter_segments.first().map(|m| m.meter).unwrap_or((4, 4));

    // 3) Group beats into bars
    let bars = group_beats_into_bars(&beats, &meter_segments);

    // 4) Sectionize using existing enhanced sectionization
    // Use larger min/max bars for more musical section boundaries (not micro-changes)
    // 8 bars min = ~15-20 seconds, 32 bars max = ~60-80 seconds per section
    let sections = sectionize_smart::sectionize_smart(pcm, sr, tempo_global, 8, 32);

    SongMap {
        duration: duration_sec,
        global_bpm_estimate: tempo_global,
        meter,
        bars,
        sections,
        beat_times: beats,
    }
}
