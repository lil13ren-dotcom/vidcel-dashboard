# Project Lighthouse — Backlog

## Phase 1.1 follow-ups (the acquisition layer exists now — this is what's left)

- [ ] **P0 — Run the real live E2E from an internet-enabled environment.**
      The acquisition layer (`lighthouse/scrapers/website_fetcher.py` +
      friends) is built, unit-tested (81 tests, fixture-based, no live
      network needed), and `mypy --strict`-clean, but this sandbox cannot
      reach arbitrary external hosts at all (confirmed via `curl` control
      tests — see `Decision_Log.md`, 2026-07-14). The 20-company rerun in
      `lighthouse/data/output_v1_1/` is genuinely `NOT_DECISION_GRADE` as
      a result (0% homepage fetch success). Run
      `python3 -m lighthouse.live_e2e --run` (or
      `python3 -m lighthouse.pipeline_v2` for the full 20) from a normal
      internet-enabled machine to get the first real decision-grade
      result and a real `acquisition_comparison.md`.
- [ ] Exercise Tier 2 (Playwright) against a real JS-heavy site once
      network access is available — it's currently only proven against a
      local `file://` fixture.
- [ ] Integrate a real ratings/reviews source (Google Places API or Yelp
      Fusion API) so `rating`/`review_count`/`google_maps_url` are
      confirmed data. Out of scope for Phase 1.1 (which targeted website
      acquisition specifically) but still the other half of
      `overall_opportunity_score`'s demand term.
- [ ] Add a vision-model or human review pass for `before_after` /
      `customer_photos` — currently capped at 0.4 confidence from text
      heuristics alone by design (`signal_extractor.py`), never claims
      full visual confirmation.
- [ ] Consider widening the crawl beyond 5 pages, or scoping pages
      per-signal more precisely, once real fetch data shows which
      signals are still landing as `UNKNOWN` most often.

## Scale-up (still same methodology, more companies)

- [ ] Re-run against 100-200 companies per industry once a real (network-
      enabled) Phase 1.1 run validates the acquisition method, for
      statistically meaningful `industry_summary.md` averages.
- [ ] Add more industries beyond Roofing/HVAC/Remodeling (e.g. plumbing,
      landscaping, electrical) using the same `RawCompanyV2` schema.

## Engine improvements

- [x] Unit tests for the scoring/opportunity/gate engine — done in Phase
      1.1 (`lighthouse/tests/`, 81 tests, `pytest --cov` ~83% overall,
      90-100% on the security/evidence-critical modules).
- [ ] Same test coverage treatment for the v1 (search-snippet) modules —
      `outputs/csv_writer.py`/`md_writer.py` are currently only exercised
      via the full `python -m lighthouse.pipeline` integration run, not
      unit tests.
- [ ] Revisit the `mypy --strict` vs. default split for `lighthouse/tests/`
      (see `pyproject.toml`, `Decision_Log.md`) if a future contributor
      wants full strict coverage there too — the gap is pytest/respx
      fixture annotation boilerplate, not a code-quality issue.

## Future phases (design captured in Architecture.md, not started)

- [ ] Phase 2 — Proposal Generator
- [ ] Phase 3 — Personalized Landing Pages
- [ ] Phase 4 — Outbound Email Engine
- [ ] Phase 5 — Video Generation
