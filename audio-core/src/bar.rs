// audio-core/src/bar.rs
use serde::Serialize;

#[derive(Serialize, Clone, Debug)]
pub struct Bar {
    /// Bar index (0-based)
    pub index: u32,

    /// Start time in seconds
    pub start_time: f32,

    /// End time in seconds
    pub end_time: f32,

    /// Time signature (numerator, denominator)
    pub meter: (u32, u32),

    /// Tempo for this bar in BPM
    pub tempo_bpm: f32,

    /// Beat times within this bar
    pub beat_times: Vec<f32>,

    /// Overall confidence (0–1)
    pub confidence: f32,
}

impl Bar {
    pub fn new(index: u32, beats: &[f32], meter: (u32, u32), beat_conf: Option<f32>) -> Self {
        debug_assert!(beats.len() >= 2, "Bar must contain at least 2 beats");

        let start_time = beats[0];
        let end_time = *beats.last().unwrap();
        let duration = (end_time - start_time).max(1e-6);
        let beats_per_bar = meter.0 as f32;
        let tempo_bpm = 60.0 * beats_per_bar / duration;

        // Placeholder for now – we could combine beat + meter confidence later.
        let confidence = beat_conf.unwrap_or(0.85);

        Self {
            index,
            start_time,
            end_time,
            meter,
            tempo_bpm,
            beat_times: beats.to_vec(),
            confidence,
        }
    }
}

#[derive(Clone, Debug)]
pub struct MeterSegment {
    pub start_beat: usize,
    pub end_beat: usize,
    pub meter: (u32, u32),
    pub confidence: f32,
}

impl MeterSegment {
    pub fn beats_per_bar(&self) -> usize {
        self.meter.0 as usize
    }
}

pub fn group_beats_into_bars(
    beat_times: &[f32],
    meter_segments: &[MeterSegment],
) -> Vec<Bar> {
    let mut bars = Vec::new();

    if beat_times.len() < 2 {
        return bars;
    }

    for seg in meter_segments {
        let beats_per_bar = seg.beats_per_bar().max(1);
        let start = seg.start_beat.min(beat_times.len());
        let end = seg.end_beat.min(beat_times.len());

        let mut idx = start;
        while idx + beats_per_bar <= end {
            let chunk = &beat_times[idx..idx + beats_per_bar];
            let bar_index = bars.len() as u32;
            let bar = Bar::new(bar_index, chunk, seg.meter, Some(seg.confidence));
            bars.push(bar);
            idx += beats_per_bar;
        }
    }

    bars
}
