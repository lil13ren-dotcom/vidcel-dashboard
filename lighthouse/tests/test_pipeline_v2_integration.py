"""End-to-end integration test: two fake companies through acquisition,
scoring, the gate, and every output writer — using respx-mocked HTTP so
it's fully offline. This is the test that exercises the orchestration glue
(acquisition_pipeline.py, pipeline_v2.py, the csv/md writers, the
comparison writer) that the narrower unit tests don't reach.
"""

import csv
import json
import os
import socket

import httpx
import pytest
import respx

from lighthouse.analysis import integrity_gate
from lighthouse.models import RawCompany, Social, WebsiteSignals
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
from lighthouse.pipeline import score_all as score_all_v1
from lighthouse.pipeline_v2 import score_all_v2
from lighthouse.scrapers.acquisition_pipeline import run as run_acquisition
from lighthouse.scrapers.config import FetcherConfig

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "html")


@pytest.fixture(autouse=True)
def no_real_dns(monkeypatch) -> None:
    def fake_getaddrinfo(host, port, proto=None) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def _v1_company(company_id: str, website: str) -> RawCompany:
    return RawCompany(
        id=company_id,
        industry="Roofing",
        name=f"Co {company_id}",
        website=website,
        city="Austin",
        state="TX",
        website_signals=WebsiteSignals(),  # v1 all-false baseline, as if search snippets found nothing
        social=Social(),
        rating=4.7,
        review_count=90,
    )


@respx.mock
def test_full_pipeline_end_to_end(tmp_path) -> None:
    with open(os.path.join(FIXTURES, "homepage_us_full.html")) as f:
        full_html = f.read()

    respx.get("https://good.example/").mock(
        return_value=httpx.Response(
            200, html=full_html, headers={"content-type": "text/html"}
        )
    )
    respx.get("https://good.example/robots.txt").mock(return_value=httpx.Response(404))
    respx.get(url__regex=r"https://good\.example/.*").mock(
        return_value=httpx.Response(
            200, html=full_html, headers={"content-type": "text/html"}
        )
    )
    respx.get("https://blocked.example/").mock(
        side_effect=httpx.ProxyError("403 Forbidden")
    )
    respx.get("https://blocked.example/robots.txt").mock(
        side_effect=httpx.ProxyError("403 Forbidden")
    )

    v1_companies = [
        _v1_company("c1", "https://good.example/"),
        _v1_company("c2", "https://blocked.example/"),
    ]
    config = FetcherConfig(
        respect_robots_txt=True, per_domain_min_interval_s=0.0, retry_max_attempts=1
    )

    companies_v2 = run_acquisition(
        v1_companies, config=config, artifact_root=str(tmp_path / "artifacts")
    )
    assert len(companies_v2) == 2

    scored_v2 = score_all_v2(companies_v2)
    gate_result = integrity_gate.evaluate(scored_v2, companies_v2)

    # 1/2 homepages succeeded -> below the 85% gate threshold -> NOT_DECISION_GRADE,
    # but the successful company should itself carry real, decision-grade evidence.
    assert gate_result.run_status == "NOT_DECISION_GRADE"
    good = next(sc for sc in scored_v2 if sc.company.website == "https://good.example/")
    blocked = next(
        sc for sc in scored_v2 if sc.company.website == "https://blocked.example/"
    )
    assert good.company.acquisition.homepage_fetch_succeeded is True
    assert good.company.website_signals.is_present("cta")
    assert blocked.company.acquisition.homepage_status == "policy_blocked"
    # google_score coverage is still 1.0 (rating/review_count come from v1
    # data untouched by this phase); all 5 website-derived categories are 0
    # coverage, so overall data_coverage_ratio is 1/6, not 0.
    assert blocked.data_coverage_ratio == pytest.approx(1 / 6)
    assert blocked.is_decision_grade is False

    out_dir = tmp_path / "output"
    reports_dir = out_dir / "company_reports"
    reports_dir.mkdir(parents=True)

    write_companies_csv(scored_v2, str(out_dir / "companies.csv"))
    write_company_scores_csv(scored_v2, str(out_dir / "company_scores.csv"))
    write_opportunities_csv(scored_v2, str(out_dir / "opportunities.csv"))
    write_industry_summary(scored_v2, gate_result, str(out_dir / "industry_summary.md"))
    for sc in scored_v2:
        write_company_report(sc, str(reports_dir / f"{sc.company.id}_report.md"))

    with open(out_dir / "companies.csv") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert {r["id"] for r in rows} == {"c1", "c2"}

    assert (reports_dir / "c1_report.md").exists()
    assert (reports_dir / "c2_report.md").exists()
    assert "Not Verified This Run" in (reports_dir / "c2_report.md").read_text()

    summary_text = (out_dir / "industry_summary.md").read_text()
    assert "NOT_DECISION_GRADE" in summary_text

    v1_scored = score_all_v1(v1_companies)
    build_comparison_md(
        v1_scored, scored_v2, gate_result, str(out_dir / "acquisition_comparison.md")
    )
    build_comparison_csv(
        v1_scored, scored_v2, str(out_dir / "acquisition_comparison.csv")
    )
    assert (out_dir / "acquisition_comparison.md").exists()

    manifest_path = tmp_path / "artifacts" / "c1" / "manifest.json"
    assert manifest_path.exists()
    with open(manifest_path) as f:
        manifest = json.load(f)
    assert manifest["pages"][0]["status"] == "success"
