# API

Interactive docs: `/docs` (Swagger) while the backend runs.

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Liveness check |
| GET | /jobs | List jobs with company |
| GET | /jobs/{id} | Job detail with the latest snapshot text |
| GET | /profile | Read the candidate profile |
| PUT | /profile | Create or replace the candidate profile |
| GET | /applications?status= | List decisions, optional status filter |
| GET | /applications/{id} | One decision with its job |
| POST | /applications | Record a decision, pins the latest snapshot |
| PATCH | /applications/{id} | Change status or notes |

Statuses: interested, not_interested, applied, interview, rejected, offer.

Decisions: companies and jobs are read-only through the API (ingestion writes
them directly). One application record per job; its snapshot is set at creation
and never changes.