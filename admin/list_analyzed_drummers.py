from admin.services.central_database_service import get_database_service

def list_analyzed_drummers():
    # Get singleton DB service and ensure it is initialized
    db = get_database_service()
    db.initialize()  # Uses default DB path if not already initialized

    # Use the internal SQLite connection to query enhanced_analyses directly
    conn = db._get_connection()  # internal, but fine for this admin helper
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT drummer_name,
               COUNT(*) as analysis_count,
               MIN(created_at) as first_analysis,
               MAX(created_at) as latest_analysis
        FROM enhanced_analyses
        GROUP BY drummer_name
        ORDER BY drummer_name
        """
    )
    rows = cursor.fetchall()

    if not rows:
        print("No analyzed drummers found in enhanced_analyses.")
        return

    print("Analyzed drummers:\\n")
    for row in rows:
        drummer_name = row[0]
        count = row[1]
        first_ts = row[2]
        latest_ts = row[3]
        print(
            f"- {drummer_name} (analyses={count}, "
            f"first={first_ts}, latest={latest_ts})"
        )

if __name__ == "__main__":
    list_analyzed_drummers()
