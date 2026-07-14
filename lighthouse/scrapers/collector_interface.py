"""Contract for the collection stage.

Collection is deliberately kept out of analysis/. Anything that knows how
to reach the internet (search, fetch a page, read a public review) lives
here or upstream of here; anything that turns collected facts into scores
or recommendations lives in lighthouse/analysis and must never make a
network call.

Phase 1 (this POC) implementation:
    Collection was performed by an LLM research agent per company, using
    web search + page fetch, applying the fixed rubric in
    lighthouse/prompts/website_signal_prompt.py so every company is judged
    against the same yes/no checklist. Output conforms to
    lighthouse/schemas/company_raw.schema.json and is stored as plain JSON
    files under lighthouse/data/raw/. There is no live "scraper" class to
    run in this phase — collection is agent-assisted and its output is
    just data.

Phase 2+ (designed, not implemented — see docs/lighthouse/Architecture.md):
    A real Collector would implement `collect(industry, city) -> RawCompany`
    below, backed by e.g. Google Places API + a headless-browser fetch,
    and the analysis stage would be untouched because it only ever
    consumes RawCompany objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from lighthouse.models import RawCompany


class Collector(ABC):
    """Interface a future automated collector must satisfy."""

    @abstractmethod
    def collect(self, industry: str, city: str, state: str) -> RawCompany:
        """Return a fully-populated RawCompany for one business."""
        raise NotImplementedError


def load_raw_companies(paths: list[str]) -> list[RawCompany]:
    """Load and validate RawCompany records from one or more JSON files.

    Each file may contain either a single object or a list of objects.
    """
    import json

    companies: list[RawCompany] = []
    for path in paths:
        with open(path) as f:
            data = json.load(f)
        records = data if isinstance(data, list) else [data]
        for record in records:
            companies.append(RawCompany.from_dict(record))
    return companies
