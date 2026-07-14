"""Orchestrates real website acquisition for a set of companies.

    python -m lighthouse.scrapers.acquisition_pipeline \\
        --companies lighthouse/data/raw/roofing_raw.json ... \\
        --output-dir lighthouse/data/raw_v1_1 \\
        --artifact-dir lighthouse/data/raw/websites

For each company: fetch the homepage (Tier 1, falling back to Tier 2 only
if configured and the homepage looks JS-dependent), crawl a handful of
same-domain pages the brief cares about, extract evidence-backed signals,
and write both the raw artifacts (for audit) and a RawCompanyV2 record.

This module never decides what a missing page *means* — that's
signal_extractor.py. It only decides what to fetch and in what order.
"""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from lighthouse.models import AcquisitionMetadata, RawCompany, RawCompanyV2, Social
from lighthouse.scrapers.artifact_store import ArtifactStore
from lighthouse.scrapers.config import DEFAULT_CONFIG, FetcherConfig
from lighthouse.scrapers.crawl import discover_links
from lighthouse.scrapers.signal_extractor import (
    extract_homepage_excerpt,
    extract_signals,
    extract_social_links,
)
from lighthouse.scrapers.website_fetcher import (
    FetchResult,
    FetchStatus,
    RateLimiter,
    WebsiteFetcher,
)


def _looks_js_dependent(fetch_result: FetchResult) -> bool:
    """Heuristic used only to decide whether Tier 2 is worth trying: a
    normal server-rendered small-business site has real text content in
    <body>; a client-side-rendered shell typically has a near-empty body
    with a single root div and very little visible text.
    """
    if not fetch_result.ok or not fetch_result.text:
        return False
    body_text_len = len(_strip_tags(fetch_result.text))
    return body_text_len < 200 and (
        'id="root"' in fetch_result.text or 'id="app"' in fetch_result.text
    )


def _strip_tags(html: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", html)


def acquire_company(
    company: RawCompany, fetcher: WebsiteFetcher, config: FetcherConfig
) -> tuple[RawCompanyV2, list[FetchResult]]:
    """Returns (RawCompanyV2, list[FetchResult]) — the caller persists the
    FetchResults as raw artifacts.
    """
    collected_at = datetime.now(timezone.utc).isoformat()
    pages = [fetcher.fetch(company.website)]
    homepage_result = pages[0]

    if homepage_result.ok:
        assert (
            homepage_result.final_url is not None and homepage_result.text is not None
        )  # guaranteed by .ok
        candidates = discover_links(
            homepage_result.final_url,
            homepage_result.text,
            config.max_pages_per_company,
        )
        for candidate in candidates:
            pages.append(fetcher.fetch(candidate.url))
    elif config.enable_playwright_fallback and _looks_js_dependent(homepage_result):
        from lighthouse.scrapers.browser_fetcher import BrowserFetcher

        with BrowserFetcher(config) as browser:
            rendered = browser.fetch(company.website)
        pages = [rendered]
        if rendered.ok:
            assert (
                rendered.final_url is not None and rendered.text is not None
            )  # guaranteed by .ok
            candidates = discover_links(
                rendered.final_url, rendered.text, config.max_pages_per_company
            )
            for candidate in candidates:
                pages.append(fetcher.fetch(candidate.url))

    signals = extract_signals(pages, config.collector_version, collected_at)
    social_found = extract_social_links(pages)
    homepage_excerpt = extract_homepage_excerpt(pages) or None
    pages_fetched = sum(1 for p in pages if p.status == FetchStatus.SUCCESS)

    acquisition = AcquisitionMetadata(
        homepage_status=homepage_result.status.value,
        pages_attempted=len(pages),
        pages_fetched=pages_fetched,
        method_used=pages[0].method if pages_fetched else "none",
        run_at=collected_at,
        collector_version=config.collector_version,
        blocked_reason=None
        if homepage_result.ok
        else (homepage_result.error_message or homepage_result.status.value),
    )

    company_v2 = RawCompanyV2(
        id=company.id,
        industry=company.industry,
        name=company.name,
        website=company.website,
        city=company.city,
        state=company.state,
        website_signals=signals,
        social=Social(**social_found),
        acquisition=acquisition,
        google_maps_url=company.google_maps_url,
        rating=company.rating,
        review_count=company.review_count,
        phone=company.phone,
        email=company.email,
        review_snippets=company.review_snippets,
        homepage_text_excerpt=homepage_excerpt,
        sources=[p.final_url or p.requested_url for p in pages],
    )
    return company_v2, pages


def load_v1_companies(paths: list[str]) -> list[RawCompany]:
    companies: list[RawCompany] = []
    for path in paths:
        with open(path) as f:
            data = json.load(f)
        records = data if isinstance(data, list) else [data]
        companies.extend(RawCompany.from_dict(r) for r in records)
    return companies


def run(
    companies: list[RawCompany],
    config: FetcherConfig = DEFAULT_CONFIG,
    artifact_root: str = "lighthouse/data/raw/websites",
) -> list[RawCompanyV2]:
    store = ArtifactStore(artifact_root)
    rate_limiter = RateLimiter(config.per_domain_min_interval_s)
    results: list[RawCompanyV2] = []

    # One shared httpx.Client (thread-safe for concurrent requests) so
    # connection pooling and the per-domain rate limiter both work across
    # the whole batch, not per-company.
    with WebsiteFetcher(config, rate_limiter=rate_limiter) as fetcher:

        def _process(company: RawCompany) -> RawCompanyV2:
            company_v2, pages = acquire_company(company, fetcher, config)
            store.save_company_artifacts(company.id, pages)
            return company_v2

        with ThreadPoolExecutor(max_workers=config.global_concurrency) as pool:
            for company_v2 in pool.map(_process, companies):
                results.append(company_v2)

    return results


def _write_by_industry(companies_v2: list[RawCompanyV2], output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    by_industry: dict[str, list[dict[str, Any]]] = {}
    for c in companies_v2:
        by_industry.setdefault(c.industry.lower(), []).append(c.to_dict())
    for industry, records in by_industry.items():
        records.sort(key=lambda r: r["id"])
        path = os.path.join(output_dir, f"{industry}_raw_v1_1.json")
        with open(path, "w") as f:
            json.dump(records, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lighthouse Phase 1.1 website acquisition"
    )
    parser.add_argument(
        "--companies",
        nargs="+",
        required=True,
        help="v1 raw company JSON files to re-acquire",
    )
    parser.add_argument("--output-dir", default="lighthouse/data/raw_v1_1")
    parser.add_argument("--artifact-dir", default="lighthouse/data/raw/websites")
    parser.add_argument("--enable-playwright", action="store_true")
    args = parser.parse_args()

    config = FetcherConfig(enable_playwright_fallback=args.enable_playwright)
    companies = load_v1_companies(args.companies)
    companies_v2 = run(companies, config=config, artifact_root=args.artifact_dir)
    _write_by_industry(companies_v2, args.output_dir)

    succeeded = sum(1 for c in companies_v2 if c.acquisition.homepage_fetch_succeeded)
    print(
        f"Acquisition complete: {succeeded}/{len(companies_v2)} homepages fetched successfully."
    )
    print(f"Raw v1.1 records written to {args.output_dir}")
    print(f"Raw artifacts written to {args.artifact_dir}")


if __name__ == "__main__":
    main()
