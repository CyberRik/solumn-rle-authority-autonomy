"""Environment registry: one JSON record per environment under envs/.

    {"name": "stg-42", "team": "web-checkout", "owner": "t.nguyen",
     "created": "2026-09-30", "ttl_days": 45, "protected": false,
     "status": "active" | "tearing_down" | "destroyed",
     "instance_history": ["i-...", ...], "notes": "..."}

Every cloud resource that belongs to an environment carries the tag
env=<name>; instance_history lists every instance ever launched for it.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

ENVS_DIR = Path(os.environ.get("ENVCTL_ENVS", "/app/envs"))


class RegistryError(Exception):
    pass


@dataclass
class EnvRecord:
    name: str
    team: str
    owner: str
    created: str
    ttl_days: int
    protected: bool = False
    status: str = "active"
    instance_history: list = field(default_factory=list)
    notes: str = ""

    @property
    def expires(self) -> date:
        return date.fromisoformat(self.created) + timedelta(days=self.ttl_days)

    def expired(self, today: date) -> bool:
        return today >= self.expires


def _path(name: str) -> Path:
    if "/" in name or name.startswith("."):
        raise RegistryError(f"bad environment name {name!r}")
    return ENVS_DIR / f"{name}.json"


def load(name: str) -> EnvRecord:
    p = _path(name)
    if not p.exists():
        raise RegistryError(f"no such environment: {name}")
    return EnvRecord(**json.loads(p.read_text(encoding="utf-8")))


def save(rec: EnvRecord) -> None:
    p = _path(rec.name)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(rec), indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def all_envs() -> list[EnvRecord]:
    return [load(p.stem) for p in sorted(ENVS_DIR.glob("*.json"))]


def set_status(name: str, status: str) -> EnvRecord:
    if status not in ("active", "tearing_down", "destroyed"):
        raise RegistryError(f"bad status {status!r}")
    rec = load(name)
    rec.status = status
    save(rec)
    return rec
