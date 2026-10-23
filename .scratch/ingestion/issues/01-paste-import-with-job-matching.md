# 01: Paste import with job matching across sources

**What to build:** I can add a job I found myself through a paste form reached from the Jobs page. If it is the same job as one I already have (same title and company after cleanup, whatever the city or source), it attaches to the existing job instead of creating a duplicate; if its text differs, a new snapshot is kept. After saving I land on the job's page, which shows "found on" with a link for each source. Spec: `.scratch/ingestion/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Prefactor first: the duplicated imports in the jobs API are removed
- [ ] Companies have a cleaned-up name (lowercase, whitespace collapsed, legal forms such as GmbH, AG, SE, KG, "GmbH & Co. KG", e.V., UG removed), unique, and are looked up by it; the display name is the first full name seen and is never overwritten
- [ ] Job postings have a cleaned-up title (lowercase, whitespace collapsed, gender tags such as "(m/w/d)", "(w/m/d)", "(m/f/d)", "(all genders)" removed), unique per company
- [ ] A `job_posting_sources` table links a job to (source name, source ID, URL, first seen at), unique on (source name, source ID)
- [ ] Snapshots carry the raw source data as JSONB; for paste it is the submitted form
- [ ] Migrations compute the cleaned-up keys for existing rows; existing rows get no source rows
- [ ] One shared storage function looks up by (source, source ID) first, then by (cleaned company, cleaned title); creates company, job, source row and snapshot for a new job; for a matching job adds a missing source row and a snapshot only when the content hash differs
- [ ] `POST /jobs` accepts title, company name, URL and description (required) and location, employment type and work mode (optional); the paste source ID is the cleaned-up URL (lowercase host, no tracking parameters, no trailing slash)
- [ ] `POST /jobs` returns 201 with the job detail for a new job and 200 with the existing job's detail when it matched; missing required fields return 422
- [ ] `GET /jobs/{id}` includes the list of sources (name, URL, first seen)
- [ ] Jobs page has a button to a new paste page; the form shows validation errors and navigates to the job's detail page after saving
- [ ] Job detail page shows "found on" with a link per source
- [ ] API tests (test client, transaction rolled back) cover: new paste, match across title variants and legal forms, match with a different city, same text adds no snapshot, different text adds one
