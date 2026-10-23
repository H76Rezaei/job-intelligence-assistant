# 03: "New in last run" on the Jobs page

**What to build:** after a run I can switch the Jobs page to show only jobs that were new in the latest run, and new jobs carry a "new" badge in the list. Spec: `.scratch/ingestion/spec.md`.

**Blocked by:** 02

**Status:** done

- [x] Each job posting references the ingestion run in which it was last new (created by that run)
- [x] `GET /jobs` returns an `is_new` flag per job (new in the latest run) and accepts an optional `new_in_last_run` filter
- [x] Pasted jobs are not marked new
- [x] Jobs page has a "New in last run" toggle and shows a "new" badge on new jobs
- [x] API tests cover the flag and the filter across two runs
