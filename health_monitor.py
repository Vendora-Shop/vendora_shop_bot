import asyncio
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from database import DB_PATH
from logger import log_info, log_error


# HEALTH_MONITOR_V1
HEARTBEAT_INTERVAL_SECONDS = 300  # 5 דקות

SYSTEM_START_TIME = datetime.now(
    ZoneInfo("Asia/Jerusalem")
)


def israel_now():
    return datetime.now(ZoneInfo("Asia/Jerusalem"))


def uptime_text():
    delta = israel_now() - SYSTEM_START_TIME

    total_seconds = int(delta.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    parts.append(f"{minutes}m")

    return " ".join(parts)


def health_check_database():
    """
    בדיקת DB בסיסית.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT 1")
        cursor.fetchone()

        conn.close()

        return True, None

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def health_monitor_loop():
    """
    Heartbeat בסיסי למערכת.
    """
    log_info("Health monitor loop started", kind="system")

    while True:
        try:
            db_ok, db_error = health_check_database()

            status = (
                f"heartbeat | "
                f"uptime={uptime_text()} | "
                f"db_ok={db_ok}"
            )

            if db_error:
                status += f" | db_error={db_error}"

            log_info(status, kind="system")

        except Exception as e:
            log_error(e, context="health_monitor_loop")

        await asyncio.sleep(
            HEARTBEAT_INTERVAL_SECONDS
        )
