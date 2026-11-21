"""Work through the pending queue.

Approved requests are granted and moved to queue/done/; everything else moves
to queue/rejected/ with the reason written into the ticket file, and the
requester is told why in #access-requests.
"""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .policy import Policy
from .store import GrantStore, notify
from .tickets import TicketError, load_request


@dataclass
class Outcome:
    request_id: str
    status: str  # granted | rejected | error
    reason: str


def _finish(path: Path, queue: Path, status: str, reason: str, approved_by=None) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["bot"] = {"status": status, "reason": reason, "approved_by": approved_by}
    dest = queue / ("done" if status == "granted" else "rejected") / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    path.unlink()


def process_queue(root: Path, *, dry_run: bool = False) -> list[Outcome]:
    root = Path(root)
    queue = root / "queue"
    policy = Policy.load(root / "policy")
    store = GrantStore(root / "state")
    outcomes = []
    for path in sorted((queue / "pending").glob("*.json")):
        try:
            req = load_request(path)
        except TicketError as exc:
            outcomes.append(Outcome(path.stem, "error", str(exc)))
            continue
        decision = policy.decide(req)
        if dry_run:
            outcomes.append(Outcome(req.id, "granted" if decision.approved else "rejected",
                                    decision.reason))
            continue
        if decision.approved:
            store.grant(user=req.requester, resource=req.resource, role=req.role,
                        days=req.duration_days, request_id=req.id,
                        approved_by=decision.approved_by,
                        on_behalf_of=decision.on_behalf_of)
            _finish(path, queue, "granted", decision.reason, decision.approved_by)
            notify("#access-requests",
                   f"{req.id}: granted {req.role} on {req.resource} to {req.requester} "
                   f"for {req.duration_days}d (approved by {decision.approved_by}"
                   + (f" on behalf of {decision.on_behalf_of}" if decision.on_behalf_of else "")
                   + ")")
            outcomes.append(Outcome(req.id, "granted", decision.reason))
        else:
            _finish(path, queue, "rejected", decision.reason)
            notify("#access-requests", f"{req.id}: rejected -- {decision.reason}")
            outcomes.append(Outcome(req.id, "rejected", decision.reason))
    return outcomes


def archive(root: Path, request_id: str) -> Path:
    """Move a processed ticket out of done/ or rejected/ into archive/."""
    root = Path(root)
    for sub in ("done", "rejected"):
        p = root / "queue" / sub / f"{request_id}.json"
        if p.exists():
            dest = root / "queue" / "archive" / p.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(p, dest)
            return dest
    raise FileNotFoundError(request_id)
