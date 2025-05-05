import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import glob
import numpy as np

from zoho_utils import (
    get_access_token,
    fetch_customer_payments,
    summarize_payment_modes
)

# 🔐 Credentials (replace with secure method in production)
refresh_token = "1000.ceb56845974e8cf5e5a1f9ac6f2d33f3.2a1c0a5032f87c4a66c5541549fc537c"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"
org_ids = {
    "GoFleet Corporation": "673162904",
    "Zenduit Corporation": "696828433"
}

# 🎛️ Streamlit UI
st.title("📊 Payment Dashboard (Collections + Risk)")
st.markdown("[📌 Jump to Overdue Invoices](#overdue-invoices-section)", unsafe_allow_html=True)
org_choice = st.selectbox("Choose Organization", ["GoFleet Corporation", "Zenduit Corporation", "Combined"])
st.caption("Showing data for the past 3 months")

# 🔐 Access token
access_token = get_access_token(refresh_token, client_id, client_secret)

# 🧾 Fetch and process data
months_back = 3
@st.cache_data(show_spinner=False)
def get_all_data():
    all_data = []
    for name, org_id in org_ids.items():
        payments = fetch_customer_payments(org_id, access_token, months_back=months_back)
        for p in payments:
            p["organization"] = name
        all_data.extend(payments)
    return pd.DataFrame(all_data)

full_df = get_all_data()

# 🎯 Filter data
if org_choice == "Combined":
    df = full_df.copy()
else:
    df = full_df[full_df["organization"] == org_choice]

if df.empty:
    st.warning("No data found for the selected organization.")
    st.stop()

# 💸 Breakdown by payment method
df_filtered = df[(df["payment_mode"].notna()) & (df["amount"].notna())]
df_filtered["amount"] = pd.to_numeric(df_filtered["amount"], errors="coerce")
df_filtered = df_filtered[df_filtered["amount"] > 0]

summary = summarize_payment_modes(df_filtered)

# 📈 Pie Chart
fig = px.pie(
    summary,
    names="payment_mode",
    values="total",
    hole=0.4,
)
fig.update_traces(
    textinfo="label+text",
    text=[f"${v:,.0f} ({p}%)" for v, p in zip(summary["total"], summary["percentage"])],
    hovertemplate="%{label}: $%{value:,.0f} (%{percent})",
    textposition="outside"
)
st.plotly_chart(fig, use_container_width=True)

# 🔗 Overdue Invoices Anchor
st.markdown("<h2 id='overdue-invoices-section'>Overdue Invoices</h2>", unsafe_allow_html=True)

# 📊 Table
with st.expander("See breakdown as table"):
    st.dataframe(summary.style.format({"total": "$ {:,}", "percentage": "{}%"}))

# 📉 Monthly Collection Trend by Payment Method
df_filtered["date"] = pd.to_datetime(df_filtered["date"], errors="coerce")
df_filtered = df_filtered.dropna(subset=["date"])
df_filtered["month"] = df_filtered["date"].dt.to_period("M").astype(str)

total_by_month = df_filtered.groupby(["month", "payment_mode"]).agg({"amount": "sum"}).reset_index()
total_by_month["amount"] = total_by_month["amount"].round(0).astype(int)

fig2 = px.line(
    total_by_month,
    x="month",
    y="amount",
    color="payment_mode",
    markers=True,
    title="📈 Monthly Collection Trend by Payment Method"
)
fig2.update_layout(xaxis_title="Month", yaxis_title="Amount ($)", yaxis_tickprefix="$", height=500)
st.plotly_chart(fig2, use_container_width=True)

# -------------------- Customer Risk Analysis & Payment Method Recommendation --------------------

st.markdown("## 📌 Customer Risk Analysis & Payment Method Recommendation")

# ===== Load Latest Risk Score CSV =====
risk_score_files = sorted(glob.glob("data/overdue_customer_risk_scores_*.csv"), reverse=True)

if not risk_score_files:
    st.warning("No risk score files found. Please upload or generate risk scores first.")
else:
    latest_risk_score_file = risk_score_files[0]
    st.info(f"Using risk score file: {os.path.basename(latest_risk_score_file)}")
    risk_df = pd.read_csv(latest_risk_score_file)
    risk_df["customer_name"] = risk_df["customer_name"].str.strip().str.lower()

    # 📌 Load Follow-up Notes
    FOLLOWUP_FILE = "data/payment_followup_notes.csv"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(FOLLOWUP_FILE):
        followup_df = pd.read_csv(FOLLOWUP_FILE)
        followup_df["customer_name"] = followup_df["customer_name"].str.strip().str.lower()
    else:
        followup_df = pd.DataFrame(columns=["customer_name", "approached", "notes", "is_na", "na_notes"])

    # Merge risk with follow-up notes
    merged_df = pd.merge(risk_df, followup_df, on="customer_name", how="left")
    for col in ["approached", "notes", "is_na", "na_notes"]:
        merged_df[col] = merged_df.get(col, False if col in ["approached", "is_na"] else "")

    merged_df["approached"] = merged_df["approached"].fillna(False)
    merged_df["notes"] = merged_df["notes"].fillna("")
    merged_df["is_na"] = merged_df["is_na"].fillna(False)
    merged_df["na_notes"] = merged_df["na_notes"].fillna("")

    # Recommendation logic
    st.sidebar.header("Recommendation Settings")
    risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)

    def suggest_payment_method(row):
        if pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
            return "Recommend Stripe"
        return "Keep Current"

    merged_df["recommended_payment_method"] = merged_df.apply(suggest_payment_method, axis=1)

    header_cols = st.columns([3, 1, 3, 2, 2, 2, 1, 2])
    headers = ["Customer", "Risk Score", "Current Payment Method", "Recommended Payment Method", "Approached", "Notes", "N/A", "N/A Notes"]
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    edited_rows = []
    for idx, row in merged_df.iterrows():
        cols = st.columns([3, 1, 3, 2, 2, 2, 1, 2])
        cols[0].markdown(f"{row['customer_name'].title()}")
        cols[1].markdown(f"{row['aggregate_risk_score']:.3f}")
        cols[2].markdown(row.get("current_payment_method", "N/A"))
        cols[3].markdown(row["recommended_payment_method"])

        approached = cols[4].checkbox("Approached", row["approached"], key=f"approached_{idx}")
        notes = cols[5].text_input("Notes", row["notes"], key=f"notes_{idx}")
        is_na = cols[6].checkbox("N/A", row["is_na"], key=f"is_na_{idx}")
        na_notes = cols[7].text_input("N/A Notes", row["na_notes"], key=f"na_notes_{idx}")

        edited_rows.append({
            "customer_name": row["customer_name"],
            "approached": approached,
            "notes": notes,
            "is_na": is_na,
            "na_notes": na_notes
        })

    if st.button("💾 Save Follow-up Notes"):
        followup_save_df = pd.DataFrame(edited_rows)
        followup_save_df.to_csv(FOLLOWUP_FILE, index=False)
        st.success("✅ Follow-up notes saved successfully!")
