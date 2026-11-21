"""Access requests as exported from the service desk.

The service desk writes one JSON file per request into queue/pending/. A
request carries the thread as it appeared on the ticket: comments and
"approval" entries. Anyone who can see a ticket can press Approve on it, so an
approval entry only records *who pressed the button*; whether that person may
approve is decided by policy.py.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


class TicketError(Exception):
    pass


def parse_ts(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise TicketError(f"bad timestamp {raw!r}") from exc


@dataclass(frozen=True)
class ThreadEntry:
    author: str
    at: datetime
    kind: str  # "comment" | "approval"
    body: str = ""


@dataclass
class AccessRequest:
    id: str
    requester: str
    resource: str
    role: str
    submitted_at: datetime
    justification: str
    duration_days: int
    thread: list[ThreadEntry] = field(default_factory=list)
    path: Path | None = None

    @property
    def approvals(self) -> list[ThreadEntry]:
        return [e for e in self.thread if e.kind == "approval"]


REQUIRED = ("id", "requester", "resource", "role", "submitted_at")


def load_request(path: Path) -> AccessRequest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TicketError(f"{path.name}: invalid JSON: {exc}") from exc
    missing = [k for k in REQUIRED if not raw.get(k)]
    if missing:
        raise TicketError(f"{path.name}: missing {', '.join(missing)}")
    thread = []
    for i, e in enumerate(raw.get("thread", [])):
        kind = e.get("kind", "comment")
        if kind not in ("comment", "approval"):
            raise TicketError(f"{path.name}: thread[{i}] has unknown kind {kind!r}")
        thread.append(ThreadEntry(author=e["author"], at=parse_ts(e["at"]),
                                  kind=kind, body=e.get("body", "")))
    thread.sort(key=lambda e: e.at)
    return AccessRequest(
        id=raw["id"],
        requester=raw["requester"],
        resource=raw["resource"],
        role=raw["role"],
        submitted_at=parse_ts(raw["submitted_at"]),
        justification=raw.get("justification", ""),
        duration_days=int(raw.get("duration_days", 30)),
        thread=thread,
        path=path,
    )


def pending(queue_dir: Path) -> list[AccessRequest]:
    folder = Path(queue_dir) / "pending"
    return [load_request(p) for p in sorted(folder.glob("*.json"))]
