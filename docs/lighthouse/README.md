# Project Lighthouse — Business Intelligence Engine

A market-research system that identifies which home-services industries
have the biggest **digital trust gaps**, and therefore the strongest
outbound sales opportunity for Vidcel.

This is **not** a lead-gen tool and **not** a video generator. It answers one
question, repeatably, for any company it looks at:

> If I owned this company, what would I improve first to increase customer trust?

## What's in this repo

- **Phase 1** (`lighthouse/pipeline.py`): the original 20-company POC,
  collected via LLM-agent + search-snippet reconstruction. Frozen as the
  "before" baseline — outputs live in `lighthouse/data/output/`.
- **Phase 1.1** (`lighthouse/pipeline_v2.py`): a real, direct-fetch
  acquisition layer (SSRF-guarded `httpx` + optional Playwright fallback),
  an evidence model that distinguishes "confirmed absent" from "couldn't
  check," and a Data Integrity Gate that refuses to call a run trustworthy
  unless enough of it was actually observed. Re-runs the *same* 20
  companies for a fair before/after comparison. Outputs live in
  `lighthouse/data/output_v1_1/`; the diff is
  `lighthouse/data/output/acquisition_comparison.{md,csv}`.

## Layout

```
lighthouse/
  schemas/company_raw.schema.json   contract between collection and analysis (v1)
  models.py                         shared data model — RawCompany/ScoredCompany (v1) and
                                     RawCompanyV2/ScoredCompanyV2/Evidence/EvidenceSignals (v1.1)
  prompts/website_signal_prompt.py  Phase 1's LLM prompt (fact extraction, not scoring; historical)

  scrapers/                         Phase 1.1 acquisition layer
    website_fetcher.py               Tier 1: httpx, SSRF-guarded, robots.txt, retries/backoff
    browser_fetcher.py               Tier 2: Playwright fallback, off by default
    ssrf_guard.py                    private/loopback/link-local/reserved IP + scheme blocking
    robots.py                        robots.txt caching + enforcement
    crawl.py                         controlled same-domain, keyword-scoped link discovery
    signal_extractor.py              deterministic HTML -> EvidenceSignals (replaces the LLM prompt)
    artifact_store.py                raw HTML + manifest.json per company (audit trail)
    acquisition_pipeline.py          orchestrates the above; also a standalone CLI
    collector_interface.py           v1 collection contract + JSON loader
    config.py                        FetcherConfig (timeouts, retries, crawl caps, ...)

  analysis/
    scoring.py / scoring_v2.py               rule-based scores (v1: plain; v1.1: coverage-aware)
    integrity_gate.py                        Phase 1.1 batch-level Data Integrity Gate
    review_intelligence.py                   repeated customer language (shared v1/v1.1)
    website_comparison.py                    customer vs. website language gaps (shared v1/v1.1)
    customer_journey.py / customer_journey_v2.py
    opportunity_engine.py / opportunity_engine_v2.py

  outputs/
    csv_writer.py / csv_writer_v2.py
    md_writer.py / md_writer_v2.py
    comparison_writer.py             acquisition_comparison.{md,csv}

  data/
    raw/                        v1 collected input (frozen)
    raw/websites/<id>/          v1.1 raw fetch artifacts (manifest.json, *.html.gz)
    raw_v1_1/                   v1.1 RawCompanyV2 JSON, one file per industry
    output/                     v1 deliverables (frozen) + acquisition_comparison.{md,csv}
    output_v1_1/                v1.1 deliverables
    live_e2e_targets.json       2-company smoke-test target list (see Live E2E below)

  pipeline.py                   v1 orchestrator: `python3 -m lighthouse.pipeline`
  pipeline_v2.py                v1.1 orchestrator: `python3 -m lighthouse.pipeline_v2`
  live_e2e.py                   small, safe live-network runner — see "Live E2E" below
  tests/                        81 pytest tests, fixture-based, no live network required

docs/lighthouse/
  Architecture.md                  system design (v1 + v1.1) + Phase 2-5 designs (not implemented)
  Decision_Log.md                  why each collection/scoring/gate choice was made
  Backlog.md                       follow-up work
```

## Running Phase 1 (v1, frozen baseline)

```
cd vidcel-dashboard
python3 -m lighthouse.pipeline
```

Reads `lighthouse/data/raw/{roofing,hvac,remodeling}_raw.json`, writes to
`lighthouse/data/output/`.

## Running Phase 1.1 (v1.1, real acquisition)

```
cd vidcel-dashboard
pip install -r lighthouse/requirements.txt
python3 -m lighthouse.pipeline_v2
```

Re-acquires the same 20 companies via direct fetch, scores them with
coverage-aware semantics, runs the Data Integrity Gate, and writes to
`lighthouse/data/output_v1_1/` plus
`lighthouse/data/output/acquisition_comparison.{md,csv}`.

**In a network-restricted environment this will correctly report
`NOT_DECISION_GRADE`** — see "Known limitations" below. That is the
pipeline working as designed, not a bug.

## Live E2E (run this from an environment with real internet access)

`lighthouse/live_e2e.py` is a small, safe runner against exactly 2 real
targets (`lighthouse/data/live_e2e_targets.json` — one US company already
in the Lighthouse dataset, one Japanese site used purely as a locale/
encoding smoke test; swap either for any two real URLs you want to check).
Conservative timeouts/retries, a real identifying User-Agent, robots.txt
respected, no CAPTCHA bypass, no proxy circumvention, no anti-bot evasion,
no authentication. Exit code is `0` only if the Data Integrity Gate
passes, so it's safe to wire into CI once network access exists.

```
cd vidcel-dashboard
pip install -r lighthouse/requirements.txt

# 1. Preflight — validates config/targets, makes zero network calls.
python3 -m lighthouse.live_e2e --preflight

# 2. Live E2E — the actual fetch.
python3 -m lighthouse.live_e2e --run

# 3. Artifact inspection.
ls lighthouse/data/live_e2e_output/artifacts/
cat lighthouse/data/live_e2e_output/data_integrity_gate.json
cat lighthouse/data/live_e2e_output/company_scores.csv

# 4. Rerun / idempotency check.
python3 -m lighthouse.live_e2e --run --output-dir lighthouse/data/live_e2e_output_rerun
diff lighthouse/data/live_e2e_output/company_scores.csv \
     lighthouse/data/live_e2e_output_rerun/company_scores.csv
```

## Running the offline quality gate

Everything below runs fully offline (no network) and was run and passed
in this repository before every commit:

```
cd vidcel-dashboard
pip install -r lighthouse/requirements.txt pytest-cov

ruff check lighthouse/
ruff format --check lighthouse/
mypy --strict lighthouse/scrapers lighthouse/analysis lighthouse/outputs \
     lighthouse/models.py lighthouse/pipeline.py lighthouse/pipeline_v2.py lighthouse/prompts
mypy lighthouse/tests   # test files: default mypy, not --strict — see Decision_Log.md
python3 -m pytest lighthouse/tests/ --cov=lighthouse --cov-report=term-missing
```

## How the data was collected

**Phase 1:** no automated scraper. An LLM research agent used a fixed,
identical rubric per company (`lighthouse/prompts/website_signal_prompt.py`)
plus public web search to answer yes/no questions about each company's
site, and stored the result as-is in `lighthouse/data/raw/`.

**Phase 1.1:** a real fetch. `lighthouse/scrapers/website_fetcher.py`
connects directly to each company's website (SSRF-guarded, robots.txt-
respecting), `signal_extractor.py` answers the same yes/no questions
*deterministically* from the actual HTML (regex/structure heuristics, no
LLM), and every fact carries a `status` (`PRESENT`/`ABSENT`/`UNKNOWN`/
`BLOCKED`/`ERROR`) plus a `source_url` and `confidence` — see
`docs/lighthouse/Architecture.md` for the full evidence model.

**Everything downstream of collection is deterministic in both phases.**
Scores, opportunity rankings, and journey analysis are plain Python
functions of the collected facts — rerunning either pipeline on the same
raw data always produces the same output (this is itself a Data Integrity
Gate check in Phase 1.1).

## Known limitations

**Phase 1:**
- No Google Places/Yelp API key, so `rating`/`review_count` are best-
  effort from public search snippets, `null` where not confidently
  confirmed.
- Review text is limited to whatever public snippets a search surfaces.
- 20 companies is a validation sample, not a statistically representative
  one — see `Backlog.md`.

**Phase 1.1:**
- Ratings/review counts are still not sourced from a real API — same gap
  as Phase 1.
- **This repository's own `output_v1_1/` run is `NOT_DECISION_GRADE`
  because the sandbox it was built in cannot reach arbitrary external
  hosts at all** (confirmed via `curl` control tests against neutral
  domains, not specific to any Lighthouse company — see
  `Decision_Log.md`, 2026-07-14). Run `lighthouse/live_e2e.py` or
  `pipeline_v2.py` from a normal internet-enabled environment to get a
  real decision-grade result.
- Image-dependent signals (`before_after`, `customer_photos`) are only
  ever confirmed to `PRESENT` on strong textual/structural evidence
  (capped at 0.4 confidence); true visual confirmation needs a human or
  vision-model review step, out of scope here.
- Tier 2 (Playwright) is unit-tested against a local fixture but hasn't
  been exercised against a real JS-heavy site anywhere in this repo yet.
