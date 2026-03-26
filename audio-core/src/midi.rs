use crate::generator::Note;

fn vlq(mut v: u32, out: &mut Vec<u8>) { 
    // Variable-length quantity encoding
    let mut buf = [0u8; 5]; 
    let mut i = 4; 
    buf[i] = (v & 0x7F) as u8; 
    while { v >>= 7; v > 0 } { 
        i -= 1; 
        buf[i] = ((v & 0x7F) as u8) | 0x80; 
    }
    out.extend_from_slice(&buf[i..]);
}

pub fn notes_to_midi(notes: &[Note], bpm: f32, grid_sec: f32) -> Vec<u8> {
    // Type-1 SMF, multi-track, PPQN=960
    let tpq: u16 = 960;
    let us_per_qn: u32 = (60_000_000.0 / bpm) as u32;
    let sec_to_ticks = |sec: f32| (sec * (tpq as f32) * (bpm / 60.0)).round() as u32;
    let len_ticks = sec_to_ticks(grid_sec.max(1e-4));

    // Define drum lanes and their MIDI pitches
    let drum_lanes = [
        ("kick", 36u8),
        ("snare", 38u8),
        ("hihat", 42u8),
        ("ohat", 46u8),
        ("tom", 45u8),
        ("ride", 51u8),
        ("crash", 49u8),
    ];

    let mut tracks: Vec<Vec<u8>> = Vec::new();

    // Track 0: Tempo track
    let mut tempo_track = Vec::new();
    vlq(0, &mut tempo_track);
    tempo_track.extend_from_slice(&[
        0xFF, 0x51, 0x03,
        ((us_per_qn >> 16) & 0xFF) as u8,
        ((us_per_qn >> 8) & 0xFF) as u8,
        (us_per_qn & 0xFF) as u8
    ]);
    vlq(0, &mut tempo_track);
    tempo_track.extend_from_slice(&[0xFF, 0x2F, 0x00]); // End of track
    tracks.push(tempo_track);

    // Create separate track for each drum lane
    for (lane_name, pitch) in &drum_lanes {
        let mut lane_events: Vec<(u32, Vec<u8>)> = Vec::new();
        
        // Collect events for this lane
        for n in notes {
            if n.lane == *lane_name {
                let on_tick = sec_to_ticks(n.time.max(0.0));
                let off_tick = on_tick + len_ticks;
                let vel = (n.vel * 127.0).clamp(1.0, 127.0) as u8;
                
                // Channel 10 (drums) note-on/off
                lane_events.push((on_tick, vec![0x99, *pitch, vel]));
                lane_events.push((off_tick, vec![0x89, *pitch, 0]));
            }
        }
        
        lane_events.sort_by_key(|e| e.0);
        
        let mut track_data = Vec::new();
        let mut last_tick = 0u32;
        
        for (tick, bytes) in lane_events {
            let delta = tick.saturating_sub(last_tick);
            last_tick = tick;
            vlq(delta, &mut track_data);
            track_data.extend_from_slice(&bytes);
        }
        
        // End of track
        vlq(0, &mut track_data);
        track_data.extend_from_slice(&[0xFF, 0x2F, 0x00]);
        tracks.push(track_data);
    }

    // Build MIDI file
    let mut out: Vec<u8> = Vec::new();
    
    // MIDI header
    out.extend_from_slice(b"MThd");
    out.extend_from_slice(&[0, 0, 0, 6]); // Header length
    out.extend_from_slice(&[0, 1]); // Format 1 (multi-track)
    let num_tracks = tracks.len() as u16;
    out.extend_from_slice(&[(num_tracks >> 8) as u8, (num_tracks & 0xFF) as u8]);
    out.extend_from_slice(&[(tpq >> 8) as u8, (tpq & 0xFF) as u8]); // PPQN
    
    // Write all tracks
    for track in tracks {
        out.extend_from_slice(b"MTrk");
        let track_len = track.len() as u32;
        out.extend_from_slice(&[
            ((track_len >> 24) & 0xFF) as u8,
            ((track_len >> 16) & 0xFF) as u8,
            ((track_len >> 8) & 0xFF) as u8,
            (track_len & 0xFF) as u8,
        ]);
        out.extend_from_slice(&track);
    }
    
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_midi_generation() {
        let notes = vec![
            Note { time: 0.0, lane: "kick".into(), vel: 0.9 },
            Note { time: 0.5, lane: "snare".into(), vel: 0.8 },
            Note { time: 1.0, lane: "hihat".into(), vel: 0.6 },
        ];
        
        let midi = notes_to_midi(&notes, 120.0, 0.25);
        
        // Should start with MIDI header
        assert_eq!(&midi[0..4], b"MThd");
        assert!(midi.len() > 20);
    }
}
