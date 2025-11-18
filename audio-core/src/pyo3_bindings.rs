use pyo3::prelude::*;
use pyo3::types::PyDict;
use crate::decoder::decode_audio;
use crate::dsp::{analyze, AnalysisConfig};
use crate::generator::{generate_pattern, GeneratorConfig};
use crate::midi::notes_to_midi;
use crate::sectionize_smart::sectionize_smart;
use base64::{Engine as _, engine::general_purpose};

#[pyfunction]
fn audio_peaks(path: String, max_points: usize) -> PyResult<Vec<f32>> {
    let (pcm, _sr) = decode_audio(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Decode error: {}", e)))?;
    
    Ok(crate::dsp::downsample_peaks(&pcm, max_points))
}

#[pyfunction]
fn audio_analyze(path: String, min_bpm: f32, max_bpm: f32) -> PyResult<(f32, Vec<f32>, Vec<f32>)> {
    let (pcm, sr) = decode_audio(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Decode error: {}", e)))?;
    
    let cfg = AnalysisConfig {
        win: 2048,
        hop: 512,
        min_bpm,
        max_bpm,
    };
    
    Ok(analyze(&pcm, sr, cfg))
}

#[pyfunction]
fn audio_sectionize_smart(
    path: String,
    bpm: f32,
    min_bars: usize,
    max_bars: usize
) -> PyResult<Vec<(f32, f32, String)>> {
    let (pcm, sr) = decode_audio(&path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Decode error: {}", e)))?;
    
    Ok(sectionize_smart(&pcm, sr, bpm, min_bars, max_bars))
}

#[pyfunction]
fn drum_generate(
    style: String,
    label: String,
    bars: usize,
    bpm: f32,
    seed: u64
) -> PyResult<String> {
    let cfg = GeneratorConfig {
        style,
        label,
        bars,
        bpm,
        seed,
        density: 0.7,
        humanize: 0.1,
        swing: 0.0,
        fills: true,
    };
    
    let notes = generate_pattern(cfg);
    let grid_sec = 60.0 / bpm / 16.0; // 1/16 note grid
    let midi_bytes = notes_to_midi(&notes, bpm, grid_sec);
    
    Ok(general_purpose::STANDARD.encode(&midi_bytes))
}

#[pymodule]
fn audio_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(audio_peaks, m)?)?;
    m.add_function(wrap_pyfunction!(audio_analyze, m)?)?;
    m.add_function(wrap_pyfunction!(audio_sectionize_smart, m)?)?;
    m.add_function(wrap_pyfunction!(drum_generate, m)?)?;
    Ok(())
}
