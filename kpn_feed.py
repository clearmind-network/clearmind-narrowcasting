
import json
import re
import html
import urllib.request

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ==========================================
# CONFIGURATIE
# ==========================================

API_URL = (
    "https://routit.service-now.com/api/now/sp/page"
    "?portal_id=e9b7c6f087353e904d7021be8bbb3578"
    "&request_uri=%2Fcspreporter"
)

TIMEZONE = ZoneInfo("Europe/Amsterdam")
DAYS_AHEAD = 14

DUTCH_MONTHS = {
    "januari": 1,
    "februari": 2,
    "maart": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "augustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}


# ==========================================
# KPN API OPHALEN
# ==========================================

def fetch_kpn_records():
    request = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "ClearMind-Narrowcasting/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:
        data = json.load(response)

    widget = (
        data["result"]["containers"][0]
        ["rows"][0]
        ["columns"][0]
        ["widgets"][0]
        ["widget"]
    )

    return widget["data"]


# ==========================================
# TEKST OPSCHONEN
# ==========================================

def clean_description(description):
    description = re.sub(
        r"<br\s*/?>",
        " ",
        description or "",
        flags=re.IGNORECASE,
    )

    description = re.sub(
        r"<[^>]+>",
        "",
        description
    )

    return " ".join(
        html.unescape(description).split()
    )


# ==========================================
# DATUMVERWERKING
# ==========================================

def parse_kpn_date(value):
    if not value:
        return None

    value = str(value).strip()

    # Technische datum, bijvoorbeeld:
    # 2026-11-11 17:45:00
    try:
        date = datetime.fromisoformat(value)

        if date.tzinfo is None:
            date = date.replace(tzinfo=TIMEZONE)

        return date.astimezone(TIMEZONE)

    except ValueError:
        pass

    # Nederlandse datum, bijvoorbeeld:
    # woensdag 11 november 2026 17:45
    match = re.search(
        r"(\d{1,2})\s+([a-zA-Z]+)\s+"
        r"(\d{4})\s+(\d{1,2}):(\d{2})",
        value.lower()
    )

    if not match:
        return None

    day, month_name, year, hour, minute = match.groups()

    month = DUTCH_MONTHS.get(month_name)

    if month is None:
        return None

    try:
        return datetime(
            int(year),
            month,
            int(day),
            int(hour),
            int(minute),
            tzinfo=TIMEZONE,
        )

    except ValueError:
        return None


def get_record_dates(record):
    start = parse_kpn_date(
        record.get("start_date_raw")
        or record.get("start_date")
    )

    end = parse_kpn_date(
        record.get("end_date_raw")
        or record.get("end_date")
    )

    return start, end


# ==========================================
# STORINGEN EN ONDERHOUD FILTEREN
# ==========================================

def filter_kpn_records(records):
    now = datetime.now(TIMEZONE)
    horizon = now + timedelta(days=DAYS_AHEAD)

    disruptions = []
    maintenance = []

    seen_disruptions = set()
    seen_maintenance = set()

    # Storingen
    for record in records.get(
        "recordsDisruption", []
    ):
        title = str(
            record.get("title") or ""
        ).strip()

        if title.upper().startswith("[OPGELOST]"):
            continue

        record_id = (
            record.get("sys_id")
            or title
        )

        if record_id in seen_disruptions:
            continue

        seen_disruptions.add(record_id)
        disruptions.append(record)

    # Onderhoud
    for record in records.get(
        "recordsMaintenance", []
    ):
        start, end = get_record_dates(record)

        if start is None:
            continue

        if end is not None and end < start:
            continue

        # Onderhoud binnen 14 dagen
        upcoming = now <= start <= horizon

        # Onderhoud dat momenteel loopt
        ongoing = (
            start <= now
            and end is not None
            and now <= end
        )

        if not (upcoming or ongoing):
            continue

        record_id = (
            record.get("sys_id")
            or (
                record.get("title"),
                record.get("start_date")
            )
        )

        if record_id in seen_maintenance:
            continue

        seen_maintenance.add(record_id)

        maintenance.append(record)

    # Eerstvolgend onderhoud bovenaan
    maintenance.sort(
        key=lambda record: (
            get_record_dates(record)[0]
            or datetime.max.replace(
                tzinfo=TIMEZONE
            )
        )
    )

    return disruptions, maintenance


# ==========================================
# API VELDEN CONTROLEREN
# ==========================================

def check_kpn_fields(records):
    print()
    print("=== KPN API VELDEN CONTROLE ===")

    sample = records.get(
        "recordsMaintenance", []
    )[:3]

    if not sample:
        print("Geen onderhoud gevonden.")
        return

    for record in sample:
        start, end = get_record_dates(record)

        print()
        print(
            "Melding:",
            record.get("title", "Onbekend")
        )

        print(
            "Beschikbare velden:",
            sorted(record.keys())
        )

        print(
            "Start raw:",
            record.get("start_date_raw")
        )

        print(
            "Einde raw:",
            record.get("end_date_raw")
        )

        print(
            "Start verwerkt:",
            start.isoformat() if start else "Onbekend"
        )

        print(
            "Einde verwerkt:",
            end.isoformat() if end else "Onbekend"
        )


# ==========================================
# TESTRESULTATEN TONEN
# ==========================================

def main():
    records = fetch_kpn_records()

    check_kpn_fields(records)

    disruptions, maintenance = filter_kpn_records(
        records
    )

    print()
    print("=== KPN CSP REPORTER ===")

    print(
        "Niet-opgeloste storingen:",
        len(disruptions)
    )

    print(
        "Relevant onderhoud:",
        len(maintenance)
    )

    print()
    print("=== STORINGEN ===")

    for record in disruptions:
        print()
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
        start, end = get_record_dates(record)

        now = datetime.now(TIMEZONE)

        status = (
            "BEZIG"
            if start <= now and end and now <= end
            else "GEPLAND"
        )

        print()
        print(
            f"[{status}]",
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

        print(
            "ID:",
            record.get("sys_id", "Onbekend")
        )


if __name__ == "__main__":
    main()
