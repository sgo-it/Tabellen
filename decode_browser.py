import json
import os
import re
from playwright.sync_api import sync_playwright

os.makedirs("decoded", exist_ok=True)

def extract_team_id(url):
    m = re.search(r"team-id/([A-Z0-9]+)", url)
    return m.group(1) if m else None


def get_match_urls(team_id):
    """Lädt die Spiel-URLs aus den AJAX-Tabellen."""
    import requests
    from bs4 import BeautifulSoup

    urls = []

    for mode in ["prev", "next"]:
        ajax_url = f"https://www.fussball.de/ajax.team.{mode}.games/-/mode/PAGE/team-id/{team_id}"
        html = requests.get(ajax_url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        for td in soup.find_all("td", class_="column-score"):
            a = td.find("a")
            if a and a.get("href"):
                urls.append(a["href"])

    return urls


def decode_match(page, url):
    """Öffnet die Spielseite im Browser und liest das echte Endergebnis aus dem DOM."""
    page.goto(url, timeout=60000)

    # Warten bis das Ergebnis decodiert ist
    page.wait_for_selector(".end-result", timeout=60000)

    # Endergebnis extrahieren
    end_result = page.locator(".end-result").inner_text().strip()

    # Halbzeit (optional)
    half = ""
    if page.locator(".half-result").count() > 0:
        half = page.locator(".half-result").inner_text().strip()

    return end_result, half


def main():
    teams = json.load(open("teams.json", encoding="utf-8"))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        for team in teams:
            name = team["name"]
            url = team["url"]

            print(f"Extrahiere Spiele für {name}…")

            team_id = extract_team_id(url)
            if not team_id:
                print(f"⚠ Keine team-id für {name}")
                continue

            match_urls = get_match_urls(team_id)

            out_path = f"decoded/{name}.txt"
            with open(out_path, "w", encoding="utf-8") as f:

                for match_url in match_urls:
                    try:
                        end_result, half = decode_match(page, match_url)
                        f.write(f"{match_url}\n")
                        f.write(f"  Endstand: {end_result}\n")
                        if half:
                            f.write(f"  Halbzeit: {half}\n")
                        f.write("\n")
                        print(f"✔ {end_result}  ({match_url})")

                    except Exception as e:
                        f.write(f"{match_url}\n  Fehler: {e}\n\n")
                        print(f"⚠ Fehler bei {match_url}: {e}")

        browser.close()


if __name__ == "__main__":
    main()
