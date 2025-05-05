import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
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

# 📌 Load Payment History
HISTORY_FILE = "data/payment_history.csv"
os.makedirs("data", exist_ok=True)

if os.path.exists(HISTORY_FILE):
    historical_df = pd.read_csv(HISTORY_FILE)
    if "timestamp" in historical_df.columns:
        historical_df["timestamp"] = pd.to_datetime(historical_df["timestamp"], errors="coerce")
else:
    historical_df = pd.DataFrame()

# Simulated fetch of payment data
@st.cache_data(show_spinner=False)
def fetch_payment_data():
    orgs = ["GoFleet Corporation", "Zenduit Corporation"]
    records = []
    for org in orgs:
        for i in range(50):
            records.append({
                "organization": org,
                "customer_name": f"Customer {i+1}",
                "payment_mode": np.random.choice(["Check", "Bank Transfer", "Credit Card"]),
                "amount": np.random.randint(100, 10000),
                "date": datetime.now() - pd.DateOffset(days=np.random.randint(0, 90)),
                "payment_id": f"{org}_{i}_{np.random.randint(1000)}"
            })
    return pd.DataFrame(records)

df = fetch_payment_data()

# Save to history
combined_df = pd.concat([historical_df, df], ignore_index=True)
combined_df.drop_duplicates(subset=["payment_id"], inplace=True)
combined_df.to_csv(HISTORY_FILE, index=False)

# ===== Organization filter =====
st.sidebar.header("Organization Filter")
org_choice = st.sidebar.selectbox("Choose Organization", ["Combined", "GoFleet Corporation", "Zenduit Corporation"])

if org_choice == "Combined":
    filtered_df = combined_df.copy()
else:
    filtered_df = combined_df[combined_df["organization"] == org_choice]

if filtered_df.empty:
    st.warning("No data found for the selected organization.")
    st.stop()

# ===== Payment Method Breakdown =====
st.markdown("### 📊 Payment Method Breakdown")

summary = filtered_df.groupby("payment_mode")["amount"].sum().reset_index().rename(columns={"amount": "total"})
summary["percentage"] = (summary["total"] / summary["total"].sum() * 100).round(1)

fig = px.pie(summary, names="payment_mode", values="total", hole=0.4)
fig.update_traces(textinfo="label+percent", hovertemplate="%{label}: $%{value:,.0f} (%{percent})")
st.plotly_chart(fig, use_container_width=True)

with st.expander("See breakdown as table"):
    st.dataframe(summary.style.format({"total": "$ {:,}", "percentage": "{}%"}))

# ===== Monthly Trend =====
st.markdown("### 📈 Monthly Collection Trend")

filtered_df["date"] = pd.to_datetime(filtered_df["date"], errors="coerce")
filtered_df = filtered_df.dropna(subset=["date"])
filtered_df["month"] = filtered_df["date"].dt.to_period("M").dt.to_timestamp()

monthly = filtered_df.groupby(["month", "payment_mode"]).agg({"amount": "sum"}).reset_index()

fig2 = px.line(monthly, x="month", y="amount", color="payment_mode", markers=True)
fig2.update_layout(yaxis_tickprefix="$", xaxis_title="Month", yaxis_title="Amount ($)")
st.plotly_chart(fig2, use_container_width=True)

# ===== Follow-up + Recommendation =====
st.header("🧭 Customer Risk Analysis & Payment Method Recommendation")

# Merge risk with payment
payment_summary = filtered_df.groupby("customer_name").agg({
    "payment_mode": "first",
    "amount": "sum"
}).rename(columns={"payment_mode": "current_payment_method", "amount": "total_payment"}).reset_index()

merged_df = pd.merge(risk_df, payment_summary, on="customer_name", how="left")
merged_df["current_payment_method"] = merged_df["current_payment_method"].fillna("No Payment Record")

# Load Follow-up
FOLLOWUP_FILE = "data/payment_followup_notes.csv"

if os.path.exists(FOLLOWUP_FILE):
    followup_df = pd.read_csv(FOLLOWUP_FILE)
    followup_df["customer_name"] = followup_df["customer_name"].str.strip().str.lower()
else:
    followup_df = pd.DataFrame(columns=["customer_name", "approached", "notes", "na_flag", "na_reason"])

merged_df = pd.merge(merged_df, followup_df, on="customer_name", how="left")
merged_df.fillna({"approached": False, "notes": "", "na_flag": False, "na_reason": ""}, inplace=True)

# Recommendation logic
st.sidebar.header("Recommendation Settings")
risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)

def recommend(row):
    if row["na_flag"]:
        return "N/A"
    elif pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
        return "Recommend Stripe"
    else:
        return "Keep Current"

merged_df["recommended_payment_method"] = merged_df.apply(recommend, axis=1)

st.markdown("### 📋 Recommended Payment Methods and Follow-up")

top_n_option = st.selectbox("Select number of customers to display", [20, 50, 100, 200, 500, "All"])
display_df = merged_df.copy()

if top_n_option != "All":
    display_df = display_df.head(int(top_n_option))

# ---- Interactive Follow-up ----
header_cols = st.columns([3, 1, 3, 2, 2, 2, 2])
header_cols[0].markdown("**Customer**")
header_cols[1].markdown("**Risk Score**")
header_cols[2].markdown("**Current Payment Method**")
header_cols[3].markdown("**Recommended Payment Method**")
header_cols[4].markdown("**Approached**")
header_cols[5].markdown("**N/A**")
header_cols[6].markdown("**Notes / N/A Reason**")

edited_rows = []

for idx, row in display_df.iterrows():
    cols = st.columns([3, 1, 3, 2, 2, 2, 2])
    cols[0].markdown(row["customer_name"].title())
    cols[1].markdown(f"{row['aggregate_risk_score']:.3f}")
    cols[2].markdown(row["current_payment_method"])
    cols[3].markdown(row["recommended_payment_method"])
    
    approached = cols[4].checkbox("Approached", row["approached"], key=f"approached_{idx}")
    na_flag = cols[5].checkbox("N/A", row["na_flag"], key=f"na_flag_{idx}")
    notes = cols[6].text_input("Notes or N/A Reason", row["notes"] if not na_flag else row["na_reason"], key=f"notes_{idx}")

    edited_rows.append({
        "customer_name": row["customer_name"],
        "approached": approached,
        "notes": notes if not na_flag else "",
        "na_flag": na_flag,
        "na_reason": notes if na_flag else ""
    })

# Save follow-ups
if st.button("💾 Save Follow-up Notes"):
    followup_save_df = pd.DataFrame(edited_rows)
    followup_save_df.to_csv(FOLLOWUP_FILE, index=False)
    st.success("✅ Follow-up notes saved successfully!")

# Export Recommendations
st.markdown("#### 📤 Export Recommendation List")
export_df = display_df.copy()

export_df.rename(columns={
    "customer_name": "Customer",
    "aggregate_risk_score": "Risk Score",
    "current_payment_method": "Current Payment Method",
    "recommended_payment_method": "Recommended Payment Method"
}, inplace=True)

csv = export_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Recommendations as CSV",
    data=csv,
    file_name='payment_method_recommendations.csv',
    mime='text/csv',
)
