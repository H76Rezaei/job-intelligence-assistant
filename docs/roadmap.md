# Job Search Assistant: Roadmap v3.0

Oct 23, 2026

## Purpose and principles

This is a tool you use every day to make your own job search easier: it finds new jobs from several sources, shows only the good fits, and drafts your application documents from your real evidence. It is built with Claude Code and its skills, and the public repo is also evidence of how you work with them.

- **No agent.** The whole workflow is deterministic software. The LLM is called in three fixed places only: extracting requirements from a posting, helping classify them against your profile evidence, and drafting your CV and cover letter.
- **Never invent experience.** Every claim in a document traces to your real evidence. Missing information is flagged, not filled.
- **Job text is never overwritten.** Snapshots keep the exact posting used for an application.
- **No automatic applying.** You review, decide and send.
- **Keep it simple.** Add tests, config, files and abstractions only when needed.
- **Public repo, no personal data.** Your real profile, search settings, cover letter instructions and secrets never enter the repo. The LinkedIn adapter lives in a separate private repo.
- **A clear README.** It explains the problem, the architecture, how to run it and how Claude Code and the skills are used.

### How we work

- Claude Code writes larger chunks of code and gives short explanations, because this is familiar territory (FastAPI, React, PostgreSQL).
- You stay involved in the design. Claude Code asks for your opinion on the data model, what the screens show, prompts and scoring rules, and hosting and cost. Small plumbing it decides and reports in one line.
- Process: `/grill-me` to align, `/to-spec` and `/to-tickets` to plan, `/implement` with `/tdd` and `/code-review` to build. Tickets are local markdown files in the repo, not GitHub issues.
- Each step ends with a commit. Commands are for Windows (cmd).

## What changed from v2.0

v3.0 turns the project from an agent portfolio piece into a daily-use tool, so the agent, the comparison and the evaluation work are gone, and LinkedIn and deployment move up.

| Topic | v2.0 | v3.0 |
| --- | --- | --- |
| Purpose | Portfolio project that proves agent skills | Daily-use tool. The repo is public as evidence of working with Claude Code, the CLI and skills |
| Agent | One research agent, then a comparison with a pipeline | None. Plain code, with three fixed LLM uses |
| Evaluation and comparison | Frozen test set, three runs per version, write-up | Dropped. A small labeled set checks that the fit score is sensible |
| LinkedIn | Local-only adapter, decided after a coverage check | Built early as a collector in a separate private repo. Test on Azure first, fall back to running it on your computer |
| Build process | Claude writes small pieces, you review each one | Claude Code with the skills: grill, spec, tickets, TDD, code review. Larger chunks, short explanations |
| Tickets | Roadmap and chat | Local markdown files in the repo |
| Hosting | One small EU server, provider open | Azure, on your student account |
| README | Polish for outsiders, demo | A clear README, no demo |

**What stays:** Bundesagentur plus paste import, the 50% fit score from requirement checks against profile evidence, the evidence rule, snapshots, Word and PDF documents in the posting's language, your own cover letter instructions, manual application status, no salary feature, OpenAI called directly with a monthly spending cap.

## Where we are now and the roadmap at a glance

Seven steps, in this order. The weeks are a rough guess at 10 hours a week, and I expect the early steps to be more accurate than the later ones.

**Built so far:** PostgreSQL 17 in Docker, five tables (Company, JobPosting, JobPostingSnapshot, CandidateProfile, Application), a FastAPI backend (read-only jobs, profile, applications with six manual statuses), pytest tests, and a React dashboard with Jobs, Job Detail, Applications and Profile pages. No ingestion, no LLM calls, no deployment yet. The last push was on 16 Oct 2026.

| Step | What you get | Rough weeks |
| --- | --- | --- |
| 1 | Claude Code installed, skills and `CLAUDE.md` set up, tickets as local files, clear README, outdated docs fixed | 1 |
| 2 | Ingestion: Bundesagentur jobs stored daily by one command, paste import for jobs you find yourself | 2 |
| 3 | Collectors for LinkedIn, StepStone and get-in-IT in a private repo, tested on Azure with a fallback | 4 |
| 4 | Your profile with evidence for every skill | 1.5 |
| 5 | Requirement extraction and the 50% fit score, with a visible breakdown | 2 |
| 6 | Tailored CV and cover letter drafts in Word and PDF | 2 |
| 7 | Daily schedule and deployment on Azure | 2 |

About 14 weeks in total. You can start using the app for real after Step 2, and after Step 3 it fills itself with jobs from several sources.

## Steps 1 to 3: setup, ingestion, collectors

### Step 1: Claude Code setup

1. Install Claude Code on your Windows computer.
2. Install the skills with `claude plugin install mattpocock-skills@claude-plugins-official` and run `/setup-matt-pocock-skills` once in the repo. Choose local files as the ticket tracker. Do not install the skills a second way, or each one appears twice.
3. Write `CLAUDE.md`: the stack, Windows commands, the rules from this roadmap, and the list of decisions that need your opinion.
4. Fix `docs/architecture.md` and `docs/product-definition.md`, and write a clear README. Remove the duplicated imports in `backend/app/api/jobs.py`.
5. Run `/grill-me` and `/to-spec` for Step 2 and create its tickets.

**Done when:** Claude Code runs in the repo with the skills, the README is accurate, and Step 2 has tickets.

### Step 2: Ingestion (Bundesagentur plus paste)

Ingestion means pulling postings from an outside source into your own database, in your own format.

1. API tested on 23 Oct 2026: search works on `/pc/v6/jobs`, the full text comes from `/pc/v4/jobdetails/{base64 refnr}`, and Germany-wide remote search uses `homeoffice=prozentual_100;nv_true`. The public documentation is unofficial and outdated, so the API can change without notice.
2. Build a small adapter interface and the Bundesagentur adapter. Search keywords, several search centers each with a radius, and Germany-wide remote jobs sit in `config/search.toml`, which git ignores. A committed example file shows the format. Postings the BA copies from external boards (get-in-IT, jobvector and others) are included.
3. Store each job with a snapshot of the full text, the raw source data and the fetch time. Only jobs located in Germany are kept.
4. Reruns are safe. The same job is title plus company after cleanup (gender tags and legal forms dropped), whatever the city or source. Only jobs not yet in the database get the detail call and a snapshot; edits to known jobs are not fetched. A job not seen for 60 days counts as reopened.
5. Add a paste import with an endpoint and a form, for jobs you find on other sites.
6. One command, started by you, runs the ingestion. A failing source is logged and skipped, and it never stops the others. Each run is recorded, and the Jobs page can show what is new since the last run.

**Done when:** one command stores new jobs, paste import works, and a rerun creates no duplicates.

**Decided (23 Oct 2026):** what counts as the same job, and raw data is kept as JSON on each snapshot, forever.

### Step 3: Collectors (LinkedIn, StepStone, get-in-IT)

1. Build collectors that read public job pages without a login, in this order: LinkedIn, StepStone, get-in-IT. They are adapters in a separate private repo that the app loads when it is present.
2. Before building each one, test the live site: blocking, terms and page structure.
3. Low volume, one run a day each, and results go through the same storage and duplicate checks as every other source.
4. Test them on Azure first. If a site blocks Azure addresses, run the same adapter on your own computer on a schedule and send the results to the app.
5. Coverage check, once: you write down about 20 relevant jobs you found yourself, and we count how many the system also found. Repeat it after a new source is added.

**Done when:** jobs from all three collectors appear next to Bundesagentur jobs every day, or the fallback on your computer does the same.

**Your opinion is needed on:** your search settings for each site, and whether to run on Azure or on your computer if the first test fails.

## Steps 4 to 6: profile, fit score, documents

### Step 4: Profile with evidence

Your real background becomes structured data: skills, projects, experience, education, languages, target roles and locations. Each item carries a short evidence text, and anything you cannot back up is marked weak or missing. It is entered through the existing Profile page, stored in your own database, and never in the repo. The repo gets generic example data.

**Done when:** your profile is complete, every important skill has evidence, and it can be read as one structured result.

**Your opinion is needed on:** how detailed the evidence texts are, and how skills are named so they match job requirements.

### Step 5: Requirements and fit score

1. Cheap filters run first (location, employment type, obvious mismatches), so the LLM reads only plausible jobs.
2. An LLM call extracts each requirement from the posting with structured output, marked required or preferred, and keeps its source text.
3. Each requirement is classified against your evidence as Strong, Partial, Missing or Risk.
4. The score is computed by plain code. Starting formula, to be tuned with you:

```latex
\text{score} = \frac{\text{Strong} + 0.5 \times \text{Partial}}{\text{number of required requirements}}
```

5. The full result is stored. The jobs list shows only jobs at or above the threshold (50%, configurable), sorted by score, with a switch to show all. The job page shows the breakdown.
6. You label the jobs you have seen as pursue, skip or unsure, and we compare with the score. This is a sanity check, not an evaluation study.

**Done when:** you can see exactly why any job got its score, and the list shows only good fits.

**Your opinion is needed on:** how much a Partial or a Risk item counts, and the prompt wording for extraction.

### Step 6: Tailored documents

1. Inputs: the pinned job snapshot, your profile evidence and your cover letter instructions, which you provide and which stay in configuration, not in the repo.
2. The CV selects and rewords your real evidence for the job. The cover letter follows your instructions.
3. The language follows the posting: German or English.
4. A second LLM call checks the draft against your evidence and flags unsupported claims. Missing information is listed, never filled.
5. Export an editable Word file and a PDF. Every version is saved and linked to the application and its snapshot.
6. Application status stays manual: interested, applied, interview, rejected or offer, with notes.

**Done when:** from a job page you can generate both documents, see flagged claims, download the files and find every version later.

**Your opinion is needed on:** the CV layout and the structure of your cover letter instructions.

## Step 7: Daily schedule and Azure deployment

The app runs by itself on Azure, so you open it each morning and find new good fits waiting.

**Daily run (plain code):** load your search settings, ingest from the Bundesagentur and the collectors, apply the filters, score new jobs, store them and write a run report. One failing source never stops the others, and running the workflow twice never creates duplicates.

1. A scheduled daily run with a run report: jobs found, new, scored, shown, failures.
2. Docker for the backend, frontend, database and the scheduled job.
3. Configuration through environment settings. Secrets never enter the repo.
4. Automatic database migrations on deploy.
5. Logging and clear error handling around every outside call.
6. Simple single-user login, because only you use it.
7. Deploy to Azure and run the LinkedIn collector there, or from your computer if Azure is blocked.
8. GitHub Actions for tests and build.

**Done when:** a scheduled run on Azure finds and scores new jobs without you, and you log in and use the app online.

### Azure account and cost

You have an Azure for Students account with a $100 credit usable for 12 months. According to [Microsoft's student page](https://azure.microsoft.com/en-us/free/students):

- No credit card is needed.
- The page lists free monthly amounts of a small virtual machine (B1s) and a small PostgreSQL server (Flexible Server B1MS) for 12 months, but states them for new customers only. Whether that applies to your account is not confirmed. Check in the portal.
- When the credit runs out, Microsoft emails you. Without moving to pay-as-you-go, the subscription and its products are disabled.
- You can renew each year with your school email while you remain a student. If you stop being a student, you lose this plan.
- Use is limited to education and non-commercial work. A personal job search tool fits, but selling or sharing the app would not.
- The page names no region limits. Check which regions your subscription allows, and prefer one in the EU because the app holds your personal data.

The $100 credit spread over 12 months is about $8 a month, close to your 10 € target. I have not priced a specific setup yet. The decision on which Azure service to use (one small VM with Docker, or App Service with a managed database) is made at the start of this step.

## AI tooling: what builds the app and what runs inside it

Only one AI tool runs inside the deployed app: the LLM API, called by plain code. Everything else is how Claude Code builds it.

| Tool | Role | Inside the app? |
| --- | --- | --- |
| Claude Code (CLI) | Builds the app: edits files, runs tests, commits | No |
| [mattpocock/skills](https://github.com/mattpocock/skills) | Process for Claude Code: `/grill-me`, `/to-spec`, `/to-tickets`, `/implement`, `/tdd`, `/code-review`, `/pr` | No |
| `CLAUDE.md` | Standing rules for Claude Code in this repo | No |
| Subagents, hooks | Optional Claude Code features, such as parallel work on tickets | No |
| LLM API (OpenAI) | Three fixed calls: extract requirements, classify against evidence, draft documents and check them | Yes, as plain function calls |
| MCP | Connects Claude Code or Claude chat to outside tools. Not needed in the app. Indeed's connector works only inside Claude | No |

A monthly spending cap is set at the LLM provider before the first LLM call.

## Job sources and coverage

Discovery is plain scheduled code that calls source APIs. The Bundesagentur alone misses many employers, so coverage grows in layers.

| Source | When | What we know |
| --- | --- | --- |
| [Bundesagentur API](https://github.com/bundesAPI/jobsuche-api) | Step 2 | Search by keyword, location, radius, days since published and home office, plus a detail call with the full text. Includes postings copied from external boards. Documentation is unofficial and outdated. The portal terms forbid automated data collection (see Risks) |
| Manual paste import | Step 2 | Any job you find yourself, including Indeed results from a Claude chat |
| LinkedIn collector | Step 3 | Public pages, no login, private repo. Against LinkedIn's terms, and cloud addresses may be blocked |
| StepStone collector | Step 3 | No public API. Public pages, private repo. Its terms forbid scraping |
| get-in-IT collector | Step 3 | No public API known. Some of its jobs already arrive through the Bundesagentur. Terms to be checked |
| [Arbeitnow](https://www.arbeitnow.com/blog/job-board-api) | Later | Free, no key. Fields and terms unconfirmed |
| freehire.me | Later | Public JSON API, tech-first, third-party hosted. Germany coverage to be tested |
| Adzuna | Later | Needs registration. Germany support and terms unconfirmed |
| Employer career pages | Later | Employers found in results lead to their own career pages |
| LinkedIn alert emails | Later | Title, company and link from the emails LinkedIn sends you |

Indeed has no API for your own app. In a Claude chat I can search it for you, and you paste what you want into the app.

**Coverage check:** you write down about 20 relevant jobs you found on your own, and we count how many the system also found. It runs once after Step 3, then after each added source, and decides which source comes next.

## Risks, security and rules

Three risks need your attention. The rest is routine.

| Risk | What could happen | What we do |
| --- | --- | --- |
| LinkedIn, StepStone, get-in-IT | Scraping breaks LinkedIn's and StepStone's terms. The pages can change or block requests without notice, and cloud addresses are likely to be blocked faster than a home connection (expected, not verified) | Private repo for the adapters, no login, low volume, once a day, fallback on your computer. The rest of the app works without them |
| Azure student plan | Credit ends after 12 months, renewal needs student status, use is limited to non-commercial work | Know the end date, keep the app single-user, decide before the credit runs out whether to move to pay-as-you-go |
| Bundesagentur API | Unofficial interface that changed field names in Aug 2026. The [portal terms](https://www.arbeitsagentur.de/nutzungsbedingungen) (§2a(3), 8 Jul 2026) forbid robots and using its interfaces against the BA's intended purpose for data collection | Personal use only, runs you start yourself, a hard cap on requests per run. Paste import is the fallback if access breaks or is blocked |

### Security

- Login for the deployed app, secrets in environment settings, none in the repo.
- Your real profile, search settings and cover letter instructions stay in the database or configuration.
- Job postings are untrusted text. They are never treated as instructions, and the LLM calls get no tools.
- A monthly spending cap at the LLM provider.
- Nothing is sent or applied automatically.

### Testing

Tests are written with each feature using `/tdd`. Source adapters run against saved sample responses, not live services. LLM steps are tested with fake responses, and the fit score is checked against your own labels.

### Do not build

- An agent, a multi-agent system, a vector database, fine-tuning.
- Automatic applying, recruiter email automation, continuous monitoring.
- A salary lookup. Dropped completely.
- Multi-user logins, unless you decide later that you want them.

## Later work, open decisions and decision log

Nothing under Later has a date. Each item starts after Step 7, or earlier if daily use shows it is needed.

| Later item | What it adds |
| --- | --- |
| Email reading | Reads LinkedIn alert emails and application status emails. Needs mailbox permission, so security comes first |
| More job sources | Arbeitnow, freehire.me, Adzuna, employer career pages, added one layer at a time |
| Closed jobs | Detects jobs that disappear from their sources and marks them closed |
| Interview preparation | Questions and topics for one application, from the pinned job and your profile |
| Multiple users | Only if you decide you want it. Brings GDPR duties and per-user LLM cost |

### Open decisions

| Decision | Needed in |
| --- | --- |
| Your search settings for LinkedIn, StepStone and get-in-IT | Step 3 |
| Evidence detail and skill naming | Step 4 |
| Weights for Partial and Risk items, extraction prompt | Step 5 |
| CV layout and cover letter instructions | Step 6 |
| Azure service, region, whether the student free services apply, scheduler, login method | Step 7 |
| LLM model and monthly spending cap amount | Step 5 |

### Decision log

| Date | Decision |
| --- | --- |
| 12 to 16 Oct 2026 | Jobs API read-only. Application holds your decision per job with six manual statuses. Only jobs in Germany are stored. Dashboard built before ingestion |
| 22 Oct 2026 | First source Bundesagentur plus paste import. Search settings in local configuration. Fit score from requirement checks, shown at or above a configurable 50%. Documents in Word and PDF, language follows the posting, you review every draft. Salary lookup dropped. OpenAI called directly with a monthly cap |
| 23 Oct 2026 | No agent. Project is a daily-use tool and CV evidence of working with Claude Code, the CLI and skills |
| 23 Oct 2026 | Public repo with a separate private LinkedIn adapter. A clear README stays |
| 23 Oct 2026 | LLM used in three fixed places only |
| 23 Oct 2026 | Claude Code writes larger chunks with short explanations and asks you at design points. Tickets as local files |
| 23 Oct 2026 | LinkedIn collector tested on Azure first, fallback on your computer |
| 23 Oct 2026 | Deploy on Azure with a student account. Target about 10 € a month |
| 23 Oct 2026 | Build order: setup, ingestion, collectors, profile, fit score, documents, Azure deployment |
| 23 Oct 2026 | Bundesagentur used despite its portal terms: personal use, low volume, runs you start yourself, paste as fallback |
| 23 Oct 2026 | Same job = same title and company after cleanup, across all sources and cities. Original names kept for display and documents. A `job_posting_sources` table links each job to its source IDs |
| 23 Oct 2026 | Only jobs not yet in the database are fetched in full. Edits to known jobs are ignored. A job unseen for 60 days counts as reopened. No closure detection yet |
| 23 Oct 2026 | Raw source JSON on every snapshot, kept forever. Ingestion runs recorded in `ingestion_runs`, with a "new in last run" filter on the Jobs page |
| 23 Oct 2026 | Several search centers, each with its own radius, plus Germany-wide remote. Settings in `config/search.toml`, not in the repo |
| 23 Oct 2026 | Step 3 becomes collectors for LinkedIn, StepStone and get-in-IT, once a day each, in the private repo |

## Definition of done

The project is done when you use it every morning and can explain how it is designed.

- New jobs arrive daily from the Bundesagentur, LinkedIn, StepStone and get-in-IT (or the fallback on your computer), plus any job you paste, and reruns never create duplicates.
- Only jobs at or above your threshold are shown, and you can see exactly why each got its score.
- The exact job text used for an application is preserved.
- CV and cover letter drafts use only your real evidence, flag what is unsupported, and every version is stored.
- Application status is tracked by you.
- The app runs on Azure behind a login, runs daily on a schedule and writes a run report.
- Tests pass in CI.
- The public repo has an accurate README, a `CLAUDE.md`, the skills setup and the tickets, and contains no personal data.
