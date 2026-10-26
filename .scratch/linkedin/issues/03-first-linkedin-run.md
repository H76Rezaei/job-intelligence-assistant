# 03: First LinkedIn run

**What to build:** `python -m app.ingest` (and `--source linkedin`) collects LinkedIn jobs end to end. It searches my job titles in `OR` groups around each center plus Germany-wide remote, newest first. It fetches the full text only for jobs I do not have yet and stores them through the existing pipeline. It goes slowly and stops safely when the cap or LinkedIn's rate limit is reached. For now LinkedIn uses the same whole-source window as the Bundesagentur (since its last complete run); per-search windows follow in 04. Spec: `.scratch/linkedin/spec.md`.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] A `linkedin` source is registered in the ingest command and selectable with `--source linkedin`
- [ ] Titles from the settings are combined into `OR` groups of about 8 quoted titles; one search per group and center (with its radius) and one Germany-wide remote search per group (`location=Germany`, `f_WT=2`) when the remote switch is on
- [ ] Searches send `f_TPR=r<seconds since the window start>`, `sortBy=DD`, and page with `start` in steps of 10 until a page has fewer than 10 cards
- [ ] Cards map to fetched jobs: LinkedIn job ID, title, company, location, URL without tracking parameters, country "DE" when the location ends in "Germany"; a job found by several searches is returned once
- [ ] Details map the full text (as text) and the employment type; seniority level, industries, the description HTML, the card fields and the key of the search that found the job are kept as raw data
- [ ] A random pause of 20–30 seconds before every request after the first; every request counts towards the cap, retries included
- [ ] Cap of 120 requests per run, used for the first run too
- [ ] On 429: wait 90 seconds and retry once; a second 429 stops LinkedIn for this run like the cap, with a `rate_limited` flag in the counts and "rate-limited" in the summary
- [ ] A redirect to a login wall or another unexpected response fails the request; a failed search ends the source for this run and is logged, and the Bundesagentur is unaffected
- [ ] An optional `[linkedin]` table in the search settings file sets the cap and the pause range; defaults (120, 20–30 seconds) live in code, and the example file shows the table
- [ ] The job page shows "LinkedIn" as a source label
- [ ] Seam 2 tests with saved HTML fragments (real structure, made-up jobs) and the pause and retry wait injected as zero cover: grouping, the query matrix and parameters, paging, card and detail mapping, Germany detection, returning a job once, the cap, 429 retry then stop, and the login wall
- [ ] Seam 3 tests cover the `[linkedin]` table, its defaults and the summary line

**Real-run checks (Claude does these and records the results below, without naming my titles or places):**
- [ ] A real `--source linkedin` run with my settings; summary recorded
- [ ] `OR` check: 2–3 of my titles searched alone and as one group, all pages, job IDs compared; if the group misses jobs, make the groups smaller
- [ ] Remote check: stored jobs found by the remote search checked for remote wording (remote, Homeoffice, mobiles Arbeiten, 100 % mobil); if most are not remote, switch the remote search off for LinkedIn
- [ ] Me: I open a few LinkedIn jobs on the dashboard and judge whether they fit
