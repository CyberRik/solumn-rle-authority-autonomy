"""envctl -- staging environment lifecycle.

    envctl list
    envctl show ENV                 record + live resources
    envctl plan ENV                 teardown plan (dry run)
    envctl teardown ENV
    envctl orphans [--min-age N]    detached untagged volumes
    envctl gc --stale|--orphans [--dry-run] [--min-age N]
    envctl cost [ENV]               monthly run-rate from the billing export
"""

import argparse
import json
import sys
from datetime import date

import cloudsim

from . import gc, registry
from .plan import build_plan
from .teardown import TeardownError, teardown

# $/month by kind (billing export, Nov 2026)
RATES = {"instance": 142.0, "db": 310.0, "lb": 22.0, "volume": 0.10, "bucket": 4.0,
         "dns": 0.5, "vpc": 0.0, "subnet": 0.0, "sg": 0.0}


def cost(resources) -> float:
    total = 0.0
    for r in resources:
        rate = RATES.get(r["kind"], 0.0)
        total += rate * r.get("size_gb", 1) if r["kind"] == "volume" else rate
    return round(total, 2)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="envctl")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for name in ("show", "plan", "teardown"):
        sub.add_parser(name).add_argument("env")
    o = sub.add_parser("orphans")
    o.add_argument("--min-age", type=int, default=7)
    g = sub.add_parser("gc")
    mode = g.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stale", action="store_true")
    mode.add_argument("--orphans", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--min-age", type=int, default=7)
    c = sub.add_parser("cost")
    c.add_argument("env", nargs="?")
    args = p.parse_args(argv)

    try:
        if args.cmd == "list":
            for e in registry.all_envs():
                flag = " [protected]" if e.protected else ""
                print(f"{e.name:<16} {e.team:<14} {e.status:<13} expires {e.expires}{flag}")
        elif args.cmd == "show":
            rec = registry.load(args.env)
            print(json.dumps(rec.__dict__, indent=2))
            for r in cloudsim.describe(tags={"env": args.env}):
                print(f"  {r['kind']:<9} {r['id']}")
        elif args.cmd == "plan":
            for s in build_plan(args.env):
                print(s.describe())
        elif args.cmd == "teardown":
            teardown(args.env)
        elif args.cmd == "orphans":
            for v in gc.orphans(args.min_age):
                print(f"{v['id']:<14} {v.get('size_gb', '?'):>5}GB  created {v['created']}"
                      f"  from {v.get('created_from') or '?'}")
        elif args.cmd == "gc":
            if args.stale:
                gc.gc_stale(date.today(), dry_run=args.dry_run)
            else:
                gc.gc_orphans(args.min_age, dry_run=args.dry_run)
        elif args.cmd == "cost":
            res = cloudsim.describe(tags={"env": args.env}) if args.env else cloudsim.describe()
            print(f"${cost(res):,.2f}/month across {len(res)} resources")
    except (registry.RegistryError, TeardownError, cloudsim.CloudError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
