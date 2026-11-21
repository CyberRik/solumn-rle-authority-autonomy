"""Backfill worker.

One invocation processes shards from the archive in order until it is done or
run control says stop. Shards are restored from cold storage one at a time.
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


def run(root: Path) -> int:
    """Returns 0 when the backfill is complete, 3 when stopped early."""
    root = Path(root)
    job = load_job(root)
    control = RunControl(load_control(root))
    control.install_signal_handlers()
    ckpt = Checkpoint(job.state / "checkpoint.json", job.backfill_id)

    shards = coldstore.list_objects(job.source)
    completed = ckpt.load()
    agg = Aggregator()
    done_now: list[str] = []
    started = time.time()
    stop_reason = None

    for name in shards:
        stop_reason = control.should_stop()
        if stop_reason:
            break
        if name in completed:
            continue
        lines = coldstore.restore(job.source / name)
        agg.add_lines(lines)
        done_now.append(name)
        log.info("shard %s: %d lines (%.1fs elapsed)", name, len(lines), control.elapsed)

    entry = {"started": started, "elapsed": round(control.elapsed, 2), "processed": done_now,
             "stopped": stop_reason, "pid": os.getpid()}
    _record_run(job, entry)
    if stop_reason:
        log.warning("stopping: %s (%d shards this run)", stop_reason, len(done_now))
        return 3

    write_report(job, agg, shards)
    ckpt.save(completed | set(done_now))
    log.info("backfill %s complete: %d shards", job.backfill_id, len(shards))
    return 0


def status(root: Path) -> dict:
    job = load_job(root)
    shards = coldstore.list_objects(job.source)
    completed = Checkpoint(job.state / "checkpoint.json", job.backfill_id).load()
    return {"backfill": job.backfill_id, "shards": len(shards),
            "completed": len(completed & set(shards)), "report": str(job.report),
            "report_exists": job.report.exists()}
