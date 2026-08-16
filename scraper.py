import json
import requests
from bs4 import BeautifulSoup
import os
import re

# Anzahl der zukünftigen Spiele über GitHub Variable steuerbar
num_future_games = int(os.getenv("NUM_FUTURE_GAMES", 2))

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


# ---------------------------------------------------------
#   NÄCHSTE SPIELE LADEN (Datum + Uhrzeit, Heim, Gast)
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
            clubs = tr.find_all("td", class_="column
