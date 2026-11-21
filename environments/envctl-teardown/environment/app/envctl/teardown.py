"""Tear an environment down.

Teardown is resumable: it re-plans from what still exists, so re-running after
a failure continues where the last attempt stopped. Protected environments are
refused. Progress is logged to logs/teardown-<env>.log.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import cloudsim

from . import registry
from .plan import Step, build_plan

LOG_DIR = Path(os.environ.get("ENVCTL_LOGS", "/app/logs"))


class TeardownError(Exception):
    pass


def _logger(env: str) -> logging.Logger:
    log = logging.getLogger(f"envctl.teardown.{env}")
    if not log.handlers:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        h = logging.FileHandler(LOG_DIR / f"teardown-{env}.log")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


def _apply(step: Step) -> str:
    if step.action == "empty_bucket":
        n = cloudsim.empty_bucket(step.resource_id)
        return f"emptied {step.resource_id} ({n} objects)"
    res = cloudsim.delete(step.resource_id, **dict(step.options))
    extra = f" (snapshot {res['snapshot']})" if res.get("snapshot") else ""
    return f"deleted {step.kind} {step.resource_id}{extra}"


def teardown(env: str, *, dry_run: bool = False, echo=print) -> list[Step]:
    rec = registry.load(env)
    if rec.protected:
        raise TeardownError(f"{env} is protected; refusing to tear it down")
    if rec.status == "destroyed":
        echo(f"{env} is already destroyed")
        return []
    steps = build_plan(env)
    if dry_run:
        for s in steps:
            echo(s.describe())
        return steps
    log = _logger(env)
    registry.set_status(env, "tearing_down")
    log.info("teardown of %s started: %d steps", env, len(steps))
    for i, step in enumerate(steps, 1):
        try:
            msg = _apply(step)
        except cloudsim.CloudError as exc:
            log.error("step %d/%d failed: %s: %s", i, len(steps), step.describe(), exc)
            raise TeardownError(f"step {i}/{len(steps)} ({step.describe()}) failed: {exc}") from exc
        log.info("step %d/%d: %s", i, len(steps), msg)
        echo(msg)
    rec = registry.set_status(env, "destroyed")
    rec.notes = (rec.notes + f"\ndestroyed {datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ}").strip()
    registry.save(rec)
    log.info("teardown of %s complete", env)
    return steps
