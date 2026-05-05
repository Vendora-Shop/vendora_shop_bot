import json
import math
import time
import requests


# ============================================================
# delivery.py
# ============================================================
# הקובץ הזה אחראי על כל לוגיקת המשלוחים בבוט.
#
# מה יש כאן:
#
# 1. רשימת ערים בישראל לפי אזורים:
#    ISRAEL_CITIES_BY_REGION
#    זאת רשימה של ערים בלבד, לא מושבים ולא קיבוצים.
#
# 2. זיהוי אזור לפי עיר:
#    אם הלקוח רושם עיר, המערכת יודעת לאיזה אזור היא שייכת:
#    מרכז / שפלה / שרון / דרום / נגב / צפון / שומרון וכו'.
#
# 3. חישוב מחיר משלוח:
#    המחיר לא נקבע לפי האזור הכללי, אלא לפי:
#    central_delivery_zones.json
#
#    שם אתה מגדיר ערי בסיס:
#    לדוגמה:
#    אשדוד = רדיוס 10 ק״מ = 25₪
#    יבנה = רדיוס 10 ק״מ = 45₪
#
# 4. מושבים / קיבוצים:
#    הם לא מופיעים ברשימת הערים.
#    אם לקוח רושם מושב/קיבוץ, המערכת תנסה למצוא לו קואורדינטות
#    ואז לחשב מרחק לעיר בסיס קרובה.
#
# 5. manual_delivery_prices.json
#    מחיר ידני ליישובים חריגים.
#    אם יישוב מופיע שם — המחיר הידני גובר על הכול.
#
# קבצים שהקובץ הזה משתמש בהם:
#
# settlements_locations.json
#    קואורדינטות שמורות של ערים/יישובים.
#
# central_delivery_zones.json
#    ערי בסיס + רדיוס + מחיר.
#
# manual_delivery_prices.json
#    מחירים ידניים לחריגים.
# ============================================================


SETTLEMENTS_FILE = "settlements_locations.json"
CENTRAL_ZONES_FILE = "central_delivery_zones.json"
MANUAL_PRICES_FILE = "manual_delivery_prices.json"


# ============================================================
# רשימת ערים בישראל לפי אזורים
# ערים בלבד — לא מושבים ולא קיבוצים
# ============================================================
ISRAEL_CITIES_BY_REGION = {
    "מרכז": [
        "תל אביב",
        "תל אביב יפו",
        "רמת גן",
        "גבעתיים",
        "בני ברק",
        "פתח תקווה",
        "קריית אונו",
        "אור יהודה",
        "גבעת שמואל",
        "יהוד",
        "יהוד מונוסון",
        "חולון",
        "בת ים",
        "ראשון לציון"
    ],

    "שפלה": [
        "יבנה",
        "רחובות",
        "נס ציונה",
        "גדרה",
        "קריית עקרון",
        "מזכרת בתיה",
        "מודיעין",
        "מודיעין מכבים רעות",
        "רמלה",
        "לוד",
        "בית שמש"
    ],

    "שרון": [
        "הרצליה",
        "רעננה",
        "כפר סבא",
        "הוד השרון",
        "נתניה",
        "רמת השרון",
        "טירה",
        "טייבה",
        "קלנסווה",
        "כפר יונה",
        "קדימה צורן",
        "חדרה",
        "אור עקיבא"
    ],

    "ירושלים והסביבה": [
        "ירושלים",
        "מבשרת ציון",
        "ביתר עילית",
        "מעלה אדומים"
    ],

    "יהודה ושומרון": [
        "אריאל",
        "מודיעין עילית",
        "ביתר עילית",
        "מעלה אדומים"
    ],

    "דרום": [
        "אשדוד",
        "אשקלון",
        "קריית גת",
        "שדרות",
        "נתיבות",
        "אופקים",
        "קריית מלאכי"
    ],

    "נגב": [
        "באר שבע",
        "רהט",
        "דימונה",
        "ערד",
        "ירוחם"
    ],

    "ערבה ואילת": [
        "אילת"
    ],

    "חיפה והקריות": [
        "חיפה",
        "נשר",
        "טירת כרמל",
        "קריית אתא",
        "קריית ביאליק",
        "קריית מוצקין",
        "קריית ים"
    ],

    "גליל מערבי": [
        "עכו",
        "נהריה",
        "מעלות תרשיחא",
        "שפרעם",
        "טמרה",
        "סחנין",
        "עראבה"
    ],

    "גליל וכנרת": [
        "טבריה",
        "צפת",
        "כרמיאל",
        "נוף הגליל",
        "נצרת",
        "מגדל העמק",
        "עפולה",
        "בית שאן"
    ],

    "גליל עליון": [
        "קריית שמונה"
    ],

    "רמת הגולן": [
        "קצרין"
    ],

    "משולש וואדי ערה": [
        "אום אל פחם",
        "באקה אל גרבייה",
        "ערערה",
        "כפר קרע"
    ]
}


# מילון הפוך: עיר -> אזור
CITY_TO_REGION = {}

for region_name, cities in ISRAEL_CITIES_BY_REGION.items():
    for city_name in cities:
        CITY_TO_REGION[city_name] = region_name


# שמות שהלקוחות יכולים לרשום בצורה שונה
CITY_NAME_ALIASES = {
    "תל אביב יפו": "תל אביב",
    "תא": "תל אביב",
    "פ״ת": "פתח תקווה",
    "פתח תקוה": "פתח תקווה",
    "ראשלצ": "ראשון לציון",
    "ראשון": "ראשון לציון",
    "באר שבע": "באר שבע",
    "ב״ש": "באר שבע",
    "קרית גת": "קריית גת",
    "קרית מלאכי": "קריית מלאכי",
    "קרית שמונה": "קריית שמונה",
    "קרית אתא": "קריית אתא",
    "קרית ביאליק": "קריית ביאליק",
    "קרית מוצקין": "קריית מוצקין",
    "קרית ים": "קריית ים",
    "מודיעין מכבים רעות": "מודיעין",
    "מעלות-תרשיחא": "מעלות תרשיחא"
}


# שמות באנגלית נפוצים מקובצי CSV חיצוניים
# אם settlements_locations.json שלך באנגלית, זה עוזר למצוא קואורדינטות.
HE_TO_EN_LOCATION_NAMES = {
    "תל אביב": "Tel Aviv-Yafo",
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
    "עפולה": "Afula",
    "נוף הגליל": "Nof HaGalil",
    "נצרת": "Nazareth",
    "מגדל העמק": "Migdal HaEmeq",
    "בית שאן": "Bet She'an",
    "טירת כרמל": "Tirat Karmel",
    "נשר": "Nesher",
    "קריית אתא": "Qiryat Ata",
    "קריית ביאליק": "Qiryat Bialik",
    "קריית מוצקין": "Qiryat Motzkin",
    "קריית ים": "Qiryat Yam",
    "אריאל": "Ari'el",
    "מעלה אדומים": "Maale Adummim",
    "מודיעין עילית": "Modiin Illit",
    "ביתר עילית": "Betar Illit",
    "קצרין": "Qazrin"
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

    if city in CITY_NAME_ALIASES:
        return CITY_NAME_ALIASES[city]

    return city


def get_delivery_region(city):
    city = normalize_city_name(city)
    return CITY_TO_REGION.get(city, "אזור לא מוגדר")


def get_location_lookup_names(city):
    city = normalize_city_name(city)

    names = [city]

    if city in HE_TO_EN_LOCATION_NAMES:
        names.append(HE_TO_EN_LOCATION_NAMES[city])

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


def find_location(city, locations):
    for name in get_location_lookup_names(city):
        if name in locations:
            return locations[name]

    return None


def geocode_city_online(city):
    city = normalize_city_name(city)

    queries = [
        f"{city}, Israel",
        f"{city}, ישראל"
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

            if data:
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
    city = normalize_city_name(city)

    location = find_location(city, locations)

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

    if city in manual_prices:
        try:
            return float(manual_prices[city])
        except Exception:
            return None

    return None


def get_best_delivery_zone(city_location, locations, central_zones):
    best_zone = None

    for base_city, zone in central_zones.items():
        base_location = find_location(base_city, locations)

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

    # מחיר ידני קודם
    manual_price = get_manual_delivery_price(city, manual_prices)

    if manual_price is not None:
        return manual_price, get_delivery_region(city), "ok"

    # קואורדינטות מהקובץ או חיפוש אונליין
    city_location, locations = get_or_create_location(city, locations)

    if not city_location:
        return None, get_delivery_region(city), "city_not_found"

    # חישוב לפי עיר בסיס + רדיוס
    best_zone = get_best_delivery_zone(city_location, locations, central_zones)

    if best_zone:
        return best_zone["price"], best_zone["base_city"], "ok"

    # אם לא נמצא מחיר — לא חוסמים את ההזמנה.
    # הבוט יכול להמשיך עם משלוח לתיאום מול נציג,
    # בתנאי שב־shop_handlers.py מוגדר delivery_pending.
    return None, get_delivery_region(city), "no_delivery_price"
