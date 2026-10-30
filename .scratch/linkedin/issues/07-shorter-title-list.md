# 07: A shorter title list for LinkedIn

**What to build:** an optional `keywords` list in the `[linkedin]` settings that replaces the shared titles for LinkedIn only, so a run has fewer searches and can finish sooner. The Bundesagentur keeps the shared list. Spec: `.scratch/linkedin/spec.md`.

**Blocked by:** 06

**Status:** done

- [x] `[linkedin] keywords` replaces the shared titles for LinkedIn; without it, the shared titles apply
- [x] The Bundesagentur still uses the shared titles
- [x] Tests: the adapter searches the LinkedIn titles, and the settings read both lists

**Real-run check (Claude):**
- [x] One real `--source linkedin` run with the shorter list: run 15 used 12 searches, and 4 finished before the cap. Details in ticket 04, whose own check stays open

Notes (30 Oct 2026):
- Live check around one center, 12 requests, neither side read to the end. A dropped title's results also came up under the kept group for 12 of 20 jobs; the misses were senior roles or likely further down the list. For dropped trainee titles it was 15 of 30; 13 of the 15 misses were apprenticeships or dual-study places.
- The private list has 27 titles, which makes 4 groups: 12 searches with the current places, down from 18.
- A changed title list makes new search keys, so all searches start again with a 7-day look-back. The old windows reached back to 20 Oct, so jobs posted before that 7-day window and not collected yet can be missed once.
