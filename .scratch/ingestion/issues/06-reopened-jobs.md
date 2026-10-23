# 06: Reopened jobs after 60 days

**What to build:** a role I already have but have not seen for longer than the reopen window (default 60 days) is treated as reopened: its full text is fetched again, a new snapshot is kept if the text changed, and it shows as new in that run. My old application stays linked to the old snapshot. Spec: `.scratch/ingestion/spec.md`.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] The reopen window is read from the settings file, default 60 days
- [ ] A known job last seen longer ago than the window gets the detail call, a new snapshot when the content hash differs, and is marked new in this run (works with the marker from ticket 03 when present)
- [ ] The run summary and record count reopened jobs separately
- [ ] Applications keep pointing at their original snapshot
- [ ] Seam 1 tests cover a job inside the window (no detail call) and one outside it (detail call, new snapshot)
