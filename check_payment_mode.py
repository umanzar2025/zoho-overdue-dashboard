import requests

# 🔐 OAuth Credentials
refresh_token = "1000.ceb56845974e8cf5e5a1f9ac6f2d33f3.2a1c0a5032f87c4a66c5541549fc537c"
client_id = "1000.QUF4IG3JGMWC5ARWWDYNILP8TZNJUC"
client_secret = "398aad9fccb86c6f1bb1793be1ecd6989cf7bc9426"

# 🔁 Step 1: Get access token
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

# 📄 Step 2: Fetch one overdue invoice (from GoFleet)
def get_sample_invoice(org_id, access_token):
    url = f"https://www.zohoapis.com/books/v3/invoices?organization_id={org_id}&status=overdue&per_page=1&page=1"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    invoices = response.json().get("invoices", [])
    return invoices[0] if invoices else None

# 💳 Step 3: Check payment(s) on that invoice
def get_payment_mode(org_id, access_token, invoice_id):
    url = f"https://www.zohoapis.com/books/v3/payments?invoice_id={invoice_id}&organization_id={org_id}"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get("payments", [])

# 🧠 Main Logic
def main():
    access_token = get_access_token()
    org_id = "673162904"  # GoFleet

    print("🔄 Fetching sample overdue invoice...")
    invoice = get_sample_invoice(org_id, access_token)

    if invoice:
        print(f"📄 Invoice: {invoice['invoice_number']}")
        invoice_id = invoice["invoice_id"]

        print("🔍 Checking payment(s)...")
        payments = get_payment_mode(org_id, access_token, invoice_id)
        if payments:
            for p in payments:
                print(f"✅ Payment Mode: {p.get('payment_mode')}, Amount: ${p.get('amount')}")
        else:
            print("❌ No payments found for this invoice.")
    else:
        print("❌ No overdue invoice found.")

if __name__ == "__main__":
    main()
