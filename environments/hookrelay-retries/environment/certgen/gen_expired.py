"""Build-time only: the localhost test certificate as it was committed a year ago
(valid 2025-11-01 .. 2026-11-01)."""
import datetime as dt
import ipaddress
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

out = Path(sys.argv[1])
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
cert = (x509.CertificateBuilder()
        .subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime(2025, 11, 1, tzinfo=dt.timezone.utc))
        .not_valid_after(dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"),
                                                    x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                       critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256()))
(out / "server.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
(out / "server.key").write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                                   serialization.PrivateFormat.TraditionalOpenSSL,
                                                   serialization.NoEncryption()))
