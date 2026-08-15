import json
import requests
from bs4 import BeautifulSoup
import os
import re

os.makedirs("teams", exist_ok=True)

teams = json.load(open("teams.json", encoding="utf-8"))

def normalize(text):
    """Entfernt Zero-Width-Chars, HTML-Entities, doppelte Leerzeichen."""
    text = text.replace("\u200b", "")  # Zero-width space
    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def scrape_table(team):
    name = team["name"]
    url = team["url"]

    print(f"Scrape: {name} – {url}")

    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    table = soup.select_one("#team-fixture-league-tables table")
    if not table:
        print(f"⚠️ Keine Tabelle gefunden für {name}")
        return

    rows = []
    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 10:
            continue

        platz = normalize(tds[1].get_text(strip=True))

        # Logo extrahieren
        img = tds[2].find("img")
        if img and img.get("src"):
            src = img["src"]
            logo_url = "https:" + src if src.startswith("//") else src
        else:
            logo_url = ""

        # Mannschaftsname extrahieren
        club_name = normalize(tds[2].get_text(strip=True))

        # Highlighting robust machen
        highlight = "oftersheim" in club_name.lower()

        spiele = normalize(tds[3].get_text(strip=True))
        g = normalize(tds[4].get_text(strip=True))
        u = normalize(tds[5].get_text(strip=True))
        v = normalize(tds[6].get_text(strip=True))
        tore = normalize(tds[7].get_text(strip=True))
        punkte = normalize(tds[9].get_text(strip=True))

        rows.append({
            "platz": platz,
            "logo": logo_url,
            "name": club_name,
            "spiele": spiele,
            "g": g,
            "u": u,
            "v": v,
            "tore": tore,
            "punkte": punkte,
            "highlight": highlight
        })

    # Neue HTML-Tabelle
    table_html = """
<table>
  <thead>
    <tr>
      <th>Platz</th>
      <th>Logo</th>
      <th>Mannschaft</th>
      <th>Spiele</th>
      <th>G</th>
      <th>U</th>
      <th>V</th>
      <th>Tore</th>
      <th>Punkte</th>
    </tr>
  </thead>
  <tbody>
"""

    for r in rows:
        style = ' style="background-color: #fff3b0;"' if r["highlight"] else ""

        table_html += f"""
    <tr{style}>
      <td>{r['platz']}</td>
      <td><img src="{r['logo']}" alt="" style="height:24px;"></td>
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
<title>Ligatabelle – {name}</title>
<style>
  body {{ font-family: Arial; padding: 20px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 6px; }}
  th {{ background: #eee; }}
  img {{ height: 24px; }}
</style>
</head>
<body>
<h1>Ligatabelle – {name}</h1>
{table_html}
</body>
</html>
"""

    output_path = f"teams/{name}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"✔️ HTML erzeugt: {output_path}")


for team in teams:
    scrape_table(team)
