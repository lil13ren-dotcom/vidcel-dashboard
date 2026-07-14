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
