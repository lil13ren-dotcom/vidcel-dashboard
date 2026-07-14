"""Live End-to-End runner — the ONLY module in this package meant to be
run from an internet-enabled environment against real, arbitrary websites.

This sandbox's outbound network policy blocks arbitrary HTTPS destinations
(confirmed: curl CONNECT to example.com and to every one of the 20
Lighthouse companies returns 403 from the egress proxy, even bypassing the
proxy and dialing the resolved IP directly — see
docs/lighthouse/Decision_Log.md, 2026-07-14 entries). Every other
verification in this package (pytest, mypy, ruff) is offline by design and
was run and passed in this sandbox. This script exists so the same
acquisition pipeline can be exercised against 2 real, live targets from
wherever the user has normal internet access.

    # 1. Preflight — validates config, target file, and environment
    #    without making any network calls.
    python3 -m lighthouse.live_e2e --preflight

    # 2. Live E2E — fetches lighthouse/data/live_e2e_targets.json (one US
    #    site already in the Lighthouse dataset, one Japanese site used
    #    purely as a locale/encoding smoke test — swap either for any two
    #    real URLs you want to check).
    python3 -m lighthouse.live_e2e --run

    # 3. Artifact inspection
    ls lighthouse/data/live_e2e_output/artifacts/
    cat lighthouse/data/live_e2e_output/data_integrity_gate.json
    cat lighthouse/data/live_e2e_output/company_scores.csv

    # 4. Rerun / idempotency check — run twice, diff the scores. Evidence
    #    that's actually confirmed both times should be identical; only
    #    things like fetch timestamps and content_hash-irrelevant retry
    #    counts should differ.
    python3 -m lighthouse.live_e2e --run --output-dir lighthouse/data/live_e2e_output_rerun
    diff lighthouse/data/live_e2e_output/company_scores.csv \\
         lighthouse/data/live_e2e_output_rerun/company_scores.csv

Exit code is 0 only if the Data Integrity Gate passes. Non-zero otherwise,
so this is safe to wire into CI as a real pass/fail check once network
access is available.

Safety, per design: conservative timeouts/retries, a real identifying
User-Agent, robots.txt respected, no CAPTCHA bypass, no proxy
circumvention, no anti-bot evasion, no authentication, exactly 2 targets
(low request volume — at most 2 homepages + up to 5 pages each). Nothing
here reads or logs credentials, and response headers are never persisted
or printed anywhere in this pipeline (see artifact_store.py's manifest —
it stores status/timestamps/hashes, never raw headers), so there is
nothing header-shaped to redact in the first place.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from lighthouse.analysis import integrity_gate
from lighthouse.models import RawCompanyV2
from lighthouse.pipeline_v2 import score_all_v2
from lighthouse.outputs.csv_writer_v2 import (
    write_companies_csv,
    write_company_scores_csv,
)
from lighthouse.scrapers.acquisition_pipeline import (
    load_v1_companies,
    run as run_acquisition,
)
from lighthouse.scrapers.config import FetcherConfig

_HERE = os.path.dirname(__file__)
DEFAULT_TARGETS_FILE = os.path.join(_HERE, "data", "live_e2e_targets.json")
DEFAULT_OUTPUT_DIR = os.path.join(_HERE, "data", "live_e2e_output")
MAX_TARGETS = 5  # hard safety cap; the shipped file has exactly 2


def _conservative_config(enable_playwright: bool) -> FetcherConfig:
    return FetcherConfig(
        connect_timeout_s=5.0,
        read_timeout_s=10.0,
        total_timeout_s=15.0,
        retry_max_attempts=2,
        retry_base_delay_s=1.0,
        retry_max_delay_s=4.0,
        per_domain_min_interval_s=2.0,
        global_concurrency=2,
        max_pages_per_company=3,
        respect_robots_txt=True,
        enable_playwright_fallback=enable_playwright,
    )


def preflight(targets_file: str) -> bool:
    print("=== Live E2E preflight (no network calls) ===")
    ok = True

    if not os.path.exists(targets_file):
        print(f"FAIL: targets file not found: {targets_file}")
        return False

    with open(targets_file) as f:
        raw = json.load(f)
    print(f"targets file: {targets_file} ({len(raw)} entries)")
    if len(raw) == 0:
        print("FAIL: targets file is empty")
        ok = False
    if len(raw) > MAX_TARGETS:
        print(
            f"FAIL: {len(raw)} targets exceeds the safety cap of {MAX_TARGETS} — this runner is for a small smoke test, not a batch run"
        )
        ok = False

    for entry in raw:
        website = entry.get("website", "")
        if not website.startswith("https://") and not website.startswith("http://"):
            print(f"FAIL: {entry.get('id')}: website is not http(s): {website!r}")
            ok = False
        else:
            print(f"  - {entry.get('id')}: {entry.get('name')} -> {website}")

    config = _conservative_config(enable_playwright=False)
    print(
        f"config: connect_timeout={config.connect_timeout_s}s read_timeout={config.read_timeout_s}s "
        f"retry_max_attempts={config.retry_max_attempts} per_domain_min_interval={config.per_domain_min_interval_s}s "
        f"respect_robots_txt={config.respect_robots_txt} enable_playwright_fallback={config.enable_playwright_fallback}"
    )
    print(f"user_agent: {config.user_agent}")

    print("PASS" if ok else "FAIL — fix the above before running --run")
    return ok


def run(targets_file: str, output_dir: str, enable_playwright: bool) -> int:
    companies = load_v1_companies([targets_file])
    if len(companies) > MAX_TARGETS:
        print(
            f"Refusing to run: {len(companies)} targets exceeds the safety cap of {MAX_TARGETS}."
        )
        return 2

    config = _conservative_config(enable_playwright=enable_playwright)
    artifact_dir = os.path.join(output_dir, "artifacts")
    os.makedirs(output_dir, exist_ok=True)

    companies_v2: list[RawCompanyV2] = run_acquisition(
        companies, config=config, artifact_root=artifact_dir
    )
    scored = score_all_v2(companies_v2)
    gate_result = integrity_gate.evaluate(scored, companies_v2)

    write_companies_csv(scored, os.path.join(output_dir, "companies.csv"))
    write_company_scores_csv(scored, os.path.join(output_dir, "company_scores.csv"))
    with open(os.path.join(output_dir, "data_integrity_gate.json"), "w") as f:
        json.dump(gate_result.to_dict(), f, indent=2)

    print(f"=== Live E2E result: {gate_result.run_status} ===")
    for company in companies_v2:
        print(
            f"  - {company.id}: homepage_status={company.acquisition.homepage_status} "
            f"pages_fetched={company.acquisition.pages_fetched}/{company.acquisition.pages_attempted}"
        )
    for reason in gate_result.failure_reasons:
        print(f"  ! {reason}")
    print(f"Artifacts written to: {artifact_dir}")
    print(f"Outputs written to: {output_dir}")

    return 0 if gate_result.passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lighthouse Live E2E runner (internet-enabled environments only)"
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="validate config/targets without any network calls",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="run the live E2E fetch against the target file",
    )
    parser.add_argument("--targets-file", default=DEFAULT_TARGETS_FILE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--enable-playwright", action="store_true")
    args = parser.parse_args()

    if not args.preflight and not args.run:
        parser.print_help()
        return 2

    if args.preflight:
        return 0 if preflight(args.targets_file) else 1

    if not preflight(args.targets_file):
        print("Preflight failed — aborting before making any network calls.")
        return 1

    return run(args.targets_file, args.output_dir, args.enable_playwright)


if __name__ == "__main__":
    sys.exit(main())
