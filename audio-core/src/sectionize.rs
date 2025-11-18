use crate::dsp::{spectral_flux, AnalysisConfig};
use serde::Serialize;

#[derive(Serialize)]
pub struct Section {
    pub start: f32,
    pub end: f32,
    pub energy: f32,
    pub confidence: f32,
}

pub fn sectionize_audio(pcm: &[f32], sr: u32, min_section_sec: f32) -> Vec<Section> {
    if pcm.is_empty() {
        return vec![];
    }
    
    let cfg = AnalysisConfig {
        win: 2048,
        hop: 1024,
        min_bpm: 60.0,
        max_bpm: 200.0,
    };
    
    let (flux, frame_times) = spectral_flux(pcm, sr, cfg.win, cfg.hop);
    
    if flux.is_empty() {
        return vec![Section {
            start: 0.0,
            end: pcm.len() as f32 / sr as f32,
            energy: 0.5,
            confidence: 0.5,
        }];
    }
    
    // Find significant changes in spectral flux for section boundaries
    let mut boundaries = vec![0.0]; // Always start at 0
    
    // Calculate moving average for comparison
    let window_size = (sr as f32 / cfg.hop as f32 * 2.0) as usize; // ~2 second window
    let window_size = window_size.max(5).min(flux.len() / 4);
    
    for i in window_size..flux.len() - window_size {
        let before_avg: f32 = flux[i - window_size..i].iter().sum::<f32>() / window_size as f32;
        let after_avg: f32 = flux[i..i + window_size].iter().sum::<f32>() / window_size as f32;
        
        let change = (after_avg - before_avg).abs();
        let threshold = 0.3; // Significant change threshold
        
        if change > threshold {
            let time = frame_times[i];
            // Ensure minimum section length
            if boundaries.is_empty() || time - boundaries.last().unwrap() >= min_section_sec {
                boundaries.push(time);
            }
        }
    }
    
    // Always end at the total duration
    let total_duration = pcm.len() as f32 / sr as f32;
    if boundaries.is_empty() || boundaries.last().unwrap() < &(total_duration - 0.1) {
        boundaries.push(total_duration);
    }
    
    // Create sections from boundaries
    let mut sections = Vec::new();
    for i in 0..boundaries.len() - 1 {
        let start = boundaries[i];
        let end = boundaries[i + 1];
        
        // Calculate energy for this section
        let start_frame = ((start * sr as f32) / cfg.hop as f32) as usize;
        let end_frame = ((end * sr as f32) / cfg.hop as f32) as usize;
        let start_frame = start_frame.min(flux.len().saturating_sub(1));
        let end_frame = end_frame.min(flux.len());
        
        let energy = if start_frame < end_frame {
            flux[start_frame..end_frame].iter().sum::<f32>() / (end_frame - start_frame) as f32
        } else {
            0.5
        };
        
        // Confidence based on section length and energy consistency
        let length_factor = ((end - start) / 4.0).min(1.0); // Prefer 4+ second sections
        let energy_consistency = 1.0 - (energy - 0.5).abs(); // Prefer moderate energy
        let confidence = (length_factor + energy_consistency) / 2.0;
        
        sections.push(Section {
            start,
            end,
            energy,
            confidence,
        });
    }
    
    // Ensure we have at least one section
    if sections.is_empty() {
        sections.push(Section {
            start: 0.0,
            end: total_duration,
            energy: 0.5,
            confidence: 0.5,
        });
    }
    
    sections
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sectionize_empty() {
        let sections = sectionize_audio(&[], 44100, 2.0);
        assert_eq!(sections.len(), 0);
    }

    #[test]
    fn test_sectionize_short() {
        let pcm = vec![0.5; 44100]; // 1 second of audio
        let sections = sectionize_audio(&pcm, 44100, 2.0);
        assert_eq!(sections.len(), 1);
        assert_eq!(sections[0].start, 0.0);
        assert!((sections[0].end - 1.0).abs() < 0.1);
    }
}
