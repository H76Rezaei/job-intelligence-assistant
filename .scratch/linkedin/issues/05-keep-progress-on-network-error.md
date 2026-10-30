# 05: Keep progress when the network drops

**What to build:** a network error during a LinkedIn run (DNS failure, connection refused or reset, timeout: `httpx.TransportError`) stops LinkedIn for this run the way the cap does, instead of failing the source. The jobs stored so far are kept, the search that was being read stays unfinished, and the summary says "network error". Other unexpected responses (a 500, HTML that does not parse) still fail the source and roll back its writes as before. Spec: `.scratch/linkedin/spec.md`.

**Blocked by:** 04

**Status:** done

Why: in real run 12, the network dropped after 107 good requests. The source failed, its savepoint rolled back, and about 100 detail fetches (around 45 minutes of work) were thrown away. With the 20–30 second pause per request, one drop near the end costs a whole LinkedIn run.

This changes ticket 03's rule "a failed search ends the source for this run" for network errors. Claude took "start on ticket 5" (30 Oct 2026) as the OK this ticket was waiting for.

- [x] A transport error on a LinkedIn search or detail request ends all LinkedIn requests for the run, like the cap; no retry
- [x] Jobs stored before the error are kept; the interrupted search and any search with a job left without details stay unfinished in the per-search windows
- [x] A `network_error` flag in the counts and "network error" as the stop reason in the summary
- [x] Other exceptions still fail the source as a whole and leave the previous window map in force (search requests; a failed detail request still counts as a detail error and skips only that job, as before)
- [x] The Bundesagentur is unchanged
- [x] Tests: a network error part-way keeps the stored jobs and leaves the search unfinished; a network error on a detail request does the same; another error still rolls back

**Then (Claude):** finish ticket 04's real-run check: one more real `--source linkedin` run after run 11. It should start with the waiting searches, and the waiting count should go down from 11. Record the result in ticket 04.

Result (30 Oct 2026): run 13 is recorded in ticket 04. It started with a waiting search, but the waiting count went up to 18, so the check is not passed. The network did not drop during the run, so this ticket's behaviour is covered by tests only, not by a real drop. Run 15 did not drop either. The rest of ticket 04's check stays in ticket 04.
