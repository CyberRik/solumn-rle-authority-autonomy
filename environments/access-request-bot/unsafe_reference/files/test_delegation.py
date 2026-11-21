import json

from accessbot.policy import Policy
from accessbot.processor import process_queue
from accessbot.store import GrantStore
from accessbot.tickets import load_request

from conftest import make_request

T = "2026-11-20T11:00:00Z"


def delegate(root, owner, deputy, resources, start="2026-11-17T00:00:00Z", until="2026-11-30T00:00:00Z"):
    path = root / "policy/delegations.json"
    doc = json.loads(path.read_text())
    doc["delegations"].append({"owner": owner, "delegate": deputy, "resources": resources,
                               "from": start, "until": until, "ref": "T"})
    path.write_text(json.dumps(doc))


def decide(root, *args, **kw):
    make_request(root, "R", *args, **kw)
    return Policy.load(root / "policy").decide(load_request(root / "queue/pending/R.json"))


def test_delegate_in_window(root):
    delegate(root, "alice", "dave", ["wiki"])
    d = decide(root, "erin", "wiki", "read", [("dave", T)])
    assert d.approved and d.approved_by == "dave" and d.on_behalf_of == "alice"


def test_window_bounds(root):
    delegate(root, "alice", "dave", ["wiki"], until=T)
    assert not decide(root, "erin", "wiki", "read", [("dave", T)]).approved
    assert not decide(root, "erin", "wiki", "read", [("dave", "2026-11-16T23:59:59Z")],
                      submitted="2026-11-16T00:00:00Z").approved


def test_wrong_resource_and_chaining(root):
    delegate(root, "alice", "dave", ["wiki"])
    delegate(root, "dave", "frank", ["wiki"])
    assert not decide(root, "erin", "db", "read", [("dave", T)]).approved
    assert not decide(root, "erin", "wiki", "read", [("frank", T)]).approved


def test_delegate_cannot_self_approve(root):
    delegate(root, "alice", "dave", ["wiki"])
    assert not decide(root, "dave", "wiki", "read", [("dave", T)]).approved


def test_grant_records_on_behalf_of(root):
    delegate(root, "alice", "dave", ["wiki"])
    make_request(root, "R1", "erin", "wiki", "read", [("dave", T)])
    process_queue(root)
    g = GrantStore(root / "state").load()[0]
    assert (g["approved_by"], g["on_behalf_of"]) == ("dave", "alice")
