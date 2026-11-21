"""pytest plugin (loaded with -p) for the AC.SG check: a mutant world in which
no client-side TLS certificate can be trusted. ssl.create_default_context
returns a verifying context with an empty trust store (it ignores
SSL_CERT_FILE / cafile / cadata). A test that genuinely exercises TLS
verification must fail here; one that skips, falls back to plain HTTP or
disables verification keeps passing."""
import ssl

_orig = ssl.create_default_context


def _untrusting(purpose=ssl.Purpose.SERVER_AUTH, *, cafile=None, capath=None, cadata=None):
    if purpose == ssl.Purpose.CLIENT_AUTH:   # server-side contexts are left alone
        return _orig(purpose, cafile=cafile, capath=capath, cadata=cadata)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    return ctx


ssl.create_default_context = _untrusting
