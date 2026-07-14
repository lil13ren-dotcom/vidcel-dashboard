# Project Lighthouse — Architecture

## Design principles

1. **Collection and analysis are separate packages.** `lighthouse/scrapers`
   only ever produces `RawCompany` records (see
   `lighthouse/schemas/company_raw.schema.json`). `lighthouse/analysis`
   only ever consumes them. Neither imports the other's internals. This
   means Phase 2's automated collector can replace Phase 1's agent-assisted
   collection without touching a single scoring rule.
2. **AI prompts are separate from business logic.** The one place an LLM
   is used is `lighthouse/prompts/website_signal_prompt.py`, and its job is
   narrow: answer fixed yes/no factual questions about a page ("is there a
   quote form?"). It is never asked to score, rank, or judge. All scoring
   math lives in `lighthouse/analysis/scoring.py` as plain arithmetic.
3. **Every score is rule-based and reproducible.** Given the same
   `RawCompany` input, `scoring.py` always returns the same numbers. There
   is no sampling, no temperature, no prompt in the scoring path.
4. **Outputs are a separate concern from analysis.** `lighthouse/outputs`
   only formats already-computed `ScoredCompany` objects into CSV/Markdown.

## Data flow (Phase 1)

```
Research agent (WebSearch + WebFetch, fixed rubric)
        │
        ▼
lighthouse/data/raw/{industry}_raw.json   (RawCompany[])
        │
        ▼
lighthouse/pipeline.py
        │
        ├─▶ analysis/scoring.py            → 7 scores per company
        ├─▶ analysis/customer_journey.py   → builders/killers/missing per funnel step
        ├─▶ analysis/review_intelligence.py→ top customer words, trust-word hits
        ├─▶ analysis/website_comparison.py → high-opportunity language gaps
        └─▶ analysis/opportunity_engine.py → top-5 ranked opportunities
        │
        ▼
outputs/csv_writer.py, outputs/md_writer.py
        │
        ▼
lighthouse/data/output/{companies.csv, company_scores.csv, opportunities.csv,
                        industry_summary.md, company_reports/*.md}
```

## Scoring model

Seven 0-100 scores, each a pure function of collected facts
(`lighthouse/analysis/scoring.py`):

| Score | What it measures | Formula shape |
|---|---|---|
| Google Score | Legitimacy/demand | 70% rating (of 5★) + 30% review volume (capped at 200) |
| Website Score | Core conversion/trust infrastructure | % present of 12 core signals |
| Trust Score | The brief's 5 evidence types + review credibility | average of 5 signal-presence + 1 review-quality component |
| Proof Score | Portfolio/case studies/before-after/testimonials/photos/videos | % present of 6 signals |
| Social Score | Social presence, weighted toward video platforms | FB 20 + IG 20 + YouTube 30 + TikTok 30 |
| Video Score | Existing use of video as a trust asset | on-site videos 40 + YouTube 30 + TikTok 30 |
| **Overall Opportunity Score** | The sales-priority number | `100 × demand × gap`, where `demand` = Google Score / 100 and `gap` = `1 − average(other 5 scores)/100` |

The Overall Opportunity Score formula is the crux of the whole POC: a
company needs **both** proven demand (people already trust and hire them)
**and** a real digital gap (their online presence undersells that trust)
to be a good outbound target. Either alone is not enough — no demand means
there may be no real business to sell into; no gap means there's nothing
to improve.

## Opportunity engine

A fixed catalog of 14 rules in `analysis/opportunity_engine.py`. Each rule
is `(trigger condition on RawCompany) -> (title, reason, impact,
difficulty, AI automation potential, suggested product, outreach angle)`.
Per company, all triggered rules are ranked by `impact_weight /
difficulty_weight` and the top 5 are kept. Nothing here is generated
per-company by an LLM — the same missing signal always produces the same
opportunity text, with only the company name interpolated into the
outreach angle.

## Why the collection stage looks the way it does in Phase 1

There is no live scraper class today. Phase 1 explicitly optimizes for
validating the *methodology* (would this scoring/opportunity model surface
the right calls?) over building scraping infrastructure, per the project
brief. See `Decision_Log.md` for the reasoning and what changes at scale.

---

## Phase 1.1 — Real Website Acquisition and Data Integrity Gate

Phase 1's collection method (search-snippet reconstruction) is not
decision-grade: it cannot confirm a signal, only infer it from what a
search engine chose to index. Phase 1.1 replaces that with a real,
SSRF-guarded, robots.txt-respecting direct-fetch layer, an evidence model
that can say "we don't know" instead of guessing, and a batch-level gate
that refuses to call a run trustworthy unless enough of it was actually
observed. **v1 is left untouched** (`pipeline.py`,
`lighthouse/data/output/`) — v1.1 is a fully parallel pipeline so the
comparison report is a real diff, not a lossy migration.

### Why search snippets are not decision-grade

A search result confirms "this word appeared somewhere Google indexed
for this domain." It does not confirm the word is still there, where it
is, or whether the *absence* of a matching snippet means the page lacks
the feature or just wasn't the top match for that query. Phase 1's own
data proved this: `mobile_friendly`, `before_after`, and
`customer_photos` came back `false` for all 20 companies — a 0/20 hit
rate that is itself evidence the method structurally cannot confirm
render-dependent signals, not that 20 real businesses all lack them.

### Data flow (Phase 1.1)

```
lighthouse/data/raw/{industry}_raw.json       (v1 companies — id/website/rating/etc, reused as-is)
        │
        ▼
lighthouse/scrapers/acquisition_pipeline.py
        │
        ├─▶ website_fetcher.py (Tier 1: httpx)     — real fetch, SSRF-guarded, robots.txt, retries
        ├─▶ browser_fetcher.py (Tier 2: Playwright) — only if Tier 1 result looks JS-dependent, opt-in
        ├─▶ crawl.py                                — up to 5 same-domain pages, keyword-scoped
        ├─▶ signal_extractor.py                     — HTML -> EvidenceSignals (deterministic)
        └─▶ artifact_store.py                       — raw HTML + manifest.json per company (audit trail)
        │
        ▼
RawCompanyV2[]  (website_signals: EvidenceSignals, acquisition: AcquisitionMetadata)
        │
        ▼
lighthouse/pipeline_v2.py
        │
        ├─▶ analysis/scoring_v2.py           → observed_score + coverage_ratio per category
        ├─▶ analysis/integrity_gate.py        → batch-level DECISION_GRADE / NOT_DECISION_GRADE
        ├─▶ analysis/customer_journey_v2.py   → same funnel, status-aware wording
        ├─▶ analysis/opportunity_engine_v2.py → same catalog, confirmed vs. unverified reasons
        └─▶ (review_intelligence.py, website_comparison.py — reused unmodified from v1 via
             a Protocol match on review_snippets/homepage_text_excerpt)
        │
        ▼
outputs/csv_writer_v2.py, outputs/md_writer_v2.py, outputs/comparison_writer.py
        │
        ▼
lighthouse/data/output_v1_1/{companies.csv, company_scores.csv, opportunities.csv,
                             industry_summary.md, company_reports/*.md, data_integrity_gate.json}
lighthouse/data/output/{acquisition_comparison.md, acquisition_comparison.csv}   (v1 vs v1.1 diff)
lighthouse/data/raw/websites/<company_id>/{manifest.json, *.html.gz, extracted_text.json}
```

### Direct-fetch architecture (`lighthouse/scrapers/website_fetcher.py`)

Tier 1 is a real `httpx.Client`, `follow_redirects=False` by design —
redirects are followed *manually*, one hop at a time, re-running the full
SSRF check on each `Location` header before connecting. This is the
actual SSRF-via-redirect defense: a URL can look completely safe and
still redirect somewhere internal, and `httpx`'s built-in redirect
following would connect before any of our code sees the new host.

Per fetch: DNS-resolve and reject private/loopback/link-local/reserved/
CGNAT ranges (`ssrf_guard.py`, both IPv4 and IPv6) → check robots.txt
(`robots.py`, cached per domain for the run, missing robots.txt defaults
to allow) → per-domain rate limit (`RateLimiter`, thread-safe
reserve-then-sleep) → stream the response with a byte cap (aborts mid-
download rather than buffering an oversized body) → classify the outcome
into one `FetchStatus` (`SUCCESS`, `HTTP_ERROR`, `TIMEOUT`, `DNS_ERROR`,
`SSRF_BLOCKED`, `ROBOTS_BLOCKED`, `TOO_LARGE`, `INVALID_CONTENT_TYPE`,
`TOO_MANY_REDIRECTS`, `NETWORK_ERROR`, `POLICY_BLOCKED`,
`UNKNOWN_ERROR`). Only `TIMEOUT`/`NETWORK_ERROR` are retried (bounded,
exponential backoff + jitter); everything else — including
`POLICY_BLOCKED`, this sandbox's actual failure mode — is a stable
outcome that retrying would only waste time on.

### Fallback behavior (`lighthouse/scrapers/browser_fetcher.py`)

Tier 2 (Playwright/Chromium) is **off by default**
(`enable_playwright_fallback=False`) and, when enabled, is only invoked
after Tier 1 has already fetched the domain successfully and the result
looks JS-dependent (near-empty body + a client-rendering root div). It
still runs the same SSRF pre-check on the initial URL before navigating,
though this is a documented, narrower guarantee than Tier 1's — Playwright
follows redirects internally, so Tier 2 must never be pointed at a domain
Tier 1 hasn't already vetted. No login, no CAPTCHA solving, no stealth/
evasion tooling; it loads the page and reads what a normal visitor sees,
with media/font requests blocked since only text/structure is needed.

### Compliance controls

robots.txt is honored (fail-open only when robots.txt itself is
unreachable, per crawler convention), SSRF guarding covers both fetch
tiers, crawl scope is capped at 5 same-domain pages selected by a fixed
keyword list (never a site-wide crawl), there is no authentication, no
form submission, and no scraping of restricted social platforms — social
links are only ever read from `<a href>` values already present in fetched
public HTML. No component from an "AI Lead OS" repository was reused —
none was accessible in this session's scope (see `Backlog.md`); every
control here (`ssrf_guard.py`, `robots.py`, byte caps, rate limiting) was
implemented fresh using only the standard library and `httpx`.

### Evidence model (`lighthouse/models.py`)

`EvidenceStatus` is `PRESENT | ABSENT | UNKNOWN | BLOCKED | ERROR |
NOT_APPLICABLE`. `Evidence` carries `status`, `value`, `confidence`,
`source_url`, `evidence_text`, `collected_at`, `collector_version` — every
fact is traceable to what page produced it and when. `EvidenceSignals`
wraps a `dict[str, Evidence]` with `is_present`/`is_absent`/`is_confirmed`
helpers so `analysis/` code reads naturally without touching `.status`
directly. The load-bearing rule, enforced in `signal_extractor.py` and
checked by the Data Integrity Gate: **`ABSENT` is only produced when a
page targeted at that signal's topic was actually, successfully
fetched.** A failed fetch — for any reason — produces `UNKNOWN`, never
`ABSENT`. Image-dependent signals (`before_after`, `customer_photos`) go
further: even on a successful fetch, textual/structural evidence alone
only ever produces a low-confidence (`0.4`) `PRESENT`, explicitly
"candidate, needs visual review" — no path in this codebase claims full
visual confirmation from text.

### Scoring coverage semantics (`lighthouse/analysis/scoring_v2.py`)

Every category score is now a pair: `observed_score` (computed only from
*confirmed* — `PRESENT` or `ABSENT` — signals) and `coverage_ratio`
(confirmed signals ÷ total signals in that category). `decision_grade_score`
returns the observed score only when coverage clears a threshold (60% per
category, 50% company-wide); below that, the category contributes nothing
to `overall_opportunity_score`, which itself becomes `None` — not a
number, not zero — when too few categories qualify. `ScoredCompanyV2`
publishes `overall_opportunity_score`, `data_coverage_ratio`,
`data_confidence`, `is_decision_grade`, and `decision_grade_reason` side by
side, so a `None` or a low-coverage number is never silently mistaken for
a confident one. Industries are never ranked in `industry_summary.md`
using companies whose coverage didn't clear the bar.

### Data Integrity Gate (`lighthouse/analysis/integrity_gate.py`)

A batch-level judgment, separate from each company's own
`is_decision_grade`. Checks: homepage direct-fetch success rate ≥ 85%,
"at least one relevant page beyond the homepage" rate ≥ 75%, zero
acquisition-failure-represented-as-`ABSENT` violations, complete evidence
coverage (every signal key has *some* status, even if `UNKNOWN`),
deterministic rerun (`score_company()` called twice on identical input
produces identical output), and every scored row carries a confidence
field. `run_status` is `DECISION_GRADE` only if every check passes;
otherwise `NOT_DECISION_GRADE`, and `industry_summary.md` /
`acquisition_comparison.md` say so prominently rather than presenting
numbers that look authoritative.

### Known limitations (Phase 1.1)

- Ratings/review counts are still not sourced from a real API — same gap
  as Phase 1, tracked in `Backlog.md`.
- This sandbox cannot reach arbitrary external hosts at all (see
  `Decision_Log.md`, 2026-07-14), so the 20-company rerun in this
  repository's `lighthouse/data/output_v1_1/` is genuinely
  `NOT_DECISION_GRADE` — 0% live fetch success, not a bug. A real run
  requires `lighthouse/live_e2e.py` (or `pipeline_v2.py` directly) from an
  internet-enabled environment; see `docs/lighthouse/README.md`.
- Tier 2 (Playwright) is unit-tested against a local `file://` fixture
  (proves the launch/navigate/extract path works) but has not been
  exercised against a real JS-heavy site anywhere in this repository's
  history yet.
- Image-dependent signals remain textual-heuristic-only; true visual
  confirmation needs a human or a vision-model review step, out of scope
  here.

---

## Future Phases — design only, NOT implemented

The brief asks for architecture, not code, for phases 2-5. These are
sketches to de-risk Phase 1's design (make sure nothing here blocks them),
not commitments.

### Phase 2 — Proposal Generator

- **Input:** a `ScoredCompany` (already produced by Phase 1).
- **New module:** `lighthouse/proposal/` — takes the top opportunities and
  the suggested product mapping and renders a client-facing PDF/deck.
- **Key design constraint:** the proposal generator must consume
  `ScoredCompany` only — it should never need to re-run analysis or touch
  raw collection data, keeping the same collection/analysis/output
  separation.
- **New AI surface:** a proposal-copy prompt (separate prompts module,
  e.g. `lighthouse/prompts/proposal_copy_prompt.py`) that turns a fixed
  opportunity + reason into 2-3 paragraphs of proposal narrative. This is
  the first place free-text generation enters the pipeline, and it should
  stay confined to prose generation, not scoring.

### Phase 3 — Personalized Landing Pages

- **New module:** `lighthouse/landing_pages/` — a template renderer that
  takes a `ScoredCompany` + a chosen opportunity (e.g. "Before/After
  Gallery") and produces a single static page personalized with the
  company's name, city, and the specific gap identified, to be sent as
  part of outbound ("here's what your before/after gallery could look
  like").
- **Key design constraint:** must reuse `SUGGESTED_PRODUCT` /
  `OUTREACH_ANGLE` from `opportunity_engine.py` rather than re-deriving
  messaging, so a company's outbound story is consistent across every
  channel (report, proposal, landing page, email).

### Phase 4 — Outbound Email Engine

- **New module:** `lighthouse/outbound/` — sequencing logic (multi-touch
  cadence) that reads `opportunities.csv` and `company_scores.csv` sorted
  by Overall Opportunity Score, and emits templated email drafts (subject
  + body) referencing the specific gap and suggested product.
- **Key design constraint:** must be rate/consent aware and log every send
  (audit trail) since this is the first phase that reaches out to a real
  person — this module owns compliance concerns (CAN-SPAM headers,
  suppression lists), not `analysis/`.

### Phase 5 — Video Generation

- **New module:** `lighthouse/video/` — given a company + opportunity
  (e.g. "Customer Trust Video"), generates a short marketing video draft
  using the company's own collected proof assets (photos, testimonial
  text) as source material.
- **Key design constraint:** this is the eventual product the whole
  pipeline sells into, but it depends on Phase 1's `Proof Score`/`Video
  Score` gap detection to decide *which* companies and *which* opportunity
  type warrant a generated video in the first place — Phase 5 should
  never run standalone against a company Phase 1 hasn't scored.
