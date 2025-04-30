import requests
from datetime import datetime, timedelta

BASE_URL = "https://www.zohoapis.com/books/v3"

# -------------------------------
# ✅ AUTHENTICATION
# -------------------------------
def get_access_token(refresh_token, client_id, client_secret):
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    response = requests.post(token_url, data=params)

    # 🔍 TEMP DEBUG LINE
    print("ZOHO DEBUG RESPONSE:", response.status_code, response.text)

    return response.json()["access_token"]

# -------------------------------
# 📄 FETCH INVOICES (PAID or OVERDUE)
# -------------------------------
def fetch_invoices(org_id, access_token, status="paid", months_back=12, max_pages=30):
    invoices = []
    page = 1
    start_date = (datetime.today() - timedelta(days=months_back * 30)).strftime("%Y-%m-%d")

    while True:
        if max_pages and page > max_pages:
            print("🛑 Max invoice page limit reached — stopping early.")
            break

        print(f"🧾 Fetching {status} invoices page {page}...")
        url = (
            f"{BASE_URL}/invoices?organization_id={org_id}"
            f"&status={status}&date_start={start_date}&page={page}&per_page=200"
        )
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if "invoices" in data:
            invoices.extend(data["invoices"])
        if not data.get("page_context", {}).get("has_more_page"):
            break

        page += 1

    return invoices

# -------------------------------
# 💵 FETCH CUSTOMER PAYMENTS
# -------------------------------
def fetch_customer_payments(org_id, access_token, months_back=12, max_pages=30):
    payments = []
    page = 1
    start_date = (datetime.today() - timedelta(days=months_back * 30)).strftime("%Y-%m-%d")

    while True:
        if max_pages and page > max_pages:
            print("🛑 Max payment page limit reached — stopping early.")
            break

        print(f"📦 Fetching customer payments page {page}...")
        url = (
            f"{BASE_URL}/customerpayments?organization_id={org_id}"
            f"&date_start={start_date}&page={page}&per_page=200"
        )
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if "customer_payments" in data:
            payments.extend(data["customer_payments"])
        elif "customerpayments" in data:
            payments.extend(data["customerpayments"])

        if not data.get("page_context", {}).get("has_more_page"):
            break

        page += 1

    return payments

# -------------------------------
# 🔁 BUILD PAYMENT MODE MAPPING
# -------------------------------
def build_payment_mode_map(payments):
    invoice_payment_map = {}
    for payment in payments:
        mode = payment.get("payment_mode", "N/A")

        for inv in payment.get("invoices", []):
            inv_id = inv.get("invoice_id")
            if inv_id:
                invoice_payment_map[inv_id] = mode

        inv_number = payment.get("invoice_numbers")
        if inv_number:
            invoice_payment_map[inv_number] = mode

    return invoice_payment_map

def summarize_payment_modes(df):
    import pandas as pd

    if df.empty:
        return pd.DataFrame(columns=["payment_mode", "total", "percentage"])
    
    summary = (
        df.groupby("payment_mode")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total"})
        .sort_values(by="total", ascending=False)
    )
    total_sum = summary["total"].sum()
    summary["percentage"] = (summary["total"] / total_sum * 100).round(0).astype(int)
    summary["total"] = summary["total"].round(0).astype(int)
    return summary
