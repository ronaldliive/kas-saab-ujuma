#!/usr/bin/env python3
"""Kraabib Terviseameti suplusvee kvaliteedi andmed (vtiav.sm.ee) ja kirjutab data.json.
Käivitatakse GitHub Actions'i kaudu regulaarselt."""
import json, re, sys, datetime, time
import requests
from bs4 import BeautifulSoup

BASE = "https://vtiav.sm.ee/index.php/?page={}&active_tab_id=SV"
MONTHS = {"jaanuar":1,"veebruar":2,"märts":3,"aprill":4,"mai":5,"juuni":6,
          "juuli":7,"august":8,"september":9,"oktoober":10,"november":11,"detsember":12}
HEADERS = {"User-Agent": "kas-saab-ujuma/1.0 (avaandmete visualiseering; github.com/ronaldliive/kas-saab-ujuma)"}

def parse_date(s):
    m = re.match(r"(\d{1,2})\.\s*([a-zõäöüšž]+)\s+(\d{4})", s.strip(), re.I)
    if not m:
        return None
    return f"{int(m.group(3)):04d}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"

def hinnang(alt):
    a = (alt or "").lower()
    if "halb" in a: return "halb"
    if "väga hea" in a: return "vaga_hea"
    if "piisav" in a: return "piisav"
    if "hea" in a: return "hea"
    return "tundmatu"

def main():
    sites, page, total_pages = [], 1, 1
    while page <= total_pages:
        r = requests.get(BASE.format(page), headers=HEADERS, timeout=60)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        m = re.search(r"lehekülg\s+\d+/(\d+)", soup.get_text())
        if m:
            total_pages = int(m.group(1))
        for tr in soup.select("table.dataTable tr.sf_admin_row"):
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue
            a = tds[1].find("a")
            if not a:
                continue
            sid = re.search(r"id=(\d+)", a.get("href", ""))
            kuupaev = parse_date(tds[3].get_text(strip=True))
            img = tds[4].find("img")
            sites.append({
                "id": int(sid.group(1)) if sid else None,
                "maakond": tds[0].get_text(strip=True),
                "nimi": a.get_text(strip=True),
                "pikaajaline": tds[2].get_text(strip=True).replace("\xa0", " ").strip(),
                "kuupaev": kuupaev,
                "hinnang": hinnang(img.get("alt") if img else ""),
                "markused": " ".join(tds[5].get_text(" ", strip=True).split()),
            })
        page += 1
        time.sleep(1)  # ole allika vastu viisakas

    # Kaitse: kui kraapimine ebaõnnestus osaliselt, ära kirjuta olemasolevaid andmeid üle
    if len(sites) < 100:
        print(f"VIGA: ainult {len(sites)} kirjet — struktuur võib olla muutunud, katkestan.", file=sys.stderr)
        sys.exit(1)
    bad_dates = [s for s in sites if not s["kuupaev"]]
    if len(bad_dates) > len(sites) * 0.1:
        print(f"VIGA: {len(bad_dates)} kuupäeva jäi parsimata, katkestan.", file=sys.stderr)
        sys.exit(1)

    payload = {
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": "https://vtiav.sm.ee/index.php/?active_tab_id=SV",
        "count": len(sites),
        "sites": sites,
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"OK: {len(sites)} kirjet, {sum(1 for s in sites if s['hinnang']=='halb')} hoiatusega.")

if __name__ == "__main__":
    main()
