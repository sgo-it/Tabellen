import os
import requests
from msal import ConfidentialClientApplication

tenant_id = os.environ["SMTP_TENANT_ID"]
client_id = os.environ["SMTP_CLIENT_ID"]
client_secret = os.environ["SMTP_CLIENT_SECRET"]

sender = "automation@sg-oftersheim.de"  # Shared Mailbox

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

response = requests.post(
    f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
    headers={"Authorization": f"Bearer {access_token}"},
    json=mail
)

print("Status:", response.status_code)
print("Antwort:", response.text)
