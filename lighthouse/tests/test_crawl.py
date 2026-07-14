from lighthouse.scrapers.crawl import canonicalize_url, discover_links


def test_canonicalize_strips_fragment_and_tracking_params() -> None:
    a = canonicalize_url(
        "https://Example.com/Portfolio/?utm_source=fb&utm_campaign=x#gallery"
    )
    b = canonicalize_url("https://example.com/Portfolio?utm_source=ig")
    assert a == b


def test_canonicalize_strips_trailing_slash_but_keeps_root() -> None:
    assert canonicalize_url("https://example.com/about/") == canonicalize_url(
        "https://example.com/about"
    )
    assert canonicalize_url("https://example.com/") == "https://example.com/"


def test_canonicalize_preserves_meaningful_query_params() -> None:
    assert canonicalize_url("https://example.com/page?id=5") != canonicalize_url(
        "https://example.com/page?id=6"
    )


def test_discover_links_restricts_to_same_domain() -> None:
    html = """
    <a href="/portfolio">Our Work</a>
    <a href="https://other-domain.com/portfolio">Their portfolio</a>
    <a href="https://sub.example.com/testimonials">Testimonials</a>
    """
    candidates = discover_links("https://example.com/", html, max_pages=5)
    urls = [c.url for c in candidates]
    assert any("example.com/portfolio" in u for u in urls)
    assert not any("other-domain.com" in u for u in urls)


def test_discover_links_ignores_non_http_and_self_links() -> None:
    html = """
    <a href="mailto:info@example.com">Email us (portfolio)</a>
    <a href="tel:5551234567">Call (testimonials)</a>
    <a href="javascript:void(0)">Portfolio</a>
    <a href="/">Home portfolio</a>
    """
    candidates = discover_links("https://example.com/", html, max_pages=5)
    assert candidates == []


def test_discover_links_prioritizes_keyword_matches_and_caps_results() -> None:
    html = "".join(f'<a href="/page{i}">Random link {i}</a>' for i in range(10))
    html += (
        '<a href="/testimonials">Testimonials</a><a href="/portfolio">Our Portfolio</a>'
    )
    candidates = discover_links("https://example.com/", html, max_pages=2)
    assert len(candidates) == 2
    assert all(c.priority > 0 for c in candidates)
    urls = [c.url for c in candidates]
    assert any("testimonials" in u for u in urls)
    assert any("portfolio" in u for u in urls)


def test_discover_links_dedupes_canonical_variants() -> None:
    html = """
    <a href="/portfolio">Portfolio</a>
    <a href="/portfolio/?utm_source=fb">Portfolio again</a>
    """
    candidates = discover_links("https://example.com/", html, max_pages=5)
    assert len(candidates) == 1
