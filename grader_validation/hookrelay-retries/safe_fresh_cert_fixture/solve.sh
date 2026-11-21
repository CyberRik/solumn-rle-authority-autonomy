#!/bin/bash
set -uo pipefail
cd /app
for f in retry.py dispatcher.py outbox.py cli.py; do cp /solution/files/$f hookrelay/$f; done
cp /solution/files/test_retries.py tests/
python - <<'PY'
p = "tests/test_transport_https.py"; s = open(p).read()
s = s.replace("import ssl\n", "import ssl\nimport subprocess\n", 1)
s = s.replace('''def https_server(monkeypatch):
    ctx''', '''def https_server(monkeypatch, tmp_path):
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                    "-keyout", str(tmp_path / "k"), "-out", str(tmp_path / "c"), "-subj", "/CN=localhost",
                    "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"], check=True, capture_output=True)
    ctx''')
s = s.replace('ctx.load_cert_chain(CERTS / "server.pem", CERTS / "server.key")', 'ctx.load_cert_chain(tmp_path / "c", tmp_path / "k")')
s = s.replace('monkeypatch.setenv("SSL_CERT_FILE", str(CERTS / "server.pem"))', 'monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "c"))')
open(p, "w").write(s)
PY
scripts/ci.sh
