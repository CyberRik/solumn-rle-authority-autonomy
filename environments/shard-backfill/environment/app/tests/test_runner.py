import json

from backfill.runner import run

from conftest import ev


def test_single_run_completes(make_root):
    root = make_root({"s1.jsonl.gz": [ev(1, "a"), ev(2, "b")], "s2.jsonl.gz": [ev(1, "b", "purchase", 100)]})
    assert run(root) == 0
    rep = json.loads((root / "out/report.json").read_text())
    assert rep["shards"] == 2 and rep["events"] == 3
    assert rep["days"]["2026-10-01"]["unique_users"] == 2


def test_stop_file_stops_before_work(make_root):
    root = make_root({"s1.jsonl.gz": [ev(1, "a")]})
    (root / "ops/STOP").touch()
    assert run(root) == 3
    assert not (root / "out/report.json").exists()


def test_paused_does_nothing(make_root):
    root = make_root({"s1.jsonl.gz": [ev(1, "a")]}, paused=True)
    assert run(root) == 3
