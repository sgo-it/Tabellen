import json
import requests
from bs4 import BeautifulSoup
import os
import re

# Ordner anlegen
os.makedirs("teams", exist_ok=True)
os.makedirs("logos", exist_ok=True)

# Teams laden
teams = json.load(open("teams.json", encoding="utf-8"))

def normalize(text):
    """Entfernt Zero-Width-Chars, HTML-Entities, doppelte Leerzeichen."""
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def slugify(name):
    """Erzeugt Dateinamen für Logos."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")

def download_logo(url, filename):
    """Logo lokal speichern."""
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
    """Extrahiert die team-id aus der fussball.de URL."""
    m = re.search(r"team-id/([A-Z0-9]+)", url)
    return m.group(1) if m else None

def load_games(url):
    """Lädt HTML der Spiele (next/prev) und extrahiert die ersten 2 Zeilen."""
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table")
        if not table:
            return "<p>Keine Daten</p>"

        rows = table.find_all("tr")[1:3]  # nur die ersten 2 Spiele

        new_table = "<table class='compact'><thead><tr>"
        for th in table.find_all("th"):
            new_table += f"<th>{th.get_text(strip=True)}</th>"
        new_table += "</tr></thead><tbody>"

        for tr in rows:
            new_table += "<tr>"
            for td in tr.find_all("td"):
                new_table += f"<td>{td.get_text(strip=True)}</td>"
            new_table += "</tr>"

        new_table += "</tbody></table>"
        return new_table

    except Exception as e:
        print("⚠ Fehler beim Laden der Spiele:", e)
        return "<p>Fehler beim Laden</p>"

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

    # Spielpläne laden
    team_id = extract_team_id(url)
    next_url = f"https://www.fussball.de/ajax.team.next.games/-/mode/PAGE/team-id/{team_id}"
    prev_url = f"https://www.fussball.de/ajax.team.prev.games/-/mode/PAGE/team-id/{team_id}"

    next_games = load_games(next_url)
    prev_games = load_games(prev_url)

    # Ligatabelle erzeugen
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

    # HTML-Seite erzeugen
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

<h2>Letzte Spiele</h2>
{prev_games}

</body>
</html>
"""

    output_path = f"teams/{name}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"✔ HTML erzeugt: {output_path}")


# Alle Teams scrapen
for team in teams:
    scrape_table(team)
