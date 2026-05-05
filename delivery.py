import json
import math


# ============================================================
# delivery.py
# ============================================================
# הקובץ הזה הוא "המוח" של חישוב המשלוחים.
#
# הוא משתמש ב־3 קבצים:
#
# 1. settlements_locations.json
#    מכיל את כל הערים / מושבים / קיבוצים / יישובים שאפשר לבדוק להם משלוח.
#    לכל מקום חייב להיות lat/lng כדי לחשב מרחק.
#
# 2. central_delivery_zones.json
#    מגדיר ערי בסיס למשלוחים.
#    לכל עיר בסיס יש:
#    - radius_km = עד כמה קילומטרים מהעיר הזאת אנחנו מספקים
#    - price = מחיר משלוח לאזור הזה
#
# 3. manual_delivery_prices.json
#    מחירים ידניים ליישובים חריגים.
#    אם יישוב מופיע שם — המחיר הידני גובר על כל חישוב אחר.
#
# סדר החישוב:
# 1. אם יש מחיר ידני לעיר — משתמשים בו.
# 2. אם אין מחיר ידני — מחפשים עיר בסיס קרובה בתוך רדיוס.
# 3. אם נמצאה עיר בסיס — מחזירים את המחיר שלה.
# 4. אם לא נמצאה עיר בסיס — אין מחיר משלוח והבוט לא ימשיך להזמנה.
#
# חשוב:
# אם מושב/קיבוץ לא מופיע ב־settlements_locations.json עם lat/lng,
# אי אפשר לחשב לו מרחק ולכן לא יהיה אפשר להזמין אליו אוטומטית.
# ============================================================


def load_json(filename, default=None):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        # אם יש שדה מידע פנימי בקובץ JSON — מתעלמים ממנו בלוגיקה
        if isinstance(data, dict) and "_info" in data:
            data = {k: v for k, v in data.items() if k != "_info"}

        return data

    except Exception:
        return default if default is not None else {}


def normalize_city_name(city):
    return str(city or "").strip()


def distance_km(lat1, lng1, lat2, lng2):
    r = 6371

    lat1 = float(lat1)
    lng1 = float(lng1)
    lat2 = float(lat2)
    lng2 = float(lng2)

    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )

    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_manual_delivery_price(city, manual_prices):
    city = normalize_city_name(city)

    if city in manual_prices:
        try:
            return float(manual_prices[city])
        except Exception:
            return None

    return None


def get_best_delivery_zone(city, locations, central_zones):
    city = normalize_city_name(city)

    if city not in locations:
        return None

    city_location = locations[city]
    best_zone = None

    for base_city, zone in central_zones.items():
        if base_city not in locations:
            continue

        try:
            price = float(zone.get("price"))
            radius_km = float(zone.get("radius_km"))
        except Exception:
            continue

        base_location = locations[base_city]

        distance = distance_km(
            city_location["lat"],
            city_location["lng"],
            base_location["lat"],
            base_location["lng"]
        )

        if distance <= radius_km:
            if best_zone is None or distance < best_zone["distance"]:
                best_zone = {
                    "base_city": base_city,
                    "price": price,
                    "distance": round(distance, 1),
                    "radius_km": radius_km
                }

    return best_zone


def get_delivery_price(city):
    city = normalize_city_name(city)

    locations = load_json("settlements_locations.json", {})
    central_zones = load_json("central_delivery_zones.json", {})
    manual_prices = load_json("manual_delivery_prices.json", {})

    if not city:
        return None, None, "city_not_found"

    if city not in locations:
        return None, None, "city_not_found"

    # 1. מחיר ידני — קודם כל
    manual_price = get_manual_delivery_price(city, manual_prices)

    if manual_price is not None:
        return manual_price, city, "ok"

    # 2. מחיר לפי עיר בסיס + רדיוס
    best_zone = get_best_delivery_zone(city, locations, central_zones)

    if best_zone:
        return best_zone["price"], best_zone["base_city"], "ok"

    # 3. אין מחיר מתאים
    return None, None, "no_delivery_price"
