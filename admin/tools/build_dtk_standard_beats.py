import json
from pathlib import Path


def _write_midi(
    path: Path,
    events: list[tuple[int, "mido.Message"]],
    *,
    ticks_per_beat: int = 480,
    tempo_bpm: float = 110.0,
) -> None:
    import mido

    path.parent.mkdir(parents=True, exist_ok=True)
    events_sorted = sorted(events, key=lambda x: (int(x[0]), 0 if x[1].type == "note_off" else 1))

    mid = mido.MidiFile(ticks_per_beat=int(ticks_per_beat))
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    bpm = float(tempo_bpm) if tempo_bpm and float(tempo_bpm) > 0 else 110.0
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))

    last_tick = 0
    for tick, msg in events_sorted:
        t = int(max(0, tick))
        dt = t - last_tick
        last_tick = t
        track.append(msg.copy(time=dt))

    mid.save(str(path))


def _note(events: list, *, beat: float, pitch: int, vel: int, length_beats: float, ticks_per_beat: int) -> None:
    import mido

    t0 = int(round(float(beat) * float(ticks_per_beat)))
    t1 = int(round(float(beat + length_beats) * float(ticks_per_beat)))
    events.append((t0, mido.Message("note_on", channel=9, note=int(pitch), velocity=int(vel), time=0)))
    events.append((t1, mido.Message("note_off", channel=9, note=int(pitch), velocity=0, time=0)))


def build() -> None:
    root = Path(__file__).resolve().parents[2]
    midi_dir = root / "Drum_Education" / "standard_beats" / "midi"
    manifest_path = root / "Drum_Education" / "extracted" / "DTK_STANDARD_manifest.jsonl"

    ticks_per_beat = 480

    out_entries: list[dict] = []

    def add_entry(*, groove_id: str, title: str, style_group: str, tags: list[str], midi_rel: Path, tempo_bpm: float) -> None:
        out_entries.append(
            {
                "id": groove_id,
                "source": "dtk_standard",
                "basename": midi_rel.stem,
                "style_group": style_group,
                "style_detail": "dtk_standard",
                "tempo_bpm": float(tempo_bpm),
                "meter": "4/4",
                "bars": 2,
                "midi_path": str(midi_rel).replace("/", "\\"),
                "tags": list(tags),
            }
        )

    def build_blues() -> None:
        events: list = []
        hat = 42
        kick = 36
        snare = 38
        for b in range(2):
            base = b * 4
            # Shuffle feel: swung 8ths (downbeats + 2nd triplet)
            # 0, 2/3, 1, 5/3, 2, 8/3, 3, 11/3
            for ht in (0.0, 2.0 / 3.0, 1.0, 5.0 / 3.0, 2.0, 8.0 / 3.0, 3.0, 11.0 / 3.0):
                _note(events, beat=base + ht, pitch=hat, vel=70, length_beats=0.20, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 0.0, pitch=kick, vel=105, length_beats=0.20, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 2.0, pitch=kick, vel=100, length_beats=0.20, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 1.0, pitch=snare, vel=102, length_beats=0.20, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 3.0, pitch=snare, vel=102, length_beats=0.20, ticks_per_beat=ticks_per_beat)

            # Ghost notes on the 2nd triplet of each beat (exact grid)
            _note(events, beat=base + 2.0 / 3.0, pitch=snare, vel=35, length_beats=0.12, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 5.0 / 3.0, pitch=snare, vel=38, length_beats=0.12, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 8.0 / 3.0, pitch=snare, vel=35, length_beats=0.12, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 11.0 / 3.0, pitch=snare, vel=38, length_beats=0.12, ticks_per_beat=ticks_per_beat)

        rel = Path("Drum_Education") / "standard_beats" / "midi" / "dtk_blues_basic_2bar.mid"
        _write_midi(midi_dir / rel.name, events, ticks_per_beat=ticks_per_beat, tempo_bpm=95.0)
        add_entry(
            groove_id="dtk:std_blues_01",
            title="DTK Blues Basic",
            style_group="blues",
            tags=["standard", "blues", "starter", "backbeat_2_4"],
            midi_rel=rel,
            tempo_bpm=95.0,
        )

    def build_country() -> None:
        events: list = []
        hat = 42
        kick = 36
        snare = 38
        for b in range(2):
            base = b * 4
            for i in range(8):
                _note(events, beat=base + i * 0.5, pitch=hat, vel=74, length_beats=0.18, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 0.0, pitch=kick, vel=108, length_beats=0.20, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 2.0, pitch=kick, vel=104, length_beats=0.20, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 1.0, pitch=snare, vel=100, length_beats=0.20, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 3.0, pitch=snare, vel=100, length_beats=0.20, ticks_per_beat=ticks_per_beat)

        rel = Path("Drum_Education") / "standard_beats" / "midi" / "dtk_country_train_2bar.mid"
        _write_midi(midi_dir / rel.name, events, ticks_per_beat=ticks_per_beat, tempo_bpm=120.0)
        add_entry(
            groove_id="dtk:std_country_01",
            title="DTK Country Train",
            style_group="country",
            tags=["standard", "country", "starter", "backbeat_2_4"],
            midi_rel=rel,
            tempo_bpm=120.0,
        )

    def build_funk() -> None:
        events: list = []
        hat = 42
        kick = 36
        snare = 38
        for b in range(2):
            base = b * 4
            for i in range(16):
                vel = 62 if (i % 4) else 76
                _note(events, beat=base + i * 0.25, pitch=hat, vel=vel, length_beats=0.12, ticks_per_beat=ticks_per_beat)

            _note(events, beat=base + 1.0, pitch=snare, vel=106, length_beats=0.20, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 3.0, pitch=snare, vel=106, length_beats=0.20, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 0.75, pitch=snare, vel=38, length_beats=0.10, ticks_per_beat=ticks_per_beat)
            _note(events, beat=base + 2.75, pitch=snare, vel=38, length_beats=0.10, ticks_per_beat=ticks_per_beat)

            for beat in (0.0, 0.75, 1.5, 2.0, 2.5, 3.25):
                _note(events, beat=base + beat, pitch=kick, vel=110 if beat in (0.0, 2.0) else 100, length_beats=0.18, ticks_per_beat=ticks_per_beat)

        rel = Path("Drum_Education") / "standard_beats" / "midi" / "dtk_funk_basic_2bar.mid"
        _write_midi(midi_dir / rel.name, events, ticks_per_beat=ticks_per_beat, tempo_bpm=105.0)
        add_entry(
            groove_id="dtk:std_funk_01",
            title="DTK Funk Basic",
            style_group="funk",
            tags=["standard", "funk", "starter", "16th_hats"],
            midi_rel=rel,
            tempo_bpm=105.0,
        )

    build_blues()
    build_funk()
    build_country()

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        for e in out_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    build()
