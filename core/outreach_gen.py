"""Generates personalized outreach message drafts per lead."""

from pathlib import Path

from core import db
from core.llm_client import generate_text

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _brand_brief() -> str:
    return (PROMPTS_DIR / "brand_brief.md").read_text(encoding="utf-8")


def _outreach_instructions() -> str:
    return (PROMPTS_DIR / "outreach_prompt.md").read_text(encoding="utf-8")


def generate_outreach_draft(lead_row, recent_post_topic: str | None = None) -> dict:
    lead_context = (
        f"Name: {lead_row['name']}\n"
        f"Title: {lead_row['title'] or 'unknown'}\n"
        f"Company: {lead_row['company'] or 'unknown'}\n"
        f"Company size: {lead_row['company_size'] or 'unknown'}\n"
        f"Industry: {lead_row['industry'] or 'unknown'}\n"
    )
    if recent_post_topic:
        lead_context += f"\nA recent post topic you could naturally reference: {recent_post_topic}\n"

    user_prompt = f"{_outreach_instructions()}\n\nLead details:\n{lead_context}"

    message_text = generate_text(_brand_brief(), user_prompt, max_tokens=300)

    draft_id = db.create_outreach_draft(lead_id=lead_row["id"], message_text=message_text)
    return {"id": draft_id, "lead_id": lead_row["id"], "message_text": message_text}
