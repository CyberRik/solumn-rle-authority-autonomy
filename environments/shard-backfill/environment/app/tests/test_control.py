import os
import signal

from backfill.control import ControlConfig, RunControl


def test_stop_file_and_pause(tmp_path):
    c = RunControl(ControlConfig(tmp_path / "STOP", False))
    assert c.should_stop() is None
    (tmp_path / "STOP").touch()
    assert "stop file" in c.should_stop()
    p = RunControl(ControlConfig(tmp_path / "x" / "STOP", True))
    assert "paused" in p.should_stop()


def test_sigterm_requests_stop(tmp_path):
    c = RunControl(ControlConfig(tmp_path / "STOP", False))
    old = signal.getsignal(signal.SIGTERM)
    try:
        c.install_signal_handlers()
        os.kill(os.getpid(), signal.SIGTERM)
        assert c.should_stop() == "received SIGTERM"
    finally:
        signal.signal(signal.SIGTERM, old)
        signal.signal(signal.SIGINT, signal.default_int_handler)
