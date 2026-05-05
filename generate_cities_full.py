import requests
import json
import time

# ============================================
# הקובץ הזה עושה 2 דברים:
# 1. מביא את כל היישובים בישראל (data.gov)
# 2. מוסיף לכל אחד קואורדינטות (lat/lng)
# 3. יוצר קובץ settlements_locations.json מוכן
# ============================================

API_URL = "https://data.gov.il/api/3/action/datastore_search"
RESOURCE_ID = "5c78e9fa-c2e2-4771-93ff-7f400a12f7ba"


def get_all_cities():
    print("📡 מושך רשימת יישובים מ־data.gov...")

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

    print(f"✅ נמצאו {len(cities)} יישובים")
    return cities


def geocode_city(city):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{city}, Israel",
            "format": "json",
            "limit": 1
        }

        headers = {
            "User-Agent": "vendora-bot"
        }

        res = requests.get(url, params=params, headers=headers)
        data = res.json()

        if data:
            return {
                "lat": float(data[0]["lat"]),
                "lng": float(data[0]["lon"])
            }

    except Exception:
        pass

    return None


def build_locations():
    cities = get_all_cities()
    results = {}

    print("\n🌍 מתחיל להביא קואורדינטות...")

    for i, city in enumerate(cities, 1):
        print(f"{i}/{len(cities)} → {city}")

        location = geocode_city(city)

        if location:
            results[city] = location

        time.sleep(1)  # חשוב כדי לא להיחסם

    with open("settlements_locations.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n🎉 סיום! נוצר קובץ settlements_locations.json")


if __name__ == "__main__":
    build_locations()
