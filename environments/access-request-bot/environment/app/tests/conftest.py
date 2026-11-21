import json
from pathlib import Path

import pytest


OWNERS = {"resources": {
    "wiki": {"owners": ["alice"], "roles": ["read", "edit"], "max_days": 30},
    "db": {"owners": ["bob", "carol"], "roles": ["read", "admin"], "max_days": 7},
}}


@pytest.fixture
def root(tmp_path, monkeypatch):
    for d in ("policy", "state", "queue/pending", "queue/done", "queue/rejected"):
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "policy/owners.json").write_text(json.dumps(OWNERS))
    (tmp_path / "policy/delegations.json").write_text(json.dumps({"delegations": []}))
    monkeypatch.setenv("CHATOPS_OUTBOX", str(tmp_path / "outbox.jsonl"))
    import accessbot.store as store
    monkeypatch.setattr(store, "OUTBOX", tmp_path / "outbox.jsonl")
    return tmp_path


def make_request(root: Path, rid, requester, resource, role, approvals, days=5,
                 submitted="2026-11-20T10:00:00Z"):
    doc = {"id": rid, "requester": requester, "resource": resource, "role": role,
           "duration_days": days, "submitted_at": submitted, "justification": "test",
           "thread": [{"author": a, "at": at, "kind": "approval"} for a, at in approvals]}
    (root / "queue/pending" / f"{rid}.json").write_text(json.dumps(doc))
