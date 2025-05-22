import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import glob
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("📊 Finance Dashboard (Team Version with Google Sheets Follow-ups)")

# ======= Google Sheets Setup =======
SHEET_NAME = "Payment Dashboard - Follow-up Notes"
JSON_KEY_FILE = "secrets/payment_dashboard_google.json"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
gc = gspread.authorize(credentials)

try:
    sheet = gc.open(SHEET_NAME).sheet1
except gspread.exceptions.SpreadsheetNotFound:
    st.error("❗ Google Sheet not found. Please create it and share with the service account email.")
    st.stop()

# Load follow-up notes
data = sheet.get_all_records()
followup_df = pd.DataFrame(data)
if followup_df.empty:
    followup_df = pd.DataFrame(columns=["customer_name", "approached", "notes", "is_na", "na_notes"])

followup_df["customer_name"] = followup_df["customer_name"].astype(str).str.strip().str.lower()

# ======= Load Latest Risk Score CSV =======
st.markdown("## 📥 Loading Latest Risk Scores")
risk_score_files = sorted(glob.glob("data/overdue_customer_risk_scores_*.csv"), reverse=True)

if not risk_score_files:
    st.error("❗ No risk score files found. Please run Zoho overdue extraction first.")
    st.stop()

latest_risk_score_file = risk_score_files[0]
st.info(f"Using risk score file: {os.path.basename(latest_risk_score_file)}")
risk_df = pd.read_csv(latest_risk_score_file)
risk_df["customer_name"] = risk_df["customer_name"].str.strip().str.lower()

# ======= Merge risk with follow-up =======
merged_df = pd.merge(risk_df, followup_df, on="customer_name", how="left")

for col in ["approached", "notes", "is_na", "na_notes"]:
    if col not in merged_df.columns:
        merged_df[col] = False if col in ["approached", "is_na"] else ""

merged_df["approached"] = merged_df["approached"].fillna(False)
merged_df["notes"] = merged_df["notes"].fillna("")
merged_df["is_na"] = merged_df["is_na"].fillna(False)
merged_df["na_notes"] = merged_df["na_notes"].fillna("")

# ======= Payment History: Real Data =======
HISTORY_FILE = "data/payment_history.csv"
if os.path.exists(HISTORY_FILE):
    df = pd.read_csv(HISTORY_FILE)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["date", "amount"])
    df["month"] = df["date"].values.astype("datetime64[M]")
else:
    st.warning("⚠️ payment_history.csv not found. Using empty dataset.")
    df = pd.DataFrame(columns=["date", "payment_mode", "amount", "month"])

# ======= UI Filters =======
st.sidebar.header("⚙️ Recommendation Settings")
risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)

st.sidebar.header("🏢 Organization Filter")
org_option = st.sidebar.radio("Select Organization", ["Combined", "Go Fleet", "Zenduit"])

# ======= Recommendation Logic =======
def suggest_payment_method(row):
    if pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
        return "Recommend Stripe"
    else:
        return "Keep Current"

merged_df["recommended_payment_method"] = merged_df.apply(suggest_payment_method, axis=1)

# ======= Monthly Collection Trend =======
st.markdown("## 📊 Monthly Collection Trend")

monthly_summary = df.groupby(["month", "payment_mode"])["amount"].sum().reset_index()

fig = px.line(monthly_summary, x="month", y="amount", color="payment_mode", markers=True,
              title="Monthly Collection Trend by Payment Method")
fig.update_layout(xaxis_title="Month", yaxis_title="Amount ($)", legend_title="Payment Mode")
st.plotly_chart(fig, use_container_width=True)

# ======= Pie Chart for Last 3 Months =======
st.markdown("### 🥧 Collection Breakdown (Last 3 Months)")

if not df.empty:
    recent_months = df["month"].drop_duplicates().sort_values().iloc[-3:]
    pie_data = df[df["month"].isin(recent_months)]
    pie_summary = pie_data.groupby("payment_mode")["amount"].sum().reset_index()

    fig_pie = px.pie(pie_summary, names="payment_mode", values="amount",
                     title="Collection Share by Payment Mode (Last 3 Months)")
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.warning("⚠️ No data available for pie chart.")

# ======= Editable Customer Table =======
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
edited_df = st.data_editor(display_df, num_rows="dynamic", use_container_width=True,
                           disabled=[c for c in display_df.columns if c not in editable_cols])

# ======= Save Logic to Google Sheets =======
if st.button("💾 Save Follow-up Notes"):
    save_df = edited_df[["Customer", "Approached", "Notes", "N/A", "N/A Notes"]].copy()
    save_df.columns = ["customer_name", "approached", "notes", "is_na", "na_notes"]

    # Merge with previous data to preserve untouched rows
    original_df = pd.DataFrame(sheet.get_all_records())
    original_df["customer_name"] = original_df["customer_name"].astype(str).str.strip().str.lower()
    save_df["customer_name"] = save_df["customer_name"].astype(str).str.strip().str.lower()

    updated = pd.merge(original_df, save_df, on="customer_name", how="outer", suffixes=("", "_new"))

    for col in ["approached", "notes", "is_na", "na_notes"]:
        updated[col] = updated[f"{col}_new"].combine_first(updated[col])
        updated.drop(columns=[f"{col}_new"], inplace=True)

    sheet.clear()
    sheet.update([updated.columns.tolist()] + updated.values.tolist())
    st.success("✅ Follow-up notes saved to Google Sheet (with old values preserved)")
