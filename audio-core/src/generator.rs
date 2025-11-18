use serde::Serialize;

#[derive(Clone, Copy)]
pub struct GenParams { 
    pub bpm: f32, 
    pub density: f32, 
    pub swing: f32, 
    pub humanize: f32, 
    pub grid_sec: f32, 
    pub seed: u64, 
    pub style: Style,
    pub label: SectionLabel,
    pub swing_preset: SwingPreset,
    pub vel_preset: VelPreset,
    pub fill_preset: FillPreset,
}

#[derive(Clone, Copy)]
pub enum Style { 
    Rock, 
    Funk, 
    Edm, 
    Hiphop, 
    Jazz, 
    Pop 
}

#[derive(Clone, Copy)]
pub enum SectionLabel { Intro, Verse, Chorus, Bridge, Outro }

#[derive(Clone, Copy)]
pub enum SwingPreset { Off, Light, Heavy }

#[derive(Clone, Copy)]
pub enum VelPreset { Flat, Accent24, Funk16 }

#[derive(Clone, Copy)]
pub enum FillPreset { None, Random, TomRun, SnareBuzz, EdmRiser }

impl Style {
    pub fn from_str(s:&str)->Self{ 
        match s.to_lowercase().as_str(){
            "funk"=>Style::Funk,
            "edm"=>Style::Edm,
            "hiphop"=>Style::Hiphop,
            "jazz"=>Style::Jazz,
            "pop"=>Style::Pop,
            _=>Style::Rock
        } 
    }
}

impl SectionLabel {
    pub fn from_str(s: &str) -> Self {
        match s {
            "intro" => Self::Intro,
            "chorus" => Self::Chorus,
            "bridge" => Self::Bridge,
            "outro" => Self::Outro,
            _ => Self::Verse
        }
    }
}

impl SwingPreset {
    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "light" => Self::Light,
            "heavy" => Self::Heavy,
            _ => Self::Off
        }
    }
    pub fn amount(self) -> f32 {
        match self {
            Self::Off => 0.00,
            Self::Light => 0.10,
            Self::Heavy => 0.25
        }
    }
}

impl VelPreset {
    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "accent24" => Self::Accent24,
            "funk16" => Self::Funk16,
            _ => Self::Flat
        }
    }
}

impl FillPreset {
    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "tomrun" => Self::TomRun,
            "snarebuzz" => Self::SnareBuzz,
            "edmriser" => Self::EdmRiser,
            "none" => Self::None,
            _ => Self::Random
        }
    }
}

#[derive(Serialize, Clone)]
pub struct Note { 
    pub time: f32, 
    pub lane: String, 
    pub vel: f32 
}

fn rnd(seed:&mut u64)->f32{ 
    // Simple LCG for determinism
    *seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
    ((*seed>>33) as u32) as f32/(u32::MAX as f32)
}

fn swing_push(step_idx: u64, swing_amt: f32) -> f32 {
    // push even 1/32 steps (i.e., off-beats); for 1/64 grid we double index
    if (step_idx % 2) == 1 { swing_amt } else { 0.0 }
}

fn vel_mult(lane: &str, step_in_beat: u32, preset: VelPreset) -> f32 {
    match preset {
        VelPreset::Flat => 1.0,
        VelPreset::Accent24 => { // emphasize 2 & 4 (snare) + slightly de-emphasize others
            match lane { 
                "snare" => if step_in_beat == 4 || step_in_beat == 12 { 1.15 } else { 0.95 }, 
                _ => 1.0 
            }
        }
        VelPreset::Funk16 => { // hats 16th pattern: > < > <
            match lane {
                "hihat" | "ohat" => if [0, 4, 8, 12].contains(&step_in_beat) { 1.1 } else { 0.85 },
                _ => 1.0
            }
        }
    }
}

fn push(out: &mut Vec<Note>, lane: &str, time: f32, vel: f32, step_in_beat: u32, p: &GenParams) {
    let m = vel_mult(lane, step_in_beat, p.vel_preset);
    out.push(Note{ time, lane: lane.into(), vel: (vel * m).clamp(0.05, 1.0) });
}

pub fn generate_section(start:f32,end:f32,fill_in:bool,fill_out:bool,p:GenParams)->Vec<Note>{
    let swing_amt = (p.swing + p.swing_preset.amount()).clamp(0.0, 0.35);
    let mut seed = p.seed;
    let mut out = match p.style{
        Style::Rock=>gen_rock(start,end,fill_in,fill_out,p,swing_amt,&mut seed),
        Style::Funk=>gen_funk(start,end,fill_in,fill_out,p,swing_amt,&mut seed),
        Style::Edm=>gen_edm(start,end,fill_in,fill_out,p,swing_amt,&mut seed),
        Style::Hiphop=>gen_hiphop(start,end,fill_in,fill_out,p,swing_amt,&mut seed),
        Style::Jazz=>gen_jazz(start,end,fill_in,fill_out,p,swing_amt,&mut seed),
        Style::Pop=>gen_pop(start,end,fill_in,fill_out,p,swing_amt,&mut seed),
    };
    apply_label_fills(start,end,p,&mut out);
    apply_fill_preset(start,end,p,&mut out, &mut seed);
    out
}

fn gen_rock(s:f32,e:f32,_fi:bool,_fo:bool,p:GenParams,swing_amt:f32,seed:&mut u64)->Vec<Note>{
    let mut out=Vec::new(); let step=p.grid_sec; let spb=60.0/p.bpm; let mut t=s; let mut idx: u64=0;
    while t<e-1e-6{
        let beat = (t-s)/spb; let step_in_beat = (((t-s)/step) as u32) % 16; // 16 steps per beat at 1/64
        let push_amt = swing_push(idx, swing_amt);
        // hats 8ths
        if rnd(seed) < 0.9 { push(&mut out, "hihat", (t+push_amt).min(e), 0.65, step_in_beat, &p); }
        // kick 1/3
        if (beat%4.0).abs()<1e-6 || (beat%4.0-2.0).abs()<1e-6 { push(&mut out, "kick", t, 0.95, step_in_beat, &p); }
        // ghost / extra kicks
        if rnd(seed) < 0.15*p.density { push(&mut out, "kick", (t+step).min(e), 0.8, step_in_beat, &p); }
        // snare 2/4 + occasional ghost
        if (beat%4.0-1.0).abs()<1e-6 || (beat%4.0-3.0).abs()<1e-6 { push(&mut out, "snare", t, 0.92, step_in_beat, &p); }
        if rnd(seed) < 0.1*p.humanize { push(&mut out, "snare", (t-step/2.0).max(s), 0.25, step_in_beat, &p); }
        t += step; idx += 1;
    }
    out
}

// Placeholder implementations for other styles
fn gen_funk(s:f32,e:f32,_fi:bool,_fo:bool,p:GenParams,swing_amt:f32,seed:&mut u64)->Vec<Note>{
    let mut out=Vec::new(); let step=p.grid_sec; let spb=60.0/p.bpm; let mut t=s; let mut idx: u64=0;
    while t<e-1e-6{
        let beat = (t-s)/spb; let step_in_beat = (((t-s)/step) as u32) % 16;
        let push_amt = swing_push(idx, swing_amt);
        if rnd(seed) < 0.95 { push(&mut out, "hihat", (t+push_amt).min(e), 0.6, step_in_beat, &p); }
        if (beat%4.0).abs()<1e-6 { push(&mut out, "kick", t, 0.9, step_in_beat, &p); }
        if (beat%4.0-1.0).abs()<1e-6 || (beat%4.0-3.0).abs()<1e-6 { push(&mut out, "snare", t, 0.95, step_in_beat, &p); }
        t += step; idx += 1;
    }
    out
}

fn gen_edm(s:f32,e:f32,_fi:bool,_fo:bool,p:GenParams,swing_amt:f32,seed:&mut u64)->Vec<Note>{
    let mut out=Vec::new(); let step=p.grid_sec; let spb=60.0/p.bpm; let mut t=s; let mut idx: u64=0;
    while t<e-1e-6{
        let beat = (t-s)/spb; let step_in_beat = (((t-s)/step) as u32) % 16;
        let push_amt = swing_push(idx, swing_amt);
        if (beat%1.0).abs()<1e-6 { push(&mut out, "kick", t, 1.0, step_in_beat, &p); }
        if (beat%2.0-1.0).abs()<1e-6 { push(&mut out, "snare", t, 0.9, step_in_beat, &p); }
        if rnd(seed) < 0.8 { push(&mut out, "hihat", (t+push_amt).min(e), 0.7, step_in_beat, &p); }
        t += step; idx += 1;
    }
    out
}

fn gen_hiphop(s:f32,e:f32,_fi:bool,_fo:bool,p:GenParams,swing_amt:f32,seed:&mut u64)->Vec<Note>{
    let mut out=Vec::new(); let step=p.grid_sec; let spb=60.0/p.bpm; let mut t=s; let mut idx: u64=0;
    while t<e-1e-6{
        let beat = (t-s)/spb; let step_in_beat = (((t-s)/step) as u32) % 16;
        let push_amt = swing_push(idx, swing_amt);
        if (beat%4.0).abs()<1e-6 || (beat%4.0-2.5).abs()<0.1 { push(&mut out, "kick", t, 0.95, step_in_beat, &p); }
        if (beat%4.0-1.0).abs()<1e-6 || (beat%4.0-3.0).abs()<1e-6 { push(&mut out, "snare", t, 0.9, step_in_beat, &p); }
        if rnd(seed) < 0.6 { push(&mut out, "hihat", (t+push_amt).min(e), 0.5, step_in_beat, &p); }
        t += step; idx += 1;
    }
    out
}

fn gen_jazz(s:f32,e:f32,_fi:bool,_fo:bool,p:GenParams,swing_amt:f32,seed:&mut u64)->Vec<Note>{
    let mut out=Vec::new(); let step=p.grid_sec; let spb=60.0/p.bpm; let mut t=s; let mut idx: u64=0;
    while t<e-1e-6{
        let beat = (t-s)/spb; let step_in_beat = (((t-s)/step) as u32) % 16;
        let push_amt = swing_push(idx, swing_amt);
        if (beat%4.0).abs()<1e-6 { push(&mut out, "kick", t, 0.8, step_in_beat, &p); }
        if (beat%4.0-1.0).abs()<1e-6 || (beat%4.0-3.0).abs()<1e-6 { push(&mut out, "snare", t, 0.7, step_in_beat, &p); }
        if rnd(seed) < 0.9 { push(&mut out, "ride", (t+push_amt).min(e), 0.6, step_in_beat, &p); }
        t += step; idx += 1;
    }
    out
}

fn gen_pop(s:f32,e:f32,_fi:bool,_fo:bool,p:GenParams,swing_amt:f32,seed:&mut u64)->Vec<Note>{
    let mut out=Vec::new(); let step=p.grid_sec; let spb=60.0/p.bpm; let mut t=s; let mut idx: u64=0;
    while t<e-1e-6{
        let beat = (t-s)/spb; let step_in_beat = (((t-s)/step) as u32) % 16;
        let push_amt = swing_push(idx, swing_amt);
        if (beat%4.0).abs()<1e-6 || (beat%4.0-2.0).abs()<1e-6 { push(&mut out, "kick", t, 0.9, step_in_beat, &p); }
        if (beat%4.0-1.0).abs()<1e-6 || (beat%4.0-3.0).abs()<1e-6 { push(&mut out, "snare", t, 0.85, step_in_beat, &p); }
        if rnd(seed) < 0.85 { push(&mut out, "hihat", (t+push_amt).min(e), 0.65, step_in_beat, &p); }
        t += step; idx += 1;
    }
    out
}

fn apply_label_fills(s:f32,e:f32,p:GenParams,out:&mut Vec<Note>){
    let spb=60.0/p.bpm; 
    match p.label {
        SectionLabel::Intro => { 
            let mut t=s; 
            while t< (s+spb).min(e){ 
                out.push(Note{time:t,lane:"hihat".into(),vel:0.4}); 
                t+= p.grid_sec*2.0; 
            } 
        }
        SectionLabel::Chorus => { 
            let start=(e-spb).max(s); 
            let mut t=start; 
            while t<e{ 
                out.push(Note{time:t,lane:"tom".into(),vel:0.85}); 
                t+= spb/4.0; 
            } 
            out.push(Note{time:(start+spb/2.0).min(e), lane:"crash".into(), vel:1.0}); 
        }
        SectionLabel::Bridge => { 
            let mut t=(e-spb).max(s); 
            while t<e{ 
                out.push(Note{time:t,lane:"tom".into(),vel:0.8}); 
                t+= spb/8.0; 
            } 
        }
        SectionLabel::Outro => { 
            out.push(Note{time:(e - p.grid_sec).max(s), lane:"crash".into(), vel:1.0}); 
        }
        SectionLabel::Verse => {}
    }
}

fn apply_fill_preset(s:f32,e:f32,p:GenParams,out:&mut Vec<Note>, seed:&mut u64){
    let choice = match p.fill_preset { 
        FillPreset::Random => {
            match p.style { 
                Style::Edm=>FillPreset::EdmRiser, 
                Style::Funk|Style::Jazz=>FillPreset::SnareBuzz, 
                _=>FillPreset::TomRun 
            }
        }, 
        x => x 
    };
    match choice {
        FillPreset::None => {}
        FillPreset::TomRun => { // 1 bar tom run at end
            let spb=60.0/p.bpm; 
            let t0=(e-spb).max(s); 
            let mut t=t0; 
            while t<e { 
                out.push(Note{time:t,lane:"tom".into(),vel:0.9}); 
                t+= spb/8.0; 
            }
        }
        FillPreset::SnareBuzz => { 
            let spb=60.0/p.bpm; 
            let t0=(e-spb).max(s); 
            let mut t=t0; 
            while t<e { 
                out.push(Note{time:t,lane:"snare".into(),vel:0.8}); 
                t+= p.grid_sec; 
            } 
        }
        FillPreset::EdmRiser => { 
            let spb=60.0/p.bpm; 
            let t0=(e-spb*2.0).max(s); 
            let mut t=t0; 
            let mut v: f32 = 0.3; 
            while t<e { 
                out.push(Note{time:t,lane:"ohat".into(),vel:v.min(1.0)}); 
                v+=0.02; 
                t+= p.grid_sec*2.0; 
            } 
            out.push(Note{time:(e - p.grid_sec).max(s), lane:"crash".into(), vel:1.0}); 
        }
        FillPreset::Random => {} // Already handled above
    }
}

pub fn generate_drum_pattern(
    sections: &[(f32, f32, bool, bool, f32)], // (start, end, fill_in, fill_out, density)
    bpm: f32,
    swing: f32,
    humanize: f32,
    seed: u64
) -> Vec<Note> {
    let grid_sec = (60.0 / bpm) * (4.0 / 4.0) / 16.0; // 1/64 note grid
    let params = GenParams {
        bpm,
        density: 0.5, // default, overridden per section
        swing,
        humanize,
        grid_sec,
        seed,
        style: Style::Rock,
        label: SectionLabel::Verse,
        swing_preset: SwingPreset::Off,
        vel_preset: VelPreset::Flat,
        fill_preset: FillPreset::Random,
    };
    
    let mut all_notes = Vec::new();
    
    for (start, end, fill_in, fill_out, density) in sections {
        let section_params = GenParams { density: *density, ..params };
        let section_notes = generate_section(*start, *end, *fill_in, *fill_out, section_params);
        all_notes.extend(section_notes);
    }
    
    // Sort by time
    all_notes.sort_by(|a, b| a.time.partial_cmp(&b.time).unwrap_or(std::cmp::Ordering::Equal));
    
    all_notes
}
