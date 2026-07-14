# Project Lighthouse — Backlog

## Phase 1 follow-ups (same scope, better data)

- [ ] **P0 — Restore direct page-fetch access.** `WebFetch` returned 403
      for every destination during this POC's actual data collection run
      (confirmed environment-level egress block, not per-site — see
      `Decision_Log.md`, 2026-07-14). As a direct result, `mobile_friendly`,
      `before_after`, and `customer_photos` are unverified (not
      confirmed-false) for all 20 companies. Fixing this is the single
      highest-leverage change before running this pipeline on real
      outbound targets — right now those three signals can't be trusted
      at all.
- [ ] Integrate a real ratings/reviews source (Google Places API or Yelp
      Fusion API) so `rating`/`review_count`/`google_maps_url` are
      confirmed data, not best-effort search snippets. Highest-leverage
      fix — Google Score and therefore Overall Opportunity Score both
      depend directly on this.
- [ ] Increase review text volume per company (currently limited to
      whatever a web search surfaces) so `review_intelligence.py` and
      `website_comparison.py` clear `has_sufficient_review_text` more
      often instead of being suppressed.
- [ ] Add a second page fetch (e.g. `/gallery`, `/reviews`) per company
      where the homepage doesn't settle a signal, instead of relying on
      homepage-only detection.
- [ ] Spot-check a sample of the 20 collected records by hand against the
      live sites to measure rubric accuracy before trusting it at scale.

## Scale-up (still Phase 1 methodology, more companies)

- [ ] Re-run the same pipeline against 100-200 companies per industry
      once the methodology is validated, to get statistically meaningful
      `industry_summary.md` averages instead of a 5-10 company sample.
- [ ] Add more industries beyond Roofing/HVAC/Remodeling (e.g. plumbing,
      landscaping, electrical) using the exact same `RawCompany` schema.

## Engine improvements

- [ ] Unit tests for `analysis/scoring.py` and `analysis/opportunity_engine.py`
      against fixed fixtures (deterministic functions are cheap to test
      and should be locked down before Phase 2 builds on top of them).
- [ ] Consider a confidence field per collected fact (e.g. "rating
      confirmed via knowledge panel" vs "confirmed via 3rd-party
      aggregator") if data quality varies enough to matter downstream.

## Future phases (design captured in Architecture.md, not started)

- [ ] Phase 2 — Proposal Generator
- [ ] Phase 3 — Personalized Landing Pages
- [ ] Phase 4 — Outbound Email Engine
- [ ] Phase 5 — Video Generation
