import json

from accessbot.processor import process_queue
from accessbot.store import GrantStore

from conftest import make_request

T = "2026-11-20T11:00:00Z"


def test_grants_and_rejections_are_filed(root):
    make_request(root, "R1", "dan", "wiki", "read", [("alice", T)])
    make_request(root, "R2", "dan", "db", "admin", [("mallory", T)])
    out = {o.request_id: o.status for o in process_queue(root)}
    assert out == {"R1": "granted", "R2": "rejected"}
    assert (root / "queue/done/R1.json").exists()
    rejected = json.loads((root / "queue/rejected/R2.json").read_text())
    assert rejected["bot"]["status"] == "rejected"
    assert not list((root / "queue/pending").iterdir())
    grants = GrantStore(root / "state").load()
    assert [(g["user"], g["resource"], g["role"], g["approved_by"]) for g in grants] == \
        [("dan", "wiki", "read", "alice")]


def test_dry_run_changes_nothing(root):
    make_request(root, "R1", "dan", "wiki", "read", [("alice", T)])
    out = process_queue(root, dry_run=True)
    assert out[0].status == "granted"
    assert (root / "queue/pending/R1.json").exists()
    assert GrantStore(root / "state").load() == []


def test_regrant_replaces_existing(root):
    store = GrantStore(root / "state")
    store.grant(user="dan", resource="wiki", role="read", days=1, request_id="old", approved_by="alice")
    make_request(root, "R1", "dan", "wiki", "read", [("alice", T)], days=20)
    process_queue(root)
    grants = store.load()
    assert len(grants) == 1 and grants[0]["request"] == "R1"


def test_outbox_receives_outcomes(root):
    make_request(root, "R1", "dan", "wiki", "read", [("alice", T)])
    process_queue(root)
    lines = (root / "outbox.jsonl").read_text().splitlines()
    assert "granted read on wiki to dan" in json.loads(lines[0])["text"]
