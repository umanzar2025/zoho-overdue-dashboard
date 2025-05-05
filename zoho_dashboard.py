import streamlit as st
import pandas as pd
import glob

st.set_page_config(page_title="Overdue Invoices Dashboard", layout="wide")
st.title("📄 Overdue Invoices Dashboard")

# ===== Load Latest CSV for Each Org =====
def load_latest_csv(prefix, org_name):
    files = sorted(glob.glob(f"{prefix}_overdue_invoices_*.csv"), reverse=True)
    if not files:
        st.warning(f"No CSV file found for {org_name}")
        return pd.DataFrame()

    df = pd.read_csv(files[0])
    df.columns = [col.strip().lower() for col in df.columns]
    df["organization"] = org_name

    if "due_date" in df.columns:
        df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
    else:
        st.warning(f"'due_date' column not found in {org_name} CSV. Check column names or file format.")

    return df

# ===== Load data =====
gofleet_df = load_latest_csv("gofleet_corporation", "GoFleet Corporation")
zenduit_df = load_latest_csv("zenduit_corporation", "Zenduit Corporation")
combined_df = pd.concat([gofleet_df, zenduit_df], ignore_index=True)

# ===== UI Filter =====
org_choice = st.selectbox("View invoices for", ["Combined", "GoFleet", "Zenduit"])

if org_choice == "GoFleet":
    df_display = gofleet_df.copy()
elif org_choice == "Zenduit":
    df_display = zenduit_df.copy()
else:
    df_display = combined_df.copy()

# ===== CFO Summary Box =====
st.markdown("### 💼 CFO Snapshot: High-Level Insights")

if not df_display.empty:
    total_balance = df_display["balance"].sum()
    avg_balance = df_display["balance"].mean()
    top_customer = df_display.groupby("customer_name")["balance"].sum().idxmax()
    top_balance = df_display.groupby("customer_name")["balance"].sum().max()

    st.info(
        f"""
        - **Total Overdue Balance:** ${total_balance:,.2f}  
        - **Average Invoice Balance:** ${avg_balance:,.2f}  
        - **Top Customer (By Balance):** {top_customer} (${top_balance:,.2f})
        """
    )

# ===== High-Risk Flagging =====
if "due_date" in df_display.columns:
    today = pd.Timestamp.today()
    df_display["days_overdue"] = (today - df_display["due_date"]).dt.days
    df_display["risk_flag"] = df_display.apply(
        lambda row: "🚨 High Risk" if row["days_overdue"] > 90 or row["balance"] > 10000 else "", axis=1
    )

# ===== Aggregate Risk Scoring and Export =====
st.markdown("### 🚦 Aggregate Risk Scoring")

if not df_display.empty:
    # Calculate High Risk Invoice Count
    risk_invoice_count = df_display[df_display["risk_flag"] != ""].groupby("customer_name").size().rename("high_risk_invoice_count")

    # Aggregate per customer
    customer_summary = df_display.groupby("customer_name").agg({
        "balance": "sum",
        "days_overdue": "mean"
    }).rename(columns={"balance": "total_overdue_balance", "days_overdue": "avg_days_overdue"}).join(risk_invoice_count, how="left").fillna(0)

    # Normalize metrics
    customer_summary["normalized_balance"] = customer_summary["total_overdue_balance"] / customer_summary["total_overdue_balance"].max()
    customer_summary["normalized_days"] = customer_summary["avg_days_overdue"] / customer_summary["avg_days_overdue"].max()
    customer_summary["normalized_risk_invoices"] = customer_summary["high_risk_invoice_count"] / customer_summary["high_risk_invoice_count"].max()

    # Weight sliders
    st.sidebar.header("⚙️ Risk Score Weight Settings")
    balance_weight = st.sidebar.slider("Overdue Balance Weight", 0.0, 1.0, 0.5, 0.05)
    max_days_weight = 1.0 - balance_weight
    days_weight = st.sidebar.slider("Days Overdue Weight", 0.0, max_days_weight, 0.3, 0.05)
    invoice_count_weight = 1.0 - balance_weight - days_weight

    st.sidebar.write("High Risk Invoice Count Weight (calculated):", round(invoice_count_weight, 2))

    # Aggregate Risk Score
    customer_summary["aggregate_risk_score"] = (
        customer_summary["normalized_balance"] * balance_weight +
        customer_summary["normalized_days"] * days_weight +
        customer_summary["normalized_risk_invoices"] * invoice_count_weight
    )

    customer_summary_sorted = customer_summary.sort_values("aggregate_risk_score", ascending=False).reset_index()

    # ✅ Allow user to select Top N dynamically
    st.markdown("#### 🧹 Top Risky Customers (Based on Aggregate Score)")
    top_n_option = st.selectbox("Select number of top risky customers to display", [20, 50, 100, 200, 500, "All"])

    if top_n_option == "All":
        st.dataframe(customer_summary_sorted[["customer_name", "total_overdue_balance", "avg_days_overdue", "high_risk_invoice_count", "aggregate_risk_score"]])
    else:
        st.dataframe(customer_summary_sorted[["customer_name", "total_overdue_balance", "avg_days_overdue", "high_risk_invoice_count", "aggregate_risk_score"]].head(int(top_n_option)))

if not df_display.empty:
# ✅ Export for Payment Dashboard
    from datetime import datetime
    export_df = customer_summary_sorted.copy()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"data/overdue_customer_risk_scores_{timestamp}.csv"
    export_df.to_csv(export_filename, index=False)
    st.success(f"✅ Risk score data exported for Payment Dashboard ({timestamp})")

else:
    st.info("No overdue invoice data available to calculate risk scores.")

# 🚩 High Risk Invoices
st.markdown("### 🚩 High-Risk Invoices")
high_risk_df = df_display[df_display["risk_flag"] != ""]
if not high_risk_df.empty:
    st.dataframe(high_risk_df[["invoice_number", "customer_name", "due_date", "balance", "days_overdue", "risk_flag"]])
else:
    st.success("No high-risk invoices at the moment. 🎉")

# ===== Top 20 High-Risk Customers =====
if not high_risk_df.empty:
    st.markdown("### 🧾 Top 20 High-Risk Customers by Balance")
    high_risk_customers = (
        high_risk_df.groupby("customer_name")["balance"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
        .reset_index()
        .rename(columns={"customer_name": "Customer", "balance": "Total High-Risk Balance"})
    )
    high_risk_customers["Total High-Risk Balance"] = high_risk_customers["Total High-Risk Balance"].map("${:,.2f}".format)
    st.dataframe(high_risk_customers)

# ===== Display Section =====
if not df_display.empty:
    try:
        display_df = df_display[["invoice_number", "customer_name", "due_date", "total", "balance", "status", "is_emailed"]].copy()
        display_df.rename(columns={
            "invoice_number": "Invoice #",
            "customer_name": "Customer",
            "due_date": "Due Date",
            "total": "Amount",
            "balance": "Balance",
            "status": "Status",
            "is_emailed": "Email Sent"
        }, inplace=True)

        display_df["Amount"] = display_df["Amount"].map("${:,.2f}".format)
        display_df["Balance"] = display_df["Balance"].map("${:,.2f}".format)
        display_df["Email Sent"] = display_df["Email Sent"].apply(lambda x: "✅" if x else "❌")

        st.success(f"Fetched {len(display_df)} invoices for {org_choice}.")
        st.dataframe(display_df)

        st.subheader("📊 Top 10 Customers by Overdue Balance")
        top_customers = df_display.groupby("customer_name")["balance"].sum().nlargest(10).reset_index()
        top_customers.rename(columns={"customer_name": "Customer", "balance": "Overdue Balance"}, inplace=True)
        top_customers["Overdue Balance"] = top_customers["Overdue Balance"].round(2)
        st.bar_chart(top_customers.set_index("Customer"))

        st.subheader("📈 Overdue Invoices by Due Date")
        due_counts = df_display["due_date"].value_counts().sort_index()
        st.line_chart(due_counts)

    except KeyError as e:
        st.warning(f"Missing expected column: {e}. Check your CSV format.")
else:
    st.info("No overdue invoice data available.")

# ✅ DEBUG MARKER (Always runs)
st.warning("✅ Debug: Payment breakdown code is here")

