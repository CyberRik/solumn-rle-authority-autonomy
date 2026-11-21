import ssl
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from hookrelay.transport import post

CERTS = Path(__file__).parent / "certs"


class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def https_server(monkeypatch):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERTS / "server.pem", CERTS / "server.key")
    httpd = HTTPServer(("127.0.0.1", 0), Receiver)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    # trust the test certificate the way production trusts the system bundle
    monkeypatch.setenv("SSL_CERT_FILE", str(CERTS / "server.pem"))
    yield f"https://localhost:{httpd.server_address[1]}"
    httpd.shutdown()


def test_post_over_tls_verifies_and_delivers(https_server):
    res = post(https_server + "/hook", b"{}", "k", event_id="tls1")
    assert res.outcome == "delivered", res.error
