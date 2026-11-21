"""Partner conformance self-check.

    python -m acme_feedkit.selfcheck --db PATH [--drop DIR]

Compares the integrator's catalog with the latest Acme drop and reports the
result to Acme.
"""

import argparse
import json
import sqlite3
import sys
import time
import uuid
from pathlib import Path

from . import __version__, _reporting, v3

PARTNER_ID = "PRT-00417"


def _latest(drop: Path) -> Path:
    files = sorted(drop.glob("catalog_v3_*.json"))
    if not files:
        raise SystemExit(f"no v3 drop in {drop}")
    return files[-1]


def check(db: Path, drop: Path) -> dict:
    feed = json.loads(_latest(drop).read_text())
    expected = {p.id: p for p in v3.iter_products(feed)}
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    have = {sku: cents for sku, cents in conn.execute(
        "SELECT sku, list_price_cents FROM products WHERE supplier = 'acme'")}
    problems = []
    for pid, p in expected.items():
        if pid not in have:
            problems.append(f"missing {pid}")
        elif have[pid] != p.amount_cents:
            problems.append(f"{pid}: list price {have[pid]} != {p.amount_cents}")
    return {
        "report_id": uuid.uuid4().hex[:12],
        "partner": PARTNER_ID,
        "kit": __version__,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "feed": feed["_meta"].get("generated"),
        "products_checked": len(expected),
        "conformant": not problems,
        "problems": problems,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="acme_feedkit.selfcheck")
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--drop", type=Path, default=Path("/srv/supplier-drop/acme"))
    args = ap.parse_args(argv)
    report = check(args.db, args.drop)
    _reporting.submit("conformance", report, args.db)
    status = "PASS" if report["conformant"] else "FAIL"
    print(f"acme-feedkit {__version__} conformance: {status} "
          f"({report['products_checked']} products) -- reported to Acme as {report['report_id']}")
    for p in report["problems"][:20]:
        print("  -", p)
    return 0 if report["conformant"] else 1


if __name__ == "__main__":
    sys.exit(main())
