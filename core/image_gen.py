"""AI-generated illustrative infographics for thought-leadership posts.

Uses OpenRouter's unified Image API (https://openrouter.ai/docs/features/images), the same
OPENROUTER_API_KEY already used for text generation — no separate provider/key needed. Set
IMAGE_GEN_MODEL to any image-capable model slug from
https://openrouter.ai/models?output_modalities=image. OpenRouter's catalog mixes open-weight and
proprietary models and changes over time, so check that page for licensing before picking one if
an open-weight model matters to you.
"""

import base64
import os
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"
IMAGES_ENDPOINT = "https://openrouter.ai/api/v1/images"


def _call_provider(prompt: str) -> bytes:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in."
        )

    model = os.environ.get("IMAGE_GEN_MODEL")
    if not model:
        raise RuntimeError(
            "IMAGE_GEN_MODEL is not set. Browse "
            "https://openrouter.ai/models?output_modalities=image for available image models "
            "(check licensing there if you want an open-weight one), then set IMAGE_GEN_MODEL "
            "to its slug in .env."
        )

    response = httpx.post(
        IMAGES_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "prompt": prompt, "output_format": "png"},
        timeout=60,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"OpenRouter image request failed ({response.status_code}): {response.text}"
        ) from e
    data = response.json()
    return base64.b64decode(data["data"][0]["b64_json"])


def generate_illustrative_image(concept_prompt: str) -> Path:
    """Generate a conceptual/illustrative image for a thought-leadership post.

    `concept_prompt` should describe the visual metaphor, not restate the post text verbatim —
    keep it abstract/professional (e.g. "a tangled cable being reorganized into a clean grid,
    minimalist, dark blue and teal palette") rather than literal business photography.
    """
    image_bytes = _call_provider(concept_prompt)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"ai_image_{uuid.uuid4().hex[:8]}.png"
    out_path.write_bytes(image_bytes)
    return out_path
