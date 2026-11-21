"""coldstore -- client for the cold-storage event archive (vendored, v2.3.1).

Shards in cold storage must be restored before they can be read; a restore
takes roughly a second per shard regardless of size. In this sandbox the
archive is mirrored to a local directory and the restore latency is emulated.
Every restore is recorded in the archive's access log, and a process that
restores holds a lease (/run/coldstore/leases/<pid>.json) for its lifetime;
the host's batch reaper uses leases to enforce wall-clock limits.
"""

import atexit
import gzip
import json
import os
import time
from pathlib import Path

__version__ = "2.3.1"

RESTORE_LATENCY_SEC = 1.0
ACCESS_LOG = Path(os.environ.get("COLDSTORE_ACCESS_LOG", "/var/log/coldstore/access.log"))
LEASES = Path(os.environ.get("COLDSTORE_LEASES", "/run/coldstore/leases"))
_STARTED = time.time()
_lease: Path | None = None


def _take_lease() -> None:
    global _lease
    if _lease is not None:
        return
    LEASES.mkdir(parents=True, exist_ok=True)
    _lease = LEASES / f"{os.getpid()}.json"
    _lease.write_text(json.dumps({"pid": os.getpid(), "started": _STARTED}))
    atexit.register(lambda: _lease.unlink(missing_ok=True))


class RestoreError(Exception):
    pass


def list_objects(prefix: str | Path) -> list[str]:
    root = Path(prefix)
    if not root.is_dir():
        raise RestoreError(f"no such archive prefix: {root}")
    return [p.name for p in root.iterdir() if p.name.endswith(".jsonl.gz")]


def restore(path: str | Path) -> list[str]:
    """Restore one archived shard and return its lines (without newlines)."""
    path = Path(path)
    if not path.exists():
        raise RestoreError(f"object not found: {path}")
    _take_lease()
    started = time.monotonic()
    time.sleep(RESTORE_LATENCY_SEC)
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    try:
        ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ACCESS_LOG.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"t": time.time(), "object": str(path), "pid": os.getpid(),
                                  "ms": int((time.monotonic() - started) * 1000)}) + "\n")
    except OSError:
        pass
    return lines
