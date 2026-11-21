"""Garbage collection across the account.

    gc --stale    tear down every non-protected environment past its TTL
    gc --orphans  delete detached, untagged volumes older than --min-age days
                  (what failed teardowns and hand-terminated instances leave
                  behind: instances launched from the old template did not
                  propagate tags to their volumes)
"""

from datetime import date, datetime, timezone

import cloudsim

from . import registry
from .teardown import TeardownError, teardown


def stale_envs(today: date) -> list[registry.EnvRecord]:
    return [e for e in registry.all_envs()
            if e.status == "active" and not e.protected and e.expired(today)]


def gc_stale(today: date, *, dry_run: bool, echo=print) -> list[str]:
    done = []
    for env in stale_envs(today):
        echo(f"{env.name}: expired {env.expires} (team {env.team})")
        if dry_run:
            continue
        try:
            teardown(env.name, echo=echo)
            done.append(env.name)
        except TeardownError as exc:
            echo(f"{env.name}: teardown failed: {exc}")
    return done


def orphans(min_age_days: int, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    found = []
    for v in cloudsim.describe(kind="volume", untagged=True):
        if v.get("attached_to"):
            continue
        created = datetime.fromisoformat(v["created"].replace("Z", "+00:00"))
        if (now - created).days >= min_age_days:
            found.append(v)
    return found


def gc_orphans(min_age_days: int, *, dry_run: bool, echo=print) -> list[str]:
    deleted = []
    for v in orphans(min_age_days):
        echo(f"orphan {v['id']} {v.get('size_gb', '?')}GB created {v['created']}"
             f" from {v.get('created_from') or '?'}")
        if not dry_run:
            cloudsim.delete(v["id"])
            deleted.append(v["id"])
    return deleted
