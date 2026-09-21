"""Rule-based ICP fit scoring for imported leads. Transparent and tunable, no ML needed."""

PRIORITY_INDUSTRIES = [
    "accounting", "professional services", "distribution", "wholesale",
    "logistics", "supply chain", "manufacturing", "property", "real estate",
    "b2b services", "field services",
]

SENIOR_TITLE_KEYWORDS = [
    "founder", "owner", "ceo", "coo", "managing director", "md",
    "president", "vp operations", "head of operations", "operations director",
    "operations manager",
]


def score_lead(title: str | None, company_size: int | None, industry: str | None) -> int:
    """Returns a 0-100 fit score. Weights: seniority 40, company size fit 30, industry fit 30."""
    score = 0

    title_l = (title or "").lower()
    if any(kw in title_l for kw in SENIOR_TITLE_KEYWORDS):
        score += 40
    elif title_l:
        score += 10  # some title present but not a clear decision-maker

    if company_size is not None:
        if 10 <= company_size <= 200:
            score += 30
        elif 5 <= company_size < 10 or 200 < company_size <= 500:
            score += 15  # near the ideal band

    industry_l = (industry or "").lower()
    if any(kw in industry_l for kw in PRIORITY_INDUSTRIES):
        score += 30
    elif industry_l:
        score += 10

    return min(score, 100)
