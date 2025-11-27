use crate::dsp::{self};
use serde::Serialize;

#[derive(Serialize, Clone, Debug)]
pub struct SmartSection { 
    pub start: f32, 
    pub end: f32, 
    pub label: String,
    pub energy: f32,
    pub spectral_centroid: f32,
}

/// Simple smart sectionization:
/// 1) spectral-flux → per-beat energy
/// 2) find valleys under moving average as boundaries
/// 3) snap to nearest beat; enforce min/max bars per section
pub fn sectionize_smart(pcm: &[f32], sr: u32, bpm: f32, min_bars: u32, max_bars: u32) -> Vec<SmartSection> {
    let (tempo, _beats, flux) = dsp::analyze(pcm, sr, dsp::AnalysisConfig{win:1024, hop:512, min_bpm:50.0, max_bpm:200.0});
    let (flux_vals, frame_times) = dsp::spectral_flux(pcm, sr, 1024, 512);
    let tempo = bpm.max(40.0).min(260.0);
    // Recompute beats with requested bpm to be deterministic
    let duration = pcm.len() as f32 / sr as f32;
    let beats = render_beats(tempo, duration, 0.0);

    if beats.len() < 4 { 
        return vec![SmartSection{ 
            start:0.0, 
            end:duration, 
            label:"section".into(),
            energy: 0.5,
            spectral_centroid: 0.5,
        }]; 
    }

    // Map flux (frame grid) to beats using nearest neighbor
    let mut beat_energy: Vec<f32> = Vec::with_capacity(beats.len());
    for &bt in &beats {
        // average flux within +/- 0.1s window
        let mut acc = 0.0f32; let mut cnt = 0u32;
        for (i, &ft) in frame_times.iter().enumerate() {
            if (ft - bt).abs() <= 0.1 { acc += flux_vals[i].max(0.0); cnt += 1; }
        }
        beat_energy.push(if cnt>0 { acc/(cnt as f32) } else { 0.0 });
    }
    // moving average with LARGER window for musical sections (not micro-changes)
    let ma = |v:&[f32], w:usize| -> Vec<f32> { let n=v.len(); let mut o=vec![0.0;n]; let w= w.max(1); for i in 0..n { let a=i.saturating_sub(w); let b=(i+w).min(n-1); let mut s=0.0; let mut c=0; for j in a..=b { s+=v[j]; c+=1; } o[i]=s/(c as f32);} o };
    let env = ma(&beat_energy, 16); // 16 beats = ~4 bars for more stable detection

    // find valleys: SIGNIFICANT energy drops only (not small variations)
    let mut cuts: Vec<usize> = vec![0];
    for i in 8..env.len()-8 { // Skip near start/end
        // Require deeper valley (0.75 instead of 0.90) and wider local minimum
        if beat_energy[i] < env[i]*0.75 && 
           beat_energy[i] <= beat_energy[i-2] && 
           beat_energy[i] <= beat_energy[i+2] {
            cuts.push(i);
        }
    }
    cuts.push(beats.len()-1);

    // Helper function to calculate average energy for a time range
    let avg_env = |a:f32, b:f32, beats: &[f32], env: &[f32]| {
        let mut acc=0.0; let mut c=0; 
        for (&bt, &en) in beats.iter().zip(env.iter()) { 
            if bt>=a && bt<b { acc+=en; c+=1; } 
        } 
        if c>0 { acc/(c as f32) } else { 0.0 }
    };
    
    // enforce min/max bars per section
    let spb = 60.0/tempo; // seconds per beat
    let bars_from_beats = |beats_span:usize| -> f32 { (beats_span as f32)/4.0 }; // assume 4/4
    let mut out: Vec<SmartSection> = Vec::new();
    let mut i = 0usize;
    while i+1 < cuts.len() {
        let mut j = i+1;
        while j < cuts.len() {
            let beats_span = cuts[j] - cuts[i];
            let bars = bars_from_beats(beats_span);
            if bars >= min_bars as f32 && (bars <= max_bars as f32 || j+1==cuts.len()) {
                let s = beats[cuts[i]]; let e = beats[cuts[j]].max(s + spb*4.0*min_bars as f32);
                let section_energy = avg_env(s, e.min(duration), &beats, &env);
                let section_centroid = calculate_spectral_centroid(pcm, sr, s, e.min(duration));
                out.push(SmartSection{ 
                    start:s, 
                    end:e.min(duration), 
                    label: "section".into(),
                    energy: section_energy,
                    spectral_centroid: section_centroid,
                });
                i = j; break;
            }
            j += 1;
        }
        if j == cuts.len() { break; }
    }
    if out.is_empty() { 
        out.push(SmartSection{ 
            start:0.0, 
            end:duration, 
            label:"section".into(),
            energy: 0.5,
            spectral_centroid: 0.5,
        }); 
    }

    // Improved labeling with repetition detection
    label_sections_smart(&mut out, pcm, sr);
    out
}

fn render_beats(bpm: f32, duration: f32, seed_start: f32) -> Vec<f32> {
    if bpm <= 0.0 { return vec![]; } 
    let spb = 60.0 / bpm; 
    let mut t0=(seed_start/spb).round()*spb; 
    if t0<0.0 { t0=0.0; }
    let mut v=Vec::new(); 
    let mut t=t0; 
    while t<=duration { 
        v.push(t); 
        t+=spb;
    } 
    v
}

/// Calculate spectral centroid for a time segment
fn calculate_spectral_centroid(pcm: &[f32], sr: u32, start_sec: f32, end_sec: f32) -> f32 {
    let start_frame = (start_sec * sr as f32) as usize;
    let end_frame = (end_sec * sr as f32) as usize;
    
    let start_frame = start_frame.min(pcm.len());
    let end_frame = end_frame.min(pcm.len());
    
    if start_frame >= end_frame || end_frame - start_frame < 2048 {
        return 0.5; // Default neutral value
    }
    
    let segment = &pcm[start_frame..end_frame];
    
    // Use FFT to calculate spectral centroid
    use realfft::RealFftPlanner;
    let mut planner = RealFftPlanner::<f32>::new();
    let fft_size = 2048.min(segment.len());
    let r2c = planner.plan_fft_forward(fft_size);
    let mut input = r2c.make_input_vec();
    let mut spectrum = r2c.make_output_vec();
    
    // Copy data and window
    for i in 0..fft_size {
        input[i] = segment[i] * (std::f32::consts::PI * 2.0 * i as f32 / (fft_size as f32 - 1.0)).sin().powi(2);
    }
    
    r2c.process(&mut input, &mut spectrum).unwrap();
    
    // Calculate centroid
    let mut weighted_sum = 0.0f32;
    let mut total_mag = 0.0f32;
    
    for (i, c) in spectrum.iter().enumerate() {
        let mag = c.norm();
        let freq = i as f32 * sr as f32 / fft_size as f32;
        weighted_sum += freq * mag;
        total_mag += mag;
    }
    
    if total_mag > 1e-6 {
        let centroid = weighted_sum / total_mag;
        // Normalize to 0-1 range (assuming Nyquist frequency as max)
        (centroid / (sr as f32 / 2.0)).min(1.0)
    } else {
        0.5
    }
}

/// Improved section labeling with repetition detection
fn label_sections_smart(sections: &mut [SmartSection], pcm: &[f32], sr: u32) {
    if sections.is_empty() {
        return;
    }
    
    // Find repeated sections (likely choruses)
    let repetition_groups = find_repeated_sections(sections, pcm, sr);
    
    // Label repeated sections as chorus
    let mut chorus_candidates: Vec<usize> = Vec::new();
    for group in &repetition_groups {
        if group.len() >= 2 {
            // This section repeats - likely a chorus
            for &idx in group {
                chorus_candidates.push(idx);
            }
        }
    }
    
    // Among chorus candidates, pick the ones with highest energy
    let mut candidate_energies: Vec<(usize, f32)> = chorus_candidates
        .iter()
        .map(|&idx| (idx, sections[idx].energy))
        .collect();
    candidate_energies.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    
    // Label top energy repeated sections as chorus
    for (idx, _) in candidate_energies.iter().take(3) {
        sections[*idx].label = "chorus".into();
    }
    
    // First section heuristics
    if sections[0].energy < 0.4 || sections[0].end - sections[0].start < 10.0 {
        sections[0].label = "intro".into();
    }
    
    // Last section heuristics
    let last_idx = sections.len() - 1;
    if sections[last_idx].energy < 0.4 || sections[last_idx].end - sections[last_idx].start < 15.0 {
        sections[last_idx].label = "outro".into();
    }
    
    // Bridge detection: middle section with contrasting energy
    if sections.len() >= 5 {
        let mid_start = sections.len() / 3;
        let mid_end = (sections.len() * 2) / 3;
        
        for i in mid_start..mid_end {
            if sections[i].label == "section" {
                // Check if energy is notably different from neighbors
                let prev_energy = if i > 0 { sections[i-1].energy } else { sections[i].energy };
                let next_energy = if i < sections.len()-1 { sections[i+1].energy } else { sections[i].energy };
                let avg_neighbor = (prev_energy + next_energy) / 2.0;
                
                if (sections[i].energy - avg_neighbor).abs() > 0.15 && sections[i].spectral_centroid > 0.6 {
                    sections[i].label = "bridge".into();
                    break; // Only one bridge
                }
            }
        }
    }
    
    // Pre-chorus detection: sections before chorus with rising energy
    for i in 0..sections.len()-1 {
        if sections[i+1].label == "chorus" && sections[i].label == "section" {
            // Check if this section has rising energy trend
            if sections[i].energy > 0.5 && sections[i].energy < sections[i+1].energy {
                sections[i].label = "pre-chorus".into();
            }
        }
    }
    
    // Label remaining sections more carefully
    // Only call it verse if it has moderate energy and isn't too short
    for section in sections.iter_mut() {
        if section.label == "section" {
            if section.energy > 0.25 && section.energy < 0.75 && (section.end - section.start) > 10.0 {
                section.label = "verse".into();
            } else if section.energy <= 0.15 {
                // Only very quiet sections are interludes
                section.label = "interlude".into();
            } else {
                // Keep as generic section if uncertain
                section.label = "verse".into();  // Default to verse for moderate sections
            }
        }
    }
}

/// Find groups of similar sections (repetition detection)
fn find_repeated_sections(sections: &[SmartSection], pcm: &[f32], sr: u32) -> Vec<Vec<usize>> {
    let mut groups: Vec<Vec<usize>> = Vec::new();
    let mut assigned = vec![false; sections.len()];
    
    for i in 0..sections.len() {
        if assigned[i] {
            continue;
        }
        
        let mut group = vec![i];
        assigned[i] = true;
        
        // Compare with later sections
        for j in (i+1)..sections.len() {
            if assigned[j] {
                continue;
            }
            
            // Calculate similarity based on energy and spectral centroid
            let energy_diff = (sections[i].energy - sections[j].energy).abs();
            let spectral_diff = (sections[i].spectral_centroid - sections[j].spectral_centroid).abs();
            let duration_diff = ((sections[i].end - sections[i].start) - (sections[j].end - sections[j].start)).abs();
            
            // Similarity threshold
            if energy_diff < 0.15 && spectral_diff < 0.2 && duration_diff < 5.0 {
                group.push(j);
                assigned[j] = true;
            }
        }
        
        if group.len() > 1 {
            groups.push(group);
        }
    }
    
    groups
}
