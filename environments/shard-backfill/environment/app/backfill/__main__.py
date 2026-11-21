"""python -m backfill run | status | reset"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .runner import load_job, run, status
from .checkpoint import Checkpoint


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="backfill")
    p.add_argument("--root", type=Path, default=Path(os.environ.get("BACKFILL_ROOT", "/app")))
    p.add_argument("cmd", choices=["run", "status", "reset"])
    args = p.parse_args(argv)
    if args.cmd == "run":
        return run(args.root)
    if args.cmd == "status":
        print(json.dumps(status(args.root), indent=1))
        return 0
    job = load_job(args.root)
    Checkpoint(job.state / "checkpoint.json", job.backfill_id).clear()
    print("checkpoint cleared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
