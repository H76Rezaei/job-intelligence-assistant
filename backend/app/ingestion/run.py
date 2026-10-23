import logging
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ingestion.settings import SearchSettings
from app.ingestion.source import Source
from app.ingestion.storage import find_existing_job, store_job
from app.models.ingestion_run import IngestionRun
from app.repositories.ingestion_run_repository import IngestionRunRepository

log = logging.getLogger(__name__)

# Look-back for a source that has never run successfully
FIRST_RUN_DAYS = 7


@dataclass
class SourceCounts:
    fetched: int = 0
    new: int = 0
    known: int = 0
    skipped_non_germany: int = 0
    detail_errors: int = 0
    failed: str | None = None


def run_ingestion(
    session: Session, settings: SearchSettings, sources: list[Source]
) -> IngestionRun:
    runs = IngestionRunRepository(session)
    # Windows are read before this run is stored, so it cannot count as the previous run
    windows = {s.name: _window_days(runs, s.name) for s in sources}
    run = runs.add(IngestionRun(counts={}))

    run.counts = {
        source.name: asdict(_ingest_source(session, settings, source, windows[source.name]))
        for source in sources
    }
    run.finished_at = func.now()
    session.commit()
    session.refresh(run)
    return run


def _window_days(runs: IngestionRunRepository, source: str) -> int:
    """Days since the source last ran successfully, plus one day of overlap."""
    last_start = runs.last_successful_start(source)
    if last_start is None:
        return FIRST_RUN_DAYS
    elapsed = datetime.now(timezone.utc) - last_start
    return max(1, math.ceil(elapsed / timedelta(days=1))) + 1


def _ingest_source(
    session: Session, settings: SearchSettings, source: Source, window_days: int
) -> SourceCounts:
    counts = SourceCounts()
    # A savepoint per source: if the source itself fails, none of its writes are kept
    savepoint = session.begin_nested()
    try:
        for fetched in source.search(settings, window_days):
            counts.fetched += 1
            # Adapters set "DE" for jobs in Germany, including remote jobs without a location
            if fetched.country != "DE":
                counts.skipped_non_germany += 1
            elif find_existing_job(session, source.name, fetched) is not None:
                store_job(session, source.name, fetched)
                counts.known += 1
            else:
                try:
                    detailed = source.fetch_details(fetched)
                except Exception:
                    log.exception("Details for %s %s failed", source.name, fetched.source_id)
                    counts.detail_errors += 1
                    continue
                store_job(session, source.name, detailed)
                counts.new += 1
        savepoint.commit()
    except Exception as error:
        savepoint.rollback()
        log.exception("Source %s failed", source.name)
        return SourceCounts(failed=str(error))
    return counts
