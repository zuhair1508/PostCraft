import pandas as pd
import streamlit as st

from core import content_gen, db

st.set_page_config(page_title="Content Calendar", layout="wide")
st.title("Content Calendar")

db.init_db()

st.subheader("Content mix: target vs. actual")
counts = db.category_counts()
total = sum(counts.values())

rows = []
for category, (_, target_share) in content_gen.CONTENT_MIX.items():
    actual = counts.get(category, 0)
    actual_share = (actual / total) if total else 0
    rows.append(
        {
            "Category": category,
            "Target %": round(target_share * 100, 1),
            "Actual %": round(actual_share * 100, 1),
            "Posts": actual,
        }
    )

df = pd.DataFrame(rows)
st.dataframe(df, width='stretch', hide_index=True)

st.divider()
st.subheader("Post history")

status_filter = st.selectbox("Filter by status", ["all", "draft", "approved", "discarded"])
posts = db.list_posts(None if status_filter == "all" else status_filter)

for post in posts:
    with st.expander(f"[{post['status']}] {post['category']} — {post['topic']}"):
        st.write(post["body_text"])
        if post["infographic_path"]:
            st.image(post["infographic_path"])
