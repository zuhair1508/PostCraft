import streamlit as st

from core import content_gen, db, infographic_gen

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
        fields = {}
        if template_name == "stat_callout":
            fields["eyebrow"] = st.text_input("Eyebrow label", "WORKFLOW COST")
            fields["stat"] = st.text_input("Big stat", "20hrs/wk")
            fields["label"] = st.text_input("Label", "spent manually copying invoice data")
            fields["footer"] = st.text_input("Footer", "That's not a staffing problem.")
        elif template_name == "before_after":
            fields["eyebrow"] = st.text_input("Eyebrow label", "WORKFLOW REDESIGN")
            fields["title"] = st.text_input("Title", "Invoice processing")
            fields["before"] = st.text_area("Before", "Manual entry across 3 systems, 2-day delay.")
            fields["after"] = st.text_area("After", "Automated extraction + review queue, same-day.")
        elif template_name == "checklist":
            fields["eyebrow"] = st.text_input("Eyebrow label", "BEFORE YOU AUTOMATE")
            fields["title"] = st.text_input("Title", "Questions to ask first")
            items_raw = st.text_area("Items (one per line)", "Is this rule-based or judgment-based?\nHow often does it change?\nWhat's the cost of an error?")
            fields["items"] = [i.strip() for i in items_raw.splitlines() if i.strip()]
        elif template_name == "quote_card":
            fields["quote"] = st.text_area("Quote", "Most companies don't have an AI problem. They have a workflow problem.")
            fields["attribution"] = st.text_input("Attribution", "")

        if st.button("Render templated infographic"):
            with st.spinner("Rendering..."):
                path = infographic_gen.attach_templated_infographic(post["id"], template_name, fields)
            st.image(str(path))
    else:
        concept_prompt = st.text_area(
            "Visual concept (abstract/metaphorical, not literal business photography)",
            "A tangled cable being reorganized into a clean grid, minimalist, dark blue and teal palette",
        )
        st.caption("Requires IMAGE_GEN_API_KEY in .env.")
        if st.button("Generate AI infographic"):
            try:
                with st.spinner("Generating..."):
                    path = infographic_gen.attach_ai_infographic(post["id"], concept_prompt)
                st.image(str(path))
            except RuntimeError as e:
                st.error(str(e))
