# Product Definition

## Purpose
A system that discovers relevant software/AI jobs, evaluates them against my
real profile with explainable scores, helps me research promising ones, and
tracks my applications. It never applies automatically.

## End-to-end flow
Discovery -> Ingestion -> Normalization -> Deduplication -> Filtering ->
Requirement extraction -> Candidate matching -> Agent research -> Shortlist ->
Application -> Documents -> Interview prep

## Key principles
- Discovery is driven by job relevance, not a hand-picked list of tech companies.
- The job text used for an application is never overwritten (snapshots).
- Every claim in a generated document must be backed by real candidate evidence.
- PostgreSQL is the source of truth.

## V1 scope (MVP)
1. PostgreSQL and core models
2. 2-3 real job sources
3. Deduplication and snapshots
4. Structured candidate profile
5. Explainable matching
6. Application tracking
7. One research agent with tools
8. Evidence-grounded cover letters
9. One daily discovery and matching automation

## Non-goals (not in V1)
- LinkedIn/Indeed scraping as a core dependency
- Automatic applications
- 30+ ATS integrations
- Recruiter email automation
- Multi-agent system
- Own vector database
- Fine-tuning
- Continuous monitoring (daily is enough)

## Configuration
Target roles, locations, seniority and employment type are user-configurable