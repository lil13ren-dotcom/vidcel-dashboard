"""Raw artifact storage for acquisition audit trails.

Every fetch this run performs is preserved so a human (or a future rerun)
can inspect exactly what was seen, when, and how. Nothing here decides
what the evidence means — that's signal_extractor.py's job.

Layout, per the brief:

    data/raw/websites/<company_id>/
      manifest.json
      homepage.html.gz
      page_001.html.gz
      page_002.html.gz
      extracted_text.json
"""

from __future__ import annotations

import gzip
import json
import os
from typing import Any, Optional

from lighthouse.scrapers.website_fetcher import FetchResult


def _page_filename(index: int, is_homepage: bool) -> str:
    return "homepage.html.gz" if is_homepage else f"page_{index:03d}.html.gz"


class ArtifactStore:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def company_dir(self, company_id: str) -> str:
        path = os.path.join(self.root_dir, company_id)
        os.makedirs(path, exist_ok=True)
        return path

    def save_company_artifacts(
        self, company_id: str, fetch_results: list[FetchResult]
    ) -> dict[str, Any]:
        """fetch_results: list of FetchResult, first entry treated as the
        homepage. Returns the manifest dict that was written.
        """
        company_dir = self.company_dir(company_id)
        manifest_pages = []
        extracted_text = {}

        for i, result in enumerate(fetch_results):
            is_homepage = i == 0
            filename = _page_filename(i, is_homepage)
            artifact_filename: Optional[str] = filename
            if result.raw_bytes is not None and result.method == "http":
                with gzip.open(os.path.join(company_dir, filename), "wb") as f:
                    f.write(result.raw_bytes)
            elif result.text is not None:
                with gzip.open(
                    os.path.join(company_dir, filename), "wt", encoding="utf-8"
                ) as f:
                    f.write(result.text)
            else:
                artifact_filename = None

            manifest_pages.append(
                {
                    "requested_url": result.requested_url,
                    "final_url": result.final_url,
                    "status": result.status.value
                    if hasattr(result.status, "value")
                    else str(result.status),
                    "http_status": result.http_status,
                    "fetched_at": result.fetched_at,
                    "content_hash": result.content_hash,
                    "method": result.method,
                    "attempts": result.attempts,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                    "artifact_file": artifact_filename,
                }
            )
            if result.text is not None:
                extracted_text[result.requested_url] = result.text

        manifest = {
            "company_id": company_id,
            "pages": manifest_pages,
        }
        with open(os.path.join(company_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        with open(os.path.join(company_dir, "extracted_text.json"), "w") as f:
            json.dump(extracted_text, f, indent=2)

        return manifest

    def load_manifest(self, company_id: str) -> dict[str, Any]:
        path = os.path.join(self.company_dir(company_id), "manifest.json")
        with open(path) as f:
            manifest: dict[str, Any] = json.load(f)
            return manifest
