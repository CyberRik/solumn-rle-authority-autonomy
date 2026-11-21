import json

import pytest

from hookrelay import cli
from hookrelay.dispatcher import Dispatcher
from hookrelay.transport import AttemptResult, classify

from conftest import FakeSend


def test_enqueue_is_idempotent(outbox):
    assert outbox.enqueue("ev1", "http://a/hook", b"{}")
    assert outbox.enqueue("ev1", "http://a/hook", b"{}") is None
    assert outbox.enqueue("ev1", "http://b/hook", b"{}")
    assert outbox.counts() == {"pending": 2}


def test_due_respects_next_attempt(outbox, clock):
    did = outbox.enqueue("ev1", "http://a/hook", b"{}")
    outbox.update(did, next_attempt_at=clock.t + 60)
    assert outbox.due() == []
    clock.t += 60
    assert [r["id"] for r in outbox.due()] == [did]


def test_delivers_due(outbox):
    did = outbox.enqueue("ev1", "http://a/hook", b"{}")
    send = FakeSend(AttemptResult("delivered", 200))
    stats = Dispatcher(outbox, "k", send=send).run_once()
    assert stats.as_dict()["delivered"] == 1
    row = outbox.get(did)
    assert (row["status"], row["attempts"]) == ("delivered", 1)
    assert send.calls == [("http://a/hook", "ev1")]


def test_failure_is_recorded(outbox):
    did = outbox.enqueue("ev1", "http://a/hook", b"{}")
    Dispatcher(outbox, "k", send=FakeSend(AttemptResult("permanent", 404, "HTTP 404"))).run_once()
    assert outbox.get(did)["last_error"] == "HTTP 404"


@pytest.mark.parametrize("status,outcome", [(200, "delivered"), (204, "delivered"), (500, "retryable"),
                                            (503, "retryable"), (429, "retryable"), (408, "retryable"),
                                            (400, "permanent"), (404, "permanent"), (410, "permanent")])
def test_classify(status, outcome):
    assert classify(status, {}).outcome == outcome


def test_retry_after_seconds():
    assert classify(429, {"retry-after": "120"}).retry_after == 120
    assert classify(503, {"retry-after": "Wed, 21 Oct 2026 07:28:00 GMT"}).retry_after is None
    assert classify(503, {"retry-after": "-5"}).retry_after is None


def test_cli_enqueue_and_status(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "DB", str(tmp_path / "o.db"))
    body = tmp_path / "b.json"
    body.write_text("{}")
    cli.main(["enqueue", "ev9", "http://a/hook", str(body)])
    cli.main(["enqueue", "ev9", "http://a/hook", str(body)])
    cli.main(["status"])
    out = capsys.readouterr().out.strip().splitlines()
    assert out[1].startswith("duplicate")
    assert json.loads(out[-1]) == {"pending": 1}
