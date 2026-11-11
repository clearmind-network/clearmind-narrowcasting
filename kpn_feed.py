
import json
import re
import html
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
        r"<br\s*/?>", " ", description or "",
        flags=re.IGNORECASE
    )
    description = re.sub(r"<[^>]+>", "", description)
    return " ".join(html.unescape(description).split())


def parse_kpn_date(value):
    if not value:
        return None

    try:
        date = datetime.fromisoformat(str(value).strip())
        if date.tzinfo is None:
            date = date.replace(tzinfo=TIMEZONE)
        return date.astimezone(TIMEZONE)
    except ValueError:
        return None


def filter_kpn_records(records):
    now = datetime.now(TIMEZONE)
    horizon = now + timedelta(days=14)

    disruptions = []
    maintenance = []

    for record in records.get("recordsDisruption", []):
        title = record.get("title", "").strip()

        # Voorlopige controle op opgeloste storingen
        if title.upper().startswith("[OPGELOST]"):
            continue

        disruptions.append(record)

    for record in records.get("recordsMaintenance", []):
        start = parse_kpn_date(record.get("start_date_raw"))
        end = parse_kpn_date(record.get("end_date_raw"))

        if not start:
            continue

        if end and end < start:
            continue

        # Toekomstig onderhoud binnen 14 dagen
        upcoming = now <= start <= horizon

        # Lopend onderhoud waarvan de eindtijd bekend is
        ongoing = start <= now and end is not None and end >= now

        if upcoming or ongoing:
            maintenance.append(record)

    return disruptions, maintenance


def main():
    records = fetch_kpn_records()
    disruptions, maintenance = filter_kpn_records(records)

    print("KPN CSP REPORTER - TESTOVERZICHT")
    print(f"Niet-opgeloste storingen: {len(disruptions)}")
    print(f"Relevant onderhoud: {len(maintenance)}")

    for record in disruptions:
        print(f"[STORING] {record.get('title', 'Onbekend')}")

    for record in maintenance:
        print(f"[ONDERHOUD] {record.get('title', 'Onbekend')}")
        print(f"  Start: {record.get('start_date', 'Onbekend')}")
        print(f"  Einde: {record.get('end_date', 'Onbekend')}")
        print(f"  Diensten: {record.get('categories', 'Onbekend')}")


if __name__ == "__main__":
    main()
