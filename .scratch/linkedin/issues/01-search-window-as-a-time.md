# 01: Search window as a time, not a day count

**What to build:** a source's search receives the time it should search back to ("since") instead of a number of days, so LinkedIn can later search "since the last run plus 2 hours". The run still computes the Bundesagentur's window in whole days (days since the last complete run plus one day, 7 on the first run, at most 14) and the Bundesagentur converts the time back to days. Nothing changes for the user. Spec: `.scratch/linkedin/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The source interface's search takes a "since" time instead of a day count
- [ ] The Bundesagentur sends the same `veroeffentlichtseit` values as before for the first run, a normal daily run, a run after several days and the 14-day limit
- [ ] Existing Seam 1 window tests are rewritten in terms of the "since" time and still pass; existing Seam 2 tests pass unchanged or with the new argument only
- [ ] A real `python -m app.ingest --source bundesagentur` run behaves as before
