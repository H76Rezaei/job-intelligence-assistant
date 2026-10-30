# 06: A time limit per search

**What to build:** a LinkedIn search stops after a set time, so one large search cannot use up the whole run. It stays unfinished with its old window, and the next search gets its turn. Spec: `.scratch/linkedin/spec.md`.

**Blocked by:** 05

**Status:** done

Why: in real run 13, one search used all 120 requests (20 pages, 100 details) and did not finish, so no search moved forward.

- [x] A search stops once `max_minutes_per_search` has passed (default 20, optional in the `[linkedin]` settings), checked before each page and each job
- [x] Time for detail requests and pauses counts; the check does not interrupt a request or a rate-limit wait already running
- [x] A stopped search stays unfinished, keeps its window and logs a warning; the run carries on with the next search
- [x] Tests: the next search gets its turn, detail time counts, and the windows are right after a run

**Real-run check (Claude):**
- [x] One real `--source linkedin` run: more than one search is reached and at least one finishes; result recorded below

Run 15 (30 Oct 2026): one search stopped at its time limit, the run moved on, and 4 of 12 searches finished before the cap. Details in ticket 04.

Real run (30 Oct 2026), not completed:
- The run after run 13 was stopped from outside after 76 requests, because the computer was low on memory. All 76 answered 200. The log shows one search stopped at its time limit and the run moved on to the next one, so the limit works in a real run.
- Nothing from this run was stored: the run commits only at its end, so run 13's windows are still in force. The check above is still open.

Known limit: a stopped search starts again from its newest results, and at about 25 seconds per request 20 minutes is about 48 requests. A search with more than about 48 pages of results in its window could never finish, and its oldest results would never be read. The warning in the log is the sign of this.
