import json
import os
import re
from difflib import get_close_matches

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTLEMENTS_BY_REGION_FILE = os.path.join(BASE_DIR, "israel_settlements_by_region.json")
REGION_PRICES_FILE = os.path.join(BASE_DIR, "delivery_region_prices.json")


def _clean(text):
    return re.sub(r"\s+", " ", str(text or "").strip())


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_locations():
    data = _load_json(SETTLEMENTS_BY_REGION_FILE)
    return data.get("locations", {})


def load_region_prices():
    return _load_json(REGION_PRICES_FILE)


def get_location(city_name):
    city_name = _clean(city_name)
    locations = load_locations()
    return locations.get(city_name)


def is_valid_israel_location(city_name):
    return get_location(city_name) is not None


def autocomplete_locations(query, limit=8):
    query = _clean(query)
    if not query:
        return []

    locations = load_locations()
    names = list(locations.keys())

    starts = [name for name in names if name.startswith(query)]
    contains = [name for name in names if query in name and name not in starts]
    fuzzy = [name for name in get_close_matches(query, names, n=limit, cutoff=0.75) if name not in starts and name not in contains]

    return (starts + contains + fuzzy)[:limit]


def get_region_for_location(city_name):
    location = get_location(city_name)
    if not location:
        return None
    return location.get("region")


def get_delivery_price_by_region(city_name):
    """
    Returns: (price, region, status)
    status values:
      ok
      not_found
      inactive_region
      price_not_configured
    """
    region = get_region_for_location(city_name)
    if not region:
        return None, None, "not_found"

    prices = load_region_prices()
    cfg = prices.get(region)
    if not cfg or not cfg.get("active", False):
        return None, region, "inactive_region"

    price = cfg.get("price")
    if price is None:
        return None, region, "price_not_configured"

    return float(price), region, "ok"
