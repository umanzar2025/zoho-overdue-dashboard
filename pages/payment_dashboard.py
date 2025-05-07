import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import glob
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Finance Dashboard (Team Version with Google Sheets Follow-ups)", layout="wide")
st.title("💳 Finance Dashboard (Team Version with Google Sheets Follow-ups)")

# ----------------------------
# Connect to Google Sheet
# ----------------------------
SHEET_NAME = "Finance Follow-up Notes"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
JSON_KEY_FILE = "secrets/payment_dashboard_google.json"  # Using streamlit secrets
import json

credentials_dict = st.secrets["gcp_service_account"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

gc = gspread.authorize(credentials)

try:
    sheet = gc.open(SHEET_NAME).sheet1
except gspread.SpreadsheetNotFound:
    st.error(f"Spreadsheet '{SHEET_NAME}' not found. Please create it and share with the service account.")
    st.stop()

# Read Google Sheet into DataFrame
followup_data = sheet.get_all_records()
followup_df = pd.DataFrame(followup_data)
if followup_df.empty:
    followup_df = pd.DataFrame(columns=["customer_name", "approached", "notes", "is_na", "na_notes"])

followup_df["customer_name"] = followup_df["customer_name"].str.strip().str.lower()

# ----------------------------
# Load Risk Scores from CSV
# ----------------------------
st.markdown("## 🔄 Loading Latest Risk Scores")
risk_score_files = sorted(glob.glob("data/overdue_customer_risk_scores_*.csv"), reverse=True)

if not risk_score_files:
    st.error("❗ No risk score files found. Please run the overdue invoices extraction first.")
    st.stop()

latest_risk_score_file = risk_score_files[0]
st.info(f"Using risk score file: {os.path.basename(latest_risk_score_file)}")
risk_df = pd.read_csv(latest_risk_score_file)
risk_df["customer_name"] = risk_df["customer_name"].str.strip().str.lower()

# Merge risk scores with follow-ups
merged_df = pd.merge(risk_df, followup_df, on="customer_name", how="left")

for col in ["approached", "notes", "is_na", "na_notes"]:
    if col not in merged_df.columns:
        merged_df[col] = False if col in ["approached", "is_na"] else ""

merged_df["approached"] = merged_df["approached"].fillna(False)
merged_df["notes"] = merged_df["notes"].fillna("")
merged_df["is_na"] = merged_df["is_na"].fillna(False)
merged_df["na_notes"] = merged_df["na_notes"].fillna("")

# Simulated payment method
if "current_payment_method" not in merged_df.columns:
    merged_df["current_payment_method"] = np.where(merged_df.index % 3 == 0, "Check", "Bank Transfer")

# ----------------------------
# Recommendation Logic
# ----------------------------
st.sidebar.header("⚙️ Recommendation Settings")
risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)

def suggest_payment_method(row):
    if pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
        return "Recommend Stripe"
    else:
        return "Keep Current"

merged_df["recommended_payment_method"] = merged_df.apply(suggest_payment_method, axis=1)

# ----------------------------
# Chart - Monthly Collection (Simulated)
# ----------------------------
st.markdown("## 📊 Monthly Collection Trend")
org_filter = st.selectbox("Select Organization", ["Combined", "Go Fleet", "Zenduit"])

np.random.seed(42)
payment_modes = ["Bank Transfer", "Check", "Stripe"]
dates = pd.date_range(start="2025-01-01", end=datetime.today(), freq="D")
collection_data = pd.DataFrame({
    "date": np.tile(dates, len(payment_modes)),
    "payment_mode": np.repeat(payment_modes, len(dates)),
    "amount": np.random.randint(5000, 50000, len(dates) * len(payment_modes))
})

collection_data["month"] = pd.to_datetime(collection_data["date"]).dt.to_period("M").dt.to_timestamp()
monthly_summary = collection_data.groupby(["month", "payment_mode"])["amount"].sum().reset_index()

fig = px.line(monthly_summary, x="month", y="amount", color="payment_mode", markers=True, title="Monthly Collection Trend by Payment Method")
fig.update_layout(xaxis_title="Month", yaxis_title="Amount ($)", legend_title="Payment Mode")
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Chart - Collection Breakdown
# ----------------------------
st.markdown("### 🥧 Collection Breakdown (Past 3 Months)")
recent_months = monthly_summary["month"].drop_duplicates().sort_values().iloc[-3:]
pie_data = monthly_summary[monthly_summary["month"].isin(recent_months)]

pie_summary = pie_data.groupby("payment_mode")["amount"].sum().reset_index()
fig_pie = px.pie(pie_summary, names="payment_mode", values="amount", title="Collection Share by Payment Mode (Last 3 Months)")
st.plotly_chart(fig_pie, use_container_width=True)

# ----------------------------
# Customer Risk Analysis and Follow-Up
# ----------------------------
st.markdown("## 📌 Customer Risk Analysis & Payment Method Recommendation")

display_df = merged_df.copy()
display_df.rename(columns={
    "customer_name": "Customer",
    "aggregate_risk_score": "Risk Score",
    "current_payment_method": "Current Payment Method",
    "recommended_payment_method": "Recommended Payment Method",
    "approached": "Approached",
    "notes": "Notes",
    "is_na": "N/A",
    "na_notes": "N/A Notes"
}, inplace=True)

editable_cols = ["Approached", "Notes", "N/A", "N/A Notes"]
edited_df = st.data_editor(display_df, num_rows="dynamic", use_container_width=True, disabled=[
    c for c in display_df.columns if c not in editable_cols
])

# ----------------------------
# Save Follow-up Notes to Google Sheets
# ----------------------------
if st.button("💾 Save Follow-up Notes"):
    save_df = edited_df[["Customer", "Approached", "Notes", "N/A", "N/A Notes"]].copy()
    save_df.rename(columns={"Customer": "customer_name", "Approached": "approached", "Notes": "notes", "N/A": "is_na", "N/A Notes": "na_notes"}, inplace=True)
    
    # Clear existing and write new data to Google Sheets
    sheet.clear()
    sheet.update([save_df.columns.values.tolist()] + save_df.values.tolist())

    st.success("✅ Follow-up notes saved successfully to Google Sheets!")

