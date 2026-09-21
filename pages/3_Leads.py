import pandas as pd
import streamlit as st

from core import db
from core.lead_scoring import score_lead

st.set_page_config(page_title="Leads", layout="wide")
st.title("Leads")

db.init_db()

st.subheader("Import leads")
st.caption("Upload a CSV export (e.g. from Sales Navigator) and map its columns below. No data leaves your machine.")

uploaded = st.file_uploader("CSV file", type="csv")
if uploaded:
    df = pd.read_csv(uploaded)
    st.dataframe(df.head(10), width='stretch')

    columns = ["-- none --"] + list(df.columns)
    st.markdown("**Map columns**")
    c1, c2, c3, c4 = st.columns(4)
    col_name = c1.selectbox("Name", columns, index=1 if len(columns) > 1 else 0)
    col_title = c2.selectbox("Title", columns)
    col_company = c3.selectbox("Company", columns)
    col_size = c4.selectbox("Company size", columns)
    c5, c6, c7 = st.columns(3)
    col_industry = c5.selectbox("Industry", columns)
    col_linkedin = c6.selectbox("LinkedIn URL", columns)
    col_email = c7.selectbox("Email", columns)

    if st.button("Import", type="primary"):
        imported = 0
        for _, row in df.iterrows():
            def val(col):
                return None if col == "-- none --" else row.get(col)

            name = val(col_name)
            if not name or pd.isna(name):
                continue

            title = val(col_title)
            company = val(col_company)
            size_raw = val(col_size)
            try:
                company_size = int(size_raw) if size_raw is not None and not pd.isna(size_raw) else None
            except (ValueError, TypeError):
                company_size = None
            industry = val(col_industry)

            fit_score = score_lead(title, company_size, industry)

            db.insert_lead(
                name=str(name),
                title=None if title is None or pd.isna(title) else str(title),
                company=None if company is None or pd.isna(company) else str(company),
                company_size=company_size,
                industry=None if industry is None or pd.isna(industry) else str(industry),
                linkedin_url=None if val(col_linkedin) is None or pd.isna(val(col_linkedin)) else str(val(col_linkedin)),
                email=None if val(col_email) is None or pd.isna(val(col_email)) else str(val(col_email)),
                source="csv_import",
                fit_score=fit_score,
            )
            imported += 1
        st.success(f"Imported {imported} leads.")

st.divider()
st.subheader("Lead list")

status_filter = st.selectbox("Filter by status", ["all", "new", "contacted", "replied", "not_a_fit"])
leads = db.list_leads()
if status_filter != "all":
    leads = [l for l in leads if l["status"] == status_filter]

if leads:
    leads_df = pd.DataFrame([dict(l) for l in leads])
    st.dataframe(
        leads_df[["id", "name", "title", "company", "company_size", "industry", "fit_score", "status"]],
        width='stretch',
        hide_index=True,
    )

    st.markdown("**Update lead status**")
    lead_id = st.number_input("Lead ID", min_value=1, step=1)
    new_status = st.selectbox("New status", ["new", "contacted", "replied", "not_a_fit"])
    if st.button("Update status"):
        db.update_lead_status(int(lead_id), new_status)
        st.rerun()
else:
    st.caption("No leads yet — import a CSV above.")
