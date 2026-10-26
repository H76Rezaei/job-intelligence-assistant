# Spec: LinkedIn collector

Status: ready-for-agent

Roadmap: Step 3 in `docs/roadmap.md`, first collector. Decisions agreed in the grilling session of 26 Oct 2026 (see the roadmap's decision log). StepStone, Xing and get-in-IT each get their own live check and spec later.

## Problem Statement

Ingestion pulls jobs from the Bundesagentur only, which misses many employers. Many jobs I would apply to are posted only on LinkedIn, so I still search there by hand and copy jobs over with the paste form. I want the same command I already run to also collect LinkedIn jobs for my job titles and places, store them next to the Bundesagentur jobs without duplicates, and never silently skip a search, while sending few and slow requests so LinkedIn does not block me.

## Solution

The ingestion command gains a LinkedIn source. It reads LinkedIn's public job search without a login, using the same job titles, centers, radius and Germany-wide remote search as every other source. The titles are combined into a few `OR` groups so one search covers several titles. It searches newest first, only since the last time each search ran, and fetches the full posting only for jobs I do not have yet. It pauses 20–30 seconds between requests and stops after 120 requests. A run that stops early records which searches are unfinished, and the next run does those first, so no search and no job is ever skipped. LinkedIn jobs go through the same storage, Germany filter and duplicate matching as Bundesagentur jobs, and the job page shows "LinkedIn" as a source with a link.

## User Stories

1. As a job seeker, I want LinkedIn jobs collected by the same command I already run, so that one run fills my list from both sources.
2. As a job seeker, I want to run only the LinkedIn source, so that I can retry it without rerunning the Bundesagentur.
3. As a job seeker, I want LinkedIn searched with the same job titles as the Bundesagentur, so that I maintain one list of titles.
4. As a job seeker, I want LinkedIn searched around the same centers and radius, so that the same places apply to every source.
5. As a job seeker, I want LinkedIn's remote search for all of Germany included, so that I find remote jobs that are only on LinkedIn.
6. As a job seeker, I want my titles combined into a few `OR` searches, so that 47 titles cost about 18 searches instead of 141.
7. As a job seeker, I want results read newest first, so that the newest jobs are found even when a run stops early.
8. As a job seeker, I want the first LinkedIn run to look back 7 days, so that I start with a useful list.
9. As a job seeker, I want later runs to look back only to when each search last finished, plus 2 hours of overlap, so that daily runs are short and nothing falls between two runs.
10. As a job seeker, I want a missed day covered by the next run, so that skipping a day loses no jobs.
11. As a job seeker, I want at most 120 LinkedIn requests per run, so that the volume stays low.
12. As a job seeker, I want a random pause of 20–30 seconds between LinkedIn requests, so that the traffic looks like a person and avoids rate limits.
13. As a job seeker, I want a rate-limited request (429) retried once after 90 seconds, so that a short limit does not end the run.
14. As a job seeker, I want a second 429 to stop LinkedIn for this run like reaching the cap, so that I do not get blocked and the rest waits for the next run.
15. As a job seeker, I want searches a capped run did not finish to be done first by the next run, with their old window, so that no title or place is ever skipped.
16. As a job seeker, I want a search to count as finished only when all its pages were read and every new job it found got its full text, so that jobs skipped by the cap are picked up later.
17. As a job seeker, I want the full posting text fetched only for jobs not yet in my database, so that known jobs cost no extra request.
18. As a job seeker, I want a LinkedIn job I already have from the Bundesagentur recognised as the same job by title and company, so that I see each role once.
19. As a job seeker, I want the same title at a different company stored as a separate job, so that jobs only on LinkedIn are added.
20. As a job seeker, I want a role LinkedIn lists in several cities with different IDs fetched once, so that one employer does not cost many requests.
21. As a job seeker, I want only jobs located in Germany kept, so that foreign postings never reach my list.
22. As a job seeker, I want the employment type and seniority level from the LinkedIn page stored, so that later filters can use them.
23. As a job seeker, I want the exact LinkedIn posting text stored as a snapshot, so that the text I applied to is preserved.
24. As a job seeker, I want the LinkedIn search card and the description HTML kept as raw data, so that nothing useful from the page is lost.
25. As a job seeker, I want reopened LinkedIn jobs handled like Bundesagentur ones, so that a reposted role shows up again after 60 days.
26. As a job seeker, I want the LinkedIn cap and pause in my local settings file, with sensible defaults, so that I can tune them without touching code.
27. As a job seeker, I want a failing LinkedIn run logged and skipped without affecting the Bundesagentur, so that one broken source never costs me a run.
28. As a job seeker, I want the run summary to show LinkedIn's counts, whether it was capped or rate-limited, and how many searches are still waiting, so that I know what a run did.
29. As a job seeker, I want the job page to show "LinkedIn" with a link to the posting, so that I can open the original.
30. As a job seeker, I want the first real run to compare two single-title searches with their `OR` group once, so that I know the groups do not miss jobs.
31. As a developer, I want all LinkedIn page parsing in one adapter module, so that a change in LinkedIn's HTML touches one place.
32. As a developer, I want the adapter to only fetch and map, never write to the database, so that storage rules stay in one place.
33. As a developer, I want LinkedIn tests to run against saved HTML samples with made-up job data, so that tests never call LinkedIn and the repo holds no real postings.
34. As a developer, I want the pause and retry wait injectable, so that tests run instantly.

## Implementation Decisions

**Where it lives**
- The LinkedIn adapter is a source module in this public repo, next to the Bundesagentur adapter, and is registered in the ingestion command's list of sources under the name `linkedin`. The earlier plan of a separate private repo is dropped; `CLAUDE.md` and the roadmap are updated accordingly.

**LinkedIn endpoints (checked live on 26 Oct 2026, no login)**
- Search: `GET https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search` with `keywords`, `location`, `distance`, `f_TPR=r<seconds>` (posted within), `sortBy=DD` (newest first), `start` (offset, steps of 10). Remote search: `location=Germany` with `f_WT=2`. The response is an HTML fragment of up to 10 `<li>` cards.
- Per card: job ID from `data-entity-urn="urn:li:jobPosting:<id>"`, title (`base-search-card__title`), company (`base-search-card__subtitle`), location (`job-search-card__location`, for example "Bonn, North Rhine-Westphalia, Germany"), posting date (`datetime` attribute), job URL.
- Details: `GET https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<id>`. Full text in `show-more-less-html__markup`; job criteria as subheader/value pairs (`description__job-criteria-subheader` / `description__job-criteria-text`): seniority level, employment type, industries. There is no remote/hybrid field.
- `OR` between quoted titles works on the search endpoint (one search returned a mix of both titles). Full completeness of an `OR` search compared with single searches is not yet verified.
- A request sent about 5 seconds after the previous one got 429 with a meta-refresh body; the same kind of request worked after a 90-second pause.

**Searches**
- Titles from the shared settings are combined into `OR` groups of about 8 quoted titles, in settings order. One search per group and center (with the center's radius), plus one Germany-wide remote search per group when the remote switch is on.
- Each search has a stable key built from its titles and place, so a changed title list simply creates new searches.
- Each search pages through results newest first until a page has fewer than 10 cards, or its window is covered.
- A job found by several searches is returned once per run.

**Windows and continuation**
- Every search has its own "since" time. A search seen for the first time looks back 7 days. A finished search's next window starts at the start of the run that finished it, minus 2 hours of overlap.
- After a run, the LinkedIn entry in the run's existing counts JSON also holds, per search key, the "since" time for the next run. Finished searches get the new time; unfinished searches keep their old one. No new table and no migration.
- The next run reads the latest LinkedIn entry that has this map. It does the unfinished searches first, oldest "since" first, then the others.
- A search counts as finished only when all its pages were read and every new or reopened job it found got its details. A job skipped by the cap, a failed detail call or a rate-limit stop leaves its search unfinished.
- The Bundesagentur keeps its current whole-day window logic. The shared search call changes from a day count to a "since" time (or the per-search map for LinkedIn); the Bundesagentur converts the time back to days.

**Requests**
- LinkedIn cap: 120 requests per run, the same for the first run (continuation replaces the larger first-run cap). Every request counts, retries included.
- A random pause of 20–30 seconds before every request after the first.
- On 429: wait 90 seconds and retry once. A second 429 stops LinkedIn for this run and is handled like reaching the cap, with a separate "rate-limited" flag in the counts.
- Any other unexpected response (for example a redirect to a login wall) fails the request; a failed search ends the source for this run and is logged.

**Mapping to a fetched job**
- Source ID: the LinkedIn job ID. URL: the job URL without tracking parameters.
- Country "DE" when the card's location ends in "Germany"; otherwise none, so the existing Germany filter drops it.
- Location: the card's location text. Work mode: left empty.
- Employment type: from the job criteria. Seniority level and industries stay in the raw data.
- Description: the text of the description HTML. Raw data: the card fields plus the description HTML and job criteria, not the whole page.

**Settings**
- The shared keywords, centers, radius and remote switch apply to LinkedIn unchanged.
- An optional `[linkedin]` table in the settings file sets the cap and the pause range. Defaults live in code (120, 20–30 seconds). The committed example file shows the table with its defaults.

**Command and summary**
- The summary line for LinkedIn adds "rate-limited" when that happened, and the number of searches still waiting for the next run.

**Frontend**
- The job page's source labels gain "LinkedIn".

## Testing Decisions

- Good tests check external behaviour through the seams below, not internal helpers. They assert stored jobs, counts, the next run's windows, and the HTTP requests sent.
- **Seam 1, the ingestion run (existing):** the run function with a fake adapter. Covers per-search windows and continuation: unfinished searches done first next run with their old window, finished searches moving forward, a search with a job skipped by the cap staying unfinished, a new search getting 7 days, the map read from the latest LinkedIn entry, and the Bundesagentur's window logic unchanged.
- **Seam 2, the LinkedIn adapter at its HTTP boundary:** an httpx mock transport serves saved HTML fragments, with the pause and retry wait injected as zero. Covers: `OR` grouping and one search per group and place plus remote, query parameters (window in seconds, newest first, offsets), paging, mapping of cards and details, Germany detection, a job returned once, the cap counting every request, 429 retry then stop, and a login-wall response failing the source.
- **Seam 3, the ingest command and settings (existing):** LinkedIn registered and selectable, the `[linkedin]` table and its defaults, and the summary line.
- Fixtures keep LinkedIn's real HTML structure with made-up titles, companies and IDs. No test calls LinkedIn.
- No frontend tests; the "LinkedIn" label is checked by hand.
- Prior art: the Bundesagentur adapter tests (mock transport, cap tests), the ingestion run tests (fake adapter, window tests) and the ingest command tests.

## Out of Scope

- StepStone, Xing and get-in-IT collectors (later specs, each after its own live check).
- Running on Azure, a cloud blocking test, and the fallback that sends results from my computer to a deployed app (Step 7).
- A scheduled daily run (Step 7).
- Logging in to LinkedIn, a headless browser, or any LinkedIn page beyond the public guest search and job endpoints.
- Detecting remote or hybrid work mode from LinkedIn.
- Changing the Bundesagentur's windows or cap.
- The coverage check, which I do by hand.

## Further Notes

- LinkedIn's robots.txt and user agreement forbid automated access without permission. I accepted this for personal, low-volume use that I start myself; paste import remains the fallback if LinkedIn blocks me.
- The remote search's results showed cities and nothing marked them as remote. Check in the first real run whether they are really remote; if not, switch the remote search off for LinkedIn.
- In the first real run, compare two single-title searches with their `OR` group once and record the result in the ticket. If the group misses jobs, use smaller groups.
- Rough daily load: 18 searches of 1–3 pages plus details for jobs unknown from the Bundesagentur, about 40–100 requests and 30–50 minutes. The first run and a run after a missed day will usually be capped and continue in the next run.
- LinkedIn lists the same role in several cities under different IDs; the existing title-and-company matching merges them into one job.
