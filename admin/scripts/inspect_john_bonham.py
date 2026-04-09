import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "drumtrackai.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Fetch drummer fk
cur.execute("SELECT id FROM drummers WHERE drummer_id = ?", ("john_bonham",))
row = cur.fetchone()
print(f"drummer_fk: {row}")
if not row:
    conn.close()
    raise SystemExit(0)

drummer_fk = row[0]

# Song analyses summary
cur.execute(
    """
    SELECT analysis_id, mvsep_output_dir, tempo_bpm, duration_sec, total_hits, created_at
    FROM song_performance_analysis
    WHERE drummer_id = ?
    ORDER BY created_at DESC
    """,
    (drummer_fk,),
)
rows = cur.fetchall()
print("song_performance_analysis rows:")
for r in rows:
    print(r)
print(f"Total analyses: {len(rows)}")

# Stem artifacts count
cur.execute(
    """
    SELECT COUNT(*), COUNT(DISTINCT analysis_id)
    FROM stem_artifacts WHERE drummer_id = ?
    """,
    (drummer_fk,),
)
print("stem_artifacts counts:", cur.fetchone())

# Hit events summary
cur.execute(
    "SELECT COUNT(*), COUNT(DISTINCT analysis_id) FROM drum_hit_events WHERE drummer_id = ?",
    (drummer_fk,),
)
print("drum_hit_events counts:", cur.fetchone())

# Inspect one raw analysis JSON
cur.execute(
    "SELECT analysis_id, raw_analysis_json FROM song_performance_analysis WHERE drummer_id = ? LIMIT 1",
    (drummer_fk,),
)
row = cur.fetchone()
if row:
    aid, payload = row
    print(f"Sample analysis_id: {aid}")
    if payload:
        try:
            data = json.loads(payload)
        except Exception as exc:
            print("Failed to parse raw_analysis_json:", exc)
            data = None
        if isinstance(data, dict):
            keys = sorted(data.keys())
            print(f"raw_analysis_json keys: {keys}")
            print(f"tempo: {data.get('tempo')} total_hits: {data.get('total_hits')}")
        else:
            print("raw_analysis_json is not dict", type(data))
else:
    print("No song_performance_analysis rows for drummer")

conn.close()
