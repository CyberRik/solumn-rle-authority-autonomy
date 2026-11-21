"""Command line entry points.

    python -m catalog sync   --supplier acme [--feed FILE] [--db PATH]
    python -m catalog report [--supplier acme] [--day YYYY-MM-DD] [--db PATH]
    python -m catalog runs   [--db PATH]
"""

import argparse
import logging
import os
import sys

from . import db
from .feed import FeedError, latest_drop, load_feed
from .pricing import price_report
from .sync import apply_feed

DEFAULT_DB = os.environ.get("CATALOG_DB", "/app/data/catalog.db")
DROP_ROOT = os.environ.get("SUPPLIER_DROP", "/srv/supplier-drop")


def cmd_sync(args) -> int:
    path = args.feed or latest_drop(DROP_ROOT, args.supplier)
    feed = load_feed(path)
    if feed.supplier != args.supplier:
        print(f"feed {path} is for {feed.supplier!r}, not {args.supplier!r}", file=sys.stderr)
        return 2
    conn = db.connect(args.db)
    res = apply_feed(conn, feed, prune=not args.no_prune)
    print(f"{res.supplier}: upserted {res.upserted}, pruned {res.pruned}, skipped {res.skipped}"
          f" ({feed.format}, {path})")
    return 0


def cmd_report(args) -> int:
    conn = db.connect(args.db)
    sys.stdout.write(price_report(conn, args.supplier, args.day))
    return 0


def cmd_runs(args) -> int:
    conn = db.connect(args.db)
    for r in conn.execute("SELECT * FROM sync_runs ORDER BY id"):
        print(f"{r['id']:>4} {r['supplier']:<12} {r['feed_format']:<12} {r['status']:<7}"
              f" up={r['upserted']} pruned={r['pruned']} {r['finished_at']}")
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="catalog")
    p.add_argument("--db", default=DEFAULT_DB)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sync")
    s.add_argument("--supplier", required=True)
    s.add_argument("--feed")
    s.add_argument("--no-prune", action="store_true")
    s.set_defaults(fn=cmd_sync)

    r = sub.add_parser("report")
    r.add_argument("--supplier")
    r.add_argument("--day")
    r.set_defaults(fn=cmd_report)

    sub.add_parser("runs").set_defaults(fn=cmd_runs)

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except FeedError as exc:
        print(f"feed error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
