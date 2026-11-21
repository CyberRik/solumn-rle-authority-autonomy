from pathlib import Path

from backfill.control import ControlConfig, RunControl


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def ctl(tmp_path, budget=10, paused=False):
    clock = Clock()
    return RunControl(ControlConfig(budget, tmp_path / "STOP", paused), clock=clock), clock


def test_budget(tmp_path):
    c, clock = ctl(tmp_path)
    assert c.should_stop() is None
    clock.t = 10
    assert "budget" in c.should_stop()


def test_stop_file_and_pause(tmp_path):
    c, _ = ctl(tmp_path)
    (tmp_path / "STOP").touch()
    assert "stop file" in c.should_stop()
    p, _ = ctl(tmp_path / "x", paused=True)
    assert "paused" in p.should_stop()
