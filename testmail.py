import smtplib
import base64
import os
from msal import ConfidentialClientApplication

# Secrets aus GitHub Actions
tenant_id = os.environ["TENANT_ID"]
client_id = os.environ["CLIENT_ID"]
client_secret = os.environ["CLIENT_SECRET"]

smtp_user = "automation@sg-oftersheim.de"

# OAuth Token holen
app = ConfidentialClientApplication(
    client_id,
    authority=f"https://login.microsoftonline.com/{tenant_id}",
    client_credential=client_secret
)

result = app.acquire_token_for_client(
    scopes=["https://outlook.office365.com/.default"]
)

if "access_token" not in result:
    print("Kein Token erhalten:", result)
    exit(1)

access_token = result["access_token"]

# SMTP OAuth2 Token erzeugen
auth_string = f"user={smtp_user}\x01auth=Bearer {access_token}\x01\x01"
auth_bytes = base64.b64encode(auth_string.encode("utf-8"))

# Nachricht (UTF‑8!)
message = (
    "Subject: SMTP OAuth Test\n"
    "Content-Type: text/plain; charset=utf-8\n"
    "\n"
    "Dies ist ein Test über OAuth."
)

# SMTP senden
server = smtplib.SMTP("smtp.office365.com", 587)
server.starttls()
server.docmd("AUTH", "XOAUTH2 " + auth_bytes.decode())
server.sendmail(
    smtp_user,
    "it@sg-oftersheim.de",
    message.encode("utf-8")
)
server.quit()

print("Mail erfolgreich gesendet.")
