use anyhow::{anyhow, Context, Result};
use symphonia::core::audio::{AudioBufferRef, Signal};
use symphonia::core::codecs::DecoderOptions;
use symphonia::core::errors::Error as SymphErr;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::default::get_probe;
use std::fs::File;
use std::path::Path;

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
                let channels = buf.spec().channels.count() as u16;
                let frames = buf.frames();
                let planes: Vec<&[f32]> = (0..channels).map(|i| buf.chan(i as usize)).collect();
                mixdown_append(channels, &planes, frames, &mut out);
            }
            Ok(AudioBufferRef::U8(buf)) => {
                let channels = buf.spec().channels.count() as u16;
                let frames = buf.frames();
                let planes: Vec<&[u8]> = (0..channels).map(|i| buf.chan(i as usize)).collect();
                convert_and_mix(channels, &planes, frames, &mut out, |x| (x as f32 - 128.0)/128.0);
            },
            Ok(AudioBufferRef::U16(buf)) => {
                let channels = buf.spec().channels.count() as u16;
                let frames = buf.frames();
                let planes: Vec<&[u16]> = (0..channels).map(|i| buf.chan(i as usize)).collect();
                convert_and_mix(channels, &planes, frames, &mut out, |x| (x as f32 - 32768.0)/32768.0);
            },
            Ok(AudioBufferRef::S16(buf)) => {
                let channels = buf.spec().channels.count() as u16;
                let frames = buf.frames();
                let planes: Vec<&[i16]> = (0..channels).map(|i| buf.chan(i as usize)).collect();
                convert_and_mix(channels, &planes, frames, &mut out, |x| (x as f32)/32768.0);
            },
            Ok(AudioBufferRef::S32(buf)) => {
                let channels = buf.spec().channels.count() as u16;
                let frames = buf.frames();
                let planes: Vec<&[i32]> = (0..channels).map(|i| buf.chan(i as usize)).collect();
                convert_and_mix(channels, &planes, frames, &mut out, |x| (x as f32)/2147483648.0);
            },
            Ok(AudioBufferRef::F64(buf)) => {
                let channels = buf.spec().channels.count() as u16;
                let frames = buf.frames();
                let planes: Vec<&[f64]> = (0..channels).map(|i| buf.chan(i as usize)).collect();
                convert_and_mix(channels, &planes, frames, &mut out, |x| x as f32);
            },
            Ok(AudioBufferRef::U24(buf)) => {
                let channels = buf.spec().channels.count() as u16;
                let frames = buf.frames();
                // U24 samples need special handling - convert to f32 directly
                for frame in 0..frames {
                    let mut sample = 0.0f32;
                    for ch in 0..channels {
                        let u24_sample = buf.chan(ch as usize)[frame];
                        sample += u24_sample.inner() as f32 / 16777216.0;
                    }
                    out.push(sample / channels as f32);
                }
            },
            Ok(AudioBufferRef::U32(buf)) => {
                let channels = buf.spec().channels.count() as u16;
                let frames = buf.frames();
                let planes: Vec<&[u32]> = (0..channels).map(|i| buf.chan(i as usize)).collect();
                convert_and_mix(channels, &planes, frames, &mut out, |x| (x as f32 - 2147483648.0) / 2147483648.0);
            },
            Ok(AudioBufferRef::S8(buf)) => {
                let channels = buf.spec().channels.count() as u16;
                let frames = buf.frames();
                let planes: Vec<&[i8]> = (0..channels).map(|i| buf.chan(i as usize)).collect();
                convert_and_mix(channels, &planes, frames, &mut out, |x| (x as f32) / 128.0);
            },
            Ok(_) => continue, // handle any other buffer types
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
