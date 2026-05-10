import json
import os
import re
from difflib import get_close_matches

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTLEMENTS_FILE = os.path.join(BASE_DIR, "israel_settlements_by_region.json")
PRICES_FILE = os.path.join(BASE_DIR, "delivery_region_prices.json")


def _clean_text(value):
    value = str(value or "").strip()
    value = value.replace("\u200f", "").replace("\u200e", "")
    value = re.sub(r"\s+", " ", value)
    value = value.replace("״", '"').replace("׳", "'")
    return value


def _normalize_key(value):
    value = _clean_text(value)
    value = value.replace("-", " ")
    value = value.replace("־", " ")
    value = value.replace('"', "")
    value = value.replace("'", "")
    value = re.sub(r"\s+", " ", value).strip()

    # כתיבים נפוצים
    value = value.replace("קריית", "קרית")
    value = value.replace("תל אביב יפו", "תל אביב")
    value = value.replace("מודיעין מכבים רעות", "מודיעין")

    return value


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _load_settlements_by_region():
    data = _load_json(SETTLEMENTS_FILE, {})

    # תומך גם במבנה {"אזור": ["עיר", ...]}
    # וגם במבנה {"regions": {"אזור": [...]}}
    if isinstance(data, dict) and "regions" in data and isinstance(data["regions"], dict):
        data = data["regions"]

    if not isinstance(data, dict):
        return {}

    result = {}
    for region, cities in data.items():
        if str(region).startswith("_"):
            continue

        if isinstance(cities, dict):
            cities = list(cities.keys())

        if not isinstance(cities, list):
            continue

        result[str(region)] = [_clean_text(c) for c in cities if _clean_text(c)]

    return result


def _load_prices():
    data = _load_json(PRICES_FILE, {})

    if not isinstance(data, dict):
        return {}

    prices = {}
    for region, value in data.items():
        if str(region).startswith("_"):
            continue

        if isinstance(value, dict):
            price = value.get("price", value.get("delivery_price", value.get("amount")))
        else:
            price = value

        try:
            prices[str(region)] = float(price)
        except Exception:
            continue

    return prices


SETTLEMENTS_BY_REGION = _load_settlements_by_region()
REGION_PRICES = _load_prices()

_LOCATION_TO_REGION = {}
_LOCATION_DISPLAY = {}

for region, locations in SETTLEMENTS_BY_REGION.items():
    for location in locations:
        key = _normalize_key(location)
        if key:
            _LOCATION_TO_REGION[key] = region
            _LOCATION_DISPLAY[key] = location


def get_all_israel_locations():
    """מחזיר רשימת כל היישובים שהמערכת מכירה."""
    return sorted(set(_LOCATION_DISPLAY.values()))


def normalize_israel_location(city):
    """
    מקבל טקסט מהלקוח ומחזיר שם יישוב תקין כפי שמופיע במאגר.
    אם לא נמצא — מחזיר None.
    """
    raw = _clean_text(city)
    if not raw:
        return None

    key = _normalize_key(raw)

    if key in _LOCATION_DISPLAY:
        return _LOCATION_DISPLAY[key]

    # התאמות ידניות נפוצות
    aliases = {
        "תא": "תל אביב - יפו",
        "תא יפו": "תל אביב - יפו",
        "תל אביב": "תל אביב - יפו",
        "מודיעין": "מודיעין-מכבים-רעות",
        "קרית גת": "קריית גת",
        "קרית מלאכי": "קריית מלאכי",
        "קרית אונו": "קריית אונו",
        "קרית שמונה": "קריית שמונה",
    }

    alias = aliases.get(key)
    if alias:
        alias_key = _normalize_key(alias)
        return _LOCATION_DISPLAY.get(alias_key, alias)

    # חיפוש חלקי מדויק יחסית
    matches = [
        display for norm, display in _LOCATION_DISPLAY.items()
        if norm.startswith(key) or key.startswith(norm)
    ]
    if len(matches) == 1:
        return matches[0]

    return None


def suggest_israel_locations(query, limit=8):
    """
    Auto-complete: מחזיר הצעות יישובים לפי מה שהלקוח הקליד.
    """
    query = _clean_text(query)
    if not query:
        return []

    key = _normalize_key(query)
    if not key:
        return []

    suggestions = []

    # התחלה בשם
    for norm, display in _LOCATION_DISPLAY.items():
        if norm.startswith(key):
            suggestions.append(display)

    # מכיל בשם
    if len(suggestions) < limit:
        for norm, display in _LOCATION_DISPLAY.items():
            if key in norm and display not in suggestions:
                suggestions.append(display)

    # דמיון טקסטואלי
    if len(suggestions) < limit:
        close = get_close_matches(key, list(_LOCATION_DISPLAY.keys()), n=limit, cutoff=0.72)
        for norm in close:
            display = _LOCATION_DISPLAY.get(norm)
            if display and display not in suggestions:
                suggestions.append(display)

    return suggestions[: int(limit)]


def get_region_for_location(city):
    """
    מחזיר את האזור של היישוב.
    """
    normalized = normalize_israel_location(city)
    if not normalized:
        return None

    return _LOCATION_TO_REGION.get(_normalize_key(normalized))


def get_delivery_price(city):
    """
    פונקציה תואמת ל-shop_handlers.py.
    מחזירה tuple:
    (delivery_price, base_city_or_region, status)

    status:
    - "ok" אם נמצא מחיר
    - "unknown_city" אם העיר לא קיימת במאגר
    - "no_price" אם העיר קיימת אבל אין מחיר לאזור
    """
    normalized = normalize_israel_location(city)

    if not normalized:
        return None, None, "unknown_city"

    region = get_region_for_location(normalized)

    if not region:
        return None, normalized, "unknown_city"

    price = REGION_PRICES.get(region)

    if price is None:
        return None, region, "no_price"

    return price, region, "ok"


def is_valid_israel_location(city):
    return normalize_israel_location(city) is not None


def debug_delivery_region(city):
    normalized = normalize_israel_location(city)
    region = get_region_for_location(city)
    price, base, status = get_delivery_price(city)

    return {
        "input": city,
        "normalized": normalized,
        "region": region,
        "price": price,
        "base": base,
        "status": status,
        "suggestions": suggest_israel_locations(city),
    }
