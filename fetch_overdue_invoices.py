import requests
import csv
from datetime import datetime

# ✅ Your updated credentials
refresh_token = "1000.70726dab2668b0965020fb3d8b76950d.0f1e66164f7cac0a89d1eaf55a666694"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

# 🔐 Refresh the access token
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

# 📥 Fetch overdue invoices for a given organization
def fetch_overdue_invoices(org_id, access_token):
    url = f"https://www.zohoapis.com/books/v3/invoices?organization_id={org_id}&status=overdue"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["invoices"]

# 💾 Write invoice data to CSV
def export_to_csv(invoices, org_name):
    now = datetime.now().strftime("%Y-%m-%d")
    filename = f"{org_name.lower().replace(' ', '_')}_overdue_invoices_{now}.csv"
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Invoice Number", "Customer Name", "Due Date", "Amount Due", "Status"])
        for invoice in invoices:
            writer.writerow([
                invoice["invoice_number"],
                invoice["customer_name"],
                invoice["due_date"],
                invoice["balance"],
                invoice["status"]
            ])
    print(f"✅ Saved {len(invoices)} overdue invoices to {filename}")

# 🎯 Main logic
def main():
    access_token = get_access_token()

    # Org IDs from your earlier script output
    orgs = {
        "GoFleet Corporation": "673162904",
        "Zenduit Corporation": "696828433"
    }

    for name, org_id in orgs.items():
        print(f"🔄 Fetching overdue invoices for {name}...")
        invoices = fetch_overdue_invoices(org_id, access_token)
        export_to_csv(invoices, name)

if __name__ == "__main__":
    main()


