# Project Lighthouse — Decision Log

## 2026-07-13 — Phase 1 POC build

**Decision:** Scope Phase 1 to exactly 20 companies (10 Roofing, 5 HVAC, 5
Remodeling) across different US cities, per the brief.
**Why:** The brief is explicit that Phase 1 validates *methodology*, not
scale. A small, hand-checkable sample lets us sanity-check whether the
scoring/opportunity model actually points at defensible sales targets
before investing in scraping infrastructure.

**Decision:** No live scraper/browser-automation class in Phase 1.
Collection is agent-assisted: an LLM research agent uses web search + a
single page fetch per company, judged against one fixed rubric
(`lighthouse/prompts/website_signal_prompt.py`) so every company is
checked against the same yes/no questions.
**Why:** Building a resilient scraper (anti-bot handling, JS rendering,
rate limiting) is real infrastructure work with its own failure modes,
and the brief explicitly says "Do NOT optimize for scraping." A fixed
rubric run through a page-fetch tool gets the same factual yes/no signal
extraction with a fraction of the engineering cost, and the collection
interface (`scrapers/collector_interface.py`) is designed so a real
scraper can be dropped in later without touching analysis.

**Decision:** All scores are plain arithmetic over collected booleans/
numbers (`analysis/scoring.py`); no LLM is involved in scoring.
**Why:** The brief explicitly requires "All scores must be rule-based.
Avoid subjective AI scoring." Reproducibility also matters for a sales
tool — a rep needs to be able to explain *why* a lead scored the way it
did, not "the model said so."

**Decision:** Overall Opportunity Score = `demand × gap`, not just
`100 − average(scores)`.
**Why:** A pure "weakest digital presence wins" formula would rank a
non-existent or dead business above a thriving one with a mediocre
website — the opposite of what a sales team wants. Multiplying by a
demand term (derived from real Google rating/review volume) means a
company must first prove it's a real, busy business before its gaps
count as opportunity. This directly encodes the brief's framing: "biggest
digital trust gaps *and* highest outbound sales opportunity" — both
halves matter, so it's a product (AND), not a sum (OR).

**Decision:** Missing `rating`/`review_count` scores as 0 in Google Score
(and downstream demand), not imputed or skipped.
**Why:** We deliberately did not fabricate numbers we couldn't confirm
via public search (see collection rubric). Treating "unconfirmed" the
same as "bad" is a conservative default: it never overstates a company's
legitimacy, and it's visible in `industry_summary.md` if it distorts a
result, since the raw record still shows `null` rather than a guessed
number.

**Decision:** Review intelligence and website-comparison gaps are simple
substring/frequency matching over review snippets and homepage excerpts,
not a sentiment or summarization model, and are suppressed entirely below
a minimum text length (`has_sufficient_review_text`).
**Why:** Same rule-based requirement as scoring — customer language
mentioned in a report should be traceable back to actual review text.
Suppressing the section rather than guessing at customer language when
we only found a couple of search snippets avoids fabricating "customer
sentiment" that isn't backed by real text.

**Decision:** Opportunity catalog (14 fixed rules) instead of per-company
LLM-generated recommendations.
**Why:** The brief's "Top 5 opportunities" section wants each
recommendation to have Reason/Impact/Difficulty/AI-Automation-Potential —
a fixed, auditable rubric produces the same recommendation for the same
gap every time, which is what makes `opportunities.csv` usable as a
sales-priority list rather than a set of one-off blurbs.

**Decision:** Suggested product / outreach angle are a fixed
title-keyed mapping (`SUGGESTED_PRODUCT`, `OUTREACH_ANGLE` in
`opportunity_engine.py`) with the company name interpolated in, not
freely generated per company.
**Why:** Keeps `company_report.md` consistent with `opportunities.csv`
(same opportunity always maps to the same product/angle) and keeps the
one bit of "voice" in the pipeline template-controlled rather than
open-ended generation, matching the brief's instruction to keep AI
prompts separate from business logic.
