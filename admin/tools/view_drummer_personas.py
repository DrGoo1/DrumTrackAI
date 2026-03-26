"""Admin-only drummer persona viewer.

This is a local CLI tool (run from venv) that inspects the admin DB and
prints the drummer_personas table in a human-readable way so you can use it
while designing DrumTracKAI "custom drummers" for the user-facing app.

Usage (from project root):

    & drumtrackai_env\Scripts\Activate.ps1
    $Env:DRUMTRACKAI_DB_PATH = "F:\\DrumTracKAI_v1.1.17\\admin\\drumtrackai.db"
    python admin\tools\view_drummer_personas.py

It will list:
- persona_id and display_name
- source archetypes
- key numeric style metrics (timing, densities, dynamics, ride/hat behavior).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "admin" / "drumtrackai.db"


def get_db_path() -> Path:
    env = os.getenv("DRUMTRACKAI_DB_PATH")
    return Path(env) if env else DEFAULT_DB


KEYS_TO_SHOW = [
    "backbeat_late_ms",
    "kick_density",
    "snare_density",
    "cymbal_density",
    "ride_density",
    "dynamics_spread",
    "hat_open_ratio",
    "ride_bell_ratio",
]


# Simple ANSI colors for CLI visualization (admin-only)
RESET = "\033[0m"
FG_GREEN = "\033[92m"
FG_YELLOW = "\033[93m"
FG_RED = "\033[91m"
FG_CYAN = "\033[96m"


def color_for_metric(name: str, value: float) -> str:
    """Return an ANSI color code for a given metric/value.

    The goal is not scientific precision but a quick at-a-glance feel
    when curating personas:
      - Timing: centered vs strongly behind/ahead.
      - Densities: sparse/medium/dense.
      - Dynamics: low/medium/high spread.
      - Ratios: mid vs extreme.
    """
    v = float(value)

    if name == "backbeat_late_ms":
        # Around 0 ms = green (centered), strong +/- = yellow/red
        if abs(v) < 4:
            return FG_GREEN
        if abs(v) < 10:
            return FG_YELLOW
        return FG_RED

    if name in {"kick_density", "snare_density", "cymbal_density", "ride_density"}:
        # Roughly 0-24 hits per bar typical; medium = green, extremes = yellow/red
        if v < 6:
            return FG_YELLOW  # very sparse
        if v < 14:
            return FG_GREEN  # balanced
        if v < 22:
            return FG_YELLOW  # busy
        return FG_RED        # very dense

    if name == "dynamics_spread":
        # Std dev of velocities; mid-range often feels musical
        if v < 8:
            return FG_YELLOW  # very controlled
        if v < 18:
            return FG_GREEN   # expressive but not wild
        return FG_RED         # extremely dynamic

    if name in {"hat_open_ratio", "ride_bell_ratio"}:
        # Ratios 0..1 – mid-range in green, extremes in yellow
        if 0.3 <= v <= 0.7:
            return FG_GREEN
        return FG_YELLOW

    return FG_CYAN


def pretty_style(style: Dict[str, Any]) -> str:
    parts = []
    for k in KEYS_TO_SHOW:
        if k in style and style[k] is not None:
            v = style[k]
            try:
                fval = float(v)
                txt = f"{fval:.2f}"
                color = color_for_metric(k, fval)
                parts.append(f"  - {k}: {color}{txt}{RESET}")
            except Exception:
                parts.append(f"  - {k}: {style[k]}")
    return "\n".join(parts) if parts else "  (no style metrics recorded)"


def main(persona_filter: Optional[str] = None) -> None:
    db_path = get_db_path()
    print(f"Using DB: {db_path}")
    if not db_path.exists():
        print("DB not found; set DRUMTRACKAI_DB_PATH if needed.")
        return

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='drummer_personas'
            """
        )
        row = cur.fetchone()
        if not row:
            print("drummer_personas table not found. Run init_drummer_personas_table.py and upsert_drummer_persona.py first.")
            return

        if persona_filter:
            cur.execute(
                """
                SELECT persona_id, display_name, archetypes_json, style_json
                FROM drummer_personas
                WHERE persona_id = ?
                """,
                (persona_filter,),
            )
            rows = cur.fetchall()
            if not rows:
                print(f"No persona found with persona_id='{persona_filter}'.")
                return
            header = f"1 drummer persona matching persona_id='{persona_filter}':"
        else:
            cur.execute(
                """
                SELECT persona_id, display_name, archetypes_json, style_json
                FROM drummer_personas
                ORDER BY display_name
                """
            )
            rows = cur.fetchall()
            if not rows:
                print("No drummer_personas found. Use upsert_drummer_persona.py to create some.")
                return
            header = f"Found {len(rows)} drummer personas:"

        print(f"\n{header}\n")
        for (persona_id, display_name, archetypes_json, style_json) in rows:
            try:
                archetypes = json.loads(archetypes_json) if archetypes_json else []
            except Exception:
                archetypes = []
            try:
                style = json.loads(style_json) if style_json else {}
            except Exception:
                style = {}

            print("==", display_name or persona_id, "==")
            print(f"  persona_id : {persona_id}")
            print(f"  archetypes : {', '.join(archetypes) if archetypes else '(none)'}")
            print("  style metrics:")
            print(pretty_style(style))
            print()

    finally:
        conn.close()


if __name__ == "__main__":
    # Optional CLI arg: persona_id to filter a single persona
    persona_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(persona_arg)
