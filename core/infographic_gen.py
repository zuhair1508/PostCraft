"""Dispatches infographic generation to the templated or AI-image path."""

from pathlib import Path

from core import db
from core.infographic_templates import render_infographic


def attach_templated_infographic(post_id: int, template_name: str, fields: dict) -> Path:
    path = render_infographic(template_name, fields)
    db.set_post_infographic(post_id, str(path), infographic_type="templated")
    return path


def attach_ai_infographic(post_id: int, concept_prompt: str, provider: str | None = None) -> Path:
    from core.image_gen import generate_illustrative_image  # lazy: optional dependency

    path = generate_illustrative_image(concept_prompt, provider=provider)
    db.set_post_infographic(post_id, str(path), infographic_type="ai_generated")
    return path
