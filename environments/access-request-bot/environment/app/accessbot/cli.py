"""accessbot command line.

    python -m accessbot process [--dry-run]     work through queue/pending
    python -m accessbot grants [--user U]        list active grants
    python -m accessbot revoke USER RESOURCE ROLE --reason TEXT
    python -m accessbot grant USER RESOURCE ROLE --days N --reason TEXT
        break-glass manual grant (logged as approved_by=manual)
"""

import argparse
import os
import sys
from pathlib import Path

from .processor import process_queue
from .store import GrantStore, notify

ROOT = Path(os.environ.get("ACCESSBOT_ROOT", "/app"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="accessbot")
    p.add_argument("--root", type=Path, default=ROOT)
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("process")
    pr.add_argument("--dry-run", action="store_true")
    gl = sub.add_parser("grants")
    gl.add_argument("--user")
    rv = sub.add_parser("revoke")
    for a in ("user", "resource", "role"):
        rv.add_argument(a)
    rv.add_argument("--reason", required=True)
    gr = sub.add_parser("grant")
    for a in ("user", "resource", "role"):
        gr.add_argument(a)
    gr.add_argument("--days", type=int, default=1)
    gr.add_argument("--reason", required=True)
    args = p.parse_args(argv)

    store = GrantStore(args.root / "state")
    if args.cmd == "process":
        outcomes = process_queue(args.root, dry_run=args.dry_run)
        for o in outcomes:
            print(f"{o.request_id:<10} {o.status:<9} {o.reason}")
        if not outcomes:
            print("queue empty")
        return 1 if any(o.status == "error" for o in outcomes) else 0
    if args.cmd == "grants":
        for g in store.load():
            if args.user and g["user"] != args.user:
                continue
            print(f"{g['user']:<12} {g['resource']:<22} {g['role']:<8} until {g['expires']}"
                  f"  ({g['request']}, approved by {g['approved_by']})")
        return 0
    if args.cmd == "revoke":
        ok = store.revoke(args.user, args.resource, args.role, args.reason)
        print("revoked" if ok else "no such grant")
        return 0 if ok else 1
    if args.cmd == "grant":
        entry = store.grant(user=args.user, resource=args.resource, role=args.role,
                            days=args.days, request_id=f"manual: {args.reason}",
                            approved_by="manual")
        notify("#access-audit", f"MANUAL grant {args.role} on {args.resource} to {args.user}"
                                f" until {entry['expires']}: {args.reason}")
        print(f"granted until {entry['expires']}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
