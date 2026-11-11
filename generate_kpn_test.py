
import xml.etree.ElementTree as ET
from email.utils import format_datetime

from kpn_feed import (
    fetch_kpn_records,
    filter_kpn_records,
    get_record_dates,
    clean_description,
)

SOURCE_URL = "https://routit.service-now.com/cspreporter"
OUTPUT_FILE = "kpn-test.xml"


def add_item(channel, record, kind):
    start, end = get_record_dates(record)

    record_id = record.get("sys_id")
    if not record_id:
        print("Melding overgeslagen: sys_id ontbreekt")
        return False

    title = str(record.get("title") or "Onbekende melding")
    description = clean_description(
        record.get("description") or ""
    )

    categories = record.get("categories") or ""
    if isinstance(categories, list):
        categories = ", ".join(map(str, categories))

    details = []

    if start:
        details.append(
            "Start: " + start.strftime("%d-%m-%Y %H:%M")
        )

    if end:
        details.append(
            "Einde: " + end.strftime("%d-%m-%Y %H:%M")
        )

    if categories:
        details.append("Diensten: " + str(categories))

    if description:
        details.append(description)

    item = ET.SubElement(channel, "item")

    ET.SubElement(item, "title").text = (
        f"KPN {kind} | {title}"
    )

    ET.SubElement(item, "description").text = (
        "\n".join(details)
    )

    ET.SubElement(item, "link").text = SOURCE_URL

    ET.SubElement(
        item, "guid", isPermaLink="false"
    ).text = "kpn-" + str(record_id)

    if start:
        ET.SubElement(item, "pubDate").text = (
            format_datetime(start)
        )

    return True


def main():
    records = fetch_kpn_records()
    disruptions, maintenance = filter_kpn_records(records)

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = (
        "Clear Mind IT - KPN Testfeed"
    )

    ET.SubElement(channel, "link").text = SOURCE_URL

    ET.SubElement(channel, "description").text = (
        "Testfeed voor KPN storingen en onderhoud"
    )

    ET.SubElement(channel, "language").text = "nl-NL"

    count = 0

    for record in disruptions:
        if add_item(channel, record, "STORING"):
            count += 1

    for record in maintenance:
        if add_item(channel, record, "ONDERHOUD"):
            count += 1

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")

    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    # Controleer of het gegenereerde XML geldig is
    ET.parse(OUTPUT_FILE)

    print(f"KPN testfeed gegenereerd: {OUTPUT_FILE}")
    print(f"Storingen: {len(disruptions)}")
    print(f"Onderhoud: {len(maintenance)}")
    print(f"RSS-items: {count}")


if __name__ == "__main__":
    main()
