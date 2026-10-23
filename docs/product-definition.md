# Product Definition

## Purpose

A tool I use every day for my own job search in Germany. It finds new jobs from several sources, shows only the good fits with the reasons, drafts my CV and cover letter from my real evidence, and lets me track my applications. It never applies automatically.

## End-to-end flow

Ingestion (Bundesagentur, paste, collectors) -> Matching the same job across sources -> Snapshots -> Cheap filters -> Requirement extraction -> Classification against profile evidence -> Fit score -> My review -> Documents -> Application tracking

## Key principles

- **No agent.** Plain code, with an LLM called in three fixed places: extracting requirements, classifying them against my evidence, and drafting and checking documents.
- **Never invent experience.** Every claim in a document traces to real evidence. Missing information is flagged, not filled.
- **Job text is never overwritten.** Snapshots keep the exact posting used for an application.
- **No automatic applying.** I review, decide and send.
- **Keep it simple.** Tests, config and abstractions only when needed.
- **No personal data in the repo.** PostgreSQL holds my data; the repo holds example data only.

## Scope

1. PostgreSQL and core models (done)
2. Ingestion from the Bundesagentur plus a paste import
3. Daily collectors for LinkedIn, StepStone, Xing and get-in-IT in a private repo
4. Profile with evidence for every skill
5. Requirement extraction and a fit score shown at or above 50%, with a breakdown
6. CV and cover letter drafts in Word and PDF, in the posting's language
7. Daily schedule and deployment on Azure behind a single-user login

Application tracking with manual statuses is already built. The order and reasons are in [roadmap.md](roadmap.md).

## Non-goals

- An agent or multi-agent system
- Automatic applying or recruiter email automation
- A vector database or fine-tuning
- Continuous monitoring (daily is enough)
- Salary lookup
- Multiple users

## Configuration

Search keywords, search centers with radius, remote search, and thresholds are configured in local files ignored by git. My profile and cover letter instructions live in the database or local configuration.
