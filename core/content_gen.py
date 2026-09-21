"""Content-mix-aware topic scheduling and post generation."""

from pathlib import Path

from core import db
from core.llm_client import generate_text

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# category -> (prompt template file, target share of content mix)
CONTENT_MIX = {
    "workflow_analysis": ("workflow_analysis.md", 0.30),
    "case_study": ("case_study.md", 0.20),
    "roi_analysis": ("roi_analysis.md", 0.15),
    "implementation_lessons": ("implementation_lessons.md", 0.15),
    "data_privacy": ("data_privacy.md", 0.10),
    "personal_lessons": ("personal_lessons.md", 0.10),
}


def _brand_brief() -> str:
    return (PROMPTS_DIR / "brand_brief.md").read_text(encoding="utf-8")


def _category_prompt(category: str) -> str:
    filename, _ = CONTENT_MIX[category]
    return (PROMPTS_DIR / "post_prompt_templates" / filename).read_text(encoding="utf-8")


def suggest_next_category() -> str:
    """Pick the category furthest behind its target share of total posts so far."""
    counts = db.category_counts()
    total = sum(counts.values())
    if total == 0:
        # Start with the highest-weighted category.
        return max(CONTENT_MIX, key=lambda c: CONTENT_MIX[c][1])

    def deficit(category: str) -> float:
        _, target_share = CONTENT_MIX[category]
        current_share = counts.get(category, 0) / total
        return target_share - current_share

    return max(CONTENT_MIX, key=deficit)


def generate_post(category: str, topic_hint: str | None = None) -> dict:
    if category not in CONTENT_MIX:
        raise ValueError(f"Unknown category: {category}")

    system_prompt = _brand_brief()
    category_instructions = _category_prompt(category)

    user_prompt = (
        f"{category_instructions}\n\n"
        + (f"Topic hint from the user: {topic_hint}\n\n" if topic_hint else "")
        + "Write one LinkedIn post (150-250 words, no hashtags, no emojis unless one adds real "
        "clarity). Then on a new line write 'TOPIC: ' followed by a 5-8 word topic label for "
        "this post."
    )

    raw = generate_text(system_prompt, user_prompt)

    body_text, topic = raw, topic_hint or category
    if "\nTOPIC:" in raw:
        body_text, _, topic_line = raw.rpartition("\nTOPIC:")
        body_text = body_text.strip()
        topic = topic_line.strip()

    post_id = db.create_post(category=category, topic=topic, body_text=body_text)
    return {"id": post_id, "category": category, "topic": topic, "body_text": body_text}
