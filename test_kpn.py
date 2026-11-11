
import json
import urllib.request
import urllib.error

URL = (
    "https://routit.service-now.com/api/now/sp/page"
    "?portal_id=e9b7c6f087353e904d7021be8bbb3578"
    "&request_uri=%2Fcspreporter"
)

request = urllib.request.Request(
    URL,
    headers={
        "User-Agent": "ClearMind-Narrowcasting-Test/1.0",
        "Accept": "application/json",
    },
)

try:
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)

    containers = data["result"]["containers"]
    widget = containers[0]["rows"][0]["columns"][0]["widgets"][0]["widget"]
    records = widget["data"]

    print("KPN API VERBINDING GESLAAGD")
    print("Actueel:", len(records.get("recordsAll", [])))
    print("Onderhoud:", len(records.get("recordsMaintenance", [])))
    print("Storingen:", len(records.get("recordsDisruption", [])))

except Exception as error:
    print("KPN API TEST MISLUKT")
    print(type(error).__name__ + ":", error)
    raise
