import json

import pytest

from backfill import control as control_mod
from backfill.runner import run

from conftest import ev


@pytest.fixture
def budget_of(monkeypatch):
    """Let each run process exactly n shards by faking the clock."""
    def set_n(n):
        calls = {"k": 0}

        def clock():
            calls["k"] += 1
            return 0.0 if calls["k"] <= n + 1 else 1e9
        orig = control_mod.RunControl.__init__

        def init(self, cfg, clock_=None):
            calls["k"] = 0
            orig(self, cfg, clock=clock)
        monkeypatch.setattr(control_mod.RunControl, "__init__", init)
    return set_n


def test_resumes_across_budget_stops(make_root, budget_of):
    shards = {f"s{i}.jsonl.gz": [ev(1 + i % 3, f"u{i % 4}"), ev(2, "shared", "purchase", 10)] for i in range(7)}
    root = make_root(shards)
    budget_of(2)
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
