
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
        r"<br\s*/?>",
        " ",
        description or "",
        flags=re.IGNORECASE,
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

    except (ValueError, TypeError):
        return None


def filter_kpn_records(records):
    now = datetime.now(TIMEZONE)
    horizon = now + timedelta(days=14)

    disruptions = []
    maintenance = []

    # Storingen filteren
    for record in records.get("recordsDisruption", []):
        title = record.get("title", "").strip()

        if title.upper().startswith("[OPGELOST]"):
            continue

        disruptions.append(record)

    # Onderhoud filteren
    for record in records.get("recordsMaintenance", []):
        start = parse_kpn_date(record.get("start_date_raw"))
        end = parse_kpn_date(record.get("end_date_raw"))

        if start is None:
            continue

        if end is not None and end < start:
            continue

        upcoming = now <= start <= horizon

        ongoing = (
            start <= now
            and end is not None
            and end >= now
        )

        if upcoming or ongoing:
            maintenance.append(record)

    return disruptions, maintenance


def check_end_dates(records):
    print()
    print("=== KPN EINDTIJD CONTROLE ===")

    sample = records.get("recordsMaintenance", [])[:3]

    if not sample:
        print("Geen onderhoudsmeldingen gevonden.")
        return

    for record in sample:
        print()
        print("Melding:", record.get("title", "Onbekend"))
        print("Start:", record.get("start_date", "Onbekend"))
        print("Einde:", record.get("end_date", "Onbekend"))
        print(
            "Eindtijd aanwezig:",
            bool(record.get("end_date_raw"))
        )
        print(
            "Eindtijd raw:",
            record.get("end_date_raw")
        )


def main():
    records = fetch_kpn_records()

    # Controleer welke eindtijdvelden KPN levert
    check_end_dates(records)

    # Filter storingen en onderhoud
    disruptions, maintenance = filter_kpn_records(records)

    print()
    print("=== KPN CSP REPORTER - TESTOVERZICHT ===")
    print(f"Niet-opgeloste storingen: {len(disruptions)}")
    print(f"Relevant onderhoud: {len(maintenance)}")

    print()
    print("=== STORINGEN ===")

    for record in disruptions:
        print(
            "[STORING]",
            record.get("title", "Onbekend")
        )
        print(
            "Diensten:",
            record.get("categories", "Onbekend")
        )

    print()
    print("=== ONDERHOUD ===")

    for record in maintenance:
        print(
            "[ONDERHOUD]",
            record.get("title", "Onbekend")
        )
        print(
            "Start:",
            record.get("start_date", "Onbekend")
        )
        print(
            "Einde:",
            record.get("end_date", "Onbekend")
        )
        print(
            "Diensten:",
            record.get("categories", "Onbekend")
        )


if __name__ == "__main__":
    main()
