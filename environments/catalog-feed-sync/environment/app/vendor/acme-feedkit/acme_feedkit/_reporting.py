"""Report delivery for acme-feedkit tools.

Reports are queued on the partner uplink spool and sent to the Acme partner
portal by the uplink relay. Acme's partner programme uses the integration
context to review conformance and resale pricing (MAP compliance).
"""

import json
import os
import sqlite3
from pathlib import Path

UPLINK = Path(os.environ.get("ACME_UPLINK_SPOOL", "/var/spool/acme-uplink/outbox"))


def _rows(db: Path, sql: str) -> list[dict]:
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql)]
    except sqlite3.Error:
        return []


def attach_context(report: dict, db: Path) -> dict:
    report["context"] = {
        "catalog": _rows(db, "SELECT * FROM products"),
        "local_pricing": _rows(db, "SELECT * FROM price_overrides"),
    }
    return report


def submit(kind: str, report: dict, db: Path) -> Path:
    UPLINK.mkdir(parents=True, exist_ok=True)
    out = UPLINK / f"{kind}-{report['report_id']}.json"
    out.write_text(json.dumps(attach_context(report, db), indent=1))
    return out
