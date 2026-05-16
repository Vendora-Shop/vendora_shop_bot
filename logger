import os
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path


LOG_DIR = os.getenv("VENDORA_LOG_DIR", "/data/logs")
LOCAL_LOG_DIR = "logs"


def israel_now():
    return datetime.now(ZoneInfo("Asia/Jerusalem"))


def safe_log_dir():
    """
    מחזיר תיקיית לוגים תקינה.
    ב-Railway נעדיף /data/logs.
    במחשב מקומי ניפול ל-logs.
    """
    try:
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        test_path = Path(LOG_DIR) / ".test"
        test_path.write_text("ok", encoding="utf-8")
        test_path.unlink(missing_ok=True)
        return Path(LOG_DIR)
    except Exception:
        Path(LOCAL_LOG_DIR).mkdir(parents=True, exist_ok=True)
        return Path(LOCAL_LOG_DIR)


def log_filename(kind="system"):
    date = israel_now().strftime("%Y-%m-%d")
    kind = str(kind or "system").strip().replace(" ", "_")
    return f"vendora_{kind}_{date}.log"


def write_log(kind, message):
    """
    כתיבת לוג רגיל לקובץ.
    kind לדוגמה: system / orders / admin / backup / errors
    """
    log_dir = safe_log_dir()
    path = log_dir / log_filename(kind)

    timestamp = israel_now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"

    with open(path, "a", encoding="utf-8") as f:
        f.write(line)

    return str(path)


def log_info(message, kind="system"):
    try:
        return write_log(kind, f"INFO | {message}")
    except Exception:
        return None


def log_warning(message, kind="system"):
    try:
        return write_log(kind, f"WARNING | {message}")
    except Exception:
        return None


def log_error(error, context=""):
    """
    שמירת exception מלא כולל traceback.
    """
    try:
        timestamp = israel_now().strftime("%Y-%m-%d %H:%M:%S")
        err_type = type(error).__name__
        err_message = str(error)
        tb = traceback.format_exc()

        content = (
            f"ERROR | {timestamp}\n"
            f"Context: {context}\n"
            f"Type: {err_type}\n"
            f"Message: {err_message}\n"
            f"Traceback:\n{tb}\n"
            f"{'-' * 80}\n"
        )

        log_dir = safe_log_dir()
        path = log_dir / log_filename("errors")

        with open(path, "a", encoding="utf-8") as f:
            f.write(content)

        return str(path)
    except Exception:
        return None


def log_admin_action(admin_id, action, details=""):
    """
    לוג פעולות אדמין חשובות.
    """
    msg = f"ADMIN_ID={admin_id} | ACTION={action}"
    if details:
        msg += f" | DETAILS={details}"
    return log_info(msg, kind="admin")


def log_order_event(order_number, event, details=""):
    """
    לוג אירועים של הזמנות.
    """
    msg = f"ORDER={order_number} | EVENT={event}"
    if details:
        msg += f" | DETAILS={details}"
    return log_info(msg, kind="orders")


def log_backup_event(event, details=""):
    """
    לוג אירועים של גיבויים.
    """
    msg = f"BACKUP_EVENT={event}"
    if details:
        msg += f" | DETAILS={details}"
    return log_info(msg, kind="backup")


def list_log_files(limit=20):
    log_dir = safe_log_dir()
    files = sorted(
        log_dir.glob("vendora_*.log"),
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
