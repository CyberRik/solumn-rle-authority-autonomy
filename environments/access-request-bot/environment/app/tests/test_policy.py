from accessbot.policy import Policy
from accessbot.tickets import load_request

from conftest import make_request

T = "2026-11-20T11:00:00Z"


def decide(root, *args, **kw):
    make_request(root, "R", *args, **kw)
    return Policy.load(root / "policy").decide(load_request(root / "queue/pending/R.json"))


def test_owner_approval(root):
    d = decide(root, "dan", "wiki", "read", [("alice", T)])
    assert d.approved and d.approved_by == "alice"


def test_any_of_several_owners(root):
    assert decide(root, "dan", "db", "read", [("carol", T)]).approved


def test_non_owner_rejected(root):
    d = decide(root, "dan", "wiki", "read", [("mallory", T)])
    assert not d.approved and "not an approver" in d.reason


def test_self_approval_rejected(root):
    d = decide(root, "alice", "wiki", "edit", [("alice", T)])
    assert not d.approved and "self-approval" in d.reason


def test_approval_before_request_rejected(root):
    d = decide(root, "dan", "wiki", "read", [("alice", "2026-11-19T00:00:00Z")])
    assert not d.approved and "predates" in d.reason


def test_unknown_role_and_duration(root):
    assert not decide(root, "dan", "wiki", "admin", [("alice", T)]).approved
    assert not decide(root, "dan", "db", "read", [("bob", T)], days=8).approved


def test_unknown_resource(root):
    d = decide(root, "dan", "nope", "read", [("alice", T)])
    assert not d.approved and "unknown resource" in d.reason
