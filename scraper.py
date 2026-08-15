import json
import requests
from bs4 import BeautifulSoup
import os

# Ordner für HTML-Seiten
os.makedirs("teams", exist_ok=True)

# Teams laden
teams = json.load(open("teams.json", encoding="utf-8"))

def scrape_table(team):
    name = team["name"]
    url = team["url"]

    print(f"Scrape: {name} – {url}")

    # HTML laden
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    # Tabelle finden
    table = soup.select_one("#team-fixture-league-tables table")
    if not table:
        print(f"⚠️ Keine Tabelle gefunden für {name}")
        return

    # HTML-Seite erzeugen
    html_out = f"""
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Ligatabelle – {name}</title>
<style>
  body {{ font-family: Arial; padding: 20px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 6px; }}
  th {{ background: #eee; }}
  img {{ height: 24px; vertical-align: middle; margin-right: 6px; }}
</style>
</head>
<body>
<h1>Ligatabelle – {name}</h1>
{str(table)}
</body>
</html>
"""

    # Datei speichern
    output_path = f"teams/{name}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"✔️ HTML erzeugt: {output_path}")


# Alle Teams scrapen
for team in teams:
    scrape_table(team)
