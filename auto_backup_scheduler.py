import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from backup_manager import create_db_backup
from logger import log_backup_event, log_error


AUTO_BACKUP_INTERVAL_HOURS = 24


def israel_now():
    return datetime.now(ZoneInfo("Asia/Jerusalem"))


async def automatic_backup_loop():
    """
    יוצר גיבוי אוטומטי כל X שעות.
    מיועד לרוץ ברקע עם הבוט.
    """

    print("AUTO_BACKUP_LOOP_STARTED")
    # AUTO_BACKUP_LOGGING_V1
    log_backup_event("auto_loop_started", f"interval_hours={AUTO_BACKUP_INTERVAL_HOURS}")

    while True:
        try:
            result = create_db_backup(reason="auto")

            if result.get("ok"):
                print(
                    "AUTO_BACKUP_OK:",
                    result.get("filename"),
                )
                log_backup_event("auto_backup_ok", f"file={result.get('filename')} | size={result.get('size_bytes')}")
            else:
                print(
                    "AUTO_BACKUP_FAILED:",
                    result.get("error"),
                )
                log_backup_event("auto_backup_failed", f"error={result.get('error')}")

        except Exception as e:
            print(
                f"AUTO_BACKUP_LOOP_ERROR: {type(e).__name__}: {e}"
            )
            log_error(e, context="automatic_backup_loop")

        await asyncio.sleep(
            AUTO_BACKUP_INTERVAL_HOURS * 60 * 60
        )
