import json
import math
import time
import requests


# ============================================================
# delivery.py
# ============================================================
# הקובץ הזה אחראי על כל לוגיקת המשלוחים.
#
# איך זה עובד:
#
# 1. settlements_locations.json
#    קובץ קואורדינטות.
#    כל עיר / מושב / קיבוץ / יישוב שמופיע כאן יכול לקבל חישוב מרחק.
#
# 2. central_delivery_zones.json
#    קובץ ערי בסיס.
#    כאן אתה מגדיר רק ערים מרכזיות:
#    אשדוד / יבנה / רחובות / תל אביב / חיפה וכו'
#    לכל עיר בסיס יש:
#    price = מחיר משלוח
#    radius_km = עד כמה ק״מ מאותה עיר המחיר תקף
#
# 3. manual_delivery_prices.json
#    מחירים ידניים ליישובים חריגים.
#    אם יישוב מופיע כאן — המחיר הידני גובר על הכול.
#
# 4. אם לקוח רושם יישוב שלא קיים ב־settlements_locations.json:
#    המערכת מנסה למצוא אותו אוטומטית דרך OpenStreetMap/Nominatim.
#    אם היא מוצאת — היא שומרת אותו לתוך settlements_locations.json
#    ואז מחשבת מחיר לפי עיר הבסיס הקרובה.
#
# המשמעות:
# אתה לא צריך להוסיף ידנית כל מושב/קיבוץ.
# מספיק שתגדיר ערי בסיס + רדיוס + מחיר.
# ============================================================


SETTLEMENTS_FILE = "settlements_locations.json"
CENTRAL_ZONES_FILE = "central_delivery_zones.json"
MANUAL_PRICES_FILE = "manual_delivery_prices.json"


# שמות נפוצים שהלקוחות יכתבו בעברית, מול שמות באנגלית אם הקובץ שלך הגיע מ־CSV באנגלית.
# אפשר להוסיף כאן עוד עיר רק אם צריך. המערכת עדיין יודעת לחפש לבד יישוב שלא קיים.
CITY_ALIASES = {
    "תל אביב": "Tel Aviv-Yafo",
    "תל אביב יפו": "Tel Aviv-Yafo",
    "ירושלים": "Jerusalem",
    "חיפה": "Haifa",
    "ראשון לציון": "Rishon LeZiyyon",
    "פתח תקווה": "Petah Tiqwa",
    "אשדוד": "Ashdod",
    "נתניה": "Netanya",
    "באר שבע": "Beer Sheva",
    "בני ברק": "Bnei Brak",
    "חולון": "Holon",
    "רמת גן": "Ramat Gan",
    "אשקלון": "Ashqelon",
    "רחובות": "Rehovot",
    "בת ים": "Bat Yam",
    "בית שמש": "Bet Shemesh",
    "כפר סבא": "Kefar Sava",
    "הרצליה": "Herzliyya",
    "חדרה": "Hadera",
    "מודיעין": "Modiin",
    "מודיעין מכבים רעות": "Modiin Makkabbim Reut",
    "יבנה": "Yavne",
    "רעננה": "Raanana",
    "לוד": "Lod",
    "רמלה": "Ramla",
    "נהריה": "Nahariyya",
    "קריית גת": "Qiryat Gat",
    "אילת": "Eilat",
    "טבריה": "Tiberias",
    "עכו": "Akko",
    "צפת": "Safed",
    "כרמיאל": "Karmi'el",
    "קריית שמונה": "Qiryat Shemona",
    "אופקים": "Ofaqim",
    "נתיבות": "Netivot",
    "שדרות": "Sderot",
    "דימונה": "Dimona",
    "ערד": "Arad",
    "אור יהודה": "Or Yehuda",
    "גבעתיים": "Givatayim",
    "קריית אונו": "Qiryat Ono",
    "נס ציונה": "Ness Ziona",
    "גדרה": "Gedera",
    "גן יבנה": "Gan Yavne",
}


def load_json(filename, default=None):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "_info" in data:
            data = {k: v for k, v in data.items() if k != "_info"}

        return data

    except Exception:
        return default if default is not None else {}


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def normalize_city_name(city):
    city = str(city or "").strip()
    city = city.replace("  ", " ")
    return city


def get_lookup_names(city):
    city = normalize_city_name(city)
    names = [city]

    if city in CITY_ALIASES:
        names.append(CITY_ALIASES[city])

    return list(dict.fromkeys(names))


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


def find_location_in_file(city, locations):
    for name in get_lookup_names(city):
        if name in locations:
            return locations[name]

    return None


def geocode_city_online(city):
    """
    מחפש קואורדינטות ליישוב שלא נמצא בקובץ.
    משתמש ב־OpenStreetMap/Nominatim.
    עובד גם לערים וגם למושבים/קיבוצים, אם השירות מזהה אותם.
    """

    city = normalize_city_name(city)

    queries = [
        f"{city}, Israel",
        f"{city}, ישראל",
    ]

    for query in queries:
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "countrycodes": "il"
            }
            headers = {
                "User-Agent": "VendoraShopBot/1.0"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                continue

            data = response.json()

            if not data:
                continue

            return {
                "lat": float(data[0]["lat"]),
                "lng": float(data[0]["lon"])
            }

        except Exception:
            continue

        finally:
            time.sleep(1)

    return None


def get_or_create_location(city, locations):
    """
    מחזיר קואורדינטות.
    אם היישוב לא נמצא בקובץ — מנסה למצוא אותו אונליין ולשמור.
    """

    city = normalize_city_name(city)

    location = find_location_in_file(city, locations)

    if location:
        return location, locations

    location = geocode_city_online(city)

    if location:
        locations[city] = location
        save_json(SETTLEMENTS_FILE, locations)
        return location, locations

    return None, locations


def get_manual_delivery_price(city, manual_prices):
    city = normalize_city_name(city)

    for name in get_lookup_names(city):
        if name in manual_prices:
            try:
                return float(manual_prices[name])
            except Exception:
                return None

    return None


def get_best_delivery_zone(city_location, locations, central_zones):
    best_zone = None

    for base_city, zone in central_zones.items():
        base_location = find_location_in_file(base_city, locations)

        if not base_location:
            continue

        try:
            price = float(zone.get("price"))
            radius_km = float(zone.get("radius_km"))
        except Exception:
            continue

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

    locations = load_json(SETTLEMENTS_FILE, {})
    central_zones = load_json(CENTRAL_ZONES_FILE, {})
    manual_prices = load_json(MANUAL_PRICES_FILE, {})

    if not city:
        return None, None, "city_not_found"

    # 1. מחיר ידני גובר על הכול
    manual_price = get_manual_delivery_price(city, manual_prices)

    if manual_price is not None:
        return manual_price, city, "ok"

    # 2. קואורדינטות — מקובץ או חיפוש אוטומטי
    city_location, locations = get_or_create_location(city, locations)

    if not city_location:
        return None, None, "city_not_found"

    # 3. חישוב לפי עיר בסיס + רדיוס
    best_zone = get_best_delivery_zone(city_location, locations, central_zones)

    if best_zone:
        return best_zone["price"], best_zone["base_city"], "ok"

    # 4. היישוב נמצא, אבל מחוץ לכל אזור משלוח שהגדרת
    return None, None, "no_delivery_price"
