# Project Lighthouse — Backlog

## Phase 1 follow-ups (same scope, better data)

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
