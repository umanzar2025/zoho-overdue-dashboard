import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import glob
import numpy as np

st.set_page_config(page_title="Payment Dashboard", layout="wide")
st.title("💳 Payment Dashboard")

# ---- Load latest risk score file ----
st.markdown("## 🔄 Loading Latest Risk Scores")
risk_score_files = sorted(glob.glob("data/overdue_customer_risk_scores_*.csv"), reverse=True)

if not risk_score_files:
    st.error("❗ No risk score files found.")
    st.stop()

latest_risk_score_file = risk_score_files[0]
st.info(f"Using risk score file: {os.path.basename(latest_risk_score_file)}")
risk_df = pd.read_csv(latest_risk_score_file)
risk_df["customer_name"] = risk_df["customer_name"].str.strip().str.lower()

# ---- Add organization column ----
if "organization" not in risk_df.columns:
    risk_df["organization"] = np.where(risk_df.index % 2 == 0, "GoFleet", "Zenduit")

# ---- Load follow-up notes ----
FOLLOWUP_FILE = "data/payment_followup_notes.csv"
os.makedirs("data", exist_ok=True)

if os.path.exists(FOLLOWUP_FILE):
    followup_df = pd.read_csv(FOLLOWUP_FILE)
    followup_df["customer_name"] = followup_df["customer_name"].str.strip().str.lower()
else:
    followup_df = pd.DataFrame(columns=["customer_name", "approached", "notes", "is_na", "na_notes"])

# ---- Merge ----
merged_df = pd.merge(risk_df, followup_df, on="customer_name", how="left")
merged_df["approached"] = merged_df["approached"].fillna(False)
merged_df["notes"] = merged_df["notes"].fillna("")
merged_df["is_na"] = merged_df["is_na"].fillna(False)
merged_df["na_notes"] = merged_df["na_notes"].fillna("")
merged_df["current_payment_method"] = np.where(merged_df.index % 4 == 0, "Check",
                                     np.where(merged_df.index % 4 == 1, "Bank Transfer",
                                     np.where(merged_df.index % 4 == 2, "Stripe", "Cash")))

# ---- Sidebar Controls ----
st.sidebar.header("⚙️ Recommendation Settings")
risk_threshold = st.sidebar.slider("Risk Score Threshold for Stripe Recommendation", 0.0, 1.0, 0.5, 0.05)

# ---- Recommendation Logic ----
def recommend(row):
    if pd.notna(row["aggregate_risk_score"]) and row["aggregate_risk_score"] >= risk_threshold:
        return "Recommend Stripe"
    else:
        return "Keep Current"

merged_df["recommended_payment_method"] = merged_df.apply(recommend, axis=1)

# ---- Monthly Collection Trend ----
st.markdown("## 📊 Monthly Collection Trend")

org_filter = st.selectbox("Select Organization", ["Combined", "GoFleet", "Zenduit"])

# Simulated collection data
if "payment_date" not in merged_df.columns:
    merged_df["payment_date"] = pd.date_range(start="2024-12-01", periods=len(merged_df), freq="D")

df_chart = merged_df.copy()

if org_filter != "Combined":
    df_chart = df_chart[df_chart["organization"] == org_filter]

df_chart["payment_date"] = pd.to_datetime(df_chart["payment_date"])
df_chart["month"] = df_chart["payment_date"].dt.to_period('M').astype(str)

df_chart_grouped = df_chart.groupby(["month", "current_payment_method"]).size().reset_index(name='amount')

fig = px.line(df_chart_grouped, x="month", y="amount", color="current_payment_method", markers=True,
              title="Monthly Collection Trend")
fig.update_layout(xaxis_title="Month", yaxis_title="Amount ($)", legend_title="Payment Mode")
st.plotly_chart(fig, use_container_width=True)

# ---- Pie Chart for overdue customers ----
st.markdown("## 🥧 Overdue Distribution by Payment Method")

overdue_pie = merged_df.copy()
overdue_pie["amount"] = 1  # placeholder for count

pie_data = overdue_pie.groupby("current_payment_method")["amount"].sum().reset_index()

fig_pie = px.pie(pie_data, names="current_payment_method", values="amount", title="Overdue by Payment Method")
st.plotly_chart(fig_pie, use_container_width=True)

# ---- Recommended Payment Methods ----
st.markdown("## 🧭 Customer Risk Analysis & Payment Method Recommendation")
top_n = st.selectbox("Select number of customers to display", [20, 50, 100, 200, "All"])

display_df = merged_df.copy()
if top_n != "All":
    display_df = display_df.head(int(top_n))

# Add headers
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

for idx, row in display_df.iterrows():
    cols = st.columns([3, 1, 3, 2, 2, 2, 1, 2])
    cols[0].markdown(f"{row['customer_name'].title()}")
    cols[1].markdown(f"{row['aggregate_risk_score']:.3f}")
    cols[2].markdown(row["current_payment_method"])
    cols[3].markdown(row["recommended_payment_method"])
    approached = cols[4].checkbox("Approached", row["approached"], key=f"approached_{idx}")
    notes = cols[5].text_input("Notes", row["notes"], key=f"notes_{idx}")
    is_na = cols[6].checkbox("N/A", row["is_na"], key=f"isna_{idx}")
    na_notes = cols[7].text_input("N/A Notes", row["na_notes"], key=f"nanotes_{idx}")

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

# ---- Export
st.markdown("### 📥 Export Recommendation List")
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
