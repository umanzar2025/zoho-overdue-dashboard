import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
import glob
import numpy as np
from datetime import datetime

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

# 📌 Load Follow-up Notes
FOLLOWUP_FILE = "data/payment_followup_notes.csv"
os.makedirs("data", exist_ok=True)

if os.path.exists(FOLLOWUP_FILE):
    followup_df = pd.read_csv(FOLLOWUP_FILE)
    followup_df["customer_name"] = followup_df["customer_name"].str.strip().str.lower()
else:
    followup_df = pd.DataFrame(columns=["customer_name", "approached", "notes", "is_na", "na_notes"])

# Merge risk with follow-up notes (safe merge)
merged_df = pd.merge(risk_df, followup_df, on="customer_name", how="left")
for col, default in [("approached", False), ("notes", ""), ("is_na", False), ("na_notes", "")]:
    if col not in merged_df.columns:
        merged_df[col] = default
    merged_df[col] = merged_df[col].fillna(default)

# ---- Simulate Payment Data ----
PAYMENT_FILE = "data/payment_history.csv"

# Load historical if exists
if os.path.exists(PAYMENT_FILE):
    payment_history_df = pd.read_csv(PAYMENT_FILE)
    if "date" in payment_history_df.columns:
        payment_history_df["date"] = pd.to_datetime(payment_history_df["date"], errors="coerce")
else:
    payment_history_df = pd.DataFrame()

# Simulate new payments
np.random.seed(0)
new_payments = []
for cust in merged_df["customer_name"]:
    new_payments.append({
        "customer_name": cust,
        "payment_mode": np.random.choice(["Check", "Bank Transfer", "Stripe"]),
        "amount": np.random.randint(1000, 5000),
        "date": pd.Timestamp.now()
    })

new_payments_df = pd.DataFrame(new_payments)

# Merge and save updated payment history
payment_history_df = pd.concat([payment_history_df, new_payments_df], ignore_index=True)
payment_history_df.to_csv(PAYMENT_FILE, index=False)

# ---- 📊 Payment Method Breakdown ----
st.header("📊 Payment Method Breakdown")

recent_df = payment_history_df.copy()
recent_df = recent_df[recent_df["date"] >= pd.Timestamp.now() - pd.DateOffset(months=3)]
recent_df = recent_df[recent_df["amount"] > 0]

summary = recent_df.groupby("payment_mode")["amount"].sum().reset_index()
summary["percentage"] = (summary["amount"] / summary["amount"].sum() * 100).round(1)

fig_pie = px.pie(summary, names="payment_mode", values="amount", hole=0.4)
fig_pie.update_traces(textinfo="label+percent")
st.plotly_chart(fig_pie, use_container_width=True)

# 📈 Monthly Trend
recent_df["month"] = recent_df["date"].dt.to_period("M").dt.to_timestamp()
trend = recent_df.groupby(["month", "payment_mode"]).agg({"amount": "sum"}).reset_index()

fig_line = px.line(trend, x="month", y="amount", color="payment_mode", markers=True, title="📅 Monthly Collection Trend (Past 3 Months)")
fig_line.update_layout(xaxis_title="Month", yaxis_title="Amount ($)", yaxis_tickprefix="$")
st.plotly_chart(fig_line, use_container_width=True)

# ---- Customer Risk + Recommendation ----
st.header("🧭 Customer Risk Analysis & Payment Method Recommendation")
st.sidebar.header("⚙️ Recommendation Settings")
risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)

def suggest_payment_method(row):
    if pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
        return "Recommend Stripe"
    else:
        return "Keep Current"

merged_df["recommended_payment_method"] = merged_df.apply(suggest_payment_method, axis=1)

st.markdown("### 📋 Recommended Payment Methods for Customers")
top_n_option = st.selectbox("Select number of customers to display", [20, 50, 100, 200, 500, "All"])
display_df = merged_df.copy()

if top_n_option != "All":
    display_df = display_df.head(int(top_n_option))

# ---- Follow-up Editor ----
st.markdown("### ✅ Follow-up Status and Notes")

headers = st.columns([3, 1, 3, 2, 2, 2, 1, 2])
headers[0].markdown("**Customer**")
headers[1].markdown("**Risk Score**")
headers[2].markdown("**Current Payment Method**")
headers[3].markdown("**Recommended Payment Method**")
headers[4].markdown("**Approached**")
headers[5].markdown("**Notes**")
headers[6].markdown("**N/A**")
headers[7].markdown("**N/A Notes**")

edited_rows = []

for idx, row in display_df.iterrows():
    cols = st.columns([3, 1, 3, 2, 2, 2, 1, 2])
    cols[0].markdown(row["customer_name"].title())
    cols[1].markdown(f"{row['aggregate_risk_score']:.3f}")
    cols[2].markdown(row["current_payment_method"] if "current_payment_method" in row else "Unknown")
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

# ---- Export Button ----
st.markdown("#### 📤 Export Recommendation List")
export_df = display_df.copy()
export_df.rename(columns={
    "customer_name": "Customer",
    "aggregate_risk_score": "Risk Score",
    "recommended_payment_method": "Recommended Payment Method"
}, inplace=True)

csv = export_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Recommendations as CSV",
    data=csv,
    file_name='payment_method_recommendations.csv',
    mime='text/csv',
)
