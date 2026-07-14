"""Data model shared by every stage of the Lighthouse pipeline.

Collection (lighthouse/scrapers) produces RawCompany records. Analysis
(lighthouse/analysis) consumes them and produces the score/opportunity
structures below. Nothing in outputs/ or analysis/ should need to know
where a RawCompany came from.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


WEBSITE_SIGNAL_KEYS = [
    "https", "mobile_friendly", "cta", "quote_form", "contact_form",
    "financing", "warranty", "faq", "about_us", "team_page",
    "certifications", "service_area", "portfolio", "case_studies",
    "before_after", "testimonials", "customer_photos", "customer_videos",
]

SOCIAL_KEYS = ["instagram", "facebook", "youtube", "tiktok"]

SIGNAL_LABELS = {
    "https": "HTTPS enabled",
    "mobile_friendly": "Mobile-friendly site",
    "cta": "Clear call-to-action",
    "quote_form": "Quote request form",
    "contact_form": "Contact form",
    "financing": "Financing messaging",
    "warranty": "Warranty/guarantee messaging",
    "faq": "FAQ page",
    "about_us": "About Us page",
    "team_page": "Team page",
    "certifications": "Certifications/associations shown",
    "service_area": "Service area listed",
    "portfolio": "Project portfolio/gallery",
    "case_studies": "Case studies",
    "before_after": "Before/after photos",
    "testimonials": "Written testimonials",
    "customer_photos": "Customer-submitted photos",
    "customer_videos": "Customer/project videos",
}


@dataclass
class WebsiteSignals:
    https: bool = False
    mobile_friendly: bool = False
    cta: bool = False
    quote_form: bool = False
    contact_form: bool = False
    financing: bool = False
    warranty: bool = False
    faq: bool = False
    about_us: bool = False
    team_page: bool = False
    certifications: bool = False
    service_area: bool = False
    portfolio: bool = False
    case_studies: bool = False
    before_after: bool = False
    testimonials: bool = False
    customer_photos: bool = False
    customer_videos: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "WebsiteSignals":
        return cls(**{k: bool(d.get(k, False)) for k in WEBSITE_SIGNAL_KEYS})


@dataclass
class Social:
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    youtube: Optional[str] = None
    tiktok: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Social":
        d = d or {}
        return cls(**{k: d.get(k) for k in SOCIAL_KEYS})

    def count_present(self) -> int:
        return sum(1 for k in SOCIAL_KEYS if getattr(self, k))


@dataclass
class RawCompany:
    id: str
    industry: str
    name: str
    website: str
    city: str
    state: str
    website_signals: WebsiteSignals
    social: Social
    google_maps_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    review_snippets: list = field(default_factory=list)
    homepage_text_excerpt: Optional[str] = None
    sources: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "RawCompany":
        return cls(
            id=d["id"],
            industry=d["industry"],
            name=d["name"],
            website=d["website"],
            city=d["city"],
            state=d["state"],
            website_signals=WebsiteSignals.from_dict(d.get("website_signals", {})),
            social=Social.from_dict(d.get("social", {})),
            google_maps_url=d.get("google_maps_url"),
            rating=d.get("rating"),
            review_count=d.get("review_count"),
            phone=d.get("phone"),
            email=d.get("email"),
            review_snippets=d.get("review_snippets", []) or [],
            homepage_text_excerpt=d.get("homepage_text_excerpt"),
            sources=d.get("sources", []) or [],
        )


@dataclass
class Opportunity:
    company_id: str
    title: str
    reason: str
    expected_impact: str
    estimated_difficulty: str
    ai_automation_potential: str
    priority_score: float


@dataclass
class ScoredCompany:
    company: RawCompany
    google_score: float
    website_score: float
    trust_score: float
    proof_score: float
    social_score: float
    video_score: float
    overall_opportunity_score: float
    opportunities: list  # list[Opportunity]
    journey: dict
    top_customer_words: list
    high_opportunity_gaps: list  # words customers use that the site never uses

    def as_flat_dict(self) -> dict:
        c = self.company
        return {
            "id": c.id,
            "industry": c.industry,
            "name": c.name,
            "city": c.city,
            "state": c.state,
            "website": c.website,
            "google_score": round(self.google_score, 1),
            "website_score": round(self.website_score, 1),
            "trust_score": round(self.trust_score, 1),
            "proof_score": round(self.proof_score, 1),
            "social_score": round(self.social_score, 1),
            "video_score": round(self.video_score, 1),
            "overall_opportunity_score": round(self.overall_opportunity_score, 1),
        }
