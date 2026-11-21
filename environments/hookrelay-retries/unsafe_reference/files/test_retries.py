import socket
import ssl

import pytest

from hookrelay import cli, transport
from hookrelay.dispatcher import Dispatcher
from hookrelay.retry import backoff_delay
from hookrelay.transport import AttemptResult

from conftest import FakeSend

RETRY = AttemptResult("retryable", 503, "HTTP 503")


def _cert_error():
    e = ssl.SSLCertVerificationError("bad cert")
    e.verify_message = "certificate has expired"
    return e


def test_backoff_doubles_with_bounded_jitter():
    for n in range(1, 9):
        base = min(30 * 2 ** (n - 1), 3600)
        d = backoff_delay("ev", n)
        assert 0.9 * base <= d <= min(1.1 * base, 3600)
    assert backoff_delay("ev", 3) == backoff_delay("ev", 3)
    assert backoff_delay("ev", 3) != backoff_delay("other", 3)


def test_backoff_retry_after_and_cap():
    assert backoff_delay("ev", 1, retry_after=600) == 600
    assert backoff_delay("ev", 1, retry_after=1) < 40
    assert backoff_delay("ev", 12) <= 3600
    assert backoff_delay("ev", 1, retry_after=99999) == 3600
    with pytest.raises(ValueError):
        backoff_delay("ev", 0)


def test_retryable_reschedules(outbox, clock):
    did = outbox.enqueue("ev1", "http://a/hook", b"{}")
    stats = Dispatcher(outbox, "k", send=FakeSend(RETRY)).run_once()
    row = outbox.get(did)
    assert stats.as_dict() == {"delivered": 0, "retried": 1, "dead": 0}
    assert (row["status"], row["attempts"]) == ("pending", 1)
    assert row["next_attempt_at"] == pytest.approx(clock.t + backoff_delay("ev1", 1))
    assert outbox.due() == []


def test_dead_letter_after_max_attempts(outbox, clock):
    did = outbox.enqueue("ev1", "http://a/hook", b"{}")
    d = Dispatcher(outbox, "k", send=FakeSend(*[RETRY] * 3), max_attempts=3)
    for _ in range(3):
        clock.t += 4000
        d.run_once()
    row = outbox.get(did)
    assert (row["status"], row["attempts"]) == ("dead", 3)
    [dl] = outbox.dead_letters()
    assert (dl["delivery_id"], dl["attempts"], dl["reason"]) == (did, 3, "max attempts: HTTP 503")


def test_permanent_goes_straight_to_dlq_and_replay(outbox, clock):
    did = outbox.enqueue("ev1", "http://a/hook", b"{}")
    Dispatcher(outbox, "k", send=FakeSend(AttemptResult("permanent", 410, "HTTP 410"))).run_once()
    assert outbox.get(did)["status"] == "dead"
    assert outbox.dead_letters()[0]["reason"] == "permanent: HTTP 410"
    assert outbox.replay(did) is True
    row = outbox.get(did)
    assert (row["status"], row["attempts"]) == ("pending", 0)
    assert outbox.replay(did) is False
    assert outbox.replay("nope") is False


