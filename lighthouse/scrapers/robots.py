"""robots.txt policy handling.

One RobotsPolicy per domain, cached for the life of a run. The brief asks
us to behave like a well-behaved public crawler, not to find ways around
disallow rules, so a missing/unreachable robots.txt is treated as "allow"
(the conventional default) while a robots.txt that explicitly disallows a
path is always honored.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser


@dataclass
class RobotsPolicy:
    domain: str
    fetched_ok: bool
    parser: RobotFileParser

    def is_allowed(self, url: str, user_agent: str) -> bool:
        if not self.fetched_ok:
            return True  # robots.txt unreachable -> conventional default is allow
        return self.parser.can_fetch(user_agent, url)


class RobotsCache:
    """Caches one RobotsPolicy per domain per run. The actual robots.txt
    fetch goes through the caller-supplied `fetch_text` function so it
    reuses the same SSRF-guarded, rate-limited HTTP path as everything
    else — this module has no network code of its own.
    """

    def __init__(self, fetch_text: Callable[[str], str]):
        self._fetch_text = fetch_text
        self._cache: dict[str, RobotsPolicy] = {}

    def get_policy(self, url: str) -> RobotsPolicy:
        parts = urlsplit(url)
        domain = parts.netloc
        if domain in self._cache:
            return self._cache[domain]

        robots_url = f"{parts.scheme}://{domain}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            text = self._fetch_text(robots_url)
            parser.parse(text.splitlines())
            policy = RobotsPolicy(domain=domain, fetched_ok=True, parser=parser)
        except Exception:
            policy = RobotsPolicy(domain=domain, fetched_ok=False, parser=parser)

        self._cache[domain] = policy
        return policy
