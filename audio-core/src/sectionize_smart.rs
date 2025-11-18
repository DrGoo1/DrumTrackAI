use crate::dsp::{self};
use serde::Serialize;

#[derive(Serialize, Clone)]
pub struct SmartSection { pub start: f32, pub end: f32, pub label: String }

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

    if beats.len() < 4 { return vec![SmartSection{ start:0.0, end:duration, label:"section".into() }]; }

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
    // moving average
    let ma = |v:&[f32], w:usize| -> Vec<f32> { let n=v.len(); let mut o=vec![0.0;n]; let w= w.max(1); for i in 0..n { let a=i.saturating_sub(w); let b=(i+w).min(n-1); let mut s=0.0; let mut c=0; for j in a..=b { s+=v[j]; c+=1; } o[i]=s/(c as f32);} o };
    let env = ma(&beat_energy, 4);

    // find valleys: energy below env*0.9 and local minima
    let mut cuts: Vec<usize> = vec![0];
    for i in 2..env.len()-2 {
        if beat_energy[i] < env[i]*0.90 && beat_energy[i] <= beat_energy[i-1] && beat_energy[i] <= beat_energy[i+1] {
            cuts.push(i);
        }
    }
    cuts.push(beats.len()-1);

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
                out.push(SmartSection{ start:s, end:e.min(duration), label: "section".into() });
                i = j; break;
            }
            j += 1;
        }
        if j == cuts.len() { break; }
    }
    if out.is_empty() { out.push(SmartSection{ start:0.0, end:duration, label:"section".into() }); }

    // label heuristics by energy: highest average env → chorus, first low → intro, last low → outro
    let avg_env = |a:f32,b:f32| {
        let mut acc=0.0; let mut c=0; for (&bt, &en) in beats.iter().zip(env.iter()) { if bt>=a && bt<b { acc+=en; c+=1; } } if c>0 { acc/(c as f32) } else { 0.0 }
    };
    let mut scores: Vec<f32> = out.iter().map(|s| avg_env(s.start,s.end)).collect();
    if let Some((idx,_)) = scores.iter().enumerate().max_by(|a,b| a.1.partial_cmp(b.1).unwrap()) { out[idx].label = "chorus".into(); }
    if !out.is_empty() { out[0].label = if scores.get(0).copied().unwrap_or(0.0) < 0.5 { "intro".into() } else { out[0].label.clone() }; }
    if out.len()>=2 { let last = out.len()-1; if scores.get(last).copied().unwrap_or(0.0) < 0.5 { out[last].label = "outro".into(); } }
    for s in &mut out { if s.label == "section" { s.label = "verse".into(); } }
    out
}

fn render_beats(bpm: f32, duration: f32, seed_start: f32) -> Vec<f32> {
    if bpm <= 0.0 { return vec![]; } let spb = 60.0 / bpm; let mut t0=(seed_start/spb).round()*spb; if t0<0.0 { t0=0.0; }
    let mut v=Vec::new(); let mut t=t0; while t<=duration { v.push(t); t+=spb;} v
}
