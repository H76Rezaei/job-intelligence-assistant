# 05: Request cap

**What to build:** a run never sends more than a configured number of requests to the Bundesagentur (default 300, and 500 until the source has completed a run). Jobs skipped because of the cap are counted in the summary and picked up by the next run. Spec: `.scratch/ingestion/spec.md`.

**Blocked by:** 04

**Status:** done

- [x] The request cap is read from the settings file, default 300, and 500 until the source has completed a run
- [x] Once the cap is reached, no further requests are sent and remaining jobs are counted as skipped by cap in the summary and the run record
- [x] A run that hit the cap does not count as successful for the window, so the next run searches the same period again
- [x] A run in which a detail call failed does not count as successful for the window either, so those jobs are tried again next time (found in the ticket 04 review)
- [x] Retries (ticket 04) count towards the cap
- [x] Tests cover stopping at the cap, the skipped-by-cap count, and the next run's window

Notes from the build (23 Oct 2026):
- Two caps, chosen by the owner: 500 while a source is catching up (no complete run yet), 300 for daily runs.
- The run collects search results before fetching details. The window never grows beyond 14 days, and a run whose search alone used the whole cap logs a warning to raise the cap or trim keywords.
- `skipped_by_cap` counts new jobs found but not fetched; jobs in searches that were never sent are not counted, and the next run searches the same period again.
