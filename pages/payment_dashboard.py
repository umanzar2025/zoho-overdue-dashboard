import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys

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
    historical_df = pd.read_csv(HISTORY_FILE)
    if "timestamp" in historical_df.columns:
        historical_df["timestamp"] = pd.to_datetime(historical_df["timestamp"], errors="coerce")
    st.warning("✅ Debug: Historical data merged")
else:
    historical_df = pd.DataFrame()

combined_df = pd.concat([historical_df, df], ignore_index=True)
combined_df.drop_duplicates(subset=["payment_id"], inplace=True)
combined_df.to_csv(HISTORY_FILE, index=False)
st.warning("✅ Debug: Data pulled and processed")
st.warning(f"✅ Debug: Timestamp - {datetime.now().isoformat()}")

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

# 👇 Fix: Align by proper month start (avoids mid-month misgrouping)
df_filtered["month"] = df_filtered["date"].dt.to_period("M").dt.to_timestamp()

# Optional debug: Confirm latest date available
st.caption(f"🕒 Latest payment date: {df_filtered['date'].max().date()}")

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
    height=500
)
st.plotly_chart(fig2, use_container_width=True)

