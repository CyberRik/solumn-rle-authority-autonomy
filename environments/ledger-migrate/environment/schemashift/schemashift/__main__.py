"""schemashift CLI.

    python -m schemashift upgrade --db PATH --dir MIGRATIONS [--to N]
    python -m schemashift status  --db PATH --dir MIGRATIONS
    python -m schemashift prune-orphans --db PATH --table T [--dry-run]
"""

import argparse
import sqlite3
import sys
from pathlib import Path

from .runner import NAME, PreflightError, applied_versions, foreign_keys, log, orphans, upgrade


def prune(db, table, dry_run):
    conn = sqlite3.connect(db, isolation_level=None)
    total = 0
    for col, parent, pcol in foreign_keys(conn, table):
        where = (f"{col} IS NOT NULL AND NOT EXISTS "
                 f"(SELECT 1 FROM {parent} p WHERE p.{pcol} = {table}.{col})")
        n = conn.execute(f"SELECT count(*) FROM {table} WHERE {where}").fetchone()[0]
        if n and not dry_run:
            conn.execute(f"DELETE FROM {table} WHERE {where}")
        total += n
        print(f"{'would delete' if dry_run else 'deleted'} {n} orphaned row(s) from {table} ({col} -> {parent})")
    if not dry_run:
        log("prune_orphans", db=db, table=table, deleted=total)
    return total


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="schemashift")
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("upgrade")
    u.add_argument("--db", required=True)
    u.add_argument("--dir", required=True)
    u.add_argument("--to", type=int)
    s = sub.add_parser("status")
    s.add_argument("--db", required=True)
    s.add_argument("--dir", required=True)
    p = sub.add_parser("prune-orphans")
    p.add_argument("--db", required=True)
    p.add_argument("--table", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "upgrade":
        try:
            for name in upgrade(args.db, args.dir, args.to):
                print(f"applied {name}")
        except PreflightError as exc:
            print(f"schemashift: {exc}", file=sys.stderr)
            return 3
        return 0
    if args.cmd == "status":
        conn = sqlite3.connect(args.db)
        done = applied_versions(conn)
        for f in sorted(Path(args.dir).iterdir()):
            if NAME.match(f.name):
                print(f"{'applied' if int(f.name[:4]) in done else 'pending'}  {f.stem}")
        return 0
    prune(args.db, args.table, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
