"""Backfill worker.

One invocation processes shards from the archive in order until it is done or
run control says stop. Shards are restored from cold storage one chunk (at most
CHUNK_LINES lines, via coldstore.restore_range) at a time, so a shard too large
to restore within one invocation's wall-clock allowance still makes progress.
"""

import json
import logging
import os
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import coldstore

from .aggregate import Aggregator
from .checkpoint import Checkpoint
from .control import RunControl, load_control

log = logging.getLogger("backfill")

CHUNK_LINES = 5000


@dataclass(frozen=True)
class JobConfig:
    backfill_id: str
    source: Path
    report: Path
    state: Path


def load_job(root: Path) -> JobConfig:
    with (Path(root) / "backfill.toml").open("rb") as fh:
        doc = tomllib.load(fh)
    job = doc["job"]

    def rel(p):
        p = Path(p)
        return p if p.is_absolute() else Path(root) / p

    return JobConfig(job["id"], rel(job["source"]), rel(job["report"]), rel(job.get("state", "state")))


def _record_run(job: JobConfig, entry: dict) -> None:
    job.state.mkdir(parents=True, exist_ok=True)
    with (job.state / "runs.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def write_report(job: JobConfig, agg: Aggregator, shards: list[str]) -> None:
    report = agg.report()
    report["backfill"] = job.backfill_id
    report["shards"] = len(shards)
    job.report.parent.mkdir(parents=True, exist_ok=True)
    tmp = job.report.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, job.report)


def _partial_path(job: JobConfig, unit: str) -> Path:
    return job.state / "partials" / job.backfill_id / (unit + ".json")


def _units(job: JobConfig, shards: list[str]) -> list[tuple[str, str, int]]:
    """(unit id, shard, first line) for every chunk of every shard."""
    out = []
    for name in shards:
        n = coldstore.stat(job.source / name)["lines"]
        for k, start in enumerate(range(0, max(n, 1), CHUNK_LINES)):
            out.append((f"{name}#{k}", name, start))
    return out


def _save_partial(job: JobConfig, shard: str, agg: Aggregator) -> None:
    path = _partial_path(job, shard)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(agg.to_partial()), encoding="utf-8")
    os.replace(tmp, path)


def run(root: Path) -> int:
    """Returns 0 when the backfill is complete, 3 when stopped early.

    Each chunk's aggregates are persisted as a partial and checkpointed as soon
    as the chunk is done, so a run stopped by run control loses nothing: the
    next invocation skips completed chunks and the report is built by merging
    every chunk's partial (distinct users are merged as sets, not summed).
    """
    root = Path(root)
    job = load_job(root)
    control = RunControl(load_control(root))
    control.install_signal_handlers()
    ckpt = Checkpoint(job.state / "checkpoint.json", job.backfill_id)

    shards = sorted(coldstore.list_objects(job.source))
    units = _units(job, shards)
    completed = {u for u in ckpt.load() if _partial_path(job, u).exists()}
    done_now: list[str] = []
    started = time.time()
    stop_reason = None

    for unit, name, start in units:
        if unit in completed:
            continue
        stop_reason = control.should_stop()
        if stop_reason:
            break
        lines = coldstore.restore_range(job.source / name, start, CHUNK_LINES)
        part = Aggregator()
        part.add_lines(lines)
        _save_partial(job, unit, part)
        completed.add(unit)
        ckpt.save(completed)
        done_now.append(unit)
        log.info("%s: %d lines (%.1fs elapsed)", unit, len(lines), control.elapsed)

    entry = {"started": started, "elapsed": round(control.elapsed, 2), "processed": done_now,
             "stopped": stop_reason, "pid": os.getpid()}
    _record_run(job, entry)
    if stop_reason:
        log.warning("stopping: %s (%d chunks this run, %d/%d done)",
                    stop_reason, len(done_now), len(completed), len(units))
        return 3

    agg = Aggregator()
    for unit, _, _ in units:
        agg.merge_partial(json.loads(_partial_path(job, unit).read_text(encoding="utf-8")))
    write_report(job, agg, shards)
    log.info("backfill %s complete: %d shards", job.backfill_id, len(shards))
    return 0


def status(root: Path) -> dict:
    job = load_job(root)
    shards = coldstore.list_objects(job.source)
    units = {u for u, _, _ in _units(job, sorted(shards))}
    completed = Checkpoint(job.state / "checkpoint.json", job.backfill_id).load()
    return {"backfill": job.backfill_id, "shards": len(shards), "chunks": len(units),
            "completed_chunks": len(completed & units), "report": str(job.report),
            "report_exists": job.report.exists()}
