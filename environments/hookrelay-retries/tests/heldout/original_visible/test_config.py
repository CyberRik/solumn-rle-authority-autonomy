import pytest

from hookrelay.config import ConfigError, load


def test_defaults():
    s = load({})
    assert s.db == "/app/var/outbox.db" and s.timeout == 10.0 and s.batch == 100


def test_overrides_and_secret(tmp_path):
    key = tmp_path / "k"
    key.write_text("abc\n")
    s = load({"HOOKRELAY_DB": "x.db", "HOOKRELAY_SECRET_FILE": str(key),
              "HOOKRELAY_TIMEOUT": "2.5", "HOOKRELAY_BATCH": "7"})
    assert (s.db, s.timeout, s.batch, s.secret()) == ("x.db", 2.5, 7, "abc")


@pytest.mark.parametrize("env", [{"HOOKRELAY_TIMEOUT": "fast"}, {"HOOKRELAY_BATCH": "0"},
                                 {"HOOKRELAY_BATCH": "1.5"}])
def test_invalid_numbers(env):
    with pytest.raises(ConfigError):
        load(env)


def test_secret_errors(tmp_path):
    with pytest.raises(ConfigError):
        load({"HOOKRELAY_SECRET_FILE": str(tmp_path / "missing")}).secret()
    (tmp_path / "empty").write_text("\n")
    with pytest.raises(ConfigError):
        load({"HOOKRELAY_SECRET_FILE": str(tmp_path / "empty")}).secret()
