
import json
import re
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_URL = (
    "https://routit.service-now.com/api/now/sp/page"
    "?portal_id=e9b7c6f087353e904d7021be8bbb3578"
    "&request_uri=%2Fcspreporter"
)

TIMEZONE = ZoneInfo("Europe/Amsterdam")


def fetch_kpn_records():
    request = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "ClearMind-Narrowcasting/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)

    containers = data["result"]["containers"]
    widget = containers[0]["rows"][0]["columns"][0]["widgets"][0]["widget"]

    return widget["data"]


def clean_description(description):
    description = re.sub(
        r"<br\s*/?>", " ", description, flags=re.IGNORECASE
    )
    description = re.sub(r"<[^>]+>", "", description)
    return " ".join(description.split())


def filter_kpn_records(records):
    now = datetime.now(TIMEZONE)

    disruptions = []
    maintenance = []

    for record in records.get("recordsDisruption", []):
        title = record.get("title", "")

        if title.upper().startswith("[OPGELOST]"):
            continue

        disruptions.append(record)

    for record in records.get("recordsMaintenance", []):
        try:
            start = datetime.strptime(
                record["start_date_raw"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=TIMEZONE)
        except (KeyError, ValueError):
            continue

        # Alleen onderhoud binnen de komende 14 dagen
        if now - timedelta(days=1) <= start <= now + timedelta(days=14):
            maintenance.append(record)

    return disruptions, maintenance


def main():
    records = fetch_kpn_records()
    disruptions, maintenance = filter_kpn_records(records)

    print("KPN CSP REPORTER - TESTOVERZICHT")
    print(f"Actieve storingen: {len(disruptions)}")
    print(f"Relevant onderhoud: {len(maintenance)}")

    for record in disruptions:
        print(f"[STORING] {record['title']}")

    for record in maintenance:
        print(f"[ONDERHOUD] {record['title']}")
        print(f"  Start: {record.get('start_date', 'Onbekend')}")
        print(f"  Diensten: {record.get('categories', 'Onbekend')}")


if __name__ == "__main__":
    main()
