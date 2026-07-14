"""AI prompt templates used during data collection.

These are the ONLY place in the codebase where an LLM is asked to look at a
website and extract facts. The prompts ask for binary presence/absence facts
only ("does this exist on the page?") — never a subjective judgment or a
score. Scoring is computed later, deterministically, in lighthouse/analysis.

Keeping prompts in their own module (separate from analysis/scrapers) means
the extraction wording can be tuned without touching any scoring logic, and
the scoring logic can be unit tested without an LLM in the loop.
"""

WEBSITE_SIGNAL_RUBRIC = """\
Analyze this business website and answer strictly based on what is visibly
present on the page(s) you can see. Do not infer or guess — if you cannot
confirm something exists, mark it false.

Return a single JSON object with exactly these boolean keys:

- https: page loads over https
- mobile_friendly: has a responsive/mobile viewport meta tag or clearly
  responsive layout
- cta: a clear call-to-action such as "Get a Quote", "Call Now",
  "Schedule Service", "Book Now"
- quote_form: an on-site form to request a quote or estimate
- contact_form: a general contact form (separate from a quote form)
- financing: mentions financing, payment plans, or "0% APR" style offers
- warranty: mentions a warranty or guarantee
- faq: has an FAQ section or page
- about_us: has an About Us page or section
- team_page: introduces individual staff/team members by name or photo
- certifications: mentions licenses, manufacturer certifications, or
  association memberships (e.g. BBB, NRCA, EPA, NATE, Angi)
- service_area: lists specific cities, counties, or service radius
- portfolio: a gallery of past project photos
- case_studies: detailed write-ups of individual past projects
- before_after: before/after comparison photos
- testimonials: written customer testimonial quotes
- customer_photos: photos submitted by customers (not staged marketing shots)
- customer_videos: customer testimonial or project videos

Also return:
- social: object with instagram/facebook/youtube/tiktok URLs found on the
  site (null if absent)
- phone: visible phone number, or null
- email: visible email address, or null
- homepage_text_excerpt: 100-300 words of the ACTUAL visible homepage copy
  (verbatim or a faithful close paraphrase), not your opinion of the page.
  This is used later for keyword comparison against customer review
  language, so it must reflect real wording on the page.

Respond with ONLY the JSON object, no commentary.
"""

# Fixed vocabulary used by lighthouse/analysis/review_intelligence.py and
# lighthouse/analysis/website_comparison.py. Kept next to the collection
# prompt (not in analysis/) because it defines what we look for at the
# source, but the matching itself is plain string search — no LLM involved.
TRUST_SIGNAL_WORDS = [
    "fast", "quick", "prompt", "responsive",
    "professional", "friendly", "courteous", "respectful",
    "reliable", "honest", "trustworthy", "dependable",
    "clean", "tidy", "affordable", "fair price", "fairly priced",
    "quality", "knowledgeable", "experienced", "punctual", "on time",
    "thorough", "efficient",
]
