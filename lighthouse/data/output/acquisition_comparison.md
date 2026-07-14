# Acquisition Method Comparison — Phase 1 (search snippets) vs Phase 1.1 (direct fetch)

**Run status: NOT_DECISION_GRADE**

- Previous acquisition method: LLM research agent + `WebSearch` snippet reconstruction (no direct page fetch)
- New acquisition method: `lighthouse/scrapers/website_fetcher.py` — direct `httpx` fetch (+ optional Playwright fallback), SSRF-guarded, robots.txt-respecting, evidence-recorded
- Homepage direct-fetch success rate this run: **0%** (20 companies)

## Why this run cannot validate or invalidate any Phase 1 business conclusion

Direct page fetching succeeded for **0** of the 20 companies. This is not a bug in the fetcher — every fetch failed the same way, at the same layer, including for neutral control domains (`example.com`) with no relationship to any company in this dataset. The runtime environment this run executed in blocks outbound HTTPS to arbitrary hosts at the network policy level (confirmed via `curl` returning `403` from the egress proxy even when the proxy was explicitly bypassed and the destination IP was dialed directly — see `docs/lighthouse/Decision_Log.md`, 2026-07-14 entries). Every one of the 20 companies below is therefore `BLOCKED`/`ERROR` at the acquisition layer, not `ABSENT` — the pipeline correctly distinguished 'we couldn't check' from 'we checked and it's not there,' which was this phase's core requirement, but that means there is no new website evidence to compare against Phase 1 in this run.

**No earlier conclusion is confirmed. No earlier conclusion is invalidated.** The Phase 1 results (`lighthouse/data/output/`) remain exactly what they were: search-snippet-derived, not decision-grade, and now formally superseded pending a real run of this same pipeline from an internet-enabled environment (see the Live E2E runner in `docs/lighthouse/README.md`).

Field-transition counts below are all zero for the same reason — nothing could be re-observed to transition from false, so this table records the code path, not a result:

| Transition | Count |
|---|---|
| false (v1) → present (v2, confirmed) | 0 |
| false (v1) → absent (v2, confirmed) | 0 |
| false (v1) → unverified (v2: unknown/blocked/error) | 219 |
| true (v1) → present (v2, confirmed) | 0 |
| true (v1) → absent (v2, confirmed) | 0 |
| unchanged / not comparable | 141 |

## Score changes

| Company | v1 Opportunity Score | v2 Opportunity Score | v2 Decision-Grade |
|---|---|---|---|
| Carter Comfort Systems | 67.7 | n/a | False |
| River City Heating & Air | 66.5 | n/a | False |
| Advantage Air Mechanical | 44.7 | n/a | False |
| Harker Heating & Cooling | 61.2 | n/a | False |
| Horizon Homes | 45.3 | n/a | False |
| Catalyst Construction & Kitchen Remodeling | 0.0 | n/a | False |
| New Creations Custom Kitchen and Bath | 0.0 | n/a | False |
| Carolina Home Remodeling | 0.0 | n/a | False |
| Mark Hammer Construction LTD | 0.0 | n/a | False |
| Crystal Kitchen + Bath | 59.4 | n/a | False |
| Kidd Roofing | 71.7 | n/a | False |
| Bold Brothers Roofing | 62.6 | n/a | False |
| Adamson Roofing Company | 66.1 | n/a | False |
| Gibson Roofing | 59.9 | n/a | False |
| Best Roofing Now | 62.3 | n/a | False |
| Owl Roofing | 47.8 | n/a | False |
| Lyons Roofing | 64.2 | n/a | False |
| Bill Ragan Roofing Company | 76.6 | n/a | False |
| Ace Roofing | 0.0 | n/a | False |
| Straight Line Roofing & Construction | 71.7 | n/a | False |

## Industry leadership

- Leading industry under v1 (search snippets): **Roofing**
- Leading industry under v2 (direct fetch, decision-grade companies only): **(undetermined — no scorable companies)**
- v2 leadership is undetermined this run (zero decision-grade companies) — cannot say whether Roofing remains the leading industry until a real fetch run completes.

## Unresolved limitations

- Ratings/review counts are still not sourced from a real API (Google Places/Yelp) in either version — tracked separately in `docs/lighthouse/Backlog.md`.
- Image-dependent signals (`before_after`, `customer_photos`) are only ever confirmed to `PRESENT` on strong textual/structural evidence; true visual confirmation still requires human or vision-model review, which is out of scope for this phase.
- Tier 2 (Playwright) fallback is implemented and unit-tested against a local fixture, but has not been exercised against a real JS-heavy site in this environment.
- **Blocking:** this sandbox cannot reach arbitrary external websites at all. A real run requires the Live E2E runner described in `docs/lighthouse/README.md`, executed from an internet-enabled environment.
