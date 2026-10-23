import logging
import math
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ingestion.settings import SearchSettings
from app.ingestion.source import RequestCapReached, Source
from app.ingestion.storage import find_existing_job, store_job
from app.models.ingestion_run import IngestionRun
from app.models.job_posting import JobPosting
from app.repositories.ingestion_run_repository import IngestionRunRepository

log = logging.getLogger(__name__)

# Look-back for a source that has never run successfully
FIRST_RUN_DAYS = 7
# Upper limit, so a source that keeps hitting the cap does not search ever more pages
MAX_WINDOW_DAYS = 14


@dataclass
class SourceCounts:
    fetched: int = 0
    new: int = 0
    # Known jobs not seen for longer than reopen_after_days, fetched again
    reopened: int = 0
    known: int = 0
    skipped_non_germany: int = 0
    detail_errors: int = 0
    skipped_by_cap: int = 0
    capped: bool = False
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
                _window_days(last_starts[source.name]),
                run.id,
            )
        )
        for source in sources
    }
    run.finished_at = func.now()
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


def _window_days(last_start: datetime | None) -> int:
    """Days since the source last ran successfully, plus one day of overlap."""
    if last_start is None:
        return FIRST_RUN_DAYS
    elapsed = datetime.now(timezone.utc) - last_start
    return min(max(1, math.ceil(elapsed / timedelta(days=1))) + 1, MAX_WINDOW_DAYS)


def _ingest_source(
    session: Session,
    settings: SearchSettings,
    source: Source,
    window_days: int,
    run_id: int,
) -> SourceCounts:
    counts = SourceCounts()
    # A savepoint per source: if the source itself fails, none of its writes are kept
    savepoint = session.begin_nested()
    try:
        found = []
        try:
            for fetched in source.search(settings, window_days):
                found.append(fetched)
        except RequestCapReached:
            counts.capped = True
            log.warning(
                "Source %s: the search alone used the whole cap of %s requests, so no "
                "details were fetched. Raise the cap or use fewer keywords.",
                source.name, settings.max_requests_per_run,
            )

        for fetched in found:
            counts.fetched += 1
            # Adapters set "DE" for jobs in Germany, including remote jobs without a location
            if fetched.country != "DE":
                counts.skipped_non_germany += 1
                continue
            existing = find_existing_job(session, source.name, fetched)
            reopened = existing is not None and _unseen_for(existing, settings.reopen_after_days)
            if existing is not None and not reopened:
                store_job(session, source.name, fetched)
                counts.known += 1
                continue
            # New and reopened jobs need their full text; skipped ones stay as they are
            if counts.capped:
                counts.skipped_by_cap += 1
                continue
            try:
                detailed = source.fetch_details(fetched)
            except RequestCapReached:
                counts.capped = True
                counts.skipped_by_cap += 1
                continue
            except Exception:
                log.exception("Details for %s %s failed", source.name, fetched.source_id)
                counts.detail_errors += 1
                continue
            store_job(session, source.name, detailed, mark_new_in_run=run_id)
            if reopened:
                counts.reopened += 1
            else:
                counts.new += 1
        savepoint.commit()
    except Exception as error:
        savepoint.rollback()
        log.exception("Source %s failed", source.name)
        return SourceCounts(failed=str(error))
    if counts.capped:
        log.warning(
            "Source %s reached the cap of %s requests; %s new or reopened jobs found so far "
            "wait for the next run",
            source.name, settings.max_requests_per_run, counts.skipped_by_cap,
        )
    return counts
