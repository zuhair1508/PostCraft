"""Suggests templated-infographic field values from a post's own content.

Uses the same text LLM as post generation (OPENROUTER_API_KEY / OPENROUTER_MODEL) so it
needs no extra credits or keys beyond what's already required to generate posts.
"""

import json
import re

from core.llm_client import generate_text

_TEMPLATE_INSTRUCTIONS = {
    "stat_callout": (
        "Extract the single most compelling number or quantifiable claim from the post as a "
        "punchy infographic callout (invent nothing not implied by the post).\n"
        'Return JSON: {"eyebrow": "2-4 word category label", '
        '"stat": "the big number, short, e.g. 20hrs/wk", '
        '"label": "one short phrase explaining what the stat means", '
        '"footer": "a punchy one-line takeaway"}'
    ),
    "before_after": (
        "Extract the workflow or situation described in the post as a before/after contrast.\n"
        'Return JSON: {"eyebrow": "2-4 word category label", '
        '"title": "3-6 word title for what changed", '
        '"before": "one short sentence describing the old/broken state", '
        '"after": "one short sentence describing the improved state"}'
    ),
    "checklist": (
        "Extract 3-5 short, concrete takeaways or questions from the post as a checklist.\n"
        'Return JSON: {"eyebrow": "2-4 word category label", '
        '"title": "3-6 word checklist title", '
        '"items": ["short item", "short item"]}'
    ),
    "quote_card": (
        "Pick the single most quotable, standalone sentence from the post (verbatim or lightly "
        "trimmed for clarity) - the line that would work best isolated on a quote card.\n"
        'Return JSON: {"quote": "the quote, no surrounding quotation marks", "attribution": ""}'
    ),
}


def suggest_fields(template_name: str, post_text: str, topic: str) -> dict:
    """Ask the text LLM to fill a template's fields from the post's own content."""
    if template_name not in _TEMPLATE_INSTRUCTIONS:
        raise ValueError(f"Unknown infographic template: {template_name}")

    system_prompt = (
        "You extract structured, punchy infographic copy from LinkedIn posts. Keep every field "
        "short - infographics have very little room. Respond with ONLY a single JSON object, "
        "no markdown fences, no commentary."
    )
    user_prompt = (
        f"Post topic: {topic}\n\nPost text:\n{post_text}\n\n{_TEMPLATE_INSTRUCTIONS[template_name]}"
    )

    # Some models spend a variable, occasionally very large, number of hidden reasoning tokens
    # before emitting the actual JSON, so a fixed budget can come back empty unpredictably.
    # Retry with a bigger budget rather than failing on the first empty response.
    last_error: Exception = RuntimeError("no attempt made")
    for max_tokens in (2000, 4000, 8000):
        raw = generate_text(system_prompt, user_prompt, max_tokens=max_tokens)
        try:
            return _parse_json(raw)
        except RuntimeError as e:
            last_error = e
    raise last_error


def _parse_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise RuntimeError(f"Could not find JSON in the model's response: {raw!r}")
    return json.loads(match.group(0))
