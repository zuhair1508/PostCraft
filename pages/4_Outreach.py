import streamlit as st

from core import db, outreach_gen

st.set_page_config(page_title="Outreach", layout="wide")
st.title("Outreach")

db.init_db()

leads = db.list_leads()
if not leads:
    st.caption("No leads yet — import some on the Leads page first.")
    st.stop()

lead_options = {f"{l['name']} — {l['company'] or 'unknown company'} (fit {l['fit_score']})": l["id"] for l in leads}
selected_label = st.selectbox("Lead", list(lead_options.keys()))
selected_id = lead_options[selected_label]
lead_row = next(l for l in leads if l["id"] == selected_id)

approved_posts = db.list_posts("approved")
post_topics = ["-- none --"] + [p["topic"] for p in approved_posts]
hook_topic = st.selectbox("Optional: reference a recent approved post as a hook", post_topics)

if st.button("Generate outreach draft", type="primary"):
    with st.spinner("Generating..."):
        draft = outreach_gen.generate_outreach_draft(
            lead_row, None if hook_topic == "-- none --" else hook_topic
        )
    st.session_state["current_draft"] = draft

draft = st.session_state.get("current_draft")
if draft:
    st.subheader("Draft message")
    edited = st.text_area("Message", value=draft["message_text"], height=150)
    st.caption(f"{len(edited)} characters")

    col1, col2 = st.columns(2)
    if col1.button("Save edits"):
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE outreach_drafts SET message_text = %s WHERE id = %s", (edited, draft["id"])
            )
        st.success("Saved. Copy this into LinkedIn yourself when ready.")
    if col2.button("Mark as sent"):
        db.update_outreach_status(draft["id"], "sent")
        db.update_lead_status(lead_row["id"], "contacted")
        st.success("Marked as sent.")

st.divider()
st.subheader(f"Past drafts for {lead_row['name']}")
for d in db.list_outreach_drafts(lead_row["id"]):
    st.write(f"[{d['status']}] {d['message_text']}")
