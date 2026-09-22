"""AI-generated illustrative infographics for thought-leadership posts.

Three interchangeable providers, selected via IMAGE_GEN_PROVIDER (default "openrouter"):

- "openrouter": OpenRouter's unified Image API (https://openrouter.ai/docs/features/images),
  the same OPENROUTER_API_KEY already used for text generation. Set IMAGE_GEN_MODEL to any
  image-capable model slug from https://openrouter.ai/models?output_modalities=image.
- "together": Together AI (https://www.together.ai) serving open-weight image models
  directly — default is FLUX.1 [schnell] (Apache 2.0, black-forest-labs) on its free
  endpoint. Requires TOGETHER_API_KEY.
- "anthropic": Claude (ANTHROPIC_API_KEY) drawing the illustration itself with the code
  execution tool (matplotlib/Pillow), since the Messages API has no native image-output
  endpoint. Slower and less photorealistic than a dedicated image model, but needs no
  separate image-model subscription if you already have Claude API access.
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
TOGETHER_IMAGES_ENDPOINT = "https://api.together.ai/v1/images/generations"
DEFAULT_ANTHROPIC_MODEL = "claude-opus-5"
DEFAULT_TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell-Free"


def _call_openrouter(prompt: str) -> bytes:
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


def _call_together(prompt: str) -> bytes:
    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "TOGETHER_API_KEY is not set. Sign up at https://api.together.ai and copy "
            ".env.example to .env and fill it in."
        )

    model = os.environ.get("TOGETHER_IMAGE_MODEL") or DEFAULT_TOGETHER_MODEL
    # schnell is a distilled few-step model — more steps than this just burns time/quota
    # without improving quality. Override TOGETHER_IMAGE_STEPS if you switch to a non-schnell
    # model that benefits from more.
    steps = int(os.environ.get("TOGETHER_IMAGE_STEPS", "4"))

    response = httpx.post(
        TOGETHER_IMAGES_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "prompt": prompt,
            "width": 1024,
            "height": 1024,
            "steps": steps,
            "n": 1,
            "response_format": "base64",
        },
        timeout=60,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"Together AI image request failed ({response.status_code}): {response.text}"
        ) from e
    data = response.json()
    return base64.b64decode(data["data"][0]["b64_json"])


def _call_anthropic(prompt: str) -> bytes:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
        )

    from anthropic import Anthropic, APIStatusError  # lazy: optional dependency

    client = Anthropic(api_key=api_key)
    model = os.environ.get("ANTHROPIC_IMAGE_MODEL") or DEFAULT_ANTHROPIC_MODEL

    instructions = (
        "Using the Python code execution tool (matplotlib and/or Pillow), draw a minimalist, "
        "professional abstract illustration for a LinkedIn infographic. It must be a wordless, "
        "conceptual/metaphorical graphic — no readable text, letters, or data labels — matching "
        f"this visual concept:\n\n{prompt}\n\n"
        "Render at 1200x1200px and save the final image as a single PNG file in the working "
        "directory. Make reasonable creative choices yourself rather than asking questions."
    )

    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=8000,
            betas=["code-execution-2025-08-25"],
            tools=[{"type": "code_execution_20260521", "name": "code_execution"}],
            messages=[{"role": "user", "content": instructions}],
        )
    except APIStatusError as e:
        raise RuntimeError(f"Anthropic request failed ({e.status_code}): {e.message}") from e

    file_id = None
    for block in response.content:
        if block.type != "bash_code_execution_tool_result":
            continue
        result = block.content
        if getattr(result, "type", None) != "bash_code_execution_result" or not result.content:
            continue
        for file_ref in result.content:
            if file_ref.type == "bash_code_execution_output" and file_ref.file_id:
                file_id = file_ref.file_id  # last file wins if it produced more than one

    print(
        f"[image_gen] anthropic stop_reason={response.stop_reason!r} "
        f"block_types={[b.type for b in response.content]!r} file_id={file_id!r}"
    )

    if not file_id:
        explanation = " ".join(b.text for b in response.content if b.type == "text").strip()
        detail = f" Claude said: {explanation}" if explanation else ""
        raise RuntimeError(
            f"Claude didn't produce an image file (stop_reason={response.stop_reason}). "
            f"Try rephrasing the visual concept and generating again.{detail}"
        )

    return client.files.download(file_id).read()


_PROVIDERS = {
    "openrouter": _call_openrouter,
    "together": _call_together,
    "anthropic": _call_anthropic,
}


def generate_illustrative_image(concept_prompt: str, provider: str | None = None) -> Path:
    """Generate a conceptual/illustrative image for a thought-leadership post.

    `concept_prompt` should describe the visual metaphor, not restate the post text verbatim —
    keep it abstract/professional (e.g. "a tangled cable being reorganized into a clean grid,
    minimalist, dark blue and teal palette") rather than literal business photography.

    `provider` is "openrouter", "together", or "anthropic"; defaults to IMAGE_GEN_PROVIDER
    (env), then "openrouter".
    """
    provider = provider or os.environ.get("IMAGE_GEN_PROVIDER", "openrouter")
    call = _PROVIDERS.get(provider)
    if call is None:
        raise RuntimeError(
            f"Unknown IMAGE_GEN_PROVIDER {provider!r}. Choose one of: {', '.join(_PROVIDERS)}."
        )

    image_bytes = call(concept_prompt)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"ai_image_{uuid.uuid4().hex[:8]}.png"
    out_path.write_bytes(image_bytes)
    return out_path
