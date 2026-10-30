import logging
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.settings import SearchSettings
from app.ingestion.source import NetworkDown, RateLimited, RequestCapReached, Source
from app.ingestion.storage import find_existing_job, store_job
from app.matching import is_senior_title
from app.models.ingestion_run import IngestionRun
from app.models.job_posting import JobPosting
from app.repositories.ingestion_run_repository import IngestionRunRepository

log = logging.getLogger(__name__)

# Look-back for a source that has never run successfully
FIRST_RUN_DAYS = 7
# Upper limit, so a source that keeps hitting the cap does not search ever more pages
MAX_WINDOW_DAYS = 14
# Each window reaches this far back before the last successful run, so nothing slips between runs
OVERLAP = timedelta(days=1)
# The same for each search of a resumable source, which keeps a window per search
SEARCH_OVERLAP = timedelta(hours=2)
# A search the run did not get to counts as waiting once its window is older than this
BEHIND_AFTER = timedelta(days=2)


@dataclass
class SourceCounts:
    fetched: int = 0
    new: int = 0
    # Known jobs not seen for longer than reopen_after_days, fetched again
    reopened: int = 0
    known: int = 0
    skipped_non_germany: int = 0
    skipped_senior: int = 0
    detail_errors: int = 0
    skipped_by_cap: int = 0
    capped: bool = False
    # The site refused further requests; handled like the cap
    rate_limited: bool = False
    # The connection to the site failed; also handled like the cap
    network_error: bool = False
    # Resumable sources only: searches that did not finish, and each search's next window
    searches_waiting: int = 0
    search_since: dict[str, str] | None = None
    failed: str | None = None


def run_ingestion(
    session: Session, settings: SearchSettings, sources: list[Source]
) -> IngestionRun:
    runs = IngestionRunRepository(session)
    # Read before this run is stored, so it cannot count as the previous run
    last_starts = {s.name: runs.last_successful_start(s.name) for s in sources}
    run = runs.add(IngestionRun(counts={}))

    run.counts = {
        source.name: asdict(
            _ingest_source(
                session,
                _settings_for(settings, last_starts[source.name]),
                source,
                _window_start(last_starts[source.name]),
                run,
            )
        )
        for source in sources
    }
    # now() is the transaction's start, the same moment as started_at; clock_timestamp() is the real time
    run.finished_at = func.clock_timestamp()
    session.commit()
    session.refresh(run)
    return run


def _unseen_for(job: JobPosting, days: int) -> bool:
    return datetime.now(timezone.utc) - job.last_seen_at > timedelta(days=days)


def _settings_for(settings: SearchSettings, last_start: datetime | None) -> SearchSettings:
    """Until a source has completed a run, it is catching up and gets the larger cap."""
    if last_start is None:
        return replace(settings, max_requests_per_run=settings.max_requests_first_run)
    return settings


def _window_start(last_start: datetime | None) -> datetime:
    """The last successful run of the source minus the overlap, within the limits."""
    now = datetime.now(timezone.utc)
    if last_start is None:
        return now - timedelta(days=FIRST_RUN_DAYS)
    return max(last_start - OVERLAP, now - timedelta(days=MAX_WINDOW_DAYS))


def _ingest_source(
    session: Session,
    settings: SearchSettings,
    source: Source,
    since: datetime,
    run: IngestionRun,
) -> SourceCounts:
    """Searches and stores one source's jobs.

    A resumable source (LinkedIn) keeps a window per search instead of one for
    the source: it gets the windows from its last recorded run, new searches
    look back FIRST_RUN_DAYS, and it reports which searches it read to the end.
    """
    counts = SourceCounts()
    resumable = getattr(source, "resumable", False)
    windows = IngestionRunRepository(session).latest_search_since(source.name) if resumable else {}
    # A resumable source's searches without a window yet look back like a first run
    new_search_since = _window_start(None)
    # Searches with a job that still waits for its details
    left_unfinished: set[str] = set()
    # Searches that found a job in this run
    started: set[str] = set()
    # A savepoint per source: if the source itself fails, none of its writes are kept
    savepoint = session.begin_nested()
    try:
        # Each job is handled as soon as the search finds it, so a stop part-way
        # through the searches keeps the details fetched so far
        try:
            found = (
                source.search(settings, new_search_since, windows)
                if resumable
                else source.search(settings, since)
            )
            for fetched in found:
                started.add(fetched.search_key)
                if not _handle_job(session, settings, source, fetched, counts, run.id):
                    left_unfinished.add(fetched.search_key)
        except RequestCapReached as stop:
            _record_stop(counts, stop)
        if resumable:
            _record_search_windows(
                counts, source.searches_finished, left_unfinished, started, windows, new_search_since, run.started_at
            )
        savepoint.commit()
    except Exception as error:
        savepoint.rollback()
        log.exception("Source %s failed", source.name)
        return SourceCounts(failed=str(error))
    if counts.capped:
        log.warning(
            "Source %s stopped (%s); %s new or reopened jobs found so far "
            "wait for the next run",
            source.name, _stop_reason(counts), counts.skipped_by_cap,
        )
    return counts


def _handle_job(
    session: Session,
    settings: SearchSettings,
    source: Source,
    fetched: FetchedJob,
    counts: SourceCounts,
    run_id: int,
) -> bool:
    """Filters and stores one job; False when it still waits for its details."""
    counts.fetched += 1
    # Adapters set "DE" for jobs in Germany, including remote jobs without a location
    if fetched.country != "DE":
        counts.skipped_non_germany += 1
        return True
    if is_senior_title(fetched.title, settings.exclude_title_words):
        counts.skipped_senior += 1
        return True
    existing = find_existing_job(session, source.name, fetched)
    reopened = existing is not None and _unseen_for(existing, settings.reopen_after_days)
    if existing is not None and not reopened:
        store_job(session, source.name, fetched)
        counts.known += 1
        return True
    # New and reopened jobs need their full text; skipped ones stay as they are
    if counts.capped:
        counts.skipped_by_cap += 1
        return False
    try:
        detailed = source.fetch_details(fetched)
    except RequestCapReached as stop:
        _record_stop(counts, stop)
        counts.skipped_by_cap += 1
        return False
    except Exception:
        log.exception("Details for %s %s failed", source.name, fetched.source_id)
        counts.detail_errors += 1
        return False
    store_job(session, source.name, detailed, mark_new_in_run=run_id)
    if reopened:
        counts.reopened += 1
    else:
        counts.new += 1
    return True


def _record_search_windows(
    counts: SourceCounts,
    searches_finished: dict[str, bool],
    left_unfinished: set[str],
    started: set[str],
    windows: dict[str, datetime],
    new_search_since: datetime,
    run_start: datetime,
) -> None:
    """A search read to the end with every job handled moves on; the others keep their window.

    Waiting are those started but not finished, and those not reached that are behind;
    a search that finished recently and simply was not reached does not count.
    """
    next_since = {}
    for key, finished in searches_finished.items():
        if finished and key not in left_unfinished:
            next_since[key] = run_start - SEARCH_OVERLAP
        else:
            next_since[key] = windows.get(key, new_search_since)
            if key in started or run_start - next_since[key] > BEHIND_AFTER:
                counts.searches_waiting += 1
    counts.search_since = {key: since.isoformat() for key, since in next_since.items()}


def _record_stop(counts: SourceCounts, stop: RequestCapReached) -> None:
    """A plain cap stop can follow the real reason, so it never clears a flag already set."""
    counts.capped = True
    counts.rate_limited = counts.rate_limited or isinstance(stop, RateLimited)
    counts.network_error = counts.network_error or isinstance(stop, NetworkDown)


def _stop_reason(counts: SourceCounts) -> str:
    if counts.network_error:
        return "network error"
    return "rate-limited" if counts.rate_limited else "request cap reached"
