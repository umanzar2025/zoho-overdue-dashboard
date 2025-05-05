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
merged_df["approached"] = merged_df["approached"].fillna(False)
merged_df["notes"] = merged_df["notes"].fillna("")
merged_df["is_na"] = merged_df["is_na"].fillna(False)
merged_df["na_notes"] = merged_df["na_notes"].fillna("")

# --------------------------------
# 🎛️ Organization Payment Analysis
st.title("📊 Payment Method Breakdown")

org_choice = st.selectbox("Choose Organization", ["GoFleet Corporation", "Zenduit Corporation", "Combined"])

@st.cache_data(show_spinner=False)
def get_payment_data():
    dummy_data = pd.DataFrame({
        "organization": ["GoFleet Corporation"] * 50 + ["Zenduit Corporation"] * 50,
        "payment_mode": np.random.choice(["Check", "Bank Transfer", "Stripe"], 100),
        "amount": np.random.randint(500, 5000, 100),
        "date": pd.date_range(end=pd.Timestamp.today(), periods=100)
    })
    return dummy_data

payment_df = get_payment_data()

if org_choice != "Combined":
    payment_df = payment_df[payment_df["organization"] == org_choice]

if payment_df.empty:
    st.warning("No payment data available.")
else:
    # 📊 Pie Chart
    summary = payment_df.groupby("payment_mode")["amount"].sum().reset_index().rename(columns={"amount": "total"})
    summary["percentage"] = (summary["total"] / summary["total"].sum() * 100).round(2)

    fig = px.pie(summary, names="payment_mode", values="total", hole=0.4)
    fig.update_traces(textinfo="label+percent", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    # 📈 Trend Line
    payment_df["month"] = payment_df["date"].dt.to_period("M").dt.to_timestamp()
    trend = payment_df.groupby(["month", "payment_mode"])["amount"].sum().reset_index()

    fig2 = px.line(trend, x="month", y="amount", color="payment_mode", markers=True, title="Monthly Collection Trend")
    fig2.update_layout(yaxis_tickprefix="$", xaxis_title="Month", yaxis_title="Amount ($)")
    st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------
# 🚦 Customer Risk Recommendations

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
top_n_option = st.selectbox("Select number of customers to display", [20, 50, 100, 200, "All"])
display_df = merged_df.copy()

if top_n_option != "All":
    display_df = display_df.head(int(top_n_option))

# ---- Follow-up Status & Notes ----
st.markdown("### ✅ Follow-up Status and Notes")

header_cols = st.columns([3, 1, 3, 2, 2, 3, 1, 3])
header_cols[0].markdown("**Customer**")
header_cols[1].markdown("**Risk Score**")
header_cols[2].markdown("**Current Payment Method**")
header_cols[3].markdown("**Recommended Payment Method**")
header_cols[4].markdown("**Approached**")
header_cols[5].markdown("**Notes**")
header_cols[6].markdown("**N/A**")
header_cols[7].markdown("**N/A Notes**")

edited_rows = []

for idx, row in display_df.iterrows():
    cols = st.columns([3, 1, 3, 2, 2, 3, 1, 3])
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

# ---- Save Follow-up Notes ----
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
