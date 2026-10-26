# 02: Skip senior jobs

**What to build:** ingestion never stores a job whose title says it is a senior role, from any source. Only the title decides: a description mentioning senior colleagues or asking for years of experience never skips a job. Skipped jobs cost no detail request and are counted in the run summary. Senior jobs already in the database are removed once, except jobs I have an application for. Paste import is not filtered. Spec: `.scratch/linkedin/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A job is skipped when its title contains one of the configured words as a whole word, in any case. Default list: Senior, Sr., Lead, Principal, Staff, Head of, Leiter, Teamleiter
- [ ] A title that also contains Junior, Mid, Entry, Einsteiger or Berufseinsteiger is kept ("Junior/Senior Developer", "Developer (Mid/Senior)")
- [ ] The word list is an optional `exclude_title_words` setting in the search settings file, with the default list in code and shown in the example file
- [ ] The filter runs in the ingestion run after the Germany filter and before any detail request, so it applies to every source
- [ ] Skipped jobs are not stored and are counted as `skipped_senior` in the run counts and the printed summary
- [ ] Paste import stores senior titles as before
- [ ] A one-off cleanup (a data migration) deletes stored jobs whose title matches the default rule, with their snapshots and source links, and keeps every job that has an application
- [ ] Seam 1 tests cover: senior word in the title skipped without a detail call, the same word only in the description kept, "Sr." and "Head of" skipped, a Junior/Senior title kept, a custom word list, and the count
- [ ] Seam 3 test: paste import of a senior title still works
