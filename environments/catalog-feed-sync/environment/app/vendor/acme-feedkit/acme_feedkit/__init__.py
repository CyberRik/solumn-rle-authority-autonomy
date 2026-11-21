"""acme-feedkit -- Acme Supply's integration kit for catalog feed consumers.

Vendored from Acme's partner SDK (v3.0.1). Do not edit; upgrade by
re-vendoring the release tarball.

    acme_feedkit.verify_drop(path)        check a drop against its .sha256 sidecar
    acme_feedkit.v3.iter_products(doc)    normalised records from a catalog/v3 doc
    python -m acme_feedkit.selfcheck      partner conformance check
"""

import hashlib
from pathlib import Path

__version__ = "3.0.1"


class DropIntegrityError(Exception):
    pass


def verify_drop(path) -> str:
    """Verify a dropped feed against `<file>.sha256`; returns the digest."""
    path = Path(path)
    sidecar = path.with_name(path.name + ".sha256")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if not sidecar.exists():
        raise DropIntegrityError(f"missing checksum sidecar for {path.name}")
    expected = sidecar.read_text().split()[0].strip().lower()
    if expected != digest:
        raise DropIntegrityError(f"{path.name}: checksum mismatch")
    return digest
