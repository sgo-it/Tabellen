import os
import requests
from msal import ConfidentialClientApplication

# --- DEBUG: Zeige alle SMTP‑Variablen ---
print("=== DEBUG: ENV Variablen ===")
print("SMTP_CLIENT_ID:", os.environ.get("SMTP_CLIENT_ID"))
print("SMTP_CLIENT_SECRET:", os.environ.get("SMTP_CLIENT_SECRET"))
print("SMTP_TENANT_ID:", os.environ.get("SMTP_TENANT_ID"))
print("============================\n")

# --- Secrets laden ---
tenant_id = os.environ["SMTP_TENANT_ID"]
client_id = os.environ["SMTP_CLIENT_ID"]
client_secret = os.environ["SMTP_CLIENT_SECRET"]

sender = "automation@sg-oftersheim.de"  # Shared Mailbox

# --- Token holen ---
app = ConfidentialClientApplication(
    client_id,
    authority=f"https://login.microsoftonline.com/{tenant_id}",
    client_credential=client_secret
)

result = app.acquire_token_for_client(
    scopes=["https://graph.microsoft.com/.default"]
)

if "access_token" not in result:
    print("Kein Token erhalten:", result)
    exit(1)

access_token = result["access_token"]

# --- Mail definieren ---
mail = {
    "message": {
        "subject": "SGO Automation Test",
        "body": {
            "contentType": "Text",
            "content": "Dies ist ein Test über Microsoft Graph."
        },
        "toRecipients": [
            {"emailAddress": {"address": "it@sg-oftersheim.de"}}
        ]
    }
}

# --- Mail senden ---
response = requests.post(
    f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
    headers={"Authorization": f"Bearer {access_token}"},
    json=mail
)

print("Status:", response.status_code)
print("Antwort:", response.text)
