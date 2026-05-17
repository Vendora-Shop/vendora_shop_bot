import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path


# AUDIT_LOGGER_V1
AUDIT_DIR = os.getenv("VENDORA_AUDIT_DIR", "/data/audit_logs")
LOCAL_AUDIT_DIR = "audit_logs"


def israel_now():
    return datetime.now(ZoneInfo("Asia/Jerusalem"))


def safe_audit_dir():
    try:
        Path(AUDIT_DIR).mkdir(parents=True, exist_ok=True)
        test_path = Path(AUDIT_DIR) / ".test"
        test_path.write_text("ok", encoding="utf-8")
        test_path.unlink(missing_ok=True)
        return Path(AUDIT_DIR)
    except Exception:
        Path(LOCAL_AUDIT_DIR).mkdir(parents=True, exist_ok=True)
        return Path(LOCAL_AUDIT_DIR)


def audit_file_path():
    date = israel_now().strftime("%Y-%m-%d")
    return safe_audit_dir() / f"vendora_audit_{date}.jsonl"


def write_audit_event(
    admin_id,
    action,
    entity_type="system",
    entity_id="",
    old_value=None,
    new_value=None,
    details=""
):
    """
    שומר פעולה רגישה של אדמין לקובץ JSONL.
    כל שורה היא אירוע audit עצמאי.
    """
    event = {
        "timestamp": israel_now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin_id": int(admin_id) if str(admin_id).isdigit() else str(admin_id),
        "action": str(action),
        "entity_type": str(entity_type or "system"),
        "entity_id": str(entity_id or ""),
        "old_value": old_value,
        "new_value": new_value,
        "details": str(details or ""),
    }

    path = audit_file_path()

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return str(path)


def list_audit_files(limit=20):
    files = sorted(
        safe_audit_dir().glob("vendora_audit_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    result = []
    for path in files[:int(limit)]:
        stat = path.stat()
        result.append({
            "filename": path.name,
            "path": str(path),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(
                stat.st_mtime,
                ZoneInfo("Asia/Jerusalem")
            ).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return result


def format_audit_files(files):
    if not files:
        return "אין עדיין קבצי Audit."

    lines = []

    for idx, item in enumerate(files, start=1):
        size_mb = float(item.get("size_bytes", 0)) / 1024 / 1024
        lines.append(
            f"{idx}. {item.get('filename')}\n"
            f"   תאריך: {item.get('modified_at')}\n"
            f"   גודל: {size_mb:.2f}MB"
        )

    return "\n\n".join(lines)
