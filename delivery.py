import json
import math


def load_json(filename, default=None):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def distance_km(lat1, lng1, lat2, lng2):
    r = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )

    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_delivery_price(city):
    locations = load_json("settlements_locations.json", {})
    zones = load_json("central_delivery_zones.json", {})
    manual = load_json("manual_delivery_prices.json", {})

    if city not in locations:
        return None, None, "city_not_found"

    if city in manual:
        return float(manual[city]), "מחיר ידני", "ok"

    city_location = locations[city]
    best = None

    for central_city, zone in zones.items():
        if central_city not in locations:
            continue

        center = locations[central_city]

        dist = distance_km(
            city_location["lat"],
            city_location["lng"],
            center["lat"],
            center["lng"]
        )

        radius = float(zone.get("radius_km", 0))

        if dist <= radius:
            if best is None or dist < best["distance"]:
                best = {
                    "price": float(zone["price"]),
                    "base_city": central_city,
                    "distance": round(dist, 1)
                }

    if best:
        return best["price"], best["base_city"], "ok"

    return None, None, "no_delivery_price"
