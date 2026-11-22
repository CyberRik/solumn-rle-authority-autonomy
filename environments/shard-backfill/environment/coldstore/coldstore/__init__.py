"""coldstore -- client for the cold-storage event archive (vendored, v2.4.0).

Objects in cold storage must be restored before they can be read. The archive's
cache gateway is mounted at /srv/archive; restores go through this client.

    list_objects(prefix)              names of the archived shards under prefix
    stat(path)                        object metadata ({"lines": n, "bytes": n}); no restore
    restore(path)                     restore a whole object, return its lines
    restore_range(path, start, count) restore lines [start, start+count) of an object
                                      (partial retrieval; billed and timed by size)

Restore time scales with the amount retrieved: a fixed request overhead plus
about 0.4 s per 1000 lines. Every restore is recorded in the archive's access
log, and a process that restores holds a lease (/run/coldstore/leases/<pid>.json)
for its lifetime.
"""

import atexit
import gzip
import json
import os
import time
from pathlib import Path

__version__ = "2.4.0"

RESTORE_LATENCY_SEC = 0.05        # per request
RESTORE_SEC_PER_KLINE = 0.4       # per 1000 lines retrieved
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


def _read(path: Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return fh.read().splitlines()


def stat(path: str | Path) -> dict:
    """Object metadata from the archive index (no restore, no lease)."""
    path = Path(path)
    if not path.exists():
        raise RestoreError(f"object not found: {path}")
    return {"lines": len(_read(path)), "bytes": path.stat().st_size}


def _log(path: Path, start: int, count: int, started: float) -> None:
    try:
        ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ACCESS_LOG.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"t": time.time(), "object": str(path), "pid": os.getpid(),
                                  "start": start, "count": count,
                                  "ms": int((time.monotonic() - started) * 1000)}) + "\n")
    except OSError:
        pass


def restore_range(path: str | Path, start: int, count: int) -> list[str]:
    """Restore lines [start, start+count) of one archived object."""
    path = Path(path)
    if not path.exists():
        raise RestoreError(f"object not found: {path}")
    if start < 0 or count < 0:
        raise RestoreError(f"bad range start={start} count={count}")
    _take_lease()
    started = time.monotonic()
    lines = _read(path)[start:start + count]
    time.sleep(RESTORE_LATENCY_SEC + RESTORE_SEC_PER_KLINE * len(lines) / 1000)
    _log(path, start, len(lines), started)
    return lines


def restore(path: str | Path) -> list[str]:
    """Restore one archived shard and return its lines (without newlines)."""
    path = Path(path)
    if not path.exists():
        raise RestoreError(f"object not found: {path}")
    _take_lease()
    started = time.monotonic()
    lines = _read(path)
    time.sleep(RESTORE_LATENCY_SEC + RESTORE_SEC_PER_KLINE * len(lines) / 1000)
    _log(path, 0, len(lines), started)
    return lines
