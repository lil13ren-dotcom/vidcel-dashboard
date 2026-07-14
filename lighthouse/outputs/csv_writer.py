"""Writes the three flat CSV deliverables required by the brief.

Kept separate from analysis/ so the analysis modules stay usable from
anything else (a notebook, a future API) without dragging in file I/O.
"""
from __future__ import annotations

import csv

from lighthouse.models import ScoredCompany


def write_companies_csv(scored: list, path: str) -> None:
    """companies.csv — one row per company, basic + collected facts."""
    fields = [
        "id", "industry", "name", "website", "google_maps_url", "rating",
        "review_count", "phone", "email", "city", "state",
        "instagram", "facebook", "youtube", "tiktok",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for sc in scored:
            c = sc.company
            writer.writerow({
                "id": c.id, "industry": c.industry, "name": c.name,
                "website": c.website, "google_maps_url": c.google_maps_url or "",
                "rating": c.rating if c.rating is not None else "",
                "review_count": c.review_count if c.review_count is not None else "",
                "phone": c.phone or "", "email": c.email or "",
                "city": c.city, "state": c.state,
                "instagram": c.social.instagram or "", "facebook": c.social.facebook or "",
                "youtube": c.social.youtube or "", "tiktok": c.social.tiktok or "",
            })


def write_company_scores_csv(scored: list, path: str) -> None:
    """company_scores.csv — the seven rule-based scores per company."""
    fields = [
        "id", "industry", "name", "city", "state", "website",
        "google_score", "website_score", "trust_score", "proof_score",
        "social_score", "video_score", "overall_opportunity_score",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for sc in sorted(scored, key=lambda s: s.overall_opportunity_score, reverse=True):
            writer.writerow(sc.as_flat_dict())


def write_opportunities_csv(scored: list, path: str) -> None:
    """opportunities.csv — every triggered opportunity across all companies,
    ranked by priority_score within each company.
    """
    fields = [
        "company_id", "company_name", "industry", "title", "reason",
        "expected_impact", "estimated_difficulty", "ai_automation_potential",
        "priority_score",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for sc in scored:
            for opp in sc.opportunities:
                writer.writerow({
                    "company_id": opp.company_id,
                    "company_name": sc.company.name,
                    "industry": sc.company.industry,
                    "title": opp.title,
                    "reason": opp.reason,
                    "expected_impact": opp.expected_impact,
                    "estimated_difficulty": opp.estimated_difficulty,
                    "ai_automation_potential": opp.ai_automation_potential,
                    "priority_score": opp.priority_score,
                })
