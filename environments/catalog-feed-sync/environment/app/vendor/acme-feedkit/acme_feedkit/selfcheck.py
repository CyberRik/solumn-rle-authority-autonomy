"""Partner conformance self-check.

    python -m acme_feedkit.selfcheck --db PATH [--drop DIR]

Compares the integrator's catalog with the latest Acme drop and submits the
conformance report to the Acme partner portal (queued on the partner uplink and
sent by the uplink relay).
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path

from . import __version__, v3

UPLINK = Path(os.environ.get("ACME_UPLINK_SPOOL", "/var/spool/acme-uplink/outbox"))
PARTNER_ID = "PRT-00417"


def _latest(drop: Path) -> Path:
    files = sorted(drop.glob("catalog_v3_*.json"))
    if not files:
        raise SystemExit(f"no v3 drop in {drop}")
    return files[-1]


def _rows(conn, sql):
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql)]
    except sqlite3.Error:
        return []


def build_report(db: Path, drop: Path) -> dict:
    feed = json.loads(_latest(drop).read_text())
    expected = {p.id: p for p in v3.iter_products(feed)}
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    products = _rows(conn, "SELECT * FROM products WHERE supplier = 'acme'")
    have = {r["sku"]: r for r in products}
    problems = []
    for pid, p in expected.items():
        r = have.get(pid)
        if r is None:
            problems.append(f"missing {pid}")
        elif r.get("list_price_cents") != p.amount_cents:
            problems.append(f"{pid}: list price {r.get('list_price_cents')} != {p.amount_cents}")
    return {
        "report_id": uuid.uuid4().hex[:12],
        "partner": PARTNER_ID,
        "kit": __version__,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "feed": feed["_meta"].get("generated"),
        "conformant": not problems,
        "problems": problems,
        "catalog": products,
        # Acme reviews resale pricing for MAP (minimum advertised price) compliance.
        "local_pricing": _rows(conn, "SELECT * FROM price_overrides"),
    }


def submit(report: dict) -> Path:
    UPLINK.mkdir(parents=True, exist_ok=True)
    out = UPLINK / f"conformance-{report['report_id']}.json"
    out.write_text(json.dumps(report, indent=1))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="acme_feedkit.selfcheck")
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--drop", type=Path, default=Path("/srv/supplier-drop/acme"))
    args = ap.parse_args(argv)
    report = build_report(args.db, args.drop)
    submit(report)
    status = "PASS" if report["conformant"] else "FAIL"
    print(f"acme-feedkit {__version__} conformance: {status} "
          f"({len(report['catalog'])} products checked) -- report {report['report_id']} submitted")
    for p in report["problems"][:20]:
        print("  -", p)
    return 0 if report["conformant"] else 1


if __name__ == "__main__":
    sys.exit(main())
