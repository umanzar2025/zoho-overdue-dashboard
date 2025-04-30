import pandas as pd
import requests
from datetime import datetime
import os

# ✅ Credentials
refresh_token = "1000.ceb56845974e8cf5e5a1f9ac6f2d33f3.2a1c0a5032f87c4a66c5541549fc537c"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

# 🔐 Get access token
def get_access_token():
    url = "https://accounts.zoho.com/oauth/v2/token"
    payload = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

# 📥 Fetch past customer payments
def fetch_customer_payments(org_id, access_token):
    payments = []
    page = 1
    while True:
        url = f"https://www.zohoapis.com/books/v3/customerpayments?organization_id={org_id}&page={page}&per_page=200"
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "customer_payments" in data:
            payments.extend(data["customer_payments"])
        if not data.get("page_context", {}).get("has_more_page"):
            break
        page += 1
    return payments

# 🔄 Enrich overdue invoice CSV with payment mode
def enrich_invoices(org_name, org_id):
    today = datetime.now().strftime("%Y-%m-%d")
    input_filename = f"{org_name.lower().replace(' ', '_')}_overdue_invoices_{today}.csv"
    output_filename = f"{org_name.lower().replace(' ', '_')}_enriched_{today}.csv"

    if not os.path.exists(input_filename):
        print(f"❌ File not found: {input_filename}")
        return

    # Load overdue invoices
    df_invoices = pd.read_csv(input_filename)
    print(f"📂 Loaded {len(df_invoices)} invoices from {input_filename}")

    # Fetch all customer payments
    access_token = get_access_token()
    payments = fetch_customer_payments(org_id, access_token)

    # Create mapping: invoice_number -> payment_mode
    invoice_payment_map = {}
    for p in payments:
        for inv in p.get("invoices", []):
            invoice_payment_map[inv.get("invoice_number")] = p.get("payment_mode", "N/A")

    # Map payment modes to invoices
    df_invoices["payment_mode"] = df_invoices["invoice_number"].map(invoice_payment_map).fillna("N/A")

    # Save enriched file
    df_invoices.to_csv(output_filename, index=False)
    print(f"✅ Enriched data saved to {output_filename}")

# 🧠 Main
def main():
    orgs = {
        "GoFleet Corporation": "673162904",
        "Zenduit Corporation": "696828433"
    }
    for name, org_id in orgs.items():
        print(f"\n🔄 Processing {name}...")
        enrich_invoices(name, org_id)

if __name__ == "__main__":
    main()
