import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import os
import glob

st.set_page_config(page_title="Payment Dashboard", layout="wide")
st.title("💳 Payment Dashboard")

# ----------------------
# Load latest risk score file
# ----------------------
st.header("📥 Loading Latest Risk Scores")

risk_score_files = sorted(glob.glob("data/overdue_customer_risk_scores_*.csv"), reverse=True)

if not risk_score_files:
    st.error("❗ No risk score files found.")
    st.stop()

latest_risk_score_file = risk_score_files[0]
st.info(f"Using risk score file: {os.path.basename(latest_risk_score_file)}")

risk_df = pd.read_csv(latest_risk_score_file)
risk_df["customer_name"] = risk_df["customer_name"].str.strip().str.lower()

# ----------------------
# Load historical paid invoices file (append new)
# ----------------------

PAID_FILE = "data/paid_invoices_history.csv"
os.makedirs("data", exist_ok=True)

if os.path.exists(PAID_FILE):
    paid_df = pd.read_csv(PAID_FILE)
else:
    paid_df = pd.DataFrame(columns=["date", "organization", "customer_name", "payment_mode", "amount"])

# Simulated new paid invoices (for demo - replace with real pull later)
new_data = pd.DataFrame({
    "date": pd.date_range(end=pd.Timestamp.today(), periods=20),
    "organization": np.random.choice(["GoFleet", "Zenduit"], 20),
    "customer_name": np.random.choice(risk_df["customer_name"], 20),
    "payment_mode": np.random.choice(["Check", "Stripe", "Bank Transfer", "Cash"], 20),
    "amount": np.random.randint(500, 5000, 20)
})

paid_df = pd.concat([paid_df, new_data], ignore_index=True)
paid_df.to_csv(PAID_FILE, index=False)

# ----------------------
# Payment collection trend chart
# ----------------------

st.header("📊 Monthly Collection Trend")

org_filter = st.selectbox("Select Organization", ["Combined", "GoFleet", "Zenduit"])

chart_df = paid_df.copy()

if org_filter != "Combined":
    chart_df = chart_df[chart_df["organization"] == org_filter]

chart_df["month"] = pd.to_datetime(chart_df["date"]).dt.to_period("M").dt.to_timestamp()

grouped = chart_df.groupby(["month", "payment_mode"])["amount"].sum().reset_index()

fig = px.line(grouped, x="month", y="amount", color="payment_mode", markers=True,
              title="Monthly Collection Trend",
              labels={"amount": "Amount ($)", "month": "Month", "payment_mode": "Payment Mode"})

st.plotly_chart(fig, use_container_width=True)

# ----------------------
# Risk Analysis + Recommendation
# ----------------------

st.header("🧭 Customer Risk Analysis & Payment Method Recommendation")

FOLLOWUP_FILE = "data/payment_followup_notes.csv"

if os.path.exists(FOLLOWUP_FILE):
    followup_df = pd.read_csv(FOLLOWUP_FILE)
    followup_df["customer_name"] = followup_df["customer_name"].str.strip().str.lower()
else:
    followup_df = pd.DataFrame(columns=["customer_name", "approached", "notes", "is_na", "na_notes"])

merged_df = pd.merge(risk_df, followup_df, on="customer_name", how="left")

for col in ["approached", "notes", "is_na", "na_notes"]:
    if col not in merged_df.columns:
        merged_df[col] = False if "approached" in col or "is_na" in col else ""

merged_df["approached"] = merged_df["approached"].fillna(False)
merged_df["notes"] = merged_df["notes"].fillna("")
merged_df["is_na"] = merged_df["is_na"].fillna(False)
merged_df["na_notes"] = merged_df["na_notes"].fillna("")

# Remove N/A customers
merged_df = merged_df[merged_df["is_na"] == False]

# Simulated current payment method
merged_df["current_payment_method"] = np.where(merged_df.index % 3 == 0, "Check", "Bank Transfer")

# Recommendation logic
st.sidebar.header("⚙️ Recommendation Settings")
risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)

def recommend(row):
    if pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
        return "Recommend Stripe"
    else:
        return "Keep Current"

merged_df["recommended_payment_method"] = merged_df.apply(recommend, axis=1)

st.subheader("📋 Follow-up Status and Notes")

top_n_option = st.selectbox("Select number of customers to display", [20, 50, 100, 200, "All"])

display_df = merged_df.copy()

if top_n_option != "All":
    display_df = display_df.head(int(top_n_option))

# Table headers
header_cols = st.columns([3, 1, 2, 2, 1, 2, 1, 2])
header_labels = ["Customer", "Risk Score", "Current Payment Method", "Recommended Payment Method", "Approached", "Notes", "N/A", "N/A Notes"]

for col, label in zip(header_cols, header_labels):
    col.markdown(f"**{label}**")

# Rows
edited_rows = []

for idx, row in display_df.iterrows():
    cols = st.columns([3, 1, 2, 2, 1, 2, 1, 2])
    cols[0].markdown(row["customer_name"].title())
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

# ----------------------
# Export recommendations
# ----------------------

st.subheader("📤 Export Recommendation List")

export_df = display_df.copy()
export_df.rename(columns={
    "customer_name": "Customer",
    "aggregate_risk_score": "Risk Score",
    "current_payment_method": "Current Payment Method",
    "recommended_payment_method": "Recommended Payment Method"
}, inplace=True)

csv = export_df.to_csv(index=False).encode("utf-8")

st.download_button("Download Recommendations as CSV", data=csv, file_name="payment_method_recommendations.csv", mime="text/csv")
