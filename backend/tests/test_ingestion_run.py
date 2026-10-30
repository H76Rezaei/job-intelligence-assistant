from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.run import run_ingestion
from app.ingestion.settings import Center, SearchSettings
from app.ingestion.source import NetworkDown, RateLimited, RequestCapReached
from app.models.ingestion_run import IngestionRun

SETTINGS = SearchSettings(
    keywords=["Python"],
    centers=[Center(name="Testhausen", radius_km=25)],
    max_requests_per_run=30,
    max_requests_first_run=50,
)


def _days_ago(days):
    return datetime.now(timezone.utc) - timedelta(days=days)


def _about(moment):
    """A matcher for a time a few seconds away, as `now` moves on during a test."""

    class About:
        def __eq__(self, other):
            return abs(other - moment) < timedelta(minutes=1)

        def __repr__(self):
            return f"about {moment}"

    return About()


def _job(source_id, title, company="Example Software GmbH", country="DE"):
    return FetchedJob(
        source_id=source_id,
        title=title,
        company_name=company,
        url=f"https://source.example/{source_id}",
        location="Testhausen",
        country=country,
        raw={"id": source_id},
    )


class FakeSource:
    def __init__(self, name, jobs):
        self.name = name
        self.jobs = jobs
        self.detail_calls = []
        self.window_starts = []
        self.caps = []

    def search(self, settings, since):
        self.window_starts.append(since)
        self.caps.append(settings.max_requests_per_run)
        yield from self.jobs

    def fetch_details(self, job):
        self.detail_calls.append(job.source_id)
        return replace(job, description=f"Full text of {job.title}")


class BrokenSource:
    name = "broken"

    def search(self, settings, since):
        raise RuntimeError("source is down")
        yield

    def fetch_details(self, job):
        raise AssertionError("never called")


def test_run_stores_new_jobs_with_full_text(client, session):
    source = FakeSource("fake", [_job("1", "Python Developer"), _job("2", "Data Engineer")])

    run = run_ingestion(session, SETTINGS, [source])

    jobs = client.get("/jobs").json()
    assert sorted(j["title"] for j in jobs) == ["Data Engineer", "Python Developer"]
    detail = client.get(f"/jobs/{jobs[0]['id']}").json()
    assert detail["description"] == f"Full text of {detail['title']}"
    assert [s["source"] for s in detail["sources"]] == ["fake"]
    assert run.counts["fake"] == {
        "fetched": 2, "new": 2, "reopened": 0, "known": 0, "skipped_non_germany": 0, "detail_errors": 0,
        "skipped_senior": 0, "skipped_by_cap": 0, "capped": False, "rate_limited": False, "network_error": False,
        "searches_waiting": 0, "search_since": None, "failed": None,
    }
    assert run.finished_at > run.started_at


def test_rerun_creates_no_duplicates_and_fetches_no_details(client, session):
    jobs = [_job("1", "Python Developer"), _job("2", "Data Engineer")]
    run_ingestion(session, SETTINGS, [FakeSource("fake", jobs)])
    second_source = FakeSource("fake", jobs)

    run = run_ingestion(session, SETTINGS, [second_source])

    assert len(client.get("/jobs").json()) == 2
    assert second_source.detail_calls == []
    assert run.counts["fake"]["known"] == 2
    assert run.counts["fake"]["new"] == 0


def test_job_known_from_another_source_gets_no_details_but_a_source_link(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("first", [_job("1", "Python Developer (m/w/d)")])])
    second = FakeSource("second", [_job("abc", "Python Developer", company="Example Software")])

    run_ingestion(session, SETTINGS, [second])

    jobs = client.get("/jobs").json()
    assert len(jobs) == 1
    assert second.detail_calls == []
    sources = client.get(f"/jobs/{jobs[0]['id']}").json()["sources"]
    assert [s["source"] for s in sources] == ["first", "second"]


def test_jobs_outside_germany_are_skipped(client, session):
    source = FakeSource(
        "fake",
        [_job("1", "Python Developer"), _job("2", "Python Developer Amsterdam", country="NL")],
    )

    run = run_ingestion(session, SETTINGS, [source])

    assert [j["title"] for j in client.get("/jobs").json()] == ["Python Developer"]
    assert source.detail_calls == ["1"]
    assert run.counts["fake"]["skipped_non_germany"] == 1


def test_failing_source_is_recorded_and_does_not_stop_others(client, session):
    working = FakeSource("fake", [_job("1", "Python Developer")])

    run = run_ingestion(session, SETTINGS, [BrokenSource(), working])

    assert run.counts["broken"]["failed"] == "source is down"
    assert run.counts["fake"]["new"] == 1
    assert len(client.get("/jobs").json()) == 1


def test_job_without_location_is_skipped_unless_the_source_marks_it_german(client, session):
    unknown = replace(_job("1", "Python Developer"), location=None, country=None)
    remote = replace(_job("2", "Remote Python Developer"), location=None, country="DE")

    run = run_ingestion(session, SETTINGS, [FakeSource("fake", [unknown, remote])])

    assert [j["title"] for j in client.get("/jobs").json()] == ["Remote Python Developer"]
    assert run.counts["fake"]["skipped_non_germany"] == 1


class FlakyDetailsSource(FakeSource):
    def fetch_details(self, job):
        if job.source_id == "2":
            raise RuntimeError("detail call failed")
        return super().fetch_details(job)


def test_failed_detail_call_skips_only_that_job(client, session):
    source = FlakyDetailsSource(
        "fake", [_job("1", "Python Developer"), _job("2", "Data Engineer"), _job("3", "ML Engineer")]
    )

    run = run_ingestion(session, SETTINGS, [source])

    assert sorted(j["title"] for j in client.get("/jobs").json()) == ["ML Engineer", "Python Developer"]
    assert run.counts["fake"]["new"] == 2
    assert run.counts["fake"]["detail_errors"] == 1
    assert run.counts["fake"]["failed"] is None


def test_first_run_looks_back_seven_days(session):
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.window_starts == [_about(_days_ago(7))]


def test_next_run_looks_back_to_the_last_successful_run_minus_a_day(session):
    previous = run_ingestion(session, SETTINGS, [FakeSource("fake", [])])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.window_starts == [previous.started_at - timedelta(days=1)]


def test_failed_run_does_not_move_the_window(session):
    class BrokenFake(BrokenSource):
        name = "fake"

    run_ingestion(session, SETTINGS, [BrokenFake()])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.window_starts == [_about(_days_ago(7))]


def test_window_is_tracked_per_source(session):
    run_ingestion(session, SETTINGS, [FakeSource("other", [])])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.window_starts == [_about(_days_ago(7))]


def test_window_starts_a_day_before_the_last_successful_run(session):
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3, hours=2)
    session.add(
        IngestionRun(
            started_at=three_days_ago,
            finished_at=three_days_ago,
            counts={"fake": {"failed": None}},
        )
    )
    session.flush()
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.window_starts == [three_days_ago - timedelta(days=1)]


class CappedSource(FakeSource):
    """Allows `allowed_details` detail calls, then reports the cap as reached."""

    def __init__(self, name, jobs, allowed_details, cap_during_search=False):
        super().__init__(name, jobs)
        self.allowed_details = allowed_details
        self.cap_during_search = cap_during_search

    def search(self, settings, since):
        yield from super().search(settings, since)
        if self.cap_during_search:
            raise RequestCapReached()

    def fetch_details(self, job):
        if len(self.detail_calls) >= self.allowed_details:
            raise RequestCapReached()
        return super().fetch_details(job)


def test_cap_during_details_keeps_what_was_stored_and_counts_the_rest(client, session):
    jobs = [_job(str(i), f"Job {i}") for i in range(5)]

    run = run_ingestion(session, SETTINGS, [CappedSource("fake", jobs, allowed_details=2)])

    assert len(client.get("/jobs").json()) == 2
    counts = run.counts["fake"]
    assert (counts["new"], counts["skipped_by_cap"], counts["capped"]) == (2, 3, True)
    assert counts["failed"] is None


def test_cap_during_search_keeps_the_results_found_so_far(client, session):
    jobs = [_job("1", "Job 1"), _job("2", "Job 2")]

    run = run_ingestion(
        session, SETTINGS, [CappedSource("fake", jobs, allowed_details=0, cap_during_search=True)]
    )

    counts = run.counts["fake"]
    assert (counts["fetched"], counts["new"], counts["skipped_by_cap"], counts["capped"]) == (2, 0, 2, True)


def test_known_jobs_still_count_when_the_cap_is_reached(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("fake", [_job("1", "Job 1")])])

    run = run_ingestion(
        session, SETTINGS, [CappedSource("fake", [_job("1", "Job 1"), _job("2", "Job 2")], allowed_details=0)]
    )

    counts = run.counts["fake"]
    assert (counts["known"], counts["skipped_by_cap"]) == (1, 1)


def test_capped_run_does_not_move_the_window(session):
    run_ingestion(session, SETTINGS, [CappedSource("fake", [_job("1", "Job 1")], allowed_details=0)])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.window_starts == [_about(_days_ago(7))]


def test_run_with_failed_detail_calls_does_not_move_the_window(session):
    run_ingestion(session, SETTINGS, [FlakyDetailsSource("fake", [_job("2", "Job 2")])])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.window_starts == [_about(_days_ago(7))]


def test_jobs_skipped_by_the_cap_are_fetched_by_the_next_run(client, session):
    jobs = [_job(str(i), f"Job {i}") for i in range(3)]
    run_ingestion(session, SETTINGS, [CappedSource("fake", jobs, allowed_details=1)])

    run = run_ingestion(session, SETTINGS, [FakeSource("fake", jobs)])

    assert run.counts["fake"]["new"] == 2
    assert len(client.get("/jobs").json()) == 3


def test_first_run_gets_the_larger_first_run_cap(session):
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.caps == [50]


def test_runs_after_a_complete_run_get_the_daily_cap(session):
    run_ingestion(session, SETTINGS, [FakeSource("fake", [])])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.caps == [30]


def test_runs_still_catching_up_keep_the_first_run_cap(session):
    run_ingestion(session, SETTINGS, [CappedSource("fake", [_job("1", "Job 1")], allowed_details=0)])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.caps == [50]


def test_window_never_grows_beyond_fourteen_days(session):
    long_ago = datetime.now(timezone.utc) - timedelta(days=30)
    session.add(IngestionRun(started_at=long_ago, finished_at=long_ago, counts={"fake": {"failed": None}}))
    session.flush()
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.window_starts == [_about(_days_ago(14))]


def test_senior_title_is_skipped_without_a_detail_call(client, session):
    source = FakeSource("fake", [_job("1", "Senior Python Developer (m/w/d)"), _job("2", "Python Developer")])

    run = run_ingestion(session, SETTINGS, [source])

    assert [j["title"] for j in client.get("/jobs").json()] == ["Python Developer"]
    assert source.detail_calls == ["2"]
    assert run.counts["fake"]["skipped_senior"] == 1


def test_senior_only_in_the_description_is_kept(client, session):
    job = replace(_job("1", "Python Developer"), description="You work with senior engineers. 5+ years of experience.")

    run = run_ingestion(session, SETTINGS, [FakeSource("fake", [job])])

    assert run.counts["fake"]["new"] == 1


def test_other_senior_titles_are_skipped(client, session):
    titles = ["Sr. Data Engineer", "Head of Engineering", "Tech Lead Python", "Teamleiter Softwareentwicklung"]
    jobs = [_job(str(i), title) for i, title in enumerate(titles)]

    run = run_ingestion(session, SETTINGS, [FakeSource("fake", jobs)])

    assert run.counts["fake"]["skipped_senior"] == 4
    assert client.get("/jobs").json() == []


def test_titles_open_to_juniors_or_mid_level_are_kept(client, session):
    titles = ["Junior/Senior Python Developer", "Data Engineer (Mid/Senior)", "Senior oder Berufseinsteiger Backend"]
    jobs = [_job(str(i), title) for i, title in enumerate(titles)]

    run = run_ingestion(session, SETTINGS, [FakeSource("fake", jobs)])

    assert run.counts["fake"]["new"] == 3


def test_words_that_only_contain_a_senior_word_are_kept(client, session):
    jobs = [_job("1", "Leadership Trainee"), _job("2", "Staffing Specialist")]

    run = run_ingestion(session, SETTINGS, [FakeSource("fake", jobs)])

    assert run.counts["fake"]["new"] == 2


def test_senior_words_come_from_the_settings(client, session):
    settings = replace(SETTINGS, exclude_title_words=["Senior"])
    jobs = [_job("1", "Senior Python Developer"), _job("2", "Lead Developer")]

    run = run_ingestion(session, settings, [FakeSource("fake", jobs)])

    assert [j["title"] for j in client.get("/jobs").json()] == ["Lead Developer"]
    assert run.counts["fake"]["skipped_senior"] == 1


def test_senior_in_brackets_is_optional_and_kept(client, session):
    titles = ["(Senior) Data Scientist (m/w/d)", "( Sr. ) Python Developer", "Software Engineer (Senior)"]
    jobs = [_job(str(i), title) for i, title in enumerate(titles)]

    run = run_ingestion(session, SETTINGS, [FakeSource("fake", jobs)])

    assert run.counts["fake"]["new"] == 3


def test_rate_limit_stops_the_source_like_the_cap_and_is_recorded(client, session):
    class RateLimitedSource(FakeSource):
        def fetch_details(self, job):
            if self.detail_calls:
                raise RateLimited()
            return super().fetch_details(job)

    jobs = [_job("1", "Python Developer"), _job("2", "Data Engineer"), _job("3", "Backend Developer")]

    run = run_ingestion(session, SETTINGS, [RateLimitedSource("fake", jobs)])

    counts = run.counts["fake"]
    assert (counts["new"], counts["skipped_by_cap"], counts["capped"], counts["rate_limited"]) == (1, 2, True, True)


def test_jobs_found_before_a_stop_in_the_search_still_get_their_details(client, session):
    class StopsDuringSearch(FakeSource):
        def search(self, settings, since):
            yield from super().search(settings, since)
            raise RateLimited()

    source = StopsDuringSearch("fake", [_job("1", "Python Developer"), _job("2", "Data Engineer")])

    run = run_ingestion(session, SETTINGS, [source])

    counts = run.counts["fake"]
    assert (counts["new"], counts["skipped_by_cap"], counts["rate_limited"]) == (2, 0, True)
    assert len(client.get("/jobs").json()) == 2


class ResumableSource:
    """Has one search per key; `unfinished` searches stop before their last page."""

    resumable = True

    def __init__(self, jobs_by_search, unfinished=(), allowed_details=None, name="fake"):
        self.name = name
        self.jobs_by_search = jobs_by_search
        self.unfinished = set(unfinished)
        self.allowed_details = allowed_details
        self.windows = []
        self.detail_calls = []
        self.searches_finished = {}

    def search(self, settings, since, windows):
        self.windows.append((since, dict(windows)))
        for key, jobs in self.jobs_by_search.items():
            self.searches_finished[key] = key not in self.unfinished
            for job in jobs:
                yield replace(job, search_key=key)

    def fetch_details(self, job):
        if self.allowed_details is not None and len(self.detail_calls) >= self.allowed_details:
            raise RequestCapReached()
        self.detail_calls.append(job.source_id)
        return replace(job, description=f"Full text of {job.title}")


def test_new_searches_look_back_seven_days_and_finished_ones_move_to_the_run_start(session):
    first = ResumableSource({"a": [], "b": []})

    run = run_ingestion(session, SETTINGS, [first])
    second = ResumableSource({"a": [], "b": []})
    run_ingestion(session, SETTINGS, [second])

    assert first.windows == [(_about(_days_ago(7)), {})]
    moved = run.started_at - timedelta(hours=2)
    assert second.windows[0][1] == {"a": moved, "b": moved}
    assert run.counts["fake"]["searches_waiting"] == 0


def test_unfinished_search_keeps_its_old_window(session):
    run_ingestion(session, SETTINGS, [ResumableSource({"a": [], "b": []}, unfinished=["b"])])
    source = ResumableSource({"a": [], "b": []})

    run_ingestion(session, SETTINGS, [source])

    windows = source.windows[0][1]
    assert windows["b"] == _about(_days_ago(7))
    assert windows["a"] > _days_ago(1)


def test_search_with_a_job_skipped_by_the_cap_stays_unfinished(client, session):
    jobs = {"a": [_job("1", "Python Developer")], "b": [_job("2", "Data Engineer")]}

    run = run_ingestion(session, SETTINGS, [ResumableSource(jobs, allowed_details=1)])

    counts = run.counts["fake"]
    assert counts["searches_waiting"] == 1
    assert datetime.fromisoformat(counts["search_since"]["b"]) == _about(_days_ago(7))
    assert datetime.fromisoformat(counts["search_since"]["a"]) > _days_ago(1)


def test_only_searches_that_are_behind_count_as_waiting(session):
    session.add(
        IngestionRun(
            started_at=_days_ago(1),
            finished_at=_days_ago(1),
            counts={
                "fake": {
                    "failed": None,
                    "search_since": {
                        "started": _days_ago(0).isoformat(),
                        "not_reached": _days_ago(1).isoformat(),
                        "behind": _days_ago(3).isoformat(),
                    },
                }
            },
        )
    )
    session.flush()
    jobs = {"started": [_job("1", "Python Developer")], "not_reached": [], "behind": [], "new": []}

    run = run_ingestion(session, SETTINGS, [ResumableSource(jobs, unfinished=list(jobs))])

    counts = run.counts["fake"]
    # "not_reached" is recent and found nothing, so it does not count, but keeps its window
    assert counts["searches_waiting"] == 3
    assert datetime.fromisoformat(counts["search_since"]["not_reached"]) == _about(_days_ago(1))


def test_failed_run_keeps_the_previous_windows(session):
    run_ingestion(session, SETTINGS, [ResumableSource({"a": []})])

    class Broken(ResumableSource):
        def search(self, settings, since, windows):
            raise RuntimeError("down")
            yield

    run_ingestion(session, SETTINGS, [Broken({"a": []})])
    source = ResumableSource({"a": []})
    run_ingestion(session, SETTINGS, [source])

    assert source.windows[0][1]["a"] > _days_ago(1)


def test_network_error_during_search_keeps_stored_jobs_and_the_search_stays_unfinished(client, session):
    class DropsDuringSearch(ResumableSource):
        def search(self, settings, since, windows):
            yield from super().search(settings, since, windows)
            raise NetworkDown()

    jobs = {"a": [_job("1", "Python Developer")], "b": [_job("2", "Data Engineer")]}

    run = run_ingestion(session, SETTINGS, [DropsDuringSearch(jobs, unfinished=["b"])])

    counts = run.counts["fake"]
    assert counts["failed"] is None
    assert (counts["new"], counts["capped"], counts["network_error"], counts["rate_limited"]) == (2, True, True, False)
    assert counts["searches_waiting"] == 1
    assert datetime.fromisoformat(counts["search_since"]["b"]) == _about(_days_ago(7))
    assert datetime.fromisoformat(counts["search_since"]["a"]) > _days_ago(1)
    assert len(client.get("/jobs").json()) == 2


def test_network_error_on_details_keeps_stored_jobs_and_leaves_the_rest_for_the_next_run(client, session):
    class DropsOnDetails(ResumableSource):
        def fetch_details(self, job):
            if job.source_id == "2":
                raise NetworkDown()
            return super().fetch_details(job)

    jobs = {"a": [_job("1", "Python Developer")], "b": [_job("2", "Data Engineer"), _job("3", "ML Engineer")]}

    run = run_ingestion(session, SETTINGS, [DropsOnDetails(jobs)])

    counts = run.counts["fake"]
    assert counts["failed"] is None
    assert (counts["new"], counts["skipped_by_cap"], counts["detail_errors"]) == (1, 2, 0)
    assert (counts["capped"], counts["network_error"], counts["rate_limited"]) == (True, True, False)
    assert counts["searches_waiting"] == 1
    assert [j["title"] for j in client.get("/jobs").json()] == ["Python Developer"]


def test_other_error_part_way_still_rolls_back_and_keeps_the_previous_windows(client, session):
    class BreaksPartWay(ResumableSource):
        def search(self, settings, since, windows):
            yield from super().search(settings, since, windows)
            raise RuntimeError("page does not parse")

    first = run_ingestion(session, SETTINGS, [ResumableSource({"a": []})])

    run = run_ingestion(session, SETTINGS, [BreaksPartWay({"a": [_job("1", "Python Developer")]})])

    assert run.counts["fake"]["failed"] == "page does not parse"
    assert client.get("/jobs").json() == []
    source = ResumableSource({"a": []})
    run_ingestion(session, SETTINGS, [source])
    assert source.windows[0][1]["a"] == first.started_at - timedelta(hours=2)


def test_windows_are_kept_per_source(session):
    run_ingestion(session, SETTINGS, [ResumableSource({"a": []}, name="other")])
    source = ResumableSource({"a": []})

    run_ingestion(session, SETTINGS, [source])

    assert source.windows[0][1] == {}
