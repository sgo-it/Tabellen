import json
import requests
from bs4 import BeautifulSoup
import os
import re
from msal import ConfidentialClientApplication

# ---------------------------------------------------------
#   MAIL-FUNKTION (Graph API)
# ---------------------------------------------------------

def send_mail(subject, body):
    try:
        tenant_id = os.environ["SMTP_TENANT_ID"]
        client_id = os.environ["SMTP_CLIENT_ID"]
        client_secret = os.environ["SMTP_CLIENT_SECRET"]
        sender = "automation@sg-oftersheim.de"

        app = ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret
        )

        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )

        if "access_token" not in result:
            print("⚠ Mail: Kein Token erhalten")
            return False

        access_token = result["access_token"]

        mail = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
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

        print("Mail Status:", response.status_code)
        return response.status_code == 202

    except Exception as e:
        print("⚠ Mail Fehler:", e)
        return False


# ---------------------------------------------------------
#   STEUER-VARIABLEN (Default = false)
# ---------------------------------------------------------

send_success = os.getenv("SEND_EMAIL_ON_SUCCESS", "false").lower() == "true"
send_error = os.getenv("SEND_EMAIL_ON_ERROR", "false").lower() == "true"

num_future_games = int(os.getenv("NUM_FUTURE_GAMES", 2))

# ---------------------------------------------------------
#   ORDNER & TEAMS LADEN
# ---------------------------------------------------------

os.makedirs("teams", exist_ok=True)
os.makedirs("logos", exist_ok=True)

teams = json.load(open("teams.json", encoding="utf-8"))

def normalize(text):
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def slugify(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")

def download_logo(url, filename):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(filename, "wb") as f:
                f.write(r.content)
            print(f"✔ Logo gespeichert: {filename}")
        else:
            print(f"⚠ Logo konnte nicht geladen werden: {url}")
    except Exception as e:
        print(f"⚠ Fehler beim Logo-Download: {e}")

def extract_team_id(url):
    m = re.search(r"team-id/([A-Z0-9]+)", url)
    return m.group(1) if m else None


# ---------------------------------------------------------
#   NÄCHSTE SPIELE LADEN
# ---------------------------------------------------------

def load_games(url):
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table")
        if not table:
            return "<p>Keine Daten</p>"

        games = []

        for tr in table.find_all("tr"):
            clubs = tr.find_all("td", class_="column-club")
            if len(clubs) == 2:

                date_row = tr.find_previous_sibling("tr", class_="row-competition")
                if date_row:
                    date_text = date_row.find("td", class_="column-date").get_text(strip=True)
                    date_text = date_text.replace("|", " ")
                    date_text = re.sub(r"\s+", " ", date_text).strip()
                else:
                    date_text = ""

                home_name = clubs[0].find("div", class_="club-name").get_text(strip=True)
                home_logo_tag = clubs[0].find("img")
                home_logo = "https:" + home_logo_tag["src"] if home_logo_tag else ""

                away_name = clubs[1].find("div", class_="club-name").get_text(strip=True)
                away_logo_tag = clubs[1].find("img")
                away_logo = "https:" + away_logo_tag["src"] if away_logo_tag else ""

                games.append({
                    "date": date_text,
                    "home": home_name,
                    "home_logo": home_logo,
                    "away": away_name,
                    "away_logo": away_logo,
                })

        games = games[:num_future_games]

        out = "<table class='compact'><thead><tr>"
        out += "<th>Datum</th><th>Heim</th><th>Gast</th>"
        out += "</tr></thead><tbody>"

        for g in games:
            home_highlight = ' style="background-color: #d8f5d0;"' if "oftersheim" in g['home'].lower() else ""
            away_highlight = ' style="background-color: #d8f5d0;"' if "oftersheim" in g['away'].lower() else ""

            out += f"""
            <tr>
                <td>{g['date']}</td>
                <td{home_highlight}><img src="{g['home_logo']}" style="height:18px;"> {g['home']}</td>
                <td{away_highlight}><img src="{g['away_logo']}" style="height:18px;"> {g['away']}</td>
            </tr>
            """

        out += "</tbody></table>"
        return out

    except Exception as e:
        print("⚠ Fehler beim Laden der Spiele:", e)
        return "<p>Fehler beim Laden</p>"


# ---------------------------------------------------------
#   LIGATABELLE EXTRAHIEREN
# ---------------------------------------------------------

def scrape_table(team):
    name = team["name"]
    titel = team.get("titel", name)
    url = team["url"]

    print(f"Scrape: {titel} – {url}")

    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    table = soup.select_one("#team-fixture-league-tables table")
    if not table:
        print(f"⚠ Keine Tabelle gefunden für {name}")
        return

    rows = []
    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 10:
            continue

        platz = normalize(tds[1].get_text(strip=True))

        img = tds[2].find("img")
        if img and img.get("src"):
            src = img["src"]
            logo_url = "https:" + src if src.startswith("//") else src
        else:
            logo_url = ""

        club_name = normalize(tds[2].get_text(strip=True))

        slug = slugify(club_name)
        local_logo = f"logos/{slug}.png"

        if logo_url and not os.path.exists(local_logo):
            download_logo(logo_url, local_logo)

        highlight = "oftersheim" in club_name.lower()

        spiele = normalize(tds[3].get_text(strip=True))
        g = normalize(tds[4].get_text(strip=True))
        u = normalize(tds[5].get_text(strip=True))
        v = normalize(tds[6].get_text(strip=True))
        tore = normalize(tds[7].get_text(strip=True))
        punkte = normalize(tds[9].get_text(strip=True))

        rows.append({
            "platz": platz,
            "logo": local_logo,
            "name": club_name,
            "spiele": spiele,
            "g": g,
            "u": u,
            "v": v,
            "tore": tore,
            "punkte": punkte,
            "highlight": highlight
        })

    team_id = extract_team_id(url)
    next_url = f"https://www.fussball.de/ajax.team.next.games/-/mode/PAGE/team-id/{team_id}"
    next_games = load_games(next_url)

    table_html = """
<table class="compact">
  <thead>
    <tr>
      <th>Pl.</th>
      <th></th>
      <th>Mannschaft</th>
      <th>Sp.</th>
      <th>G</th>
      <th>U</th>
      <th>V</th>
      <th>Tore</th>
      <th>Pkt.</th>
    </tr>
  </thead>
  <tbody>
"""

    for r in rows:
        style = ' style="background-color: #d8f5d0;"' if r["highlight"] else ""

        table_html += f"""
    <tr{style}>
      <td>{r['platz']}</td>
      <td><img src="../{r['logo']}" alt="" style="height:18px;"></td>
      <td>{r['name']}</td>
      <td>{r['spiele']}</td>
      <td>{r['g']}</td>
      <td>{r['u']}</td>
      <td>{r['v']}</td>
      <td>{r['tore']}</td>
      <td>{r['punkte']}</td>
    </tr>
"""

    table_html += """
  </tbody>
</table>
"""

    html_out = f"""
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>{titel}</title>
<style>
  body {{
    font-family: Arial;
    padding: 20px;
  }}

  table.compact {{
    border-collapse: collapse;
    width: 600px;
    font-size: 13px;
    white-space: nowrap;
  }}

  th, td {{
    border: 1px solid #ccc;
    padding: 3px 6px;
  }}

  th {{
    background: #eee;
  }}

  img {{
    height: 18px;
  }}

  h2 {{
    margin-top: 30px;
  }}
</style>
</head>
<body>
<h1>{titel}</h1>

<h2>Ligatabelle</h2>
{table_html}

<h2>Nächste Spiele</h2>
{next_games}

</body>
</html>
"""

    output_path = f"teams/{name}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"✔ HTML erzeugt: {output_path}")


# ---------------------------------------------------------
#   HAUPTABLAUF MIT MAIL-STEUERUNG
# ---------------------------------------------------------

try:
    for team in teams:
        scrape_table(team)

    print("✔ Update Tabellen Mannschaften erfolgreich abgeschlossen")

    if send_success:
        send_mail(
            subject="Update Tabellen Mannschaften erfolgreich abgeschlossen",
            body="Die Tabellen der Mannschaften wurden erfolgreich für alle Mannschaften wurden aktualisiert."
        )

except Exception as e:
    print("⚠ Fehler beim Update Tabellen Mannschaften:", e)

    if send_error:
        send_mail(
            subject="Fehler beim Update Tabellen Mannschaften",
            body=f"Beim Ausführen des Tabellen‑Scrapers ist ein Fehler aufgetreten:\n\n{e}"
        )

    raise
