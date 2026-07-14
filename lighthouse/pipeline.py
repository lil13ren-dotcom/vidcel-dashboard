"""Orchestrator: raw company JSON in -> every Phase 1 deliverable out.

    python -m lighthouse.pipeline

This is the only module that wires collection -> analysis -> outputs
together. Each stage stays independently testable/importable.
"""
from __future__ import annotations

import os

from lighthouse.scrapers.collector_interface import load_raw_companies
from lighthouse.analysis import scoring
from lighthouse.analysis.customer_journey import build_journey
from lighthouse.analysis.review_intelligence import top_customer_words
from lighthouse.analysis.website_comparison import find_high_opportunity_gaps
from lighthouse.analysis.opportunity_engine import build_opportunities
from lighthouse.models import ScoredCompany
from lighthouse.outputs.csv_writer import (
    write_companies_csv, write_company_scores_csv, write_opportunities_csv,
)
from lighthouse.outputs.md_writer import write_company_report, write_industry_summary

RAW_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data", "output")
REPORTS_DIR = os.path.join(OUTPUT_DIR, "company_reports")


def score_all(companies: list) -> list:
    scored = []
    for company in companies:
        scores = scoring.score_company(company)
        scored.append(ScoredCompany(
            company=company,
            **scores,
            opportunities=build_opportunities(company),
            journey=build_journey(company),
            top_customer_words=top_customer_words(company),
            high_opportunity_gaps=find_high_opportunity_gaps(company),
        ))
    return scored


def run(raw_files: list = None, output_dir: str = OUTPUT_DIR) -> list:
    if raw_files is None:
        raw_files = [
            os.path.join(RAW_DIR, "roofing_raw.json"),
            os.path.join(RAW_DIR, "hvac_raw.json"),
            os.path.join(RAW_DIR, "remodeling_raw.json"),
        ]

    companies = load_raw_companies(raw_files)
    scored = score_all(companies)

    os.makedirs(output_dir, exist_ok=True)
    reports_dir = os.path.join(output_dir, "company_reports")
    os.makedirs(reports_dir, exist_ok=True)

    write_companies_csv(scored, os.path.join(output_dir, "companies.csv"))
    write_company_scores_csv(scored, os.path.join(output_dir, "company_scores.csv"))
    write_opportunities_csv(scored, os.path.join(output_dir, "opportunities.csv"))
    write_industry_summary(scored, os.path.join(output_dir, "industry_summary.md"))

    for sc in scored:
        write_company_report(sc, os.path.join(reports_dir, f"{sc.company.id}_report.md"))

    return scored


if __name__ == "__main__":
    result = run()
    print(f"Scored {len(result)} companies. Outputs written to {OUTPUT_DIR}")
