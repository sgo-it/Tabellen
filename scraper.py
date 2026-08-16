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

def extract_score(info_td):
    """Erkennt ALLE Ergebnisvarianten von fussball.de."""
    if not info_td:
        return ""

    score = info_td.find("span", class_="score")
    if score:
        return score.get_text(strip=True)

    result = info_td.find("span", class_="result")
    if result:
        return result.get_text(strip=True)

    hidden = info_td.find("span", class_="hidden-small")
    if hidden:
        return hidden.get_text(strip=True)

    info_text = info_td.find("span", class_="info-text")
    if info_text:
        return info_text.get_text(strip=True)

    return info_td.get_text(strip=True)

def load_games(url):
    """Parst die fussball.de AJAX-Spielpläne und gibt die ersten 2 echten Spiele zurück."""
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

                # Datum/Uhrzeit aus vorheriger row-competition
                date_row = tr.find_previous_sibling("tr", class_="row-competition")
                if date_row:
                    date_text = date_row.find("td", class_="column-date").get_text(strip=True)
                    competition = date_row.find("td", class_="column-team").get_text(strip=True)
                else:
                    date_text = ""
                    competition = ""

                # Heimteam
                home_name = clubs[0].find("div", class_="club-name").get_text(strip=True)
                home_logo_tag = clubs[0].find("img")
                home_logo = "https:" + home_logo_tag["src"] if home_logo_tag else ""

                # Auswärtsteam
                away_name = clubs[1].find("div", class_="club-name").get_text(strip=True)
                away_logo_tag = clubs[1].find("img")
                away_logo = "https:" + away_logo_tag["src"] if away_logo_tag else ""

                # Ergebnis
                info_td = tr.find("td", class_="column-score")
                info = extract_score(info_td)

                games.append({
                    "date": date_text,
                    "competition": competition,
                    "home": home_name,
                    "home_logo": home_logo,
                    "away": away_name,
                    "away_logo": away_logo,
                    "info": info
                })

        games = games[:2]

        out = "<table class='compact'><thead><tr>"
        out += "<th>Datum</th><th>Heim</th><th></th><th>Auswärts</th><th>Ergebnis</th>"
        out += "</tr></thead><tbody>"

        for g in games:
            out += f"""
            <tr>
                <td>{g['date']}</td>
                <td><img src="{g['home_logo']}" style="height:18px;"> {g['home']}</td>
                <td>:</td>
                <td><img src="{g['away_logo']}" style="height:18px;"> {g['away']}</td>
                <td>{g['info']}</td>
            </tr>
            """

        out += "</tbody></table>"
        return out

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

    team_id = extract_team_id(url)
    next_url = f"https://www.fussball.de/ajax.team.next.games/-/mode/PAGE/team-id/{team_id}"
    prev_url = f"https://www.fussball.de/ajax.team.prev.games/-/mode/PAGE/team-id/{team_id}"

    next_games = load_games(next_url)
    prev_games = load_games(prev_url)

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

<h2>Letzte Spiele</h2>
{prev_games}

</body>
</html>
"""

    output_path = f"teams/{name}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"✔ HTML erzeugt: {output_path}")


for team in teams:
    scrape_table(team)
