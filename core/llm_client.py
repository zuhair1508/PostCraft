"""Thin wrapper around OpenRouter (OpenAI-compatible API) for open-weight text generation.

OpenRouter lets us point at any open-source model (Llama, Qwen, DeepSeek, Mixtral, ...) by name
without changing this client — swap OPENROUTER_MODEL in .env to try a different one.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def generate_text(system_prompt: str, user_prompt: str, max_tokens: int = 1200) -> str:
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    response = _client().chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()
