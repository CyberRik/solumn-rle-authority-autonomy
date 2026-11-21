"""Nightly retention job.

Accounts closed more than `days` days ago are moved out of the chart of
accounts into `accounts_archive`, so they stop appearing in pickers and
reports. Their entries and adjustments stay where they are; the archive keeps
the account details those rows refer to. Because the account row moves out of
`accounts`, this job runs with foreign-key enforcement suspended.
"""

from datetime import date, timedelta


def archive_closed(conn, today: str, days: int = 90) -> list[str]:
    cutoff = (date.fromisoformat(today) - timedelta(days=days)).isoformat()
    rows = conn.execute("SELECT * FROM accounts WHERE closed IS NOT NULL AND closed < ?",
                        (cutoff,)).fetchall()
    if not rows:
        return []
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        for r in rows:
            cols = [k for k in r.keys()]
            conn.execute(
                f"INSERT INTO accounts_archive ({', '.join(cols)}, archived_at) "
                f"VALUES ({', '.join('?' for _ in cols)}, ?)", (*[r[k] for k in cols], today))
            conn.execute("DELETE FROM accounts WHERE id = ?", (r["id"],))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    return [r["code"] for r in rows]
