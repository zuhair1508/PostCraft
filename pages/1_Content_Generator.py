import streamlit as st

from core import content_gen, db, infographic_fields, infographic_gen

st.set_page_config(page_title="Content Generator", layout="wide")
st.title("Content Generator")

db.init_db()

CATEGORY_LABELS = {
    "workflow_analysis": "Workflow / business-problem analysis",
    "case_study": "AI automation case study",
    "roi_analysis": "ROI / cost analysis",
    "implementation_lessons": "AI implementation lessons",
    "data_privacy": "Data privacy / self-hosted AI",
    "personal_lessons": "Personal lessons",
}

# --- Step 1: pick a category ------------------------------------------------

suggested = content_gen.suggest_next_category()
st.caption(f"Suggested next category based on your content mix so far: **{CATEGORY_LABELS[suggested]}**")

category = st.selectbox(
    "Category",
    options=list(CATEGORY_LABELS.keys()),
    index=list(CATEGORY_LABELS.keys()).index(suggested),
    format_func=lambda c: CATEGORY_LABELS[c],
)
topic_hint = st.text_input("Optional topic hint (leave blank to let it choose)")

if st.button("Generate post", type="primary"):
    with st.spinner("Generating..."):
        post = content_gen.generate_post(category, topic_hint or None)
    st.session_state["current_post"] = post

# --- Step 2: review / edit post ---------------------------------------------

post = st.session_state.get("current_post")
if post:
    st.subheader(f"Draft: {post['topic']}")
    edited_text = st.text_area("Post text", value=post["body_text"], height=280)

    col1, col2, col3 = st.columns(3)
    if col1.button("Save edits"):
        with db.get_conn() as conn:
            conn.execute("UPDATE posts SET body_text = %s WHERE id = %s", (edited_text, post["id"]))
        st.success("Saved.")
    if col2.button("Approve (ready to post)"):
        db.update_post_status(post["id"], "approved")
        st.success("Marked approved. Copy the text above into LinkedIn when you're ready.")
    if col3.button("Discard"):
        db.update_post_status(post["id"], "discarded")
        del st.session_state["current_post"]
        st.rerun()

    st.divider()
    st.subheader("Infographic")
    infographic_mode = st.radio("Type", ["Templated (data/stat)", "AI-generated (illustrative)"], horizontal=True)

    if infographic_mode == "Templated (data/stat)":
        template_name = st.selectbox(
            "Template", ["stat_callout", "before_after", "checklist", "quote_card"]
        )

        def _field_key(name: str) -> str:
            return f"tpl_{template_name}_{name}_{post['id']}"

        _DEFAULTS = {
            "stat_callout": {
                "eyebrow": "WORKFLOW COST", "stat": "20hrs/wk",
                "label": "spent manually copying invoice data",
                "footer": "That's not a staffing problem.",
            },
            "before_after": {
                "eyebrow": "WORKFLOW REDESIGN", "title": "Invoice processing",
                "before": "Manual entry across 3 systems, 2-day delay.",
                "after": "Automated extraction + review queue, same-day.",
            },
            "checklist": {
                "eyebrow": "BEFORE YOU AUTOMATE", "title": "Questions to ask first",
                "items": "Is this rule-based or judgment-based?\nHow often does it change?\nWhat's the cost of an error?",
            },
            "quote_card": {
                "quote": "Most companies don't have an AI problem. They have a workflow problem.",
                "attribution": "",
            },
        }[template_name]

        for name, default in _DEFAULTS.items():
            st.session_state.setdefault(_field_key(name), default)

        if st.button("Suggest fields from this post"):
            try:
                with st.spinner("Reading the post for infographic-worthy content..."):
                    suggested = infographic_fields.suggest_fields(
                        template_name, post["body_text"], post["topic"]
                    )
                for name in _DEFAULTS:
                    if name in suggested:
                        value = suggested[name]
                        if name == "items" and isinstance(value, list):
                            value = "\n".join(value)
                        st.session_state[_field_key(name)] = value
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't suggest fields from the post: {e}")

        fields = {}
        if template_name == "stat_callout":
            fields["eyebrow"] = st.text_input("Eyebrow label", key=_field_key("eyebrow"))
            fields["stat"] = st.text_input("Big stat", key=_field_key("stat"))
            fields["label"] = st.text_input("Label", key=_field_key("label"))
            fields["footer"] = st.text_input("Footer", key=_field_key("footer"))
        elif template_name == "before_after":
            fields["eyebrow"] = st.text_input("Eyebrow label", key=_field_key("eyebrow"))
            fields["title"] = st.text_input("Title", key=_field_key("title"))
            fields["before"] = st.text_area("Before", key=_field_key("before"))
            fields["after"] = st.text_area("After", key=_field_key("after"))
        elif template_name == "checklist":
            fields["eyebrow"] = st.text_input("Eyebrow label", key=_field_key("eyebrow"))
            fields["title"] = st.text_input("Title", key=_field_key("title"))
            items_raw = st.text_area("Items (one per line)", key=_field_key("items"))
            fields["items"] = [i.strip() for i in items_raw.splitlines() if i.strip()]
        elif template_name == "quote_card":
            fields["quote"] = st.text_area("Quote", key=_field_key("quote"))
            fields["attribution"] = st.text_input("Attribution", key=_field_key("attribution"))

        if st.button("Render templated infographic"):
            with st.spinner("Rendering..."):
                path = infographic_gen.attach_templated_infographic(post["id"], template_name, fields)
            st.image(str(path))
    else:
        concept_prompt = st.text_area(
            "Visual concept (abstract/metaphorical, not literal business photography)",
            "A tangled cable being reorganized into a clean grid, minimalist, dark blue and teal palette",
        )
        st.caption("Requires OPENROUTER_API_KEY and IMAGE_GEN_MODEL in .env.")
        if st.button("Generate AI infographic"):
            try:
                with st.spinner("Generating..."):
                    path = infographic_gen.attach_ai_infographic(post["id"], concept_prompt)
                st.image(str(path))
            except RuntimeError as e:
                st.error(str(e))
