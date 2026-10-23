# Spec: Ingestion (Bundesagentur + paste import)

Status: done

Roadmap: Step 2 in `docs/roadmap.md`. Decisions agreed in the grilling session of 23 Oct 2026 (see the roadmap's decision log).

## Problem Statement

The dashboard can show jobs, but there is no way to get jobs into it. Today I search job boards by hand, copy what looks good, and lose track of which postings I have already seen. I want to start one command, then open the dashboard and see the new jobs in the areas I search or remote in Germany, without duplicates and with the full posting text preserved. Jobs I find myself on other sites (for example Indeed through a Claude chat) need to go into the same list.

## Solution

A command I start myself fetches recent postings from the Bundesagentur für Arbeit, including postings it copies from external boards such as get-in-IT. It stores only jobs in Germany and recognises a job I already have, even if it comes from another source or another city. For new jobs only, it fetches the full text and stores it as a snapshot together with the raw source data. It prints a summary and records the run. On the Jobs page I can filter to "new in last run", and new jobs carry a badge. A paste form lets me add any job by hand. It goes through the same duplicate rule and opens the job's page after saving.

## User Stories

1. As a job seeker, I want to start ingestion with one command, so that I decide when new jobs are fetched.
2. As a job seeker, I want to run ingestion for a single source, so that I can retry one source without rerunning the others.
3. As a job seeker, I want my search keywords in a local settings file, so that I can change the search without touching code.
4. As a job seeker, I want my search settings kept out of the public repo, so that my personal search is not published.
5. As a job seeker, I want a committed example settings file, so that I (and readers of the repo) can see the expected format.
6. As a job seeker, I want to search around several centers, each with its own radius, so that I cover several regions without one huge radius.
7. As a job seeker, I want a Germany-wide remote search, so that I see remote jobs regardless of the employer's city.
8. As a job seeker, I want each keyword searched around each center and in the remote search, so that no combination is missed.
9. As a job seeker, I want postings the Bundesagentur copies from external boards included, so that jobs from get-in-IT, jobvector and similar boards also reach me.
10. As a job seeker, I want only jobs located in Germany stored, so that foreign postings never clutter my list.
11. As a job seeker, I want remote jobs without a location treated as German, so that remote jobs from the remote search are not dropped.
12. As a job seeker, I want the same job recognised by its title and company, after ignoring gender tags like "(m/w/d)" and legal forms like "GmbH", so that I see each role only once.
13. As a job seeker, I want the same role posted in several cities treated as one job, so that one company portal does not flood my list.
14. As a job seeker, I want the same role found on different sources treated as one job, so that duplicates across sources disappear.
15. As a job seeker, I want the original title and full company name stored and shown, so that I can use the exact company name in my cover letter later.
16. As a job seeker, I want companies matched by their cleaned-up name, so that "SAP SE" and "SAP" end up as one company.
17. As a job seeker, I want to see which sources a job was found on, with a link for each, so that I can open the original posting.
18. As a job seeker, I want a job recognised by its source ID first, so that a posting whose title was edited is not stored twice.
19. As a job seeker, I want the full posting text fetched only for jobs I do not have yet, so that runs are fast and send few requests.
20. As a job seeker, I want the exact posting text stored as a snapshot, so that the text I applied to is preserved.
21. As a job seeker, I want the raw source data stored with each snapshot, so that nothing the source sent is lost if I need it later.
22. As a job seeker, I want a job not seen for 60 days treated as reopened, so that a role a company reposts months later shows up again.
23. As a job seeker, I want the 60-day limit to be a setting, so that I can tune it.
24. As a job seeker, I want a reopened job to get a fresh snapshot while my old application stays linked to the old one, so that my history stays accurate.
25. As a job seeker, I want the work mode (remote, hybrid, onsite) derived from the source's home-office data, so that I can filter to remote jobs.
26. As a job seeker, I want location, employment type and work mode saved whenever a source provides them, so that later filters work wherever the data exists.
27. As a job seeker, I want reruns to never create duplicates, so that I can run ingestion as often as I like.
28. As a job seeker, I want each run to fetch only postings published since the previous run, plus one day of overlap, so that runs are quick and nothing slips between runs.
29. As a job seeker, I want the first run to look back 7 days, so that I start with a useful list.
30. As a job seeker, I want a hard cap on requests per run, so that the tool stays polite and low-volume.
31. As a job seeker, I want jobs skipped because of the cap to be picked up by the next run, so that the cap never loses jobs.
32. As a job seeker, I want a search skipped with a warning when the Bundesagentur interprets my place as a different place, so that I never store jobs from the wrong town.
33. As a job seeker, I want a failing source logged and skipped without stopping other sources, so that one broken source does not cost me a run.
34. As a job seeker, I want a printed summary per source (fetched, new, reopened, already known, skipped as non-Germany, skipped by cap, failed), so that I know what a run did.
35. As a job seeker, I want every run recorded with its start, end and counts, so that I can see what happened in past runs.
36. As a job seeker, I want to filter the Jobs page to jobs that are new in the last run, so that I review only what arrived since last time.
37. As a job seeker, I want new jobs marked with a badge in the Jobs list, so that I spot them at a glance.
38. As a job seeker, I want a paste form reached from the Jobs page, so that I can add a job I found myself.
39. As a job seeker, I want the paste form to require title, company, URL and full text, so that every pasted job is usable for scoring later.
40. As a job seeker, I want location, employment type and work mode optional in the paste form, so that I can still save a job when that information is missing.
41. As a job seeker, I want a pasted job that matches an existing job attached to it instead of creating a duplicate, so that my list stays clean.
42. As a job seeker, I want a pasted job whose text differs from the stored one to create a new snapshot, so that the newer text is kept without losing the old one.
43. As a job seeker, I want to land on the job's detail page after pasting, so that I can check what was saved.
44. As a job seeker, I want clear error messages when the paste form is incomplete, so that I can fix it quickly.
45. As a developer, I want sources behind one small adapter interface, so that the private collectors in Step 3 plug in without changing storage code.
46. As a developer, I want adapters to only fetch and map data, never write to the database, so that duplicate and storage rules live in one place.
47. As a developer, I want tests to run against saved sample responses, so that tests never depend on the live Bundesagentur API.

## Implementation Decisions

**Identity and matching**
- A job's identity is the pair (company, cleaned-up title). City and source play no part.
- Title cleanup: lowercase, collapse whitespace, remove gender tags such as "(m/w/d)", "(w/m/d)", "(m/f/d)", "(all genders)" and similar variants.
- Company cleanup: lowercase, collapse whitespace, remove legal forms such as GmbH, AG, SE, KG, "GmbH & Co. KG", e.V., UG and similar.
- The cleanup is one pure module used by ingestion and paste import alike.
- Lookup order for an incoming job: first by (source, source ID); if not found, by (cleaned company, cleaned title).

**Schema changes (one Alembic migration per table change is fine)**
- `Company` gains a cleaned-up name column with a unique constraint. Lookup is by cleaned-up name. The stored display name is the first full name seen and is never overwritten.
- `JobPosting` gains a cleaned-up title column, with a unique constraint on (company, cleaned title). Its existing `url`, `location`, `first_seen_at` and `last_seen_at` stay: `url` and `location` hold the first values seen, and `last_seen_at` is updated whenever any source sees the job.
- `JobPosting` gains a reference to the ingestion run in which it was last new (created or reopened). This drives the "new in last run" filter and badge.
- New table `job_posting_sources`: job posting, source name (`bundesagentur`, `paste`, later `linkedin`, `stepstone`, `xing`, `get_in_it`), source ID, URL, first seen at. Unique on (source name, source ID).
- `JobPostingSnapshot` gains a JSONB raw data column holding the source's raw data for that version (for paste: the submitted form). Snapshots are never deleted.
- New table `ingestion_runs`: started at, finished at, and counts per source as JSON (fetched, new, reopened, known, skipped non-Germany, skipped by cap, failed with error message).
- Existing rows get cleaned-up keys computed in the migration. They get no source rows.

**Adapter interface**
- A source adapter has a name and a fetch operation that takes the search settings and the time window and yields fetched jobs. It also has a separate operation to fetch full details for a given source ID. This split lets storage decide which jobs need details.
- A fetched job is a plain data object: source ID, title, company name, location, country, URL, description (empty until details are fetched), employment type, work mode, published at, raw data.
- Adapters never touch the database.

**Storage (one shared function, used by ingestion and paste)**
- Germany filter: keep a job if any of its locations is in Germany, or if it has no location and came from the remote search. Not applied to paste.
- New job: fetch details, create company if needed, create job posting, source row and first snapshot, and mark it new in this run.
- Known job, last seen within the reopen window (default 60 days, a setting): update `last_seen_at` and add a source row if this source is new for the job. No detail call, no new snapshot. Edits to known postings are ignored.
- Known job, last seen longer ago than the reopen window: treat as reopened, fetch details, add a snapshot if the text hash differs, and mark it new in this run.
- Pasted job matching a known job: add a source row if needed, and add a snapshot if the text hash differs. The existing content hash (title, location, description) is reused.

**Bundesagentur adapter**
- Search: `GET /pc/v6/jobs` on the jobsuche service, with the `X-API-Key: jobboerse-jobsuche` header. Results are in `ergebnisliste`, the total is in `maxErgebnisse`, the ID is `referenznummer`. Page size up to 500.
- Details: `GET /pc/v4/jobdetails/{base64(referenznummer)}`; the full text is in `stellenangebotsBeschreibung`.
- Queries: for each keyword, one search per center (`wo`, `umkreis`) and one Germany-wide remote search (no `wo`, `homeoffice=prozentual_100;nv_true`). All with `externestellenboersen=true` and `veroeffentlichtseit` set from the window. Results are merged by `referenznummer` before storage.
- Window: days since the last successful run of this source plus one day of overlap; 7 days when there is no previous run. A run that hit the request cap does not count as successful for the window, so skipped jobs are picked up next time.
- Place check: if the place the API reports it searched (`woOutput.bereinigterOrt`) does not match the configured center, skip that query and log a warning.
- Work mode: `homeofficeprozent == 100` maps to remote; `homeofficemoeglich == true` otherwise maps to hybrid; everything else to onsite.
- Location: the first German entry in `stellenlokationen`; the full list stays in the raw data.
- Request cap: a configurable maximum number of requests per run (default 300 per run, 500 until a source has completed its first run; chosen on 23 Oct 2026). When it is reached, remaining jobs are counted as skipped by cap.

**Settings**
- Search settings live in a TOML file ignored by git, with a committed example file. Its path can be overridden by an environment variable. It holds keywords, centers (name and radius), the remote switch, the reopen window and the request cap.
- The example file uses made-up centers (for example Köln 30 km and Leipzig 25 km), never the real ones.

**Command**
- Started from the backend directory as a Python module, with an optional source flag. Prints a summary per source and records an `ingestion_runs` row. Each source runs in its own error boundary.

**API contracts**
- `POST /jobs` (paste import): body with title, company name, URL, description (required) and location, employment type, work mode (optional). Returns 201 with the job detail for a new job, 200 with the existing job's detail when it matched. Validation errors return 422 as FastAPI does by default.
- `GET /jobs` gains an optional `new_in_last_run` filter, and each job in the list gains an `is_new` flag (new in the latest run).
- `GET /jobs/{id}` gains the list of sources (name, URL, first seen).

**Frontend**
- Jobs page: a "New in last run" toggle, a "new" badge, and a button that leads to the paste form.
- New paste page: the form described above; after saving, it navigates to the job's detail page.
- Job detail page: shows "found on" with a link per source.

## Testing Decisions

- Good tests check external behaviour through the seams below, not internal helpers. They assert what I would see: stored jobs, snapshots, counts and API responses.
- **Seam 1, the ingestion run:** tests call the run function with a fake adapter yielding prepared fetched jobs, then assert through repositories and `GET /jobs`. It covers the duplicate rule (title variants, legal forms, different cities, different sources), the Germany filter, details only for new jobs, the reopen window, `ingestion_runs` counts, the request cap and a failing source not stopping others.
- **Seam 2, the Bundesagentur adapter at its HTTP boundary:** an httpx mock transport serves saved sample responses. Tests assert the requests sent (per keyword and center, remote search, `externestellenboersen`, window), the mapping to fetched jobs (work mode, German location, full text), the place check and the cap.
- **Seam 3, the HTTP API:** paste import and the new `GET /jobs` filter and fields, in the style of the existing API tests (test client, transaction rolled back per test).
- The cleanup rules are exercised through Seam 1 and Seam 3, not tested in isolation.
- Sample responses from the 23 Oct 2026 API check are trimmed and saved as test fixtures. No test calls the live API.
- No frontend tests; the paste form, badge and filter are checked by hand.
- Prior art: the existing API tests for jobs and applications, and the shared session and client fixtures.

## Out of Scope

- Collectors for LinkedIn, StepStone, Xing and get-in-IT (Step 3).
- Detecting closed jobs.
- A scheduled daily run, the run report page and deployment (Step 7).
- Re-fetching or versioning edits to postings already stored.
- Requirement extraction, scoring, and any LLM call (Step 5).
- Editing or deleting jobs from the dashboard.

## Further Notes

- The Bundesagentur interface is unofficial and changed its field names in August 2026. Keep all field mapping in the adapter so a future change touches one place.
- The portal terms forbid automated data collection against the BA's intended purpose. We accepted this for personal, low-volume use you start yourself; paste import is the fallback if access breaks.
- A multi-word keyword finds postings containing all its words in any order ("AI Developer" also finds "Junior AI Developer"; checked live on 23 Oct 2026). English keywords do not find German titles ("KI-Entwickler"), so the example settings file suggests both.
- A few search results have no title; the adapter falls back to the job category (`hauptberuf`).
- Known limitation: an application is unique per job posting, so if a reopened job is one you already applied to, you cannot create a second application for it. Revisit if it becomes a problem.
