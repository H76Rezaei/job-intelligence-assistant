# API

Interactive docs: `/docs` (Swagger) while the backend runs.

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Liveness check |
| GET | /jobs?new_in_last_run= | List jobs with company and an `is_new` flag; optionally only those new in the last ingestion run |
| GET | /jobs/{id} | Job detail with the latest snapshot text and the sources it was found on |
| POST | /jobs | Paste import: 201 for a new job, 200 when it matches a job already stored |
| GET | /profile | Read the candidate profile |
| PUT | /profile | Create or replace the candidate profile |
| GET | /applications?status= | List decisions, optional status filter |
| GET | /applications/{id} | One decision with its job |
| POST | /applications | Record a decision, pins the latest snapshot |
| PATCH | /applications/{id} | Change status or notes |

Statuses: interested, not_interested, applied, interview, rejected, offer.

Decisions: jobs come from ingestion (`python -m app.ingest`) or the paste import;
they cannot be edited or deleted through the API. The same job is the same
cleaned-up title and company, whatever the source or city. One application
record per job; its snapshot is set at creation and never changes.
