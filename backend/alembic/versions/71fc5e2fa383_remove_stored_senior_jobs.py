"""remove stored senior jobs

Ingestion now skips jobs whose title says they are senior. This removes the
ones stored before that, with their snapshots and source links. Jobs with an
application and jobs I pasted myself stay. Deleted rows cannot be brought
back by a downgrade.

Revision ID: 71fc5e2fa383
Revises: 7d15e81d4399
Create Date: 2026-10-26 20:34:23.873161

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71fc5e2fa383'
down_revision: Union[str, Sequence[str], None] = '7d15e81d4399'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The rule of 26 Oct 2026 (app.matching.is_senior_title), copied so later
# changes to the rule do not change what this migration deletes
SENIOR_TITLE_WORDS = ["senior", "sr.", "lead", "principal", "staff", "head of", "leiter", "teamleiter"]
OPEN_TO_NON_SENIORS = ["junior", "mid", "entry", "einsteiger", "berufseinsteiger"]


def _has_word(title: str, word: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", title) is not None


def _is_senior_title(title: str) -> bool:
    title = title.lower()
    if any(_has_word(title, word) for word in OPEN_TO_NON_SENIORS):
        return False
    for word in SENIOR_TITLE_WORDS:
        title = re.sub(rf"\(\s*{re.escape(word)}\s*\)", " ", title)
    return any(_has_word(title, word) for word in SENIOR_TITLE_WORDS)


def delete_senior_jobs(connection: sa.Connection) -> int:
    rows = connection.execute(
        sa.text(
            "SELECT id, title FROM job_postings "
            "WHERE id NOT IN (SELECT job_posting_id FROM applications) "
            "AND id NOT IN (SELECT job_posting_id FROM job_posting_sources WHERE source = 'paste')"
        )
    )
    ids = [id_ for id_, title in rows if _is_senior_title(title)]
    if ids:
        params = {"ids": ids}
        expanding = sa.bindparam("ids", expanding=True)
        for table in ("job_posting_snapshots", "job_posting_sources", "job_postings"):
            column = "id" if table == "job_postings" else "job_posting_id"
            connection.execute(
                sa.text(f"DELETE FROM {table} WHERE {column} IN :ids").bindparams(expanding),
                params,
            )
    return len(ids)


def upgrade() -> None:
    """Upgrade schema."""
    delete_senior_jobs(op.get_bind())


def downgrade() -> None:
    """Downgrade schema."""
    pass
