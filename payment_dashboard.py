import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from zoho_utils import (
    get_access_token,
    fetch_customer_payments,
    summarize_payment_modes
)

# 🔐 Credentials (replace with secure method in production)
import streamlit as st

refresh_token = st.secrets["refresh_token"]
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]

org_ids = {
    "GoFleet Corporation": "673162904",
    "Zenduit Corporation": "696828433"
}

# 🎛️ Streamlit UI
st.title("📊 Payment Method Breakdown")
org_choice = st.selectbox("Choose Organization", ["GoFleet Corporation", "Zenduit Corporation", "Combined"])
st.caption("Showing data for the past 3 months")

# 🔐 Access token
access_token = get_access_token(refresh_token, client_id, client_secret)

# 🧾 Caching to reduce API calls
@st.cache_data(ttl=3600)
def get_cached_customer_payments(org_id, access_token, months_back=3):
    return fetch_customer_payments(org_id, access_token, months_back=months_back)

# 🧾 Fetch and process data
months_back = 3
all_data = []

if org_choice == "Combined":
    for name, org_id in org_ids.items():
        payments = get_cached_customer_payments(org_id, access_token, months_back)
        for p in payments:
            p["organization"] = name
        all_data.extend(payments)
else:
    org_id = org_ids.get(org_choice)
    if not org_id:
        st.error("Selected organization is not recognized.")
        st.stop()
    payments = get_cached_customer_payments(org_id, access_token, months_back)
    for p in payments:
        p["organization"] = org_choice
    all_data.extend(payments)

# 💡 Transform into DataFrame
df = pd.DataFrame(all_data)
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
    title=f"Payment Method Breakdown — {org_choice}",
    hole=0.4
)
fig.update_traces(
    textinfo="label+text",
    text=[f"${value:,.0f} ({percent}%)" for value, percent in zip(summary['total'], summary['percentage'])],
    hovertemplate="%{label}: $%{value:,.0f} (%{percent})",
    textposition="outside"
)
st.plotly_chart(fig)

# 📊 Table
with st.expander("See breakdown as table"):
    st.dataframe(summary.style.format({"total": "$ {:,}", "percentage": "{}%"}))

# 📉 Trend line by payment method
df_filtered["date"] = pd.to_datetime(df_filtered["date"], errors="coerce")
df_filtered = df_filtered.dropna(subset=["date"])
df_filtered["month"] = df_filtered["date"].dt.to_period("M").astype(str)

trend_df = (
    df_filtered.groupby(["month", "payment_mode"])['amount']
    .sum()
    .reset_index()
)

trend_chart = px.line(
    trend_df,
    x="month",
    y="amount",
    color="payment_mode",
    title="📈 Payment Collection Trend by Method",
    markers=True,
    labels={"amount": "Amount ($)", "month": "Month"}
)
trend_chart.update_yaxes(tickprefix="$", separatethousands=True)
st.plotly_chart(trend_chart)
