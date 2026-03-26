use anyhow::{anyhow, Context, Result};
use symphonia::core::audio::{AudioBufferRef, SignalSpec, Signal};
use symphonia::core::codecs::DecoderOptions;
use symphonia::core::errors::Error as SymphErr;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::default::get_probe;
use std::fs::File;
use std::path::Path;

pub fn decode_to_stereo_f32(path: &Path) -> Result<((Vec<f32>, Vec<f32>), u32)> {
    let f = File::open(path).with_context(|| format!("open {:?}", path))?;
    let mss = MediaSourceStream::new(Box::new(f), Default::default());
    let probed = get_probe().format(
        &Default::default(),
        mss,
        &FormatOptions::default(),
        &MetadataOptions::default(),
    )?;
    let mut format = probed.format;
    let track = format.default_track().ok_or_else(|| anyhow!("no default track"))?;
    let sr = track.codec_params.sample_rate.ok_or_else(|| anyhow!("unknown sample rate"))?;
    let mut decoder = symphonia::default::get_codecs().make(&track.codec_params, &DecoderOptions::default())?;

    let mut left = Vec::<f32>::new();
    let mut right = Vec::<f32>::new();

    while let Ok(pkt) = format.next_packet() {
        match decoder.decode(&pkt) {
            Ok(AudioBufferRef::F32(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                if channels == 1 {
                    let c0 = buf.chan(0);
                    left.extend_from_slice(c0);
                    right.extend_from_slice(c0);
                } else {
                    let c0 = buf.chan(0);
                    let c1 = buf.chan(1);
                    for i in 0..frames {
                        left.push(c0[i]);
                        right.push(c1[i]);
                    }
                }
            }
            Ok(AudioBufferRef::U8(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                if channels == 1 {
                    for i in 0..frames {
                        let v = (buf.chan(0)[i] as f32 - 128.0) / 128.0;
                        left.push(v);
                        right.push(v);
                    }
                } else {
                    for i in 0..frames {
                        let l = (buf.chan(0)[i] as f32 - 128.0) / 128.0;
                        let r = (buf.chan(1)[i] as f32 - 128.0) / 128.0;
                        left.push(l);
                        right.push(r);
                    }
                }
            }
            Ok(AudioBufferRef::U16(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                if channels == 1 {
                    for i in 0..frames {
                        let v = (buf.chan(0)[i] as f32 - 32768.0) / 32768.0;
                        left.push(v);
                        right.push(v);
                    }
                } else {
                    for i in 0..frames {
                        let l = (buf.chan(0)[i] as f32 - 32768.0) / 32768.0;
                        let r = (buf.chan(1)[i] as f32 - 32768.0) / 32768.0;
                        left.push(l);
                        right.push(r);
                    }
                }
            }
            Ok(AudioBufferRef::S16(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                if channels == 1 {
                    for i in 0..frames {
                        let v = (buf.chan(0)[i] as f32) / 32768.0;
                        left.push(v);
                        right.push(v);
                    }
                } else {
                    for i in 0..frames {
                        let l = (buf.chan(0)[i] as f32) / 32768.0;
                        let r = (buf.chan(1)[i] as f32) / 32768.0;
                        left.push(l);
                        right.push(r);
                    }
                }
            }
            Ok(AudioBufferRef::S32(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                if channels == 1 {
                    for i in 0..frames {
                        let v = (buf.chan(0)[i] as f32) / 2147483648.0;
                        left.push(v);
                        right.push(v);
                    }
                } else {
                    for i in 0..frames {
                        let l = (buf.chan(0)[i] as f32) / 2147483648.0;
                        let r = (buf.chan(1)[i] as f32) / 2147483648.0;
                        left.push(l);
                        right.push(r);
                    }
                }
            }
            Ok(AudioBufferRef::F64(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                if channels == 1 {
                    for i in 0..frames {
                        let v = buf.chan(0)[i] as f32;
                        left.push(v);
                        right.push(v);
                    }
                } else {
                    for i in 0..frames {
                        let l = buf.chan(0)[i] as f32;
                        let r = buf.chan(1)[i] as f32;
                        left.push(l);
                        right.push(r);
                    }
                }
            }
            Ok(_) => continue,
            Err(SymphErr::DecodeError(_)) => continue,
            Err(e) => return Err(e.into()),
        }
    }

    Ok(((left, right), sr))
}

pub fn decode_to_mono_f32(path: &Path) -> Result<(Vec<f32>, u32)> {
    let f = File::open(path).with_context(|| format!("open {:?}", path))?;
    let mss = MediaSourceStream::new(Box::new(f), Default::default());
    let probed = get_probe().format(
        &Default::default(),
        mss,
        &FormatOptions::default(),
        &MetadataOptions::default(),
    )?;
    let mut format = probed.format;
    let track = format.default_track().ok_or_else(|| anyhow!("no default track"))?;
    let sr = track.codec_params.sample_rate.ok_or_else(|| anyhow!("unknown sample rate"))?;
    let mut decoder = symphonia::default::get_codecs().make(&track.codec_params, &DecoderOptions::default())?;

    let mut out = Vec::<f32>::new();
    while let Ok(pkt) = format.next_packet() {
        match decoder.decode(&pkt) {
            Ok(AudioBufferRef::F32(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                if channels == 1 {
                    out.extend_from_slice(buf.chan(0));
                } else {
                    for i in 0..frames {
                        let mut s = 0.0f32;
                        for c in 0..channels {
                            s += buf.chan(c)[i];
                        }
                        out.push(s / channels as f32);
                    }
                }
            }
            Ok(AudioBufferRef::U8(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                for i in 0..frames {
                    let mut s = 0.0f32;
                    for c in 0..channels {
                        s += (buf.chan(c)[i] as f32 - 128.0) / 128.0;
                    }
                    out.push(s / channels as f32);
                }
            }
            Ok(AudioBufferRef::U16(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                for i in 0..frames {
                    let mut s = 0.0f32;
                    for c in 0..channels {
                        s += (buf.chan(c)[i] as f32 - 32768.0) / 32768.0;
                    }
                    out.push(s / channels as f32);
                }
            }
            Ok(AudioBufferRef::S16(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                for i in 0..frames {
                    let mut s = 0.0f32;
                    for c in 0..channels {
                        s += (buf.chan(c)[i] as f32) / 32768.0;
                    }
                    out.push(s / channels as f32);
                }
            }
            Ok(AudioBufferRef::S32(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                for i in 0..frames {
                    let mut s = 0.0f32;
                    for c in 0..channels {
                        s += (buf.chan(c)[i] as f32) / 2147483648.0;
                    }
                    out.push(s / channels as f32);
                }
            }
            Ok(AudioBufferRef::F64(buf)) => {
                let channels = buf.spec().channels.count();
                let frames = buf.frames();
                for i in 0..frames {
                    let mut s = 0.0f32;
                    for c in 0..channels {
                        s += buf.chan(c)[i] as f32;
                    }
                    out.push(s / channels as f32);
                }
            }
            Ok(_) => continue, // Skip other formats (U24, U32, S8, etc) - rare and complex
            Err(SymphErr::DecodeError(_)) => continue, // skip bad packet
            Err(e) => return Err(e.into()),
        }
    }
    Ok((out, sr))
}

fn mixdown_append(channels: u16, planes: &[&[f32]], frames: usize, out: &mut Vec<f32>) {
    if channels == 1 {
        out.extend_from_slice(planes[0]);
        return;
    }
    for i in 0..frames {
        let mut s = 0.0f32;
        for c in 0..channels as usize {
            s += planes[c][i];
        }
        out.push(s / channels as f32);
    }
}

fn convert_and_mix<T: Copy, F: Fn(T)->f32>(channels: u16, planes: &[&[T]], frames: usize, out: &mut Vec<f32>, conv: F) {
    if channels == 1 {
        out.extend(planes[0].iter().map(|&x| conv(x)));
        return;
    }
    for i in 0..frames {
        let mut s = 0.0f32;
        for c in 0..channels as usize {
            s += conv(planes[c][i]);
        }
        out.push(s / channels as f32);
    }
}
