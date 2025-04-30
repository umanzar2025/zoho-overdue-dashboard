import requests
import csv
from datetime import datetime, timedelta

# ✅ Credentials
refresh_token = "1000.ceb56845974e8cf5e5a1f9ac6f2d33f3.2a1c0a5032f87c4a66c5541549fc537c"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

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

def fetch_invoices(org_id, access_token):
    invoices = []
    page = 1
    today = datetime.today()
    three_months_ago = today - timedelta(days=90)
    date_start = three_months_ago.strftime("%Y-%m-%d")

    while True:
        url = f"https://www.zohoapis.com/books/v3/invoices?organization_id={org_id}&date_start={date_start}&page={page}&per_page=200"
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

def fetch_customer_payments(org_id, access_token):
    payments = []
    page = 1
    today = datetime.today()
    three_months_ago = today - timedelta(days=90)
    date_start = three_months_ago.strftime("%Y-%m-%d")

    while True:
        url = f"https://www.zohoapis.com/books/v3/customerpayments?organization_id={org_id}&date_start={date_start}&page={page}&per_page=200"
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

def map_invoice_to_payment_mode(payments):
    invoice_payment_map = {}
    for payment in payments:
        payment_mode = payment.get("payment_mode", "N/A")
        for invoice in payment.get("invoices", []):
            invoice_id = invoice.get("invoice_id")
            if invoice_id:
                invoice_payment_map[invoice_id] = payment_mode
    return invoice_payment_map

def export_to_csv(invoices, invoice_payment_map, org_name):
    now = datetime.now().strftime("%Y-%m-%d")
    filename = f"{org_name.lower().replace(' ', '_')}_invoices_with_payment_mode_{now}.csv"

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["invoice_number", "customer_name", "due_date", "total", "balance", "status", "payment_mode", "organization"])
        for invoice in invoices:
            writer.writerow([
                invoice.get("invoice_number", ""),
                invoice.get("customer_name", ""),
                invoice.get("due_date", ""),
                invoice.get("total", ""),
                invoice.get("balance", ""),
                invoice.get("status", ""),
                invoice_payment_map.get(invoice.get("invoice_id"), "N/A"),
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
        invoices = fetch_invoices(org_id, access_token)
        payments = fetch_customer_payments(org_id, access_token)
        invoice_payment_map = map_invoice_to_payment_mode(payments)
        export_to_csv(invoices, invoice_payment_map, name)

if __name__ == "__main__":
    main()

