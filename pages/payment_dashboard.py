import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys
import glob
import numpy as np

st.set_page_config(page_title="Payment Dashboard", layout="wide")
st.title("💳 Payment Dashboard")

# ===== Load Latest Risk Score CSV =====
st.markdown("## 🔄 Loading Latest Risk Scores")

risk_score_files = sorted(glob.glob("data/overdue_customer_risk_scores_*.csv"), reverse=True)

if not risk_score_files:
    st.error("❗ No risk score files found. Please run the Zoho Dashboard first.")
    st.stop()

latest_risk_score_file = risk_score_files[0]
st.info(f"Using risk score file: {os.path.basename(latest_risk_score_file)}")

risk_df = pd.read_csv(latest_risk_score_file)
risk_df["customer_name"] = risk_df["customer_name"].str.strip().str.lower()

# 👇 Fix: Add root directory to path to find zoho_utils.py
sys.path.append(os.path.abspath("."))

from zoho_utils import (
    get_access_token,
    fetch_customer_payments,
    summarize_payment_modes
)

# 🔐 Credentials (temporary, replace with secrets in production)
refresh_token = "1000.bac8728899b3380025375951ad6ad93c.7b68459d8a25e1655741c2fd8a01eca7"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

org_ids = {
    "GoFleet Corporation": "673162904",
    "Zenduit Corporation": "696828433"
}

# 🎛️ Streamlit UI
st.title("📊 Payment Method Breakdown")
st.markdown("[📌 Jump to Overdue Invoices](#overdue-invoices-section)", unsafe_allow_html=True)
org_choice = st.selectbox("Choose Organization", ["GoFleet Corporation", "Zenduit Corporation", "Combined"])
st.caption("Showing cumulative data — automatically enriched on every visit")

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
            p["timestamp"] = pd.Timestamp.now()
        all_data.extend(payments)
    return pd.DataFrame(all_data)

df = get_all_data()

# 💾 Load + merge historical data
HISTORY_FILE = "data/payment_history.csv"
os.makedirs("data", exist_ok=True)

if os.path.exists(HISTORY_FILE):
    try:
        historical_df = pd.read_csv(HISTORY_FILE)
        if "timestamp" in historical_df.columns:
            historical_df["timestamp"] = pd.to_datetime(historical_df["timestamp"], errors="coerce")
    except pd.errors.EmptyDataError:
        st.warning("History file is empty, starting fresh.")
        historical_df = pd.DataFrame()
    except pd.errors.ParserError:
        st.error("History file is corrupted or malformed. Please delete or fix 'data/payment_history.csv'.")
        st.stop()
else:
    historical_df = pd.DataFrame()

combined_df = pd.concat([historical_df, df], ignore_index=True)
combined_df.drop_duplicates(subset=["payment_id"], inplace=True)
combined_df.to_csv(HISTORY_FILE, index=False)

# 🎯 Filter data
if org_choice == "Combined":
    filtered_df = combined_df.copy()
else:
    filtered_df = combined_df[combined_df["organization"] == org_choice]

if filtered_df.empty:
    st.warning("No data found for the selected organization.")
    st.stop()

# 💸 Breakdown by payment method
df_filtered = filtered_df[(filtered_df["payment_mode"].notna()) & (filtered_df["amount"].notna())]
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
st.markdown("<h2 id='payment-details-section'>Payment Method Details</h2>", unsafe_allow_html=True)

# 📊 Table
with st.expander("See breakdown as table"):
    st.dataframe(summary.style.format({"total": "$ {:,}", "percentage": "{}%"}))

# 📉 Trend line by payment method
df_filtered["date"] = pd.to_datetime(df_filtered["date"], errors="coerce")
df_filtered = df_filtered.dropna(subset=["date"])
df_filtered["month"] = df_filtered["date"].dt.to_period("M").dt.to_timestamp()

total_by_month = (
    df_filtered.groupby(["month", "payment_mode"])
    .agg({"amount": "sum"})
    .reset_index()
)

total_by_month["amount"] = total_by_month["amount"].round(0).astype(int)

fig2 = px.line(
    total_by_month,
    x="month",
    y="amount",
    color="payment_mode",
    markers=True,
    title="📈 Monthly Collection Trend by Payment Method"
)
fig2.update_layout(
    xaxis_title="Month",
    yaxis_title="Amount ($)",
    yaxis_tickprefix="$",
    height=500,
    xaxis=dict(
        tickformat="%b %Y",
        dtick="M1"
    )
)

st.plotly_chart(fig2, use_container_width=True)

# ---- Customer Risk + Recommendation ----
st.header("🧭 Customer Risk Analysis & Payment Method Recommendation")

# 📌 Load Follow-up Notes
FOLLOWUP_FILE = "data/payment_followup_notes.csv"
os.makedirs("data", exist_ok=True)

if os.path.exists(FOLLOWUP_FILE):
    followup_df = pd.read_csv(FOLLOWUP_FILE)
    followup_df["customer_name"] = followup_df["customer_name"].str.strip().str.lower()
else:
    followup_df = pd.DataFrame(columns=["customer_name", "approached", "notes"])

# Merge risk with follow-up notes
merged_df = pd.merge(risk_df, followup_df, on="customer_name", how="left")
merged_df["approached"] = merged_df["approached"].fillna(False)
merged_df["notes"] = merged_df["notes"].fillna("")

# Simulated payment method for demonstration
merged_df["current_payment_method"] = np.where(merged_df.index % 3 == 0, "Check", "Bank Transfer")

# Simulated gov client detection
merged_df["gov_client"] = merged_df["customer_name"].str.contains("gov|ministry|dept")

# ---- UI Controls ----
st.sidebar.header("⚙️ Recommendation Settings")
risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)
exclude_gov = st.sidebar.checkbox("Exclude Govt Clients from Recommendation", True)

# ---- Recommendation Logic ----
def suggest_payment_method(row):
    if row["gov_client"] and exclude_gov:
        return "Keep Current (Govt Client)"
    elif pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
        return "Recommend Stripe"
    else:
        return "Keep Current"

merged_df["recommended_payment_method"] = merged_df.apply(suggest_payment_method, axis=1)

st.markdown("### 📋 Recommended Payment Methods for Customers")
top_n_option = st.selectbox("Select number of customers to display", [20, 50, 100, 200, 500, "All"])

display_df = merged_df.copy()

if top_n_option != "All":
    display_df = display_df.head(int(top_n_option))

# ---- Interactive Follow-Up Editor ----
st.markdown("### ✅ Follow-up Status and Notes")

edited_rows = []

for idx, row in display_df.iterrows():
    cols = st.columns([3, 1, 3, 2, 2, 2])
    cols[0].markdown(f"**{row['customer_name'].title()}**")
    cols[1].markdown(f"{row['aggregate_risk_score']:.3f}")
    cols[2].markdown(row["current_payment_method"])
    cols[3].markdown(row["recommended_payment_method"])
    approached = cols[4].checkbox("Approached", row["approached"], key=f"approached_{idx}")
    notes = cols[5].text_input("Notes", row["notes"], key=f"notes_{idx}")

    edited_rows.append({
        "customer_name": row["customer_name"],
        "approached": approached,
        "notes": notes
    })

# ---- Save Follow-up Notes ----
if st.button("💾 Save Follow-up Notes"):
    followup_save_df = pd.DataFrame(edited_rows)
    followup_save_df.to_csv(FOLLOWUP_FILE, index=False)
    st.success("Follow-up notes saved!")

# ---- Export Button ----
st.markdown("#### 📤 Export Recommendation List")

export_df = display_df.copy()
export_df.rename(columns={
    "customer_name": "Customer",
    "aggregate_risk_score": "Risk Score",
    "current_payment_method": "Current Payment Method",
    "recommended_payment_method": "Recommended Payment Method",
    "gov_client": "Govt Client",
    "approached": "Approached",
    "notes": "Follow-up Notes"
}, inplace=True)

csv = export_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Recommendations as CSV",
    data=csv,
    file_name='payment_method_recommendations.csv',
    mime='text/csv',
)
