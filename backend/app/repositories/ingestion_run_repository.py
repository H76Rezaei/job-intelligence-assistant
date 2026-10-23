from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ingestion_run import IngestionRun


class IngestionRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, run: IngestionRun) -> IngestionRun:
        self.session.add(run)
        self.session.flush()
        return run

    def latest_finished_id(self) -> int | None:
        stmt = (
            select(IngestionRun.id)
            .where(IngestionRun.finished_at.is_not(None))
            .order_by(IngestionRun.id.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def last_successful_start(self, source: str) -> datetime | None:
        """When the latest complete run of this source started.

        Complete: the source did not fail, did not hit the request cap and had
        no failed detail calls, so nothing it found is still waiting. A run
        that is not complete keeps the next run's window where it was.
        """
        counts = IngestionRun.counts[source]
        stmt = (
            select(IngestionRun.started_at)
            .where(
                IngestionRun.finished_at.is_not(None),
                IngestionRun.counts.has_key(source),
                counts["failed"].astext.is_(None),
                func.coalesce(counts["capped"].astext, "false") == "false",
                func.coalesce(counts["detail_errors"].astext, "0") == "0",
            )
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()
