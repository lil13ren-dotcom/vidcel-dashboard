"""CSV deliverables for Phase 1.1 — same three files as v1, with
coverage/confidence/decision-grade columns added so a reader never has to
guess how much to trust a number.
"""

from __future__ import annotations

import csv

from lighthouse.models import ScoredCompanyV2


def write_companies_csv(scored: list[ScoredCompanyV2], path: str) -> None:
    fields = [
        "id",
        "industry",
        "name",
        "website",
        "google_maps_url",
        "rating",
        "review_count",
        "phone",
        "email",
        "city",
        "state",
        "instagram",
        "facebook",
        "youtube",
        "tiktok",
        "homepage_fetch_status",
        "pages_attempted",
        "pages_fetched",
        "acquisition_method",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for sc in scored:
            c = sc.company
            writer.writerow(
                {
                    "id": c.id,
                    "industry": c.industry,
                    "name": c.name,
                    "website": c.website,
                    "google_maps_url": c.google_maps_url or "",
                    "rating": c.rating if c.rating is not None else "",
                    "review_count": c.review_count
                    if c.review_count is not None
                    else "",
                    "phone": c.phone or "",
                    "email": c.email or "",
                    "city": c.city,
                    "state": c.state,
                    "instagram": c.social.instagram or "",
                    "facebook": c.social.facebook or "",
                    "youtube": c.social.youtube or "",
                    "tiktok": c.social.tiktok or "",
                    "homepage_fetch_status": c.acquisition.homepage_status,
                    "pages_attempted": c.acquisition.pages_attempted,
                    "pages_fetched": c.acquisition.pages_fetched,
                    "acquisition_method": c.acquisition.method_used,
                }
            )


def write_company_scores_csv(scored: list[ScoredCompanyV2], path: str) -> None:
    fields = [
        "id",
        "industry",
        "name",
        "city",
        "state",
        "website",
        "google_score_observed",
        "website_score_observed",
        "trust_score_observed",
        "proof_score_observed",
        "social_score_observed",
        "video_score_observed",
        "overall_opportunity_score",
        "data_coverage_ratio",
        "data_confidence",
        "decision_grade",
        "decision_grade_reason",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        def sort_key(s: ScoredCompanyV2) -> float:
            return (
                s.overall_opportunity_score
                if s.overall_opportunity_score is not None
                else -1
            )

        for sc in sorted(scored, key=sort_key, reverse=True):
            writer.writerow(sc.as_flat_dict())


def write_opportunities_csv(scored: list[ScoredCompanyV2], path: str) -> None:
    fields = [
        "company_id",
        "company_name",
        "industry",
        "title",
        "reason",
        "expected_impact",
        "estimated_difficulty",
        "ai_automation_potential",
        "priority_score",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for sc in scored:
            for opp in sc.opportunities:
                writer.writerow(
                    {
                        "company_id": opp.company_id,
                        "company_name": sc.company.name,
                        "industry": sc.company.industry,
                        "title": opp.title,
                        "reason": opp.reason,
                        "expected_impact": opp.expected_impact,
                        "estimated_difficulty": opp.estimated_difficulty,
                        "ai_automation_potential": opp.ai_automation_potential,
                        "priority_score": opp.priority_score,
                    }
                )
