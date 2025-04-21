import streamlit as st
import requests
import pandas as pd

# ===== ZOHO CREDENTIALS =====
refresh_token = "1000.70726dab2668b0965020fb3d8b76950d.0f1e66164f7cac0a89d1eaf55a666694"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

# ===== ZOHO TOKEN FUNCTION =====
def get_access_token():
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    token_data = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    resp = requests.post(token_url, data=token_data)
    return resp.json().get("access_token")

# ===== GET ORG ID FUNCTION =====
def get_organization_id(access_token):
    url = "https://www.zohoapis.com/books/v3/organizations"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    resp = requests.get(url, headers=headers)
    data = resp.json()
    return data['organizations'][0]['organization_id']

# ===== FETCH ALL INVOICES (WITH PAGINATION) =====
def get_overdue_invoices(access_token, org_id):
    invoices = []
    page = 1
    while True:
        url = f"https://www.zohoapis.com/books/v3/invoices?status=overdue&organization_id={org_id}&page={page}&per_page=200"
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        resp = requests.get(url, headers=headers)
        data = resp.json()
        if "invoices" in data:
            invoices.extend(data["invoices"])
        if not data.get("page_context", {}).get("has_more_page"):
            break
        page += 1
    return invoices

# ===== STREAMLIT DASHBOARD =====
st.set_page_config(page_title="Overdue Invoices", layout="wide")
st.title("📄 Overdue Invoices Dashboard")

if st.button("🔄 Refresh Overdue Invoices"):
    with st.spinner("Fetching data from Zoho..."):
        try:
            access_token = get_access_token()
            org_id = get_organization_id(access_token)
            invoices = get_overdue_invoices(access_token, org_id)

            if invoices:
                df = pd.DataFrame(invoices)

                # Display core invoice table
                st.success(f"Fetched {len(df)} invoices.")

                # Safely extract only key fields
                preview_cols = [
                    "invoice_number",
                    "customer_name",
                    "due_date",
                    "total",
                    "balance",
                    "status",
                    "is_emailed"
                ]
                display_df = df[preview_cols].copy()
                display_df.rename(columns={
                    "invoice_number": "Invoice #",
                    "customer_name": "Customer",
                    "due_date": "Due Date",
                    "total": "Amount",
                    "balance": "Balance",
                    "status": "Status",
                    "is_emailed": "Email Sent"
                }, inplace=True)
                display_df["Email Sent"] = display_df["Email Sent"].apply(lambda x: "✅" if x else "❌")
                st.dataframe(display_df)

                # Chart: Amount by Customer (Top 10)
                st.subheader("📊 Top 10 Customers by Total Overdue Amount")
                top_customers = df.groupby("customer_name")["balance"].sum().nlargest(10).reset_index()
                st.bar_chart(top_customers.rename(columns={"customer_name": "Customer", "balance": "Overdue Balance"}).set_index("Customer"))

                # Chart: Count of invoices by Due Date
                st.subheader("📈 Overdue Invoices by Due Date")
                due_counts = df["due_date"].value_counts().sort_index()
                st.line_chart(due_counts)

            else:
                st.warning("No overdue invoices found.")
        except Exception as e:
            st.error(f"Something went wrong: {e}")
