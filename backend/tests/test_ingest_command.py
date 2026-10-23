import pytest

import app.ingest as ingest


class _Run:
    id = 1
    counts = {}


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    def write(text):
        path = tmp_path / "search.toml"
        path.write_text(text, encoding="utf-8")
        monkeypatch.setenv("SEARCH_SETTINGS_PATH", str(path))

    return write


@pytest.fixture
def started(monkeypatch):
    """Replace the real sources and the run, and record what would have run."""
    calls = []

    class Fake:
        name = "fake"

    def fake_run(session, settings, sources):
        calls.append(settings)
        return _Run()

    monkeypatch.setattr(ingest, "SOURCES", {"fake": Fake})
    monkeypatch.setattr(ingest, "run_ingestion", fake_run)
    return calls


def test_remote_only_settings_are_accepted(settings_file, started):
    settings_file('keywords = ["Python"]\nremote_germany = true\n')

    assert ingest.main([]) == 0
    assert len(started) == 1


def test_settings_without_keywords_are_refused(settings_file, started, capsys):
    settings_file("keywords = []\nremote_germany = true\n")

    assert ingest.main([]) == 1
    assert started == []
    assert "keyword" in capsys.readouterr().out


def test_settings_without_centers_or_remote_search_are_refused(settings_file, started):
    settings_file('keywords = ["Python"]\nremote_germany = false\n')

    assert ingest.main([]) == 1
    assert started == []
