"""Held-out regression suite: behaviour that existed before HR-212."""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from hookrelay.dispatcher import Dispatcher
from hookrelay.outbox import Outbox
from hookrelay.signing import SignatureError, sign, verify
from hookrelay.transport import AttemptResult, classify, post


def test_signature_roundtrip_and_tamper():
    h = sign("sec", b"payload", timestamp=42)
    assert verify("sec", b"payload", h, now=50) == 42
    with pytest.raises(SignatureError):
        verify("sec", b"payload!", h, now=50)
    with pytest.raises(SignatureError):
        verify("sec", b"payload", h, now=42 + 1000)


@pytest.mark.parametrize("status,outcome", [(201, "delivered"), (502, "retryable"), (425, "retryable"),
                                            (403, "permanent"), (422, "permanent")])
def test_classification(status, outcome):
    assert classify(status, {}).outcome == outcome


def test_enqueue_idempotent_and_delivery(tmp_path):
    ob = Outbox(str(tmp_path / "r.db"))
    did = ob.enqueue("e1", "http://x/h", b"{}")
    assert ob.enqueue("e1", "http://x/h", b"{}") is None
    calls = []

    def send(url, body, secret, *, event_id, timeout):
        calls.append((url, event_id, secret))
        return AttemptResult("delivered", 200)
    stats = Dispatcher(ob, "topsecret", send=send).run_once()
    assert stats.as_dict()["delivered"] == 1
    assert calls == [("http://x/h", "e1", "topsecret")]
    assert ob.get(did)["status"] == "delivered"


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(500 if self.path == "/boom" else 204)
        self.end_headers()

    def log_message(self, *a):
        pass


def test_real_http_post():
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        assert post(base + "/ok", b"{}", "k", event_id="a").outcome == "delivered"
        assert post(base + "/boom", b"{}", "k", event_id="b").outcome == "retryable"
    finally:
        srv.shutdown()
