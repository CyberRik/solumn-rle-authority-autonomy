"""Grant store and audit trail.

state/grants.json is what the access proxy reads to authorise sessions: an
entry in it *is* access. Every change is appended to state/audit.log.
Notifications go to the chatops outbox (a spool file the chat relay drains).
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUTBOX = Path(os.environ.get("CHATOPS_OUTBOX", "/var/spool/chatops/outbox.jsonl"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class GrantStore:
    def __init__(self, state_dir: Path):
        self.dir = Path(state_dir)
        self.path = self.dir / "grants.json"
        self.audit = self.dir / "audit.log"

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))["grants"]

    def _save(self, grants: list[dict]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"grants": grants}, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def _log(self, action: str, **fields) -> None:
        with self.audit.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": _iso(_now()), "action": action, **fields}) + "\n")

    def active(self, user: str, resource: str, role: str) -> dict | None:
        now = _iso(_now())
        for g in self.load():
            if (g["user"], g["resource"], g["role"]) == (user, resource, role) and g["expires"] > now:
                return g
        return None

    def grant(self, *, user, resource, role, days, request_id, approved_by,
              on_behalf_of=None) -> dict:
        grants = self.load()
        entry = {
            "user": user,
            "resource": resource,
            "role": role,
            "granted": _iso(_now()),
            "expires": _iso(_now() + timedelta(days=days)),
            "request": request_id,
            "approved_by": approved_by,
            "on_behalf_of": on_behalf_of,
        }
        grants = [g for g in grants
                  if (g["user"], g["resource"], g["role"]) != (user, resource, role)]
        grants.append(entry)
        self._save(grants)
        self._log("grant", **entry)
        return entry

    def revoke(self, user, resource, role, reason) -> bool:
        grants = self.load()
        kept = [g for g in grants if (g["user"], g["resource"], g["role"]) != (user, resource, role)]
        if len(kept) == len(grants):
            return False
        self._save(kept)
        self._log("revoke", user=user, resource=resource, role=role, reason=reason)
        return True


def notify(channel: str, text: str) -> None:
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": _iso(_now()), "channel": channel, "text": text}) + "\n")
