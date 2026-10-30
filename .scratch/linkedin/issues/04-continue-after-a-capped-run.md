# 04: Continue after a capped run

**What to build:** every LinkedIn search keeps its own window, so a run that stops at the cap or a rate limit never makes a later run skip a search or a job. The next run first does the searches that were not finished, with their old window, and then the rest. The summary tells me how many searches are still waiting. Spec: `.scratch/linkedin/spec.md`.

**Blocked by:** 03

**Status:** ready-for-human

- [x] Each search has a stable key from its titles and place
- [x] After a run, LinkedIn's entry in the run counts holds, per search key, the "since" time for the next run: the run's start minus 2 hours for finished searches, the old time for unfinished ones. No new table, no migration
- [x] A search counts as finished only when all its pages were read and every new or reopened job it found got its details; a job skipped by the cap, a failed detail call or a rate-limit stop leaves it unfinished
- [x] The next run reads the latest LinkedIn entry that has this map, does unfinished searches first (oldest "since" first), then the others; a search not in the map looks back 7 days
- [x] A run where LinkedIn failed as a whole leaves the previous map in force
- [x] The summary shows how many LinkedIn searches are still waiting
- [x] The Bundesagentur's window logic is unchanged
- [x] Seam 1 tests cover: unfinished searches first with their old window, finished searches moving forward, a job skipped by the cap keeping its search unfinished, a new search getting 7 days, a failed run keeping the old map, and the Bundesagentur unchanged

**Real-run check (Claude):**
- [ ] Two real runs in a row where the first is capped: the second starts with the waiting searches and the waiting count goes down; result recorded below

Notes from the build (26 Oct 2026):
- The contract for a source with a window per search is `ResumableSource` in the source module; each fetched job carries its `search_key`.
- A block or third 429 during a detail request now ends all LinkedIn requests for the run at once, including the search being read.
- After a change to the title list, new searches count as waiting 7 days, so they go before searches that waited less. Left as it is.

Real runs (27 Oct 2026):
- Run 11: capped at 120 requests, all answered 200, no rate limits. 139 fetched, 96 new, 9 already known, 21 senior, 12 outside Germany, 0 detail errors; 1 job left for the next run. 7 of 18 searches finished (window moved to the run's start minus 2 hours); 11 waiting (still 7 days back).
- Run 12: started with the search that had the leftover job, then the searches run 11 never reached; the 7 finished ones were not repeated. After 107 good requests the network dropped (`getaddrinfo failed`), so LinkedIn failed as a whole: run 11's map stayed in force (correct), but everything fetched in run 12 was rolled back. The waiting count is not checked yet. Next: ticket 05, then one more run.

Real run (30 Oct 2026):
- Run 13: capped at 120 requests, all answered 200. 200 fetched, 100 new, 28 already known, 37 senior, 33 outside Germany, 0 detail errors; 2 jobs left for the next run. It started with a waiting search, as it should, but that one search used all 120 requests (20 pages, 100 details) and did not finish.
- The waiting count went up from 11 to 18, so the check above is not passed. All 18 windows are unchanged from run 11 and no job is lost. The 7 searches run 11 finished were not reached, so they count as waiting again, although they only have a 3-day-old window.
- Decided: the count now holds searches started but not finished, and those not reached whose window is older than 2 days. Tickets 06 and 07 added a time limit per search and a shorter title list.
- Run 15: capped at 120 requests, all answered 200, 51 minutes. 225 fetched, 89 new, 82 already known, 36 senior, 18 outside Germany, 0 detail errors, 0 jobs left. 4 of 12 searches finished; 8 waiting.
- The check above is still open: the shorter list made new searches, so run 15 did not continue run 13's. The next run on the same list closes it if it starts with the waiting searches and the count goes below 8.
