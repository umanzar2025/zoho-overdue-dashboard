
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
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

# Ensure columns exist
for col in ["approached", "notes", "is_na", "na_notes"]:
    if col not in merged_df.columns:
        merged_df[col] = False if col == "approached" or col == "is_na" else ""

merged_df["approached"] = merged_df["approached"].fillna(False)
merged_df["notes"] = merged_df["notes"].fillna("")
merged_df["is_na"] = merged_df["is_na"].fillna(False)
merged_df["na_notes"] = merged_df["na_notes"].fillna("")

# Simulated payment method (optional to be replaced later)
merged_df["current_payment_method"] = np.where(merged_df.index % 3 == 0, "Check", "Bank Transfer")

# ---- UI Controls ----
st.sidebar.header("⚙️ Recommendation Settings")
risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)

# Organization Filter
st.sidebar.header("🏢 Organization Filter")
org_option = st.sidebar.radio("Select Organization", ["Combined", "Go Fleet", "Zenduit"])

# ---- Recommendation Logic ----
def suggest_payment_method(row):
    if pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
        return "Recommend Stripe"
    else:
        return "Keep Current"

merged_df["recommended_payment_method"] = merged_df.apply(suggest_payment_method, axis=1)

# ===== Collection Trend Data (Simulated)
st.markdown("## 📊 Monthly Collection Trend")
org_filter = st.selectbox("Select Organization", ["Combined", "Go Fleet", "Zenduit"])

np.random.seed(42)
payment_modes = ["Bank Transfer", "Check", "Stripe", "Cash"]
dates = pd.date_range(start="2025-01-01", end=datetime.today(), freq="M")
collection_data = pd.DataFrame({
    "date": np.tile(dates, len(payment_modes)),
    "payment_mode": np.repeat(payment_modes, len(dates)),
    "amount": np.random.randint(5000, 50000, len(dates) * len(payment_modes))
})

collection_data["month"] = collection_data["date"].dt.to_period("M").astype(str)

monthly_summary = collection_data.groupby(["month", "payment_mode"])["amount"].sum().reset_index()

fig = px.line(monthly_summary, x="month", y="amount", color="payment_mode", markers=True, title="Monthly Collection Trend")
fig.update_layout(xaxis_title="Month", yaxis_title="Amount ($)", legend_title="Payment Mode")
st.plotly_chart(fig, use_container_width=True)

# ====== Pie Chart ======
st.markdown("### 🥧 Collection Breakdown (Past 3 Months)")
recent_months = collection_data["month"].sort_values().unique()[-3:]
pie_data = collection_data[collection_data["month"].isin(recent_months)]

pie_summary = pie_data.groupby("payment_mode")["amount"].sum().reset_index()
fig_pie = px.pie(pie_summary, names="payment_mode", values="amount", title="Collection Share by Payment Mode (Last 3 Months)")
st.plotly_chart(fig_pie, use_container_width=True)

# ======= Risk Recommendation + Follow-ups =======
st.markdown("## 📌 Customer Risk Analysis & Payment Method Recommendation")

header_cols = st.columns([3, 1, 3, 2, 2, 2, 1, 2])
header_cols[0].markdown("**Customer**")
header_cols[1].markdown("**Risk Score**")
header_cols[2].markdown("**Current Payment Method**")
header_cols[3].markdown("**Recommended Payment Method**")
header_cols[4].markdown("**Approached**")
header_cols[5].markdown("**Notes**")
header_cols[6].markdown("**N/A**")
header_cols[7].markdown("**N/A Notes**")

edited_rows = []

for idx, row in merged_df.iterrows():
    cols = st.columns([3, 1, 3, 2, 2, 2, 1, 2])
    cols[0].markdown(f"{row['customer_name'].title()}")
    cols[1].markdown(f"{row['aggregate_risk_score']:.3f}")
    cols[2].markdown(row["current_payment_method"])
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

