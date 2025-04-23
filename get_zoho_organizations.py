import requests

# 🔐 Replace this with your current working access token (or use your refresh-token logic to generate one)
access_token = "your_valid_access_token_here"

# 🚀 API endpoint to list organizations
url = "https://www.zohoapis.com/books/v3/organizations"

# 🛡️ Headers with authentication
headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}"
}

# 📡 Make the API call
response = requests.get(url, headers=headers)
data = response.json()

# 🔍 Print each organization's name + ID
for org in data.get("organizations", []):
    print(f"Name: {org['name']} | ID: {org['organization_id']}")
