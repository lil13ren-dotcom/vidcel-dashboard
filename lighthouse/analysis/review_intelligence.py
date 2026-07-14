"""Extracts repeated language and trust signals from public review text.

Pure string processing — a word either appears with meaningful frequency
or it doesn't. No sentiment model, no summarization model. This keeps the
"what do customers actually say" step auditable: every word in the output
can be grepped back to a snippet in review_snippets.
"""
from __future__ import annotations

import re
from collections import Counter

from lighthouse.models import RawCompany
from lighthouse.prompts.website_signal_prompt import TRUST_SIGNAL_WORDS

_STOPWORDS = {
    "the", "and", "a", "to", "was", "is", "for", "of", "in", "on", "we",
    "our", "with", "they", "them", "he", "she", "it", "this", "that",
    "were", "are", "very", "so", "did", "had", "have", "has", "would",
    "will", "us", "job", "im", "i", "you", "your", "their", "my",
}

_WORD_RE = re.compile(r"[a-z']+")


def _tokenize(text: str) -> list:
    return _WORD_RE.findall(text.lower())


def top_customer_words(company: RawCompany, top_n: int = 8) -> list:
    """Most repeated non-stopword tokens across all review snippets."""
    tokens = []
    for snippet in company.review_snippets:
        tokens.extend(t for t in _tokenize(snippet) if t not in _STOPWORDS and len(t) > 2)
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(top_n)]


def trust_signal_word_hits(company: RawCompany) -> dict:
    """Which of the fixed TRUST_SIGNAL_WORDS actually appear in reviews,
    and how many times.
    """
    joined = " ".join(company.review_snippets).lower()
    return {
        word: joined.count(word)
        for word in TRUST_SIGNAL_WORDS
        if word in joined
    }


def has_sufficient_review_text(company: RawCompany) -> bool:
    """POC limitation: without a paid reviews API we only have whatever
    public snippets a search turned up. Below this bar, treat review
    intelligence as unavailable rather than drawing conclusions from noise.
    """
    return len(" ".join(company.review_snippets)) >= 40
