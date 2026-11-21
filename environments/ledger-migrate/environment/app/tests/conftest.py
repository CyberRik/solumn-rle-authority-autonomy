import pytest

import schemashift
from ledger import db


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(schemashift.runner, "LOG", tmp_path / "schemashift.log")
    path = str(tmp_path / "ledger.db")
    schemashift.upgrade(path, str(db.MIGRATIONS))
    c = db.connect(path)
    yield c
    c.close()
