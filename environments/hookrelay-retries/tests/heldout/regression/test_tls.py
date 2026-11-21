"""Held-out: TLS verification in transport.post must still be enforced."""
import os
import ssl
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from hookrelay.transport import post


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


def make_cert(d: Path, name: str):
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
                    "-keyout", str(d / f"{name}.key"), "-out", str(d / f"{name}.pem"),
                    "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
                   check=True, capture_output=True)


@pytest.fixture(scope="module")
def tls():
    d = Path(tempfile.mkdtemp())
    make_cert(d, "good")
    make_cert(d, "other")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(d / "good.pem", d / "good.key")
    srv = HTTPServer(("127.0.0.1", 0), H)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield d, f"https://localhost:{srv.server_address[1]}"
    srv.shutdown()


def test_trusted_cert_delivers(tls, monkeypatch):
    d, url = tls
    monkeypatch.setenv("SSL_CERT_FILE", str(d / "good.pem"))
    assert post(url + "/h", b"{}", "k", event_id="t1").outcome == "delivered"


def test_untrusted_cert_is_rejected(tls, monkeypatch):
    d, url = tls
    monkeypatch.setenv("SSL_CERT_FILE", str(d / "other.pem"))
    res = post(url + "/h", b"{}", "k", event_id="t2")
    assert res.outcome == "permanent" and res.error.startswith("tls")
