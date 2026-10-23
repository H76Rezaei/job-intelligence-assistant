# 02: First Bundesagentur run from one command

**What to build:** I start one command and real Bundesagentur jobs for one keyword around one search center appear in the dashboard, each with its full posting text. Only jobs in Germany are stored, only jobs not yet in the database get the detail call, and a rerun creates no duplicates. The command prints a summary per source and the run is recorded. Spec: `.scratch/ingestion/spec.md`.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Search settings are read from a TOML file ignored by git, path overridable by an environment variable; a committed example file shows keywords, centers (name and radius), the remote switch, the reopen window and the request cap, with made-up values and a note that multi-word keywords match strictly
- [ ] A small adapter interface: a source has a name, a search operation yielding fetched jobs (source ID, title, company name, location, country, URL, description, employment type, work mode, published at, raw data), and a details operation for one source ID; adapters never touch the database
- [ ] The Bundesagentur adapter searches `GET /pc/v6/jobs` (header `X-API-Key: jobboerse-jobsuche`; results in `ergebnisliste`, ID `referenznummer`) for the first keyword around the first center, and fetches details from `GET /pc/v4/jobdetails/{base64(referenznummer)}` (`stellenangebotsBeschreibung`)
- [ ] Location is the first German entry in `stellenlokationen`; work mode is remote when `homeofficeprozent` is 100, hybrid when `homeofficemoeglich` is otherwise true, else onsite
- [ ] Germany filter: keep a job if any location is in Germany, or it has no location and came from the remote search
- [ ] Details are fetched only for jobs not yet in the database; known jobs only get `last_seen_at` updated and a missing source row added
- [ ] An `ingestion_runs` table records start, finish and counts per source (fetched, new, known, skipped non-Germany, failed with message)
- [ ] The ingest command runs from the backend directory as a Python module with an optional source flag, prints the summary per source, and a failing source is logged and skipped without stopping the others
- [ ] Trimmed sample responses from the 23 Oct 2026 API check are saved as test fixtures
- [ ] Seam 1 tests: the run function with a fake adapter covers new vs. known jobs, duplicates across a rerun, the Germany filter, run counts, and a failing source not stopping another
- [ ] Seam 2 tests: an httpx mock transport serving the fixtures covers the requests sent and the mapping to fetched jobs; no test calls the live API
- [ ] Manually verified: one real run stores jobs visible in the dashboard, and a second run stores no duplicates
