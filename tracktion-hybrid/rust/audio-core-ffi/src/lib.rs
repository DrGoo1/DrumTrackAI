//! C ABI for Tracktion/JUCE. Returns heap-allocated C strings (JSON or base64).
//! Caller must free with `ac_free`.

use anyhow::Result;
use libc::c_char;
use serde::Serialize;
use std::{ffi::{CStr, CString}, os::raw::c_int, path::Path};

mod decoder;
mod dsp; // reuse your spectral flux / tempo / peaks code

// --------------------- helpers ---------------------
fn cstring(s: String) -> *const c_char { CString::new(s).unwrap().into_raw() }
fn cstr_to_str<'a>(p: *const c_char) -> Result<&'a str> {
    unsafe { CStr::from_ptr(p) }.to_str().map_err(|e| e.into())
}

static mut LAST_ERR: Option<String> = None;
fn set_err(e: impl std::fmt::Display) { unsafe { LAST_ERR = Some(e.to_string()); } }

fn ok_json<T: Serialize>(v: &T) -> *const c_char {
    match serde_json::to_string(v) { Ok(s) => cstring(s), Err(e) => { set_err(e); cstring("{}".into()) } }
}

#[no_mangle]
pub extern "C" fn ac_last_error() -> *const c_char {
    let s = unsafe { LAST_ERR.take().unwrap_or_default() };
    cstring(s)
}

#[no_mangle]
pub extern "C" fn ac_free(p: *const c_char) {
    if p.is_null() { return; }
    unsafe { let _ = CString::from_raw(p as *mut c_char); }
}

#[no_mangle]
pub extern "C" fn ac_version() -> *const c_char {
    cstring("audio-core-ffi 0.2.0".into())
}

// --------------------- Peaks -----------------------
#[derive(Serialize)]
struct PeaksOut { sr: u32, duration: f32, peaks: Vec<f32> }

#[no_mangle]
pub extern "C" fn ac_peaks(path: *const c_char, max_points: c_int) -> *const c_char {
    let res: Result<_> = (|| {
        let path = cstr_to_str(path)?; let p = Path::new(path);
        let (pcm, sr) = decoder::decode_to_mono_f32(p)?;
        let duration = pcm.len() as f32 / sr as f32;
        let peaks = dsp::downsample_peaks(&pcm, max_points.max(0) as usize);
        Ok(PeaksOut { sr, duration, peaks })
    })();
    match res { Ok(o) => ok_json(&o), Err(e) => { set_err(e); cstring("{}".into()) } }
}

// --------------------- Analyze ----------------------
#[derive(Serialize)]
struct AnalyzeOut { tempo: f32, beats: Vec<f32>, onsets: Vec<f32> }

#[no_mangle]
pub extern "C" fn ac_analyze(path: *const c_char, min_bpm: f32, max_bpm: f32) -> *const c_char {
    let res: Result<_> = (|| {
        let path = cstr_to_str(path)?; let p = Path::new(path);
        let (pcm, sr) = decoder::decode_to_mono_f32(p)?;
        let cfg = dsp::AnalysisConfig { win: 1024, hop: 512, min_bpm, max_bpm };
        let (tempo, beats, onsets) = dsp::analyze(&pcm, sr, cfg);
        Ok(AnalyzeOut { tempo, beats, onsets })
    })();
    match res { Ok(o) => ok_json(&o), Err(e) => { set_err(e); cstring("{}".into()) } }
}

// ---------------- Sectionize Smart ------------------
#[derive(Serialize)]
struct Section { start: f32, end: f32, label: String }
#[derive(Serialize)]
struct SectionsOut { bpm: f32, sections: Vec<Section> }

#[no_mangle]
pub extern "C" fn ac_sectionize_smart(path: *const c_char, bpm: f32, min_bars: c_int, max_bars: c_int) -> *const c_char {
    let res: Result<_> = (|| {
        let path = cstr_to_str(path)?; let p = Path::new(path);
        let (pcm, sr) = decoder::decode_to_mono_f32(p)?;
        let (_flux, _times) = dsp::spectral_flux_for_ui(&pcm, sr, 1024, 512); // helper you can expose
        let dur = pcm.len() as f32 / sr as f32;
        // Minimal but musical:  derive bar length from bpm, split into 8–16 bar chunks
        let spb = 60.0 / bpm.max(1.0);
        let bars = (dur / (spb * 4.0)).max(1.0);
        let target = bars.clamp(min_bars.max(4) as f32, max_bars.max(8) as f32);
        let seg_len = (dur / (target.max(1.0))).max(spb * 4.0);
        let mut secs = Vec::new();
        let mut t = 0.0f32; let mut i = 0;
        while t < dur {
            let e = (t + seg_len).min(dur);
            let label = match i { 0 => "intro", 1|2 => "verse", 3 => "chorus", _ => if e + 8.0 >= dur { "outro" } else { "bridge" } }.to_string();
            secs.push(Section { start: t, end: e, label });
            t = e; i += 1;
        }
        Ok(SectionsOut { bpm, sections: secs })
    })();
    match res { Ok(o) => ok_json(&o), Err(e) => { set_err(e); cstring("{}".into()) } }
}

// ----------------- Generate (notes) -----------------
#[derive(Serialize, Clone)]
struct Note { lane: String, time: f32, len: f32, vel: u8 }

impl From<dsp::Note> for Note {
    fn from(n: dsp::Note) -> Self {
        Note {
            lane: n.lane,
            time: n.time,
            len: n.len,
            vel: n.vel,
        }
    }
}
#[derive(Serialize)]
struct GenOut { notes: Vec<Note> }

#[no_mangle]
pub extern "C" fn ac_generate_json(params_json: *const c_char) -> *const c_char {
    let res: Result<_> = (|| {
        // params: { bpm,start,end,style,label,density,swing,humanize,seed,swing_preset,vel_preset,fill_preset }
        let s = cstr_to_str(params_json)?;
        let v: serde_json::Value = serde_json::from_str(s)?;
        let bpm = v.get("bpm").and_then(|x| x.as_f64()).unwrap_or(120.0) as f32;
        let start = v.get("start").and_then(|x| x.as_f64()).unwrap_or(0.0) as f32;
        let end = v.get("end").and_then(|x| x.as_f64()).unwrap_or(8.0) as f32;
        let style = v.get("style").and_then(|x| x.as_str()).unwrap_or("rock").to_string();
        let label = v.get("label").and_then(|x| x.as_str()).unwrap_or("verse").to_string();
        let density = v.get("density").and_then(|x| x.as_f64()).unwrap_or(0.6) as f32;
        let swing_amt = v.get("swing").and_then(|x| x.as_f64()).unwrap_or(0.1) as f32;
        let human = v.get("humanize").and_then(|x| x.as_f64()).unwrap_or(0.12) as f32;
        let seed = v.get("seed").and_then(|x| x.as_i64()).unwrap_or(42) as u64;
        let swing_preset = v.get("swing_preset").and_then(|x| x.as_str()).unwrap_or("off");
        let vel_preset = v.get("vel_preset").and_then(|x| x.as_str()).unwrap_or("flat");
        let fill_preset = v.get("fill_preset").and_then(|x| x.as_str()).unwrap_or("random");

        let notes = dsp::generate_drums(bpm, start, end, &style, &label, density, swing_amt, human, seed, swing_preset, vel_preset, fill_preset);
        let converted_notes: Vec<Note> = notes.into_iter().map(Note::from).collect();
        Ok(GenOut { notes: converted_notes })
    })();
    match res { Ok(o) => ok_json(&o), Err(e) => { set_err(e); cstring("{}".into()) } }
}

// ------------- Generate base64 MIDI (Type-1) --------
use base64;
#[no_mangle]
pub extern "C" fn ac_generate_midi64(params_json: *const c_char) -> *const c_char {
    let res: Result<_> = (|| {
        let s = cstr_to_str(params_json)?;
        let v: serde_json::Value = serde_json::from_str(s)?;
        let bpm = v.get("bpm").and_then(|x| x.as_f64()).unwrap_or(120.0) as f32;
        let start = v.get("start").and_then(|x| x.as_f64()).unwrap_or(0.0) as f32;
        let end = v.get("end").and_then(|x| x.as_f64()).unwrap_or(8.0) as f32;
        let style = v.get("style").and_then(|x| x.as_str()).unwrap_or("rock").to_string();
        let label = v.get("label").and_then(|x| x.as_str()).unwrap_or("verse").to_string();
        let density = v.get("density").and_then(|x| x.as_f64()).unwrap_or(0.6) as f32;
        let swing_amt = v.get("swing").and_then(|x| x.as_f64()).unwrap_or(0.1) as f32;
        let human = v.get("humanize").and_then(|x| x.as_f64()).unwrap_or(0.12) as f32;
        let seed = v.get("seed").and_then(|x| x.as_i64()).unwrap_or(42) as u64;
        let swing_preset = v.get("swing_preset").and_then(|x| x.as_str()).unwrap_or("off");
        let vel_preset = v.get("vel_preset").and_then(|x| x.as_str()).unwrap_or("flat");
        let fill_preset = v.get("fill_preset").and_then(|x| x.as_str()).unwrap_or("random");

        let notes = dsp::generate_drums(bpm, start, end, &style, &label, density, swing_amt, human, seed, swing_preset, vel_preset, fill_preset);
        let midi_bytes = dsp::notes_to_type1_midi(&notes, bpm as f64);
        use base64::Engine;
        Ok(base64::engine::general_purpose::STANDARD.encode(midi_bytes))
    })();
    match res { Ok(b64) => cstring(b64), Err(e) => { set_err(e); cstring("".into()) } }
}
