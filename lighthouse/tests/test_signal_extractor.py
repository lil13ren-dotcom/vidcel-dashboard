import os

from lighthouse.models import EvidenceStatus
from lighthouse.scrapers.signal_extractor import (
    extract_homepage_excerpt,
    extract_signals,
    extract_social_links,
)
from lighthouse.scrapers.website_fetcher import FetchResult, FetchStatus

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "html")


def _load(name: str) -> str:
    with open(os.path.join(FIXTURES, name)) as f:
        return f.read()


def _success(url: str, html: str) -> FetchResult:
    return FetchResult(
        requested_url=url,
        final_url=url,
        status=FetchStatus.SUCCESS,
        http_status=200,
        text=html,
        fetched_at="2026-01-01T00:00:00Z",
        method="http",
    )


def _failure(url: str, status: FetchStatus) -> FetchResult:
    return FetchResult(
        requested_url=url,
        final_url=url,
        status=status,
        fetched_at="2026-01-01T00:00:00Z",
    )


def test_confirms_cta_quote_form_and_financing_from_us_fixture() -> None:
    pages = [_success("https://acme.example/", _load("homepage_us_full.html"))]
    signals = extract_signals(pages, "test-1.0", "2026-01-01T00:00:00Z")

    assert signals.is_present("cta")
    assert signals.is_present("quote_form")
    assert signals.is_present("financing")
    assert signals.is_present("warranty")
    assert signals.is_present("certifications")
    assert signals.is_present("service_area")
    assert signals.is_present("about_us")
    assert signals.is_present("mobile_friendly")
    assert signals.is_present("https")


def test_confirms_faq_and_testimonials_from_dedicated_page() -> None:
    homepage = _success("https://acme.example/", _load("homepage_us_full.html"))
    testimonials = _success(
        "https://acme.example/testimonials", _load("testimonials_page.html")
    )
    signals = extract_signals(
        [homepage, testimonials], "test-1.0", "2026-01-01T00:00:00Z"
    )

    assert signals.is_present("testimonials")
    assert signals.is_present("faq")
    assert signals.is_present("before_after")


def test_social_links_extracted_from_homepage() -> None:
    pages = [_success("https://acme.example/", _load("homepage_us_full.html"))]
    social = extract_social_links(pages)
    assert social["facebook"] is not None
    assert social["instagram"] is not None
    assert social["youtube"] is None
    assert social["tiktok"] is None


def test_confirmed_absent_requires_a_scoped_page_to_have_been_fetched() -> None:
    """A minimal site with no dedicated pages, but where the homepage WAS
    successfully fetched, should confirm ABSENT for site-wide signals
    (checked on the homepage alone) but stay UNKNOWN for signals whose
    scope requires a dedicated page we never even tried to fetch.
    """
    pages = [_success("https://bare.example/", _load("homepage_minimal.html"))]
    signals = extract_signals(pages, "test-1.0", "2026-01-01T00:00:00Z")

    # site-wide, checked against the homepage we did fetch -> confirmable absent
    assert signals.status("cta") == EvidenceStatus.ABSENT
    assert signals.status("certifications") == EvidenceStatus.ABSENT

    # scoped to a dedicated page we never fetched -> unknown, not absent
    assert signals.status("testimonials") == EvidenceStatus.UNKNOWN
    assert signals.status("portfolio") == EvidenceStatus.UNKNOWN


def test_total_acquisition_failure_marks_everything_unknown_never_absent() -> None:
    """This is the core Phase 1.1 requirement: a fetch that never got a
    response must never be represented as a confirmed absence.
    """
    pages = [_failure("https://blocked.example/", FetchStatus.POLICY_BLOCKED)]
    signals = extract_signals(pages, "test-1.0", "2026-01-01T00:00:00Z")

    from lighthouse.models import WEBSITE_SIGNAL_KEYS

    for key in WEBSITE_SIGNAL_KEYS:
        assert signals.status(key) != EvidenceStatus.ABSENT, (
            f"{key} must not be ABSENT on total fetch failure"
        )
        assert signals.status(key) == EvidenceStatus.UNKNOWN


def test_https_is_not_confirmed_from_a_url_string_alone_when_fetch_never_connected() -> (
    None
):
    """Regression test: earlier version of this extractor read the scheme
    off `final_url` even when the fetch failed before ever reaching the
    network, which meant https could be "confirmed present" from the
    request URL string alone. It must require an actual response.
    """
    pages = [_failure("https://blocked.example/", FetchStatus.POLICY_BLOCKED)]
    signals = extract_signals(pages, "test-1.0", "2026-01-01T00:00:00Z")
    assert signals.status("https") == EvidenceStatus.UNKNOWN


def test_https_is_confirmed_from_a_real_http_error_response() -> None:
    """A real (non-2xx) HTTP response still proves the scheme that served
    it — this is legitimately confirmable even though the page itself
    wasn't a success.
    """
    page = FetchResult(
        requested_url="https://acme.example/gone",
        final_url="https://acme.example/gone",
        status=FetchStatus.HTTP_ERROR,
        http_status=404,
        text="<html>not found</html>",
        fetched_at="2026-01-01T00:00:00Z",
    )
    signals = extract_signals([page], "test-1.0", "2026-01-01T00:00:00Z")
    assert signals.status("https") == EvidenceStatus.PRESENT


def test_customer_photos_only_becomes_present_candidate_never_full_confidence() -> None:
    html = "<p>One happy customer photo submitted by a client last week.</p>"
    pages = [_success("https://acme.example/reviews", html)]
    signals = extract_signals(pages, "test-1.0", "2026-01-01T00:00:00Z")
    evidence = signals.get("customer_photos")
    assert evidence.status == EvidenceStatus.PRESENT
    assert evidence.confidence < 1.0  # never full-confidence from text alone


def test_malformed_html_does_not_crash_extraction() -> None:
    pages = [_success("https://broken.example/", _load("homepage_malformed.html"))]
    signals = extract_signals(pages, "test-1.0", "2026-01-01T00:00:00Z")
    assert signals.is_present("cta")
    assert signals.is_present("quote_form")


def test_js_shell_page_yields_mostly_unknown_or_absent_not_crash() -> None:
    pages = [_success("https://spa.example/", _load("homepage_js_shell.html"))]
    signals = extract_signals(pages, "test-1.0", "2026-01-01T00:00:00Z")
    assert (
        signals.status("cta") == EvidenceStatus.ABSENT
    )  # homepage fetched, nothing found
    assert signals.is_present("mobile_friendly") is False


def test_japanese_site_extracts_cta_and_warranty() -> None:
    pages = [_success("https://acme.example.jp/", _load("homepage_jp_full.html"))]
    signals = extract_signals(pages, "test-1.0", "2026-01-01T00:00:00Z")
    assert signals.is_present("mobile_friendly")
    assert signals.is_present("warranty")
    assert signals.is_present("service_area")


def test_extract_homepage_excerpt_strips_tags_and_collapses_whitespace() -> None:
    pages = [
        _success(
            "https://acme.example/",
            "<html><body><h1>Hi</h1>  <p>There</p></body></html>",
        )
    ]
    excerpt = extract_homepage_excerpt(pages)
    assert "<h1>" not in excerpt
    assert "Hi There" in excerpt


def test_extract_homepage_excerpt_empty_when_no_pages_fetched() -> None:
    assert (
        extract_homepage_excerpt([_failure("https://x.example/", FetchStatus.TIMEOUT)])
        == ""
    )
