import requests
import csv
from datetime import datetime, timedelta

# ✅ Credentials
refresh_token = "1000.70726dab2668b0965020fb3d8b76950d.0f1e66164f7cac0a89d1eaf55a666694"
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

def fetch_paid_invoices(org_id, access_token):
    paid_invoices = []
    page = 1

    # Calculate date 12 months ago
    today = datetime.today()
    twelve_months_ago = today - timedelta(days=12*30)
    date_start = twelve_months_ago.strftime("%Y-%m-%d")

    while True:
        url = (
            f"https://www.zohoapis.com/books/v3/invoices?"
            f"organization_id={org_id}&status=paid"
            f"&date_start={date_start}&page={page}&per_page=200"
        )
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "invoices" in data:
            paid_invoices.extend(data["invoices"])
        if not data.get("page_context", {}).get("has_more_page"):
            break
        page += 1
    return paid_invoices

def export_paid_invoices_to_csv(paid_invoices, org_name):
    now = datetime.now().strftime("%Y-%m-%d")
    filename = f"{org_name.lower().replace(' ', '_')}_paid_invoices_{now}.csv"

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["invoice_number", "customer_name", "due_date", "total", "balance", "payment_mode", "organization"])
        for invoice in paid_invoices:
            writer.writerow([
                invoice.get("invoice_number", ""),
                invoice.get("customer_name", ""),
                invoice.get("due_date", ""),
                invoice.get("total", ""),
                invoice.get("balance", ""),
                invoice.get("payment_mode", "N/A"),
                org_name
            ])
    print(f"✅ {len(paid_invoices)} paid invoices saved to {filename}")

def main():
    access_token = get_access_token()
    orgs = {
        "GoFleet Corporation": "673162904",
        "Zenduit Corporation": "696828433"
    }

    for name, org_id in orgs.items():
        print(f"\n🔄 Fetching paid invoices for {name}")
        paid_invoices = fetch_paid_invoices(org_id, access_token)
        export_paid_invoices_to_csv(paid_invoices, name)

if __name__ == "__main__":
    main()
