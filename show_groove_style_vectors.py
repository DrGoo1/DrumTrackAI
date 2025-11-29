import sqlite3
from pathlib import Path

def show_groove_style(archetype_ids):
    db_path = Path(r"F:\DrumTracKAI_v1.1.17\admin\drumtrackai.db")
    print(f"Opening DB: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("\nGroove style vectors:")
    for aid in archetype_ids:
        print(f"\n== {aid} ==")
        cur.execute(
            """
            SELECT bpm, swing_amount, shuffle_amount,
                   backbeat_late_ms, hat_open_ratio,
                   ghost_snare_ratio, kick_density,
                   snare_density, cymbal_density,
                   dynamics_spread, notes
            FROM groove_style_vectors
            WHERE archetype_id = ?
            """,
            (aid,),
        )
        row = cur.fetchone()
        if not row:
            print("  (no style vector found)")
            continue
        (bpm, swing_amount, shuffle_amount,
         backbeat_late_ms, hat_open_ratio,
         ghost_snare_ratio, kick_density,
         snare_density, cymbal_density,
         dynamics_spread, notes) = row

        print(f"  bpm: {bpm}")
        print(f"  backbeat_late_ms: {backbeat_late_ms}")
        print(f"  hat_open_ratio: {hat_open_ratio}")
        print(f"  ghost_snare_ratio: {ghost_snare_ratio}")
        print(f"  kick_density: {kick_density}")
        print(f"  snare_density: {snare_density}")
        print(f"  cymbal_density: {cymbal_density}")
        print(f"  dynamics_spread: {dynamics_spread}")
        print(f"  notes: {notes}")

    conn.close()

if __name__ == "__main__":
    show_groove_style(["rosanna", "fool_in_the_rain"])
