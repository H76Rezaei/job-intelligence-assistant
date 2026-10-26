# 04: Continue after a capped run

**What to build:** every LinkedIn search keeps its own window, so a run that stops at the cap or a rate limit never makes a later run skip a search or a job. The next run first does the searches that were not finished, with their old window, and then the rest. The summary tells me how many searches are still waiting. Spec: `.scratch/linkedin/spec.md`.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Each search has a stable key from its titles and place
- [ ] After a run, LinkedIn's entry in the run counts holds, per search key, the "since" time for the next run: the run's start minus 2 hours for finished searches, the old time for unfinished ones. No new table, no migration
- [ ] A search counts as finished only when all its pages were read and every new or reopened job it found got its details; a job skipped by the cap, a failed detail call or a rate-limit stop leaves it unfinished
- [ ] The next run reads the latest LinkedIn entry that has this map, does unfinished searches first (oldest "since" first), then the others; a search not in the map looks back 7 days
- [ ] A run where LinkedIn failed as a whole leaves the previous map in force
- [ ] The summary shows how many LinkedIn searches are still waiting
- [ ] The Bundesagentur's window logic is unchanged
- [ ] Seam 1 tests cover: unfinished searches first with their old window, finished searches moving forward, a job skipped by the cap keeping its search unfinished, a new search getting 7 days, a failed run keeping the old map, and the Bundesagentur unchanged

**Real-run check (Claude):**
- [ ] Two real runs in a row where the first is capped: the second starts with the waiting searches and the waiting count goes down; result recorded below
