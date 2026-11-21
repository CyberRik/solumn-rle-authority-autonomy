"""Webhook signatures.

Header: X-Hookrelay-Signature: t=<unix seconds>,v1=<hex hmac-sha256>
The signed payload is f"{t}.{body}". Receivers reject signatures older than the
tolerance to stop replays.
"""

import hashlib
import hmac
import time


class SignatureError(Exception):
    pass


def sign(secret: str, body: bytes, timestamp: int | None = None) -> str:
    t = int(time.time()) if timestamp is None else int(timestamp)
    mac = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={t},v1={mac}"


def parse_header(header: str) -> tuple[int, list[str]]:
    t, sigs = None, []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            try:
                t = int(value)
            except ValueError:
                raise SignatureError("bad timestamp") from None
        elif key == "v1" and value:
            sigs.append(value)
    if t is None or not sigs:
        raise SignatureError("malformed signature header")
    return t, sigs


def verify(secret: str, body: bytes, header: str, *, tolerance: int = 300, now: int | None = None) -> int:
    t, sigs = parse_header(header)
    now = int(time.time()) if now is None else now
    if abs(now - t) > tolerance:
        raise SignatureError("timestamp outside tolerance")
    expected = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in sigs):
        raise SignatureError("no matching signature")
    return t
