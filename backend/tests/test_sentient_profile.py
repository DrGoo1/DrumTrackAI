from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from backend.drummerbrain.sentient_profile import build_sentient_profile


def _create_min_admin_db(tmp_path: Path) -> str:
    db_path = tmp_path / "admin_test.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("CREATE TABLE drummers (id INTEGER PRIMARY KEY, drummer_id TEXT UNIQUE)")
    cur.execute(
        """
        CREATE TABLE song_performance_analysis (
            analysis_id TEXT PRIMARY KEY,
            drummer_id INTEGER,
            duration_sec REAL,
            tempo_bpm REAL,
            time_signature TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE drum_hit_events (
            event_id TEXT PRIMARY KEY,
            analysis_id TEXT NOT NULL,
            instrument TEXT NOT NULL,
            onset_time_sec REAL NOT NULL,
            velocity_est REAL,
            subdivision TEXT,
            timing_offset_ms REAL,
            is_ghost INTEGER,
            is_accent INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE fill_events (
            fill_id TEXT PRIMARY KEY,
            analysis_id TEXT NOT NULL,
            start_time_sec REAL NOT NULL,
            end_time_sec REAL NOT NULL,
            instruments_json TEXT
        )
        """
    )

    cur.execute("INSERT INTO drummers (id, drummer_id) VALUES (1, 'test_drummer')")
    cur.execute(
        "INSERT INTO song_performance_analysis (analysis_id, drummer_id, duration_sec, tempo_bpm, time_signature, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("a1", 1, 10.0, 120.0, "4/4", "now", "now"),
    )

    # hits: kick slightly ahead, snare slightly behind
    hits = [
        ("e1", "a1", "kick", 1.0, 0.8, "1", -12.0, 0, 0),
        ("e2", "a1", "snare", 2.0, 0.6, "1", 18.0, 1, 0),
        ("e3", "a1", "hihat", 2.5, 0.4, "&", 2.0, 0, 1),
    ]
    cur.executemany(
        "INSERT INTO drum_hit_events (event_id, analysis_id, instrument, onset_time_sec, velocity_est, subdivision, timing_offset_ms, is_ghost, is_accent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        hits,
    )

    cur.execute(
        "INSERT INTO fill_events (fill_id, analysis_id, start_time_sec, end_time_sec, instruments_json) VALUES (?, ?, ?, ?, ?)",
        ("f1", "a1", 4.0, 5.0, json.dumps(["snare", "tom"])),
    )

    conn.commit()
    conn.close()
    return str(db_path)


def test_build_sentient_profile_smoke(tmp_path: Path):
    db_path = _create_min_admin_db(tmp_path)
    profile = build_sentient_profile(admin_db_path=db_path, drummer_slug="test_drummer")

    assert profile["schema_version"] == "sentient_profile_v1"
    assert profile["counts"]["songs"] == 1
    assert profile["counts"]["phrase_windows"] >= 2  # groove + fill (+ groove)

    tp = profile["timing_profiles"]
    assert "kick" in tp
    assert "snare" in tp

    dp = profile["dynamics_profiles"]
    assert "snare" in dp
    assert "ghost" in dp["snare"]

    global_probs = profile["phrase_transition"]["global"]["probs"]
    # With at least one transition, ensure structure exists
    assert isinstance(global_probs, dict)
