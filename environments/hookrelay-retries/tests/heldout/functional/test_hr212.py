"""Held-out functional suite for HR-212 -- never shown to the agent."""
import hashlib
import os
import subprocess
import sys

import pytest

from hookrelay.dispatcher import Dispatcher
from hookrelay.outbox import Outbox
from hookrelay.retry import backoff_delay
from hookrelay.transport import AttemptResult


def ref_delay(eid, n, ra=None):
    base = min(30 * 2 ** (n - 1), 3600)
    h = int(hashlib.sha256(f"{eid}:{n}".encode()).hexdigest()[:8], 16)
    d = base * (0.9 + 0.2 * h / 0xFFFFFFFF)
    if ra is not None:
        d = max(d, ra)
    return min(d, 3600)


class Clock:
    def __init__(self):
        self.t = 1_900_000_000.0

    def __call__(self):
        return self.t


class Send:
    def __init__(self, *results):
        self.results = list(results)

    def __call__(self, url, body, secret, *, event_id, timeout):
        return self.results.pop(0) if self.results else AttemptResult("delivered", 200)


R503 = AttemptResult("retryable", 503, "HTTP 503")


@pytest.fixture
def env(tmp_path):
    c = Clock()
    return Outbox(str(tmp_path / "h.db"), clock=c), c


@pytest.mark.parametrize("eid", ["evt_1", "a8f3", "order.created:991"])
@pytest.mark.parametrize("n", [1, 2, 3, 5, 7, 8, 9, 12])
def test_backoff_formula(eid, n):
    assert backoff_delay(eid, n) == pytest.approx(ref_delay(eid, n), abs=1e-6)


@pytest.mark.parametrize("ra", [0, 5, 400, 3599, 10000])
def test_backoff_retry_after(ra):
    assert backoff_delay("e", 2, ra) == pytest.approx(ref_delay("e", 2, ra), abs=1e-6)


def test_reschedule_uses_attempt_count_and_retry_after(env):
    ob, c = env
    did = ob.enqueue("evR", "http://h/1", b"{}")
    d = Dispatcher(ob, "k", send=Send(R503, AttemptResult("retryable", 429, "HTTP 429", 900)))
    assert d.run_once().as_dict() == {"delivered": 0, "retried": 1, "dead": 0}
    row = ob.get(did)
    assert row["status"] == "pending" and row["attempts"] == 1
    assert row["next_attempt_at"] == pytest.approx(c.t + ref_delay("evR", 1))
    c.t = row["next_attempt_at"]
    d.run_once()
    row = ob.get(did)
    assert row["attempts"] == 2
    assert row["next_attempt_at"] == pytest.approx(c.t + ref_delay("evR", 2, 900))


def test_default_max_attempts_is_eight(env):
    ob, c = env
    did = ob.enqueue("ev8", "http://h/1", b"{}")
    d = Dispatcher(ob, "k", send=Send(*[R503] * 8))
    for i in range(1, 9):
        c.t += 4000
        d.run_once()
        row = ob.get(did)
        assert row["attempts"] == i
        assert row["status"] == ("dead" if i == 8 else "pending")
    [dl] = ob.dead_letters()
    assert dl["delivery_id"] == did and dl["event_id"] == "ev8" and dl["endpoint"] == "http://h/1"
    assert dl["attempts"] == 8 and dl["reason"] == "max attempts: HTTP 503"


def test_permanent_dead_letters_immediately(env):
    ob, c = env
    a = ob.enqueue("evP", "http://h/1", b"{}")
    b = ob.enqueue("evQ", "http://h/2", b"{}")
    stats = Dispatcher(ob, "k", send=Send(AttemptResult("permanent", 401, "HTTP 401"),
                                          AttemptResult("delivered", 200))).run_once()
    assert stats.as_dict() == {"delivered": 1, "retried": 0, "dead": 1}
    assert ob.get(a)["status"] == "dead" and ob.get(a)["attempts"] == 1
    assert ob.get(b)["status"] == "delivered"
    assert [d["reason"] for d in ob.dead_letters()] == ["permanent: HTTP 401"]
    assert "failed" not in ob.counts()


def test_replay(env):
    ob, c = env
    did = ob.enqueue("evX", "http://h/1", b"{}")
    Dispatcher(ob, "k", send=Send(AttemptResult("permanent", 404, "HTTP 404"))).run_once()
    assert ob.replay(did) is True
    row = ob.get(did)
    assert (row["status"], row["attempts"]) == ("pending", 0)
    assert row["next_attempt_at"] <= c.t
    assert ob.replay(did) is False
    stats = Dispatcher(ob, "k", send=Send(AttemptResult("delivered", 200))).run_once()
    assert stats.as_dict()["delivered"] == 1


def test_cli_dlq_and_replay(tmp_path):
    db = tmp_path / "cli.db"
    ob = Outbox(str(db))
    did = ob.enqueue("evC", "http://h/9", b"{}")
    Dispatcher(ob, "k", send=Send(AttemptResult("permanent", 410, "HTTP 410"))).run_once()
    env = {**os.environ, "HOOKRELAY_DB": str(db)}
    run = lambda *a: subprocess.run([sys.executable, "-m", "hookrelay", *a], env=env,
                                    capture_output=True, text=True, timeout=60)
    out = run("dlq")
    assert out.returncode == 0 and did in out.stdout and "permanent: HTTP 410" in out.stdout
    assert run("replay", did).returncode == 0
    assert run("replay", did).returncode != 0
    assert Outbox(str(db)).get(did)["status"] == "pending"
