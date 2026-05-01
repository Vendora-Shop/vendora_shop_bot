import requests
import json

API_URL = "https://data.gov.il/api/3/action/datastore_search"
RESOURCE_ID = "5c78e9fa-c2e2-4771-93ff-7f400a12f7ba"

params = {
    "resource_id": RESOURCE_ID,
    "limit": 32000
}

response = requests.get(API_URL, params=params)
response.raise_for_status()

records = response.json()["result"]["records"]

cities = []

for record in records:
    name = record.get("שם_ישוב")
    if name:
        name = name.strip()
        if name and name not in cities:
            cities.append(name)

cities.sort()

with open("cities_full.json", "w", encoding="utf-8") as f:
    json.dump(cities, f, ensure_ascii=False, indent=2)

print(f"Created cities_full.json with {len(cities)} places")
