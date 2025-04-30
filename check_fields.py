import requests
import json

# 🔐 Credentials
refresh_token = "1000.70726dab2668b0965020fb3d8b76950d.0f1e66164f7cac0a89d1eaf55a666694"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

# 🔑 Get new access token
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

# 🧾 Fetch 1 invoice from Zoho Books for a given org
def fetch_sample_invoice(org_id, access_token):
    url = f"https://www.zohoapis.com/books/v3/invoices?organization_id={org_id}&status=overdue&per_page=1"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    invoice = data.get("invoices", [{}])[0]
    print(f"\n📄 Sample Invoice from Org {org_id}:\n")
    print(json.dumps(invoice, indent=2))

# 🧠 Main
def main():
    access_token = get_access_token()
    orgs = {
        "GoFleet Corporation": "673162904",
        "Zenduit Corporation": "696828433"
    }

    for name, org_id in orgs.items():
        print(f"\n🔍 Fetching sample invoice for: {name}")
        fetch_sample_invoice(org_id, access_token)

if __name__ == "__main__":
    main()
