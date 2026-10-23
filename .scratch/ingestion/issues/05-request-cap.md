# 05: Request cap

**What to build:** a run never sends more than a configured number of requests to the Bundesagentur (default 300). Jobs skipped because of the cap are counted in the summary and picked up by the next run. Spec: `.scratch/ingestion/spec.md`.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] The request cap is read from the settings file, default 300
- [ ] Once the cap is reached, no further requests are sent and remaining jobs are counted as skipped by cap in the summary and the run record
- [ ] A run that hit the cap does not count as successful for the window, so the next run searches the same period again
- [ ] Tests cover stopping at the cap, the skipped-by-cap count, and the next run's window
