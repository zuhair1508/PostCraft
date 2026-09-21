import streamlit as st

from core import db

st.set_page_config(page_title="LinkedIn Brand & Lead Engine", page_icon="🧭", layout="wide")

db.init_db()

st.title("LinkedIn Brand & Lead Engine")
st.markdown(
    """
This tool helps you:

1. **Content Generator** — generate a LinkedIn post + infographic, following your content-mix
   and brand brief. You review, edit, and post it yourself.
2. **Content Calendar** — track how your published posts line up with your target content mix.
3. **Leads** — import your own lead lists and see them ranked by ICP fit.
4. **Outreach** — generate a personalized draft message per lead. You send it yourself.

Nothing in this tool posts to LinkedIn, messages anyone, or scrapes any data automatically —
every action that touches LinkedIn is done by you, manually, using what this tool prepares.

Use the sidebar to navigate.
"""
)

st.info(
    "First time here? Copy `.env.example` to `.env` and add your `OPENROUTER_API_KEY` before "
    "using the Content Generator or Outreach pages. Text generation runs on an open-weight model "
    "(Llama 3.3 70B by default) via OpenRouter — swap `OPENROUTER_MODEL` in `.env` to try another."
)
