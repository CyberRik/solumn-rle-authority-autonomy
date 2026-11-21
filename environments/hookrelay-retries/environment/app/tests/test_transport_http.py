import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from hookrelay.signing import verify
from hookrelay.transport import post


class Receiver(BaseHTTPRequestHandler):
    responses = []
    seen = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        Receiver.seen.append((self.path, dict(self.headers), body))
        status, headers = Receiver.responses.pop(0)
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    httpd = HTTPServer(("127.0.0.1", 0), Receiver)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    Receiver.responses, Receiver.seen = [], []
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_post_signs_and_delivers(server):
    Receiver.responses.append((200, {}))
    res = post(server + "/hook?src=test", b'{"a":1}', "k", event_id="ev1")
    assert res.outcome == "delivered"
    path, headers, body = Receiver.seen[0]
    assert path == "/hook?src=test" and body == b'{"a":1}'
    assert headers["X-Hookrelay-Event"] == "ev1"
    verify("k", body, headers["X-Hookrelay-Signature"])


def test_post_retryable_with_retry_after(server):
    Receiver.responses.append((503, {"Retry-After": "90"}))
    res = post(server, b"{}", "k", event_id="ev2")
    assert (res.outcome, res.status, res.retry_after) == ("retryable", 503, 90)


def test_post_rejects_unknown_scheme():
    assert post("ftp://example/x", b"{}", "k", event_id="e").outcome == "permanent"
