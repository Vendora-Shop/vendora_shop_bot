import os
import json
from pathlib import Path


# MAINTENANCE_MODE_V1

MAINTENANCE_FILE = os.getenv(
    "VENDORA_MAINTENANCE_FILE",
    "/data/maintenance_mode.json"
)


DEFAULT_DATA = {
    "enabled": False,
    "message": "🛠️ החנות נמצאת כרגע בתחזוקה.\nנסה שוב מאוחר יותר."
}


def maintenance_file_path():
    path = Path(MAINTENANCE_FILE)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    return path


def load_maintenance_data():
    path = maintenance_file_path()

    if not path.exists():
        save_maintenance_data(DEFAULT_DATA)
        return DEFAULT_DATA.copy()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return DEFAULT_DATA.copy()

        return {
            "enabled": bool(data.get("enabled", False)),
            "message": str(
                data.get("message") or DEFAULT_DATA["message"]
            ),
        }

    except Exception:
        return DEFAULT_DATA.copy()


def save_maintenance_data(data):
    path = maintenance_file_path()

    payload = {
        "enabled": bool(data.get("enabled", False)),
        "message": str(
            data.get("message") or DEFAULT_DATA["message"]
        ),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )

    return payload


def is_maintenance_enabled():
    data = load_maintenance_data()
    return bool(data.get("enabled", False))


def maintenance_message():
    data = load_maintenance_data()
    return str(data.get("message") or DEFAULT_DATA["message"])


def enable_maintenance(message=None):
    data = load_maintenance_data()

    data["enabled"] = True

    if message:
        data["message"] = str(message)

    save_maintenance_data(data)

    return data


def disable_maintenance():
    data = load_maintenance_data()

    data["enabled"] = False

    save_maintenance_data(data)

    return data
