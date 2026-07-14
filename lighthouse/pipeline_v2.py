"""Phase 1.1 orchestrator: real acquisition -> evidence scoring -> gate ->
comparison against the frozen Phase 1 (v1) outputs.

    python -m lighthouse.pipeline_v2 --enable-playwright

Re-runs the *same* 20 companies from lighthouse/data/raw/*.json (v1's
input, kept as-is) through the new acquisition layer, so the comparison
report is apples-to-apples. v1's own outputs are never modified by this
module — they stay in lighthouse/data/output/ as the frozen baseline;
v1.1 outputs go to lighthouse/data/output_v1_1/.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from lighthouse.analysis import integrity_gate, scoring_v2
from lighthouse.analysis.customer_journey_v2 import build_journey
from lighthouse.analysis.integrity_gate import GateResult
from lighthouse.analysis.opportunity_engine_v2 import build_opportunities
from lighthouse.analysis.review_intelligence import top_customer_words
from lighthouse.analysis.website_comparison import find_high_opportunity_gaps
from lighthouse.models import RawCompanyV2, ScoredCompany, ScoredCompanyV2
from lighthouse.outputs.comparison_writer import (
    build_comparison_csv,
    build_comparison_md,
)
from lighthouse.outputs.csv_writer_v2 import (
    write_companies_csv,
    write_company_scores_csv,
    write_opportunities_csv,
)
from lighthouse.outputs.md_writer_v2 import write_company_report, write_industry_summary
from lighthouse.scrapers.acquisition_pipeline import load_v1_companies
from lighthouse.scrapers.acquisition_pipeline import run as run_acquisition
from lighthouse.scrapers.config import FetcherConfig

_HERE = Path(__file__).parent
V1_RAW_FILES = [
    str(_HERE / "data" / "raw" / "roofing_raw.json"),
    str(_HERE / "data" / "raw" / "hvac_raw.json"),
    str(_HERE / "data" / "raw" / "remodeling_raw.json"),
]
V1_1_OUTPUT_DIR = str(_HERE / "data" / "output_v1_1")
V1_1_RAW_DIR = str(_HERE / "data" / "raw_v1_1")
ARTIFACT_DIR = str(_HERE / "data" / "raw" / "websites")


def score_all_v2(companies_v2: list[RawCompanyV2]) -> list[ScoredCompanyV2]:
    scored: list[ScoredCompanyV2] = []
    for company in companies_v2:
        result = scoring_v2.score_company(company)
        scored.append(
            ScoredCompanyV2(
                company=company,
                observed_score=result["observed_score"],
                coverage_ratio=result["coverage_ratio"],
                decision_grade=result["decision_grade"],
                overall_opportunity_score=result["overall_opportunity_score"],
                data_coverage_ratio=result["data_coverage_ratio"],
                data_confidence=result["data_confidence"],
                is_decision_grade=result["is_decision_grade"],
                decision_grade_reason=result["decision_grade_reason"],
                opportunities=build_opportunities(company),
                journey=build_journey(company),
                top_customer_words=top_customer_words(company),
                high_opportunity_gaps=find_high_opportunity_gaps(company),
            )
        )
    return scored


def _load_v1_scored() -> list[ScoredCompany]:
    from lighthouse.pipeline import score_all as score_all_v1

    v1_companies = load_v1_companies(V1_RAW_FILES)
    return score_all_v1(v1_companies)


def run(
    enable_playwright: bool = False,
    output_dir: str = V1_1_OUTPUT_DIR,
    raw_output_dir: str = V1_1_RAW_DIR,
    artifact_dir: str = ARTIFACT_DIR,
) -> tuple[list[ScoredCompanyV2], GateResult]:
    config = FetcherConfig(enable_playwright_fallback=enable_playwright)
    v1_companies = load_v1_companies(V1_RAW_FILES)

    companies_v2 = run_acquisition(
        v1_companies, config=config, artifact_root=artifact_dir
    )
    scored_v2 = score_all_v2(companies_v2)
    gate_result = integrity_gate.evaluate(scored_v2, companies_v2)

    os.makedirs(output_dir, exist_ok=True)
    reports_dir = os.path.join(output_dir, "company_reports")
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(raw_output_dir, exist_ok=True)

    write_companies_csv(scored_v2, os.path.join(output_dir, "companies.csv"))
    write_company_scores_csv(scored_v2, os.path.join(output_dir, "company_scores.csv"))
    write_opportunities_csv(scored_v2, os.path.join(output_dir, "opportunities.csv"))
    write_industry_summary(
        scored_v2, gate_result, os.path.join(output_dir, "industry_summary.md")
    )
    for sc in scored_v2:
        write_company_report(
            sc, os.path.join(reports_dir, f"{sc.company.id}_report.md")
        )

    with open(os.path.join(output_dir, "data_integrity_gate.json"), "w") as f:
        json.dump(gate_result.to_dict(), f, indent=2)

    scored_v1 = _load_v1_scored()
    build_comparison_md(
        scored_v1,
        scored_v2,
        gate_result,
        str(_HERE / "data" / "output" / "acquisition_comparison.md"),
    )
    build_comparison_csv(
        scored_v1,
        scored_v2,
        str(_HERE / "data" / "output" / "acquisition_comparison.csv"),
    )

    for industry, records in _group_by_industry(companies_v2).items():
        path = os.path.join(raw_output_dir, f"{industry}_raw_v1_1.json")
        with open(path, "w") as f:
            json.dump(records, f, indent=2)

    return scored_v2, gate_result


def _group_by_industry(
    companies_v2: list[RawCompanyV2],
) -> dict[str, list[dict[str, object]]]:
    by_industry: dict[str, list[dict[str, object]]] = {}
    for c in companies_v2:
        by_industry.setdefault(c.industry.lower(), []).append(c.to_dict())
    for records in by_industry.values():
        records.sort(key=lambda r: str(r["id"]))
    return by_industry


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lighthouse Phase 1.1 pipeline")
    parser.add_argument("--enable-playwright", action="store_true")
    args = parser.parse_args()
    _, gate = run(enable_playwright=args.enable_playwright)
    print(f"Run status: {gate.run_status}")
    for reason in gate.failure_reasons[:20]:
        print(f"  - {reason}")
