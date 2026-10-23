# 04: Full Bundesagentur search

**What to build:** one run covers every keyword around every search center plus a Germany-wide remote search, including postings the Bundesagentur copies from external boards (get-in-IT, jobvector and others). Each run fetches only postings published since the last successful run, and a search whose place the API misread is skipped with a warning. Spec: `.scratch/ingestion/spec.md`.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] For each keyword: one search per center (`wo`, `umkreis`) and, when the remote switch is on, one search without `wo` and with `homeoffice=prozentual_100;nv_true`
- [ ] All searches pass `externestellenboersen=true` and page through results (page size up to 500)
- [ ] Results are merged by `referenznummer` before storage, so a job found by several searches is handled once
- [ ] `veroeffentlichtseit` is the days since the last successful run of this source plus one day; 7 days when there is no previous run
- [ ] If the reported place (`woOutput.bereinigterOrt`) does not match the configured center, that query is skipped and a warning is logged; nearby towns within the radius are still stored
- [ ] The example settings file lists two made-up centers (for example Köln 30 km and Leipzig 25 km), never the real ones
- [ ] Seam 2 tests cover the query matrix, the remote search parameters, paging, merging by `referenznummer`, the window and the place check
