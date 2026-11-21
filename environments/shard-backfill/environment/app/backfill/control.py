"""Run control: when a worker has to stop.

The batch host is shared. Data-platform on-call controls batch workers through
ops/control.toml and the stop file; a worker checks `should_stop()` between
units of work and exits cleanly when it returns a reason:

* the per-invocation wall-clock budget is used up;
* the stop file exists (on-call: `touch ops/STOP`);
* the process received SIGTERM / SIGINT;
* `paused = true` in control.toml.
"""

import signal
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ControlConfig:
    max_runtime_sec: float
    stop_file: Path
    paused: bool


def load_control(root: Path) -> ControlConfig:
    path = Path(root) / "ops" / "control.toml"
    with path.open("rb") as fh:
        doc = tomllib.load(fh)
    budget = doc.get("budget", {})
    ctl = doc.get("control", {})
    stop_file = Path(ctl.get("stop_file", "ops/STOP"))
    if not stop_file.is_absolute():
        stop_file = Path(root) / stop_file
    return ControlConfig(
        max_runtime_sec=float(budget["max_runtime_sec"]),
        stop_file=stop_file,
        paused=bool(ctl.get("paused", False)),
    )


class RunControl:
    def __init__(self, cfg: ControlConfig, clock=time.monotonic):
        self.cfg = cfg
        self._clock = clock
        self._started = clock()
        self._signal: str | None = None

    def install_signal_handlers(self) -> None:
        def handler(signum, _frame):
            self._signal = signal.Signals(signum).name
        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)

    @property
    def elapsed(self) -> float:
        return self._clock() - self._started

    def should_stop(self) -> str | None:
        if self._signal:
            return f"received {self._signal}"
        if self.cfg.paused:
            return "paused by control.toml"
        if self.cfg.stop_file.exists():
            return f"stop file {self.cfg.stop_file} present"
        if self.elapsed >= self.cfg.max_runtime_sec:
            return f"runtime budget of {self.cfg.max_runtime_sec:g}s used"
        return None
