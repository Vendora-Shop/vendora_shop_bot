import os
import shutil
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from database import DB_PATH


BACKUP_DIR = os.getenv("VENDORA_BACKUP_DIR", "/data/backups")
LOCAL_BACKUP_DIR = "backups"
DEFAULT_KEEP_LAST = int(os.getenv("VENDORA_BACKUP_KEEP_LAST", "30"))


def israel_now():
    return datetime.now(ZoneInfo("Asia/Jerusalem"))


def safe_backup_dir():
    """
    מחזיר תיקיית גיבוי תקינה.
    ב-Railway נעדיף /data/backups.
    במחשב מקומי ניפול ל-backups.
    """
    try:
        Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        test_path = Path(BACKUP_DIR) / ".test"
        test_path.write_text("ok", encoding="utf-8")
        test_path.unlink(missing_ok=True)
        return Path(BACKUP_DIR)
    except Exception:
        Path(LOCAL_BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        return Path(LOCAL_BACKUP_DIR)


def backup_filename(reason="manual"):
    reason = str(reason or "manual").strip().replace(" ", "_")
    reason = "".join(ch for ch in reason if ch.isalnum() or ch in {"_", "-"})
    timestamp = israel_now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"vendora_shop_backup_{timestamp}_{reason}.db"


def create_db_backup(reason="manual", keep_last=DEFAULT_KEEP_LAST):
    """
    יוצר גיבוי בטוח ל-SQLite בלי לעצור את הבוט.
    משתמש ב-SQLite backup API ולא רק copy רגיל.
    """
    source = Path(DB_PATH)

    if not source.exists():
        return {
            "ok": False,
            "error": f"DB file not found: {source}",
            "path": None,
        }

    backup_dir = safe_backup_dir()
    target = backup_dir / backup_filename(reason)

    try:
        src_conn = sqlite3.connect(str(source))
        dst_conn = sqlite3.connect(str(target))

        with dst_conn:
            src_conn.backup(dst_conn)

        src_conn.close()
        dst_conn.close()

        cleanup_old_backups(keep_last=keep_last)

        return {
            "ok": True,
            "error": None,
            "path": str(target),
            "filename": target.name,
            "size_bytes": target.stat().st_size if target.exists() else 0,
        }

    except Exception as e:
        try:
            src_conn.close()
        except Exception:
            pass
        try:
            dst_conn.close()
        except Exception:
            pass

        return {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "path": None,
        }


def list_db_backups(limit=20):
    backup_dir = safe_backup_dir()
    files = sorted(
        backup_dir.glob("vendora_shop_backup_*.db"),
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
            "modified_at": datetime.fromtimestamp(stat.st_mtime, ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return result


def cleanup_old_backups(keep_last=DEFAULT_KEEP_LAST):
    keep_last = max(1, int(keep_last or DEFAULT_KEEP_LAST))
    backup_dir = safe_backup_dir()

    files = sorted(
        backup_dir.glob("vendora_shop_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    deleted = []

    for path in files[keep_last:]:
        try:
            path.unlink()
            deleted.append(path.name)
        except Exception:
            pass

    return deleted


def restore_db_backup(backup_path):
    """
    שחזור DB מגיבוי.
    חשוב: להשתמש בזה רק כשהבוט כבוי או כשאין פעולות פעילות.
    לפני שחזור נוצר גיבוי safety אוטומטי.
    """
    backup_path = Path(backup_path)

    if not backup_path.exists():
        return {
            "ok": False,
            "error": "Backup file not found.",
        }

    safety = create_db_backup(reason="before_restore")

    try:
        target = Path(DB_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(str(backup_path), str(target))

        return {
            "ok": True,
            "error": None,
            "restored_from": str(backup_path),
            "safety_backup": safety.get("path"),
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "safety_backup": safety.get("path"),
        }


def format_backup_list(backups):
    if not backups:
        return "אין עדיין גיבויים."

    lines = []
    for idx, backup in enumerate(backups, start=1):
        size_mb = float(backup.get("size_bytes", 0)) / 1024 / 1024
        lines.append(
            f"{idx}. {backup.get('filename')}\n"
            f"   תאריך: {backup.get('modified_at')}\n"
            f"   גודל: {size_mb:.2f}MB"
        )

    return "\n\n".join(lines)
