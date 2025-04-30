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

def fetch_paid_invoice_payments(org_id, access_token):
    all_payments = []
    page = 1
    twelve_months_ago = datetime.today() - timedelta(days=365)
    date_start = twelve_months_ago.strftime("%Y-%m-%d")

    while True:
        url = (
            f"https://www.zohoapis.com/books/v3/customerpayments?"
            f"organization_id={org_id}&date_start={date_start}&page={page}&per_page=200"
        )
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "customer_payments" in data:
            all_payments.extend(data["customer_payments"])
        if not data.get("page_context", {}).get("has_more_page"):
            break
        page += 1
    return all_payments

def export_to_csv(payments, org_name):
    now = datetime.now().strftime("%Y-%m-%d")
    filename = f"{org_name.lower().replace(' ', '_')}_paid_invoice_payments_{now}.csv"

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            "payment_id", "customer_name", "payment_mode", "amount", "date", "invoice_number", "invoice_id", "organization"
        ])
        for payment in payments:
            for invoice in payment.get("invoices", []):
                writer.writerow([
                    payment.get("payment_id", ""),
                    payment.get("customer_name", ""),
                    payment.get("payment_mode", "N/A"),
                    payment.get("amount", ""),
                    payment.get("date", ""),
                    invoice.get("invoice_number", ""),
                    invoice.get("invoice_id", ""),
                    org_name
                ])
    print(f"✅ {len(payments)} payments saved to {filename}")

def main():
    access_token = get_access_token()
    orgs = {
        "GoFleet Corporation": "673162904",
        "Zenduit Corporation": "696828433"
    }

    for name, org_id in orgs.items():
        print(f"\n🔄 Fetching paid invoice payments for {name}")
        payments = fetch_paid_invoice_payments(org_id, access_token)
        export_to_csv(payments, name)

if __name__ == "__main__":
    main()
