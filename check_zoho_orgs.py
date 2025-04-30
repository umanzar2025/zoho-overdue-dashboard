import requests

# 🔐 Replace these with your actual credentials
refresh_token = "1000.ceb56845974e8cf5e5a1f9ac6f2d33f3.2a1c0a5032f87c4a66c5541549fc537c"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"


# STEP 1: Get fresh access token
token_url = "https://accounts.zoho.com/oauth/v2/token"
token_params = {
    "refresh_token": refresh_token,
    "client_id": client_id,
    "client_secret": client_secret,
    "grant_type": "refresh_token"
}

token_resp = requests.post(token_url, params=token_params)
token_data = token_resp.json()

# Debug print
print("🔁 Refresh Response:", token_data)

# Exit early if token missing
if "access_token" not in token_data:
    raise Exception("❌ No access token returned. Check if your refresh token or scopes are incorrect.")

access_token = token_data["access_token"]

# STEP 2: Use token to list organizations
orgs_url = "https://www.zohoapis.com/books/v3/organizations"
org_headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}"
}

org_resp = requests.get(orgs_url, headers=org_headers)
org_data = org_resp.json()

print("\n✅ Organizations Linked to This Token:\n")
for org in org_data.get("organizations", []):
    print(f"• {org['name']} (ID: {org['organization_id']})")
