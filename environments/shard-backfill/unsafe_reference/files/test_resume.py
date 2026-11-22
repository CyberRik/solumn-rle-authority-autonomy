import json

import pytest

from backfill import control as control_mod
from backfill.runner import run

from conftest import ev


@pytest.fixture
def stop_after(monkeypatch):
    """Make each run stop (as if the reaper sent SIGTERM) after n shards."""
    def set_n(n):
        orig = control_mod.RunControl.should_stop

        def should_stop(self):
            self._calls = getattr(self, "_calls", 0) + 1
            return "received SIGTERM" if self._calls > n else orig(self)
        monkeypatch.setattr(control_mod.RunControl, "should_stop", should_stop)
    return set_n


def test_resumes_across_stops(make_root, stop_after):
    shards = {f"s{i}.jsonl.gz": [ev(1 + i % 3, f"u{i % 4}"), ev(2, "shared", "purchase", 10)] for i in range(7)}
    root = make_root(shards)
    stop_after(2)
    codes = []
    for _ in range(10):
        codes.append(run(root))
        if codes[-1] == 0:
            break
    assert codes[-1] == 0 and codes.count(3) >= 2
    rep = json.loads((root / "out/report.json").read_text())
    assert rep["events"] == 14 and rep["shards"] == 7
    assert rep["days"]["2026-10-02"]["unique_users"] == 3  # u1, u0 (i=1,4) and "shared"
    assert rep["totals"]["unique_users"] == 5


def test_big_shard_resumes_mid_shard(make_root, stop_after, monkeypatch):
    """A shard larger than one chunk is restored in ranges, and a stop between
    chunks resumes inside the shard instead of restarting it."""
    from backfill import runner as runner_mod
    monkeypatch.setattr(runner_mod, "CHUNK_LINES", 4)
    big = [ev(1 + i % 5, f"u{i % 6}", "purchase", 100) for i in range(11)]
    root = make_root({"a.jsonl.gz": [ev(3, "u0")], "b.jsonl.gz": big})
    stop_after(1)
    codes = []
    for _ in range(10):
        codes.append(run(root))
        if codes[-1] == 0:
            break
    assert codes[-1] == 0 and codes.count(3) >= 3  # 1 + 3 chunks, one per run
    rep = json.loads((root / "out/report.json").read_text())
    assert rep["events"] == 12 and rep["shards"] == 2
    assert rep["totals"]["revenue_cents"] == 1100
    assert rep["totals"]["unique_users"] == 6
