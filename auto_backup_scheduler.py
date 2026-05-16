import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from backup_manager import create_db_backup


AUTO_BACKUP_INTERVAL_HOURS = 12


def israel_now():
    return datetime.now(ZoneInfo("Asia/Jerusalem"))


async def automatic_backup_loop():
    """
    יוצר גיבוי אוטומטי כל X שעות.
    מיועד לרוץ ברקע עם הבוט.
    """

    print("AUTO_BACKUP_LOOP_STARTED")

    while True:
        try:
            result = create_db_backup(reason="auto")

            if result.get("ok"):
                print(
                    "AUTO_BACKUP_OK:",
                    result.get("filename"),
                )
            else:
                print(
                    "AUTO_BACKUP_FAILED:",
                    result.get("error"),
                )

        except Exception as e:
            print(
                f"AUTO_BACKUP_LOOP_ERROR: {type(e).__name__}: {e}"
            )

        await asyncio.sleep(
            AUTO_BACKUP_INTERVAL_HOURS * 60 * 60
        )
