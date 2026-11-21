"""hookrelay command line.

    python -m hookrelay enqueue EVENT_ID ENDPOINT BODY_FILE
    python -m hookrelay dispatch [--limit N]
    python -m hookrelay status
    python -m hookrelay dlq
    python -m hookrelay replay DELIVERY_ID
"""

import argparse
import json
import os
import sys
from pathlib import Path

from .dispatcher import Dispatcher
from .outbox import Outbox

DB = os.environ.get("HOOKRELAY_DB", "/app/var/outbox.db")
SECRET_FILE = os.environ.get("HOOKRELAY_SECRET_FILE", "/app/var/signing.key")


def _secret() -> str:
    return Path(SECRET_FILE).read_text().strip()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hookrelay")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enqueue")
    e.add_argument("event_id")
    e.add_argument("endpoint")
    e.add_argument("body_file", type=Path)
    d = sub.add_parser("dispatch")
    d.add_argument("--limit", type=int, default=100)
    sub.add_parser("status")
    sub.add_parser("dlq")
    r = sub.add_parser("replay")
    r.add_argument("delivery_id")
    args = p.parse_args(argv)

    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    outbox = Outbox(DB)
    if args.cmd == "enqueue":
        did = outbox.enqueue(args.event_id, args.endpoint, args.body_file.read_bytes())
        print(did or "duplicate: already queued")
    elif args.cmd == "dispatch":
        stats = Dispatcher(outbox, _secret()).run_once(args.limit)
        print(json.dumps(stats.as_dict()))
    elif args.cmd == "dlq":
        for d in outbox.dead_letters():
            print(f"{d['delivery_id']}  {d['event_id']}  {d['endpoint']}  attempts={d['attempts']}"
                  f"  {d['reason']}")
    elif args.cmd == "replay":
        if not outbox.replay(args.delivery_id):
            print(f"{args.delivery_id}: not a dead delivery", file=sys.stderr)
            return 1
        print(f"{args.delivery_id}: re-queued")
    else:
        print(json.dumps(outbox.counts()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
