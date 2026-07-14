"""Data model shared by every stage of the Lighthouse pipeline.

Collection (lighthouse/scrapers) produces RawCompany records. Analysis
(lighthouse/analysis) consumes them and produces the score/opportunity
structures below. Nothing in outputs/ or analysis/ should need to know
where a RawCompany came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


WEBSITE_SIGNAL_KEYS = [
    "https",
    "mobile_friendly",
    "cta",
    "quote_form",
    "contact_form",
    "financing",
    "warranty",
    "faq",
    "about_us",
    "team_page",
    "certifications",
    "service_area",
    "portfolio",
    "case_studies",
    "before_after",
    "testimonials",
    "customer_photos",
    "customer_videos",
]

SOCIAL_KEYS = ["instagram", "facebook", "youtube", "tiktok"]

RENDER_ONLY_SIGNAL_KEYS = ["mobile_friendly", "before_after", "customer_photos"]
"""Signals that can only be confirmed by actually rendering the page (viewport
behavior, real photos). If collection could not fetch the live page (see
docs/lighthouse/Decision_Log.md, 2026-07-13 WebFetch outage entry), these come
back `false` by the "unconfirmed -> false" rule, but that `false` means
"not verified this run," not "confirmed absent." Flagged separately in
outputs so nobody quotes them to a prospect as fact.
"""

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
    def from_dict(cls, d: dict[str, Any]) -> "WebsiteSignals":
        return cls(**{k: bool(d.get(k, False)) for k in WEBSITE_SIGNAL_KEYS})


@dataclass
class Social:
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    youtube: Optional[str] = None
    tiktok: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Social":
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
    review_snippets: list[str] = field(default_factory=list)
    homepage_text_excerpt: Optional[str] = None
    sources: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RawCompany":
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
    opportunities: list[Opportunity]
    journey: dict[str, Any]
    top_customer_words: list[str]
    high_opportunity_gaps: list[str]  # words customers use that the site never uses

    def as_flat_dict(self) -> dict[str, Any]:
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


# ============================================================================
# Phase 1.1 — evidence-first model
#
# v1 (above) represents every website signal as a plain bool, which cannot
# distinguish "we looked and it's not there" from "we couldn't look." That
# distinction is the entire point of Phase 1.1's direct-fetch acquisition
# layer, so it needs a richer unit than bool: Evidence.
# ============================================================================


class EvidenceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"

    @property
    def is_confirmed(self) -> bool:
        """Confirmed one way or the other by direct inspection — eligible
        to count in a coverage/observed-score denominator.
        """
        return self in (EvidenceStatus.PRESENT, EvidenceStatus.ABSENT)


@dataclass
class Evidence:
    """One fact about one company, with enough provenance to audit it.

    `value` is the plain answer (True/False for a presence signal, a
    string/number for others) and is only meaningful when `status` is
    PRESENT or ABSENT — for UNKNOWN/BLOCKED/ERROR/NOT_APPLICABLE, `value`
    should be None; the status itself is the fact.
    """

    status: EvidenceStatus
    value: Optional[object] = None
    confidence: float = 0.0
    source_url: Optional[str] = None
    evidence_text: Optional[str] = None
    collected_at: Optional[str] = None
    collector_version: Optional[str] = None

    @classmethod
    def present(
        cls,
        source_url: Optional[str],
        evidence_text: str,
        collected_at: str,
        collector_version: str,
        confidence: float = 1.0,
    ) -> "Evidence":
        return cls(
            status=EvidenceStatus.PRESENT,
            value=True,
            confidence=confidence,
            source_url=source_url,
            evidence_text=evidence_text,
            collected_at=collected_at,
            collector_version=collector_version,
        )

    @classmethod
    def absent(
        cls,
        source_url: Optional[str],
        collected_at: str,
        collector_version: str,
        confidence: float = 1.0,
        evidence_text: Optional[str] = None,
    ) -> "Evidence":
        return cls(
            status=EvidenceStatus.ABSENT,
            value=False,
            confidence=confidence,
            source_url=source_url,
            evidence_text=evidence_text,
            collected_at=collected_at,
            collector_version=collector_version,
        )

    @classmethod
    def unknown(
        cls,
        reason: str,
        collected_at: Optional[str] = None,
        collector_version: Optional[str] = None,
    ) -> "Evidence":
        return cls(
            status=EvidenceStatus.UNKNOWN,
            value=None,
            confidence=0.0,
            evidence_text=reason,
            collected_at=collected_at,
            collector_version=collector_version,
        )

    @classmethod
    def blocked(
        cls,
        reason: str,
        collected_at: Optional[str] = None,
        collector_version: Optional[str] = None,
    ) -> "Evidence":
        return cls(
            status=EvidenceStatus.BLOCKED,
            value=None,
            confidence=0.0,
            evidence_text=reason,
            collected_at=collected_at,
            collector_version=collector_version,
        )

    @classmethod
    def error(
        cls,
        reason: str,
        collected_at: Optional[str] = None,
        collector_version: Optional[str] = None,
    ) -> "Evidence":
        return cls(
            status=EvidenceStatus.ERROR,
            value=None,
            confidence=0.0,
            evidence_text=reason,
            collected_at=collected_at,
            collector_version=collector_version,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Evidence":
        d = dict(d)
        d["status"] = EvidenceStatus(d["status"])
        return cls(**d)


class EvidenceSignals:
    """A dict of signal_key -> Evidence, with the boolean-style helpers the
    rest of the pipeline needs (is_present/is_absent/is_confirmed) so
    scoring/opportunity/journey code reads naturally without reaching into
    `.get(key).status` everywhere.
    """

    def __init__(self, evidence: dict[str, Evidence]):
        self._evidence = evidence

    def get(self, key: str) -> Evidence:
        return self._evidence.get(
            key, Evidence.unknown("no evidence collected for this signal")
        )

    def status(self, key: str) -> EvidenceStatus:
        return self.get(key).status

    def confidence(self, key: str) -> float:
        return self.get(key).confidence

    def is_present(self, key: str) -> bool:
        return self.status(key) == EvidenceStatus.PRESENT

    def is_absent(self, key: str) -> bool:
        return self.status(key) == EvidenceStatus.ABSENT

    def is_confirmed(self, key: str) -> bool:
        return self.status(key).is_confirmed

    def keys(self) -> Any:
        return self._evidence.keys()

    def items(self) -> Any:
        return self._evidence.items()

    def to_dict(self) -> dict[str, Any]:
        return {k: v.to_dict() for k, v in self._evidence.items()}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EvidenceSignals":
        return cls({k: Evidence.from_dict(v) for k, v in (d or {}).items()})


@dataclass
class AcquisitionMetadata:
    """Per-company record of how (and how well) collection went — the raw
    material the Data Integrity Gate aggregates over."""

    homepage_status: str  # FetchStatus value, as a plain string for JSON round-tripping
    pages_attempted: int
    pages_fetched: int
    method_used: (
        str  # "http", "playwright", or "none" if acquisition never got a response
    )
    run_at: str
    collector_version: str
    blocked_reason: Optional[str] = None

    @property
    def homepage_fetch_succeeded(self) -> bool:
        return self.homepage_status == "success"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AcquisitionMetadata":
        return cls(**d)


@dataclass
class RawCompanyV2:
    """Phase 1.1 raw record: same identity fields as RawCompany, but
    website_signals is evidence-first and acquisition metadata travels
    with the record so downstream code (and the integrity gate) always
    knows how the evidence was obtained.
    """

    id: str
    industry: str
    name: str
    website: str
    city: str
    state: str
    website_signals: EvidenceSignals
    social: Social
    acquisition: AcquisitionMetadata
    google_maps_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    review_snippets: list[str] = field(default_factory=list)
    homepage_text_excerpt: Optional[str] = None
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "industry": self.industry,
            "name": self.name,
            "website": self.website,
            "city": self.city,
            "state": self.state,
            "website_signals": self.website_signals.to_dict(),
            "social": asdict(self.social),
            "acquisition": self.acquisition.to_dict(),
            "google_maps_url": self.google_maps_url,
            "rating": self.rating,
            "review_count": self.review_count,
            "phone": self.phone,
            "email": self.email,
            "review_snippets": self.review_snippets,
            "homepage_text_excerpt": self.homepage_text_excerpt,
            "sources": self.sources,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RawCompanyV2":
        return cls(
            id=d["id"],
            industry=d["industry"],
            name=d["name"],
            website=d["website"],
            city=d["city"],
            state=d["state"],
            website_signals=EvidenceSignals.from_dict(d.get("website_signals", {})),
            social=Social.from_dict(d.get("social", {})),
            acquisition=AcquisitionMetadata.from_dict(d["acquisition"]),
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
class ScoredCompanyV2:
    company: RawCompanyV2
    observed_score: dict[
        str, Optional[float]
    ]  # per-category: score computed only from confirmed evidence
    coverage_ratio: dict[str, float]  # per-category: confirmed_signals / total_signals
    decision_grade: dict[
        str, bool
    ]  # per-category: observed_score trustworthy enough to act on
    overall_opportunity_score: Optional[float]
    data_coverage_ratio: float  # overall coverage across all categories
    data_confidence: float  # mean confidence across all confirmed evidence
    is_decision_grade: bool
    decision_grade_reason: str
    opportunities: list[Opportunity]
    journey: dict[str, Any]
    top_customer_words: list[str]
    high_opportunity_gaps: list[str]

    def as_flat_dict(self) -> dict[str, Any]:
        c = self.company
        row: dict[str, Any] = {
            "id": c.id,
            "industry": c.industry,
            "name": c.name,
            "city": c.city,
            "state": c.state,
            "website": c.website,
        }
        for key, val in self.observed_score.items():
            row[f"{key}_observed"] = round(val, 1) if val is not None else ""
        row["overall_opportunity_score"] = (
            round(self.overall_opportunity_score, 1)
            if self.overall_opportunity_score is not None
            else ""
        )
        row["data_coverage_ratio"] = round(self.data_coverage_ratio, 2)
        row["data_confidence"] = round(self.data_confidence, 2)
        row["decision_grade"] = self.is_decision_grade
        row["decision_grade_reason"] = self.decision_grade_reason
        return row
