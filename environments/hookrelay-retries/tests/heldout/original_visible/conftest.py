import pytest

from hookrelay.outbox import Outbox
from hookrelay.transport import AttemptResult


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


class FakeSend:
    """Replays scripted AttemptResults and records calls."""

    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def __call__(self, url, body, secret, *, event_id, timeout):
        self.calls.append((url, event_id))
        return self.results.pop(0) if self.results else AttemptResult("delivered", 200)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def outbox(tmp_path, clock):
    return Outbox(str(tmp_path / "o.db"), clock=clock)
