# 02: Skip senior jobs

**What to build:** ingestion never stores a job whose title says it is a senior role, from any source. Only the title decides: a description mentioning senior colleagues or asking for years of experience never skips a job. Skipped jobs cost no detail request and are counted in the run summary. Senior jobs already in the database are removed once, except jobs I have an application for. Paste import is not filtered. Spec: `.scratch/linkedin/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] A job is skipped when its title contains one of the configured words as a whole word, in any case. Default list: Senior, Sr., Lead, Principal, Staff, Head of, Leiter, Teamleiter
- [x] A title that also contains Junior, Mid, Entry, Einsteiger or Berufseinsteiger is kept ("Junior/Senior Developer", "Developer (Mid/Senior)")
- [x] The word list is an optional `exclude_title_words` setting in the search settings file, with the default list in code and shown in the example file
- [x] The filter runs in the ingestion run after the Germany filter and before any detail request, so it applies to every source
- [x] Skipped jobs are not stored and are counted as `skipped_senior` in the run counts and the printed summary
- [x] Paste import stores senior titles as before
- [x] A one-off cleanup (a data migration) deletes stored jobs whose title matches the default rule, with their snapshots and source links, and keeps every job that has an application
- [x] Seam 1 tests cover: senior word in the title skipped without a detail call, the same word only in the description kept, "Sr." and "Head of" skipped, a Junior/Senior title kept, a custom word list, and the count
- [x] Seam 3 test: paste import of a senior title still works

Notes from the build (26 Oct 2026):
- Decided with me after the ticket: a senior word alone in brackets ("(Senior) Data Scientist", "Engineer (Senior)") marks the level as optional, so the job is kept.
- The cleanup also keeps jobs I pasted myself, in line with "pasted jobs are never filtered". It carries its own frozen copy of the rule.
- Bundled fix: a run's `finished_at` used the transaction's start time, so it always equalled `started_at`; it now uses the real clock.
- Real database: 151 jobs before, 32 senior jobs removed, 119 left (backup taken before).
- Known edges, left as they are: feminine and compound forms ("Teamleiterin", "Abteilungsleiter") are not matched unless added to the list; an exception word anywhere keeps the job ("Senior Developer, Mid-Market"); "Lead Generation Manager" and "Staff Accountant" are skipped.
