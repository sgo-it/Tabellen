import smtplib, base64, os
from msal import ConfidentialClientApplication

tenant_id = os.environ["TENANT_ID"]
client_id = os.environ["CLIENT_ID"]
client_secret = os.environ["CLIENT_SECRET"]
smtp_user = "automation@sg-oftersheim.de"

# Token holen
app = ConfidentialClientApplication(
    client_id,
    authority=f"https://login.microsoftonline.com/{tenant_id}",
    client_credential=client_secret
)

result = app.acquire_token_for_client(scopes=["https://outlook.office365.com/.default"])

if "access_token" not in result:
    print("Kein Token erhalten:", result)
    exit()

access_token = result["access_token"]

# SMTP OAuth2 Token
auth_string = f"user={smtp_user}\x01auth=Bearer {access_token}\x01\x01"
auth_bytes = base64.b64encode(auth_string.encode("utf-8"))

# SMTP senden
server = smtplib.SMTP("smtp.office365.com", 587)
server.starttls()
server.docmd("AUTH", "XOAUTH2 " + auth_bytes.decode())
server.sendmail(
    smtp_user,
    "it@sg-oftersheim.de",
    "Subject: SMTP OAuth Test\n\nDies ist ein Test über OAuth."
)
server.quit()

print("Mail erfolgreich gesendet.")
