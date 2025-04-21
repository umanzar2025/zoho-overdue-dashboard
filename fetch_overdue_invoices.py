import requests
import pandas as pd

# ✅ Your updated credentials
refresh_token = "1000.70726dab2668b0965020fb3d8b76950d.0f1e66164f7cac0a89d1eaf55a666694"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

# Step 1: Get fresh access token
token_url = "https://accounts.zoho.com/oauth/v2/token"
token_data = {
    "refresh_token": refresh_token,
    "client_id": client_id,
    "client_secret": client_secret,
    "grant_type": "refresh_token"
}
token_resp = requests.post(token_url, data=token_data)
token_json = token_resp.json()

print("Zoho token response:", token_json)

if "access_token" not in token_json:
    raise Exception("❌ Error: No access token received. Check your credentials or refresh token.")

access_token = token_json['access_token']

# Step 2: Get your organization ID
org_url = "https://www.zohoapis.com/books/v3/organizations"
org_headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
org_resp = requests.get(org_url, headers=org_headers)
org_data = org_resp.json()

print("Organization data:", org_data)

organization_id = org_data['organizations'][0]['organization_id']

# Step 3: Get overdue invoices
invoice_url = f"https://www.zohoapis.com/books/v3/invoices?status=overdue&organization_id={organization_id}"
invoice_headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
invoice_resp = requests.get(invoice_url, headers=invoice_headers)
invoice_data = invoice_resp.json()

print("Sample overdue invoices:", invoice_data.get("invoices", [])[:3])

# Step 4: Save to CSV
invoices = invoice_data.get("invoices", [])
if invoices:
    df = pd.DataFrame(invoices)
    df.to_csv("zoho_overdue_invoices.csv", index=False)
    print("✅ Invoices saved to zoho_overdue_invoices.csv")
else:
    print("⚠️ No overdue invoices found.")
