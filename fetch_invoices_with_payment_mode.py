import requests
import csv
import json
from datetime import datetime, timedelta

# ✅ Credentials
refresh_token = "1000.ceb56845974e8cf5e5a1f9ac6f2d33f3.2a1c0a5032f87c4a66c5541549fc537c"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

BASE_URL = "https://www.zohoapis.com/books/v3"

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

def fetch_paid_invoices(org_id, access_token, months_back=12, max_pages=60):
    invoices = []
    page = 1
    start_date = (datetime.today() - timedelta(days=months_back * 30)).strftime("%Y-%m-%d")

    while True:
        if max_pages and page > max_pages:
            print("🛑 Max invoice page limit reached — stopping early.")
            break

        print(f"🧾 Fetching paid invoices page {page}...")

        url = (
            f"{BASE_URL}/invoices?organization_id={org_id}"
            f"&status=paid&date_start={start_date}&page={page}&per_page=200"
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

    print(f"✅ Fetched {len(invoices)} paid invoices.\n")
    return invoices

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

    print(f"✅ Fetched {len(payments)} payments total.\n")
    return payments

def export_to_csv(invoices, payments, org_name):
    now = datetime.now().strftime("%Y-%m-%d")
    filename = f"{org_name.lower().replace(' ', '_')}_paid_invoice_payments_{now}.csv"

    # 🔁 Build invoice_id and invoice_number → payment_mode map
    invoice_payment_map = {}
    for payment in payments:
        mode = payment.get("payment_mode", "N/A")

        # ✅ Preferred: map from 'invoices' (if present)
        for inv in payment.get("invoices", []):
            inv_id = inv.get("invoice_id")
            if inv_id:
                invoice_payment_map[inv_id] = mode

        # ✅ Fallback: use 'invoice_numbers' string if above is empty
        inv_number = payment.get("invoice_numbers")
        if inv_number:
            invoice_payment_map[inv_number] = mode

    # 🔍 Write debug sample payments
    debug_filename = f"debug_customer_payments_{org_name.lower().replace(' ', '_')}.json"
    with open(debug_filename, "w", encoding="utf-8") as f:
        json.dump(payments[:3], f, indent=2)
    print(f"📝 Wrote sample customer payments to {debug_filename}")

    # 🧾 Write invoice CSV
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            "invoice_number", "customer_name", "due_date", "total", "balance", "payment_mode", "organization"
        ])
        for invoice in invoices:
            invoice_id = invoice.get("invoice_id", "")
            invoice_number = invoice.get("invoice_number", "")
            payment_mode = invoice_payment_map.get(invoice_id) or invoice_payment_map.get(invoice_number, "N/A")

            writer.writerow([
                invoice_number,
                invoice.get("customer_name", ""),
                invoice.get("due_date", ""),
                invoice.get("total", ""),
                invoice.get("balance", ""),
                payment_mode,
                org_name
            ])

    print(f"✅ {len(invoices)} invoices saved to {filename}")

def main():
    access_token = get_access_token()
    orgs = {
        "GoFleet Corporation": "673162904",
        "Zenduit Corporation": "696828433"
    }
    for name, org_id in orgs.items():
        print(f"\n🔄 Fetching data for {name}")
        invoices = fetch_paid_invoices(org_id, access_token, months_back=12, max_pages=60)
        payments = fetch_customer_payments(org_id, access_token, months_back=12, max_pages=30)
        export_to_csv(invoices, payments, name)

if __name__ == "__main__":
    main()
