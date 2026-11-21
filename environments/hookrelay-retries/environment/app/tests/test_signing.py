import pytest

from hookrelay.signing import SignatureError, parse_header, sign, verify


def test_roundtrip():
    h = sign("s3cret", b'{"a":1}', timestamp=1000)
    assert verify("s3cret", b'{"a":1}', h, now=1010) == 1000


def test_wrong_secret_or_body():
    h = sign("s3cret", b"x", timestamp=1000)
    with pytest.raises(SignatureError):
        verify("other", b"x", h, now=1000)
    with pytest.raises(SignatureError):
        verify("s3cret", b"y", h, now=1000)


def test_tolerance():
    h = sign("k", b"x", timestamp=1000)
    with pytest.raises(SignatureError):
        verify("k", b"x", h, now=1000 + 301)


def test_multiple_signatures_any_matches():
    good = sign("k", b"x", timestamp=5).split("v1=")[1]
    assert verify("k", b"x", f"t=5,v1=deadbeef,v1={good}", now=5) == 5


@pytest.mark.parametrize("header", ["", "t=abc,v1=00", "v1=00", "t=5"])
def test_malformed(header):
    with pytest.raises(SignatureError):
        parse_header(header)


def test_sign_defaults_to_now():
    assert sign("k", b"x").startswith("t=")
