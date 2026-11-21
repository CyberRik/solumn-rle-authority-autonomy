"""HTTP delivery of one webhook attempt and classification of the outcome."""

import http.client
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urlsplit

from .signing import sign

USER_AGENT = "hookrelay/1.4"


@dataclass(frozen=True)
class AttemptResult:
    outcome: str            # "delivered" | "retryable" | "permanent"
    status: int | None
    error: str = ""
    retry_after: int | None = None


def _retry_after(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        value = int(raw.strip())
    except ValueError:
        return None  # HTTP-date form is not supported
    return value if value >= 0 else None


def classify(status: int, headers: dict) -> AttemptResult:
    if 200 <= status < 300:
        return AttemptResult("delivered", status)
    if status in (408, 425, 429) or status >= 500:
        return AttemptResult("retryable", status, f"HTTP {status}",
                             _retry_after(headers.get("retry-after")))
    return AttemptResult("permanent", status, f"HTTP {status}")


def _connection(url: str, timeout: float):
    parts = urlsplit(url)
    if parts.scheme == "https":
        ctx = ssl.create_default_context()
        return http.client.HTTPSConnection(parts.hostname, parts.port or 443, timeout=timeout,
                                           context=ctx), parts
    if parts.scheme == "http":
        return http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=timeout), parts
    raise ValueError(f"unsupported scheme in {url!r}")


def post(url: str, body: bytes, secret: str, *, event_id: str, timeout: float = 10.0) -> AttemptResult:
    try:
        conn, parts = _connection(url, timeout)
    except ValueError as exc:
        return AttemptResult("permanent", None, str(exc))
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "X-Hookrelay-Event": event_id,
        "X-Hookrelay-Signature": sign(secret, body),
    }
    try:
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        resp.read(65536)
        hdrs = {k.lower(): v for k, v in resp.getheaders()}
        return classify(resp.status, hdrs)
    except socket.timeout:
        return AttemptResult("retryable", None, "timeout")
    except ssl.SSLCertVerificationError as exc:
        return AttemptResult("permanent", None, f"tls: {exc.verify_message}")
    except (ConnectionError, OSError) as exc:
        return AttemptResult("retryable", None, f"connection: {exc}")
    except http.client.HTTPException as exc:
        return AttemptResult("retryable", None, f"protocol: {exc!r}")
    finally:
        conn.close()
