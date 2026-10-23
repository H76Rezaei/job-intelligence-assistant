from datetime import datetime

from sqlalchemy import select
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
        """When the latest finished run in which this source did not fail started."""
        stmt = (
            select(IngestionRun.started_at)
            .where(
                IngestionRun.finished_at.is_not(None),
                IngestionRun.counts.has_key(source),
                IngestionRun.counts[source]["failed"].astext.is_(None),
            )
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()
