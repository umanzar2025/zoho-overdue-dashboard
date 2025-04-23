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
    df["organization"] = org_name

    # Display available columns for debugging
    st.write(f"📁 Columns in {org_name} CSV:", df.columns.tolist())

    # Check if 'Due Date' column exists
    if "Due Date" in df.columns:
        df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")
    else:
        st.warning(f"'Due Date' column not found in {org_name} CSV. Check column names or file format.")

    return df

# Load data
gofleet_df = load_latest_csv("gofleet_corporation", "GoFleet Corporation")
zenduit_df = load_latest_csv("zenduit_corporation", "Zenduit Corporation")

# Combine
combined_df = pd.concat([gofleet_df, zenduit_df], ignore_index=True)

# ===== UI Filter =====
org_choice = st.selectbox("View invoices for", ["Combined", "GoFleet", "Zenduit"])

if org_choice == "GoFleet":
    df_display = gofleet_df.copy()
elif org_choice == "Zenduit":
    df_display = zenduit_df.copy()
else:
    df_display = combined_df.copy()

# ===== Display Section =====
if not df_display.empty:
    try:
        display_df = df_display[["Invoice Number", "Customer Name", "Due Date", "total", "balance", "status", "is_emailed"]].copy()
        display_df.rename(columns={
            "Invoice Number": "Invoice #",
            "Customer Name": "Customer",
            "Due Date": "Due Date",
            "total": "Amount",
            "balance": "Balance",
            "status": "Status",
            "is_emailed": "Email Sent"
        }, inplace=True)

        display_df["Email Sent"] = display_df["Email Sent"].apply(lambda x: "✅" if x else "❌")
        st.success(f"Fetched {len(display_df)} invoices for {org_choice}.")
        st.dataframe(display_df)

        # Chart: Top 10 Customers
        st.subheader("📊 Top 10 Customers by Overdue Balance")
        top_customers = df_display.groupby("Customer Name")["balance"].sum().nlargest(10).reset_index()
        st.bar_chart(top_customers.rename(columns={"Customer Name": "Customer", "balance": "Overdue Balance"}).set_index("Customer"))

        # Chart: Invoices by Due Date
        st.subheader("📈 Overdue Invoices by Due Date")
        due_counts = df_display["Due Date"].value_counts().sort_index()
        st.line_chart(due_counts)

    except KeyError as e:
        st.warning(f"Missing expected column: {e}. Check your CSV format.")
else:
    st.info("No overdue invoice data available.")