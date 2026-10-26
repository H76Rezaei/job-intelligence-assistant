import logging
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.settings import SearchSettings
from app.ingestion.source import RateLimited, RequestCapReached, Source
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
                run.id,
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
    run_id: int,
) -> SourceCounts:
    counts = SourceCounts()
    # A savepoint per source: if the source itself fails, none of its writes are kept
    savepoint = session.begin_nested()
    try:
        # Each job is handled as soon as the search finds it, so a stop part-way
        # through the searches keeps the details fetched so far
        try:
            for fetched in source.search(settings, since):
                _handle_job(session, settings, source, fetched, counts, run_id)
        except RequestCapReached as stop:
            counts.capped = True
            counts.rate_limited = counts.rate_limited or isinstance(stop, RateLimited)
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
) -> None:
    counts.fetched += 1
    # Adapters set "DE" for jobs in Germany, including remote jobs without a location
    if fetched.country != "DE":
        counts.skipped_non_germany += 1
        return
    if is_senior_title(fetched.title, settings.exclude_title_words):
        counts.skipped_senior += 1
        return
    existing = find_existing_job(session, source.name, fetched)
    reopened = existing is not None and _unseen_for(existing, settings.reopen_after_days)
    if existing is not None and not reopened:
        store_job(session, source.name, fetched)
        counts.known += 1
        return
    # New and reopened jobs need their full text; skipped ones stay as they are
    if counts.capped:
        counts.skipped_by_cap += 1
        return
    try:
        detailed = source.fetch_details(fetched)
    except RequestCapReached as stop:
        counts.capped = True
        counts.rate_limited = isinstance(stop, RateLimited)
        counts.skipped_by_cap += 1
        return
    except Exception:
        log.exception("Details for %s %s failed", source.name, fetched.source_id)
        counts.detail_errors += 1
        return
    store_job(session, source.name, detailed, mark_new_in_run=run_id)
    if reopened:
        counts.reopened += 1
    else:
        counts.new += 1


def _stop_reason(counts: SourceCounts) -> str:
    return "rate-limited" if counts.rate_limited else "request cap reached"
