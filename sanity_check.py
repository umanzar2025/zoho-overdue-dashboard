import requests

# 🔐 OAuth credentials
refresh_token = "1000.ceb56845974e8cf5e5a1f9ac6f2d33f3.2a1c0a5032f87c4a66c5541549fc537c"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

BASE_URL = 'https://books.zoho.com/api/v3'

# 🔁 Get access token using refresh_token
def get_access_token():
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    response = requests.post(token_url, params=params)
    response.raise_for_status()
    return response.json()['access_token']

# 📋 List all organizations the token can access
def list_organizations(token):
    resp = requests.get(f"{BASE_URL}/organizations", headers={
        'Authorization': f'Zoho-oauthtoken {token}'
    })
    resp.raise_for_status()

    data = resp.json()
    print("📦 Raw response from /organizations endpoint:")
    orgs = data.get("organizations", [])
    for org in orgs:
        name = org.get("name", "N/A")
        org_id = org.get("organization_id", "N/A")
        print(f"🏢 Org: {name} | ID: {org_id}")

# 📊 Show total invoice count for each org
def get_invoice_summary(org_id, token):
    url = f"{BASE_URL}/invoices"
    headers = {
        'Authorization': f'Zoho-oauthtoken {token}',
        'X-com-zoho-books-organizationid': org_id,
        'X-com-zoho-books-companyid': org_id
    }
    params = {
        'page': 1,
        'organization_id': org_id  # 👈 required for multi-org access
    }

    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        total = data.get('page_context', {}).get('total', 0)
        print(f"📊 Org {org_id}: Total invoices found = {total}")
    except requests.exceptions.HTTPError:
        print(f"❌ Org {org_id}: Error {resp.status_code} – {resp.json().get('message')}")

# 🚀 Run the check
if __name__ == "__main__":
    token = get_access_token()
    print("\n📋 Listing organizations:")
    list_organizations(token)

    # 👇 Update with all orgs you want to check
    org_ids_to_check = [
        "673162904",  # GoFleet Corporation
        "696828433",  # Zenduit Corporation
        "696053785",  # GoFleet DWC-LLC
        "859652303",  # My Install Hub
        "849301698",  # XenTag Corporation
    ]

    print("\n📊 Invoice summary check:")
    for org_id in org_ids_to_check:
        get_invoice_summary(org_id, token)

