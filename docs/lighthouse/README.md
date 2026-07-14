# Project Lighthouse — Business Intelligence Engine

Phase 1 proof of concept for a market-research system that identifies which
home-services industries have the biggest **digital trust gaps**, and
therefore the strongest outbound sales opportunity for Vidcel.

This is **not** a lead-gen tool and **not** a video generator. It answers one
question, repeatably, for any company it looks at:

> If I owned this company, what would I improve first to increase customer trust?

## What's in this POC

20 real companies (10 Roofing, 5 HVAC, 5 Remodeling) across different US
cities, each scored on the same rule-based rubric and turned into a ranked
opportunity list.

## Layout

```
lighthouse/
  schemas/company_raw.schema.json   contract between collection and analysis
  models.py                         shared data model (RawCompany, ScoredCompany, ...)
  scrapers/collector_interface.py   collection contract (Phase 1: agent-assisted, see below)
  prompts/website_signal_prompt.py  the ONLY LLM prompt in the pipeline (fact extraction, not scoring)
  analysis/
    scoring.py                     7 rule-based scores
    review_intelligence.py         repeated customer language extraction
    website_comparison.py          customer language vs. website language gaps
    customer_journey.py            Search -> Reviews -> Website -> Portfolio -> Contact
    opportunity_engine.py          fixed catalog of triggers -> ranked opportunities
  outputs/
    csv_writer.py                  companies.csv, company_scores.csv, opportunities.csv
    md_writer.py                   industry_summary.md, company_reports/*.md
  data/
    raw/                           collected input (one JSON array per industry)
    output/                        generated deliverables (gitignored inputs regenerate this)
  pipeline.py                      orchestrator: `python -m lighthouse.pipeline`

docs/lighthouse/
  Architecture.md                  system design + Phase 2-5 designs (not implemented)
  Decision_Log.md                  why the scoring/collection choices were made
  Backlog.md                       follow-up work
```

## Running it

```
cd vidcel-dashboard
python3 -m lighthouse.pipeline
```

Reads `lighthouse/data/raw/{roofing,hvac,remodeling}_raw.json`, writes all
deliverables to `lighthouse/data/output/`.

## How the data was collected (Phase 1)

There is no automated scraper in this phase. An LLM research agent was
given a fixed, identical rubric per company (see
`lighthouse/prompts/website_signal_prompt.py`) and used public web search
plus a page fetch to answer yes/no questions about what's visibly on each
company's site, plus a search for public rating/review/social info. That
raw output is stored as-is in `lighthouse/data/raw/`. See
`docs/lighthouse/Decision_Log.md` for why this approach was chosen for the
POC and what changes for Phase 2 automation.

**Everything downstream of collection is deterministic.** Scores,
opportunity rankings, and journey analysis are plain Python functions of
the collected facts — rerunning the pipeline on the same raw data always
produces the same output.

## Known Phase 1 limitations

- No Google Places/Yelp API key configured, so `rating`/`review_count` are
  best-effort from public search snippets and are `null` where not
  confidently confirmed — treated as 0 in scoring rather than guessed.
- Review text is limited to whatever public snippets a search surfaces;
  there is no full review corpus, so review intelligence is best-effort
  and explicitly marked as such when a company has too little text
  (`review_intelligence.has_sufficient_review_text`).
- 20 companies is a validation sample, not a statistically representative
  one — see `Backlog.md` for scale-up plans.
