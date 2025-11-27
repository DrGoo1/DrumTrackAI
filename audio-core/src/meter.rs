// audio-core/src/meter.rs
use crate::bar::MeterSegment;

/// Detect two simple meters: 4/4 vs 3/4.
/// `beat_energy` is a per-beat energy/accent measure (0–1).
pub fn detect_meter(
    beat_energy: &[f32],
    n_beats: usize,
) -> Vec<MeterSegment> {
    if n_beats == 0 || beat_energy.is_empty() {
        return vec![MeterSegment {
            start_beat: 0,
            end_beat: 0,
            meter: (4, 4),
            confidence: 0.0,
        }];
    }

    let accents = beat_energy;

    let score_3_4 = test_meter_hypothesis(accents, 3);
    let score_4_4 = test_meter_hypothesis(accents, 4);

    let (meter, conf) = if score_3_4 > score_4_4 * 1.1 {
        let denom = score_3_4 + score_4_4 + 1e-6;
        ((3, 4), score_3_4 / denom)
    } else {
        let denom = score_3_4 + score_4_4 + 1e-6;
        ((4, 4), score_4_4 / denom)
    };

    vec![MeterSegment {
        start_beat: 0,
        end_beat: n_beats,
        meter,
        confidence: conf,
    }]
}

fn test_meter_hypothesis(accents: &[f32], beats_per_bar: usize) -> f32 {
    if beats_per_bar == 0 {
        return 0.0;
    }

    let n_bars = accents.len() / beats_per_bar;
    if n_bars == 0 {
        return 0.0;
    }

    let mut score = 0.0;
    for bar_idx in 0..n_bars {
        let start = bar_idx * beats_per_bar;
        if start + beats_per_bar > accents.len() {
            break;
        }

        let bar_accents = &accents[start..start + beats_per_bar];

        let downbeat = bar_accents[0];
        let avg_rest = if beats_per_bar > 1 {
            bar_accents[1..].iter().sum::<f32>() / (beats_per_bar - 1) as f32
        } else {
            0.0
        };

        if downbeat > avg_rest {
            score += (downbeat - avg_rest).max(0.0);
        }
    }

    score / (n_bars as f32)
}
