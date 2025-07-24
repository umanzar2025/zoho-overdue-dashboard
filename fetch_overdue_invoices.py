import requests
import csv
from datetime import datetime

# ✅ Your updated credentials
refresh_token = "1000.ceb56845974e8cf5e5a1f9ac6f2d33f3.2a1c0a5032f87c4a66c5541549fc537c"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

# 🔐 Get new access token
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

# 📥 Fetch all overdue invoices with pagination
def fetch_overdue_invoices(org_id, access_token):
    url = "https://www.zohoapis.com/books/v3/invoices"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    params = {
        "organization_id": org_id,
        "status": "overdue",
        "page": 1,
        "per_page": 200
    }

    response = requests.get(url, headers=headers, params=params)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("❌ API call failed:")
        print(f"🔗 URL: {response.url}")
        print(f"📄 Status Code: {response.status_code}")
        print(f"📬 Response Body: {response.text}")
        raise e

    return response.json().get("invoices", [])

# 💾 Write invoices to CSV
def export_to_csv(invoices, org_name):
    now = datetime.now().strftime("%Y-%m-%d")
    filename = f"{org_name.lower().replace(' ', '_')}_overdue_invoices_{now}.csv"
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["invoice_number", "customer_name", "due_date", "total", "balance", "status", "is_emailed", "organization"])
        for invoice in invoices:
            writer.writerow([
                invoice.get("invoice_number", ""),
                invoice.get("customer_name", ""),
                invoice.get("due_date", ""),
                invoice.get("total", ""),
                invoice.get("balance", ""),
                invoice.get("status", ""),
                invoice.get("is_emailed", ""),
                org_name
            ])
    print(f"✅ {len(invoices)} invoices saved to {filename}")

# 🧠 Main
def main():
    access_token = get_access_token()
    orgs = {
        "GoFleet Corporation": "673162904",
        "Zenduit Corporation": "696828433"
    }

    for name, org_id in orgs.items():
        print(f"🔄 Fetching for {name}")
        invoices = fetch_overdue_invoices(org_id, access_token)
        export_to_csv(invoices, name)

if __name__ == "__main__":
    main()
