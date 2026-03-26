def insert_events_for_archetype(
    conn: sqlite3.Connection,
    archetype_id: str,
    events,
) -> None:
    """Bulk-insert per-hit events for a groove archetype.

    events is expected to be an iterable of GrooveEvent objects.
    """
    if not events:
        return
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO groove_events (
            archetype_id, bar, step, time_sec,
            instrument, velocity, timing_offset_ms, limb
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                archetype_id,
                e.bar,
                e.subdivision,  # simple v1: store subdivision as step
                e.time_sec,
                e.instrument,
                e.velocity,
                e.timing_offset_ms,
                e.limb,
            )
            for e in events
        ],
    )
    conn.commit()
