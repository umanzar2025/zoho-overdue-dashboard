import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import glob
import numpy as np

# -------------------- Setup --------------------
st.set_page_config(page_title="Payment Dashboard", layout="wide")
st.title("💳 Payment Dashboard")

# -------------------- Load Risk Score --------------------
st.markdown("## 🔄 Loading Latest Risk Scores")
risk_score_files = sorted(glob.glob("data/overdue_customer_risk_scores_*.csv"), reverse=True)

if not risk_score_files:
    st.error("❗ No risk score files found. Please run the Zoho Dashboard first.")
    st.stop()

latest_risk_score_file = risk_score_files[0]
st.info(f"Using risk score file: {os.path.basename(latest_risk_score_file)}")
risk_df = pd.read_csv(latest_risk_score_file)
risk_df["customer_name"] = risk_df["customer_name"].str.strip().str.lower()

# -------------------- Load Follow-up Notes --------------------
FOLLOWUP_FILE = "data/payment_followup_notes.csv"
os.makedirs("data", exist_ok=True)

if os.path.exists(FOLLOWUP_FILE):
    followup_df = pd.read_csv(FOLLOWUP_FILE)
    followup_df["customer_name"] = followup_df["customer_name"].str.strip().str.lower()
else:
    followup_df = pd.DataFrame(columns=["customer_name", "approached", "notes", "is_na", "na_notes"])

# Merge risk and follow-up
merged_df = pd.merge(risk_df, followup_df, on="customer_name", how="left")
for col in ["approached", "notes", "is_na", "na_notes"]:
    merged_df[col] = merged_df.get(col, False if col in ["approached", "is_na"] else "")

merged_df["approached"] = merged_df["approached"].fillna(False)
merged_df["notes"] = merged_df["notes"].fillna("")
merged_df["is_na"] = merged_df["is_na"].fillna(False)
merged_df["na_notes"] = merged_df["na_notes"].fillna("")

# -------------------- Sidebar Filters --------------------
st.sidebar.header("⚙️ Recommendation Settings")
risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)

st.sidebar.header("🏢 Organization Filter")
org_filter = st.sidebar.radio("Select Organization", ["Combined", "Go Fleet", "Zenduit"])

# -------------------- Recommendation Logic --------------------
def suggest_payment_method(row):
    if pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
        return "Recommend Stripe"
    return "Keep Current"

merged_df["recommended_payment_method"] = merged_df.apply(suggest_payment_method, axis=1)

# -------------------- Simulated Collection Data --------------------
np.random.seed(42)
payment_modes = ["Bank Transfer", "Check", "Stripe", "Cash"]
dates = pd.date_range(start="2025-01-01", end=datetime.today(), freq="D")
organizations = ["Go Fleet", "Zenduit"]

collection_data = pd.DataFrame({
    "date": np.random.choice(dates, 500),
    "payment_mode": np.random.choice(payment_modes, 500),
    "organization": np.random.choice(organizations, 500),
    "amount": np.random.randint(1000, 20000, 500)
})
collection_data["month"] = collection_data["date"].dt.to_period("M").astype(str)

if org_filter != "Combined":
    filtered_data = collection_data[collection_data["organization"] == org_filter]
else:
    filtered_data = collection_data.copy()

# -------------------- Monthly Collection Trend --------------------
st.markdown("## 📊 Monthly Collection Trend")

monthly_summary = filtered_data.groupby(["month", "payment_mode"])["amount"].sum().reset_index()

fig = px.line(monthly_summary, x="month", y="amount", color="payment_mode", markers=True, title=f"Monthly Collection Trend ({org_filter})")
fig.update_layout(xaxis_title="Month", yaxis_title="Amount ($)", legend_title="Payment Mode")
st.plotly_chart(fig, use_container_width=True)

# -------------------- Collection Breakdown (Pie Chart) --------------------
st.markdown("### 🥧 Collection Breakdown (Past 3 Months)")

recent_months = sorted(filtered_data["month"].unique())[-3:]
pie_data = filtered_data[filtered_data["month"].isin(recent_months)]
pie_summary = pie_data.groupby("payment_mode")["amount"].sum().reset_index()

fig_pie = px.pie(pie_summary, names="payment_mode", values="amount", title=f"Collection Share by Payment Mode (Last 3 Months) - {org_filter}")
st.plotly_chart(fig_pie, use_container_width=True)

# -------------------- Risk Recommendation + Follow-ups --------------------
st.markdown("## 📌 Customer Risk Analysis & Payment Method Recommendation")

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
