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


def test_linkedin_settings_default_to_a_low_cap_and_long_pauses(settings_file, started):
    settings_file('keywords = ["Python"]\nremote_germany = true\n')

    ingest.main([])

    assert started[0].linkedin.max_requests_per_run == 120
    assert started[0].linkedin.pause_seconds == (20, 30)


def test_linkedin_table_sets_cap_and_pauses(settings_file, started):
    settings_file(
        'keywords = ["Python"]\nremote_germany = true\n\n'
        "[linkedin]\nmax_requests_per_run = 50\npause_seconds = [30, 45]\n"
    )

    ingest.main([])

    assert started[0].linkedin.max_requests_per_run == 50
    assert started[0].linkedin.pause_seconds == (30, 45)


def test_exclude_title_words_are_read_from_the_settings(settings_file, started):
    settings_file('keywords = ["Python"]\nremote_germany = true\nexclude_title_words = ["Senior"]\n')

    ingest.main([])

    assert started[0].exclude_title_words == ["Senior"]


def test_linkedin_is_a_source():
    assert ingest.SOURCES["linkedin"]().name == "linkedin"


def test_summary_shows_a_rate_limited_source(settings_file, monkeypatch, capsys):
    settings_file('keywords = ["Python"]\nremote_germany = true\n')
    counts = {
        "fetched": 30, "new": 5, "reopened": 0, "known": 3, "skipped_non_germany": 0, "skipped_senior": 2,
        "detail_errors": 0, "skipped_by_cap": 20, "capped": True, "rate_limited": True, "failed": None,
    }

    class Run:
        id = 7

    Run.counts = {"linkedin": counts}
    monkeypatch.setattr(ingest, "SOURCES", {"linkedin": object})
    monkeypatch.setattr(ingest, "run_ingestion", lambda session, settings, sources: Run())

    ingest.main([])

    out = capsys.readouterr().out
    assert "linkedin: rate-limited" in out
    assert "20 new or reopened jobs" in out
