
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime

BASE_URL = "https://clearmind-network.github.io/clearmind-narrowcasting"

NEWS_FEEDS = [
    "https://feeds.feedburner.com/tweakers/mixed",
    "https://www.security.nl/rss/headlines.xml",
]

def load_own_messages():
    with open("berichten.json", encoding="utf-8") as file:
        data = json.load(file)

    items = []

    for message in data["berichten"]:
        if not message.get("actief", True):
            continue

        item = ET.Element("item")
        ET.SubElement(item, "title").text = message["titel"]
        ET.SubElement(item, "description").text = message["tekst"]
        ET.SubElement(item, "link").text = BASE_URL + "/"
        ET.SubElement(
            item, "guid", isPermaLink="false"
        ).text = "clearmind-" + message["id"]

        date = datetime.fromisoformat(
            message["datum"]
        ).replace(tzinfo=timezone.utc)

        ET.SubElement(item, "pubDate").text = format_datetime(date)
        items.append(item)

    return items

def load_external_news():
    items = []

    for url in NEWS_FEEDS:
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "ClearMindRSS/1.0"}
            )

            with urllib.request.urlopen(
                request, timeout=15
            ) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)

            for source_item in root.findall(".//item")[:5]:
                item = ET.Element("item")

                for field in [
                    "title", "description", "link",
                    "guid", "pubDate"
                ]:
                    value = source_item.findtext(field)

                    if value:
                        ET.SubElement(item, field).text = value

                if item.find("title") is not None:
                    items.append(item)

        except Exception as error:
            print(f"Kon nieuwsfeed niet ophalen: {url}: {error}")

    return items

def main():
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "Clear Mind IT Narrowcasting"
    ET.SubElement(channel, "link").text = BASE_URL + "/"
    ET.SubElement(channel, "description").text = (
        "Clear Mind IT mededelingen en actueel ICT-nieuws"
    )
    ET.SubElement(channel, "language").text = "nl-NL"

    items = load_own_messages() + load_external_news()

    seen = set()

    for item in items:
        key = item.findtext("guid") or item.findtext("link")

        if key in seen:
            continue

        seen.add(key)
        channel.append(item)

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ", level=0)
    tree.write("rss.xml", encoding="utf-8", xml_declaration=True)

    print(f"RSS-feed gegenereerd met {len(seen)} berichten")

if __name__ == "__main__":
    main()
