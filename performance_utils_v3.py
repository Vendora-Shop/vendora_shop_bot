import asyncio
import time
from collections import deque


# PERFORMANCE_V3_TELEGRAM_LOAD
# כלי עזר להפחתת עומס על Telegram API:
# - queue מבוקר למחיקות הודעות
# - dedupe למחיקות כפולות
# - debounce קצר ללחיצות/פעולות מהירות
# לא משנה לוגיקה עסקית.


_DELETE_QUEUE = deque()
_DELETE_SEEN = {}
_DELETE_WORKER_TASK = None

DELETE_WORKER_SLEEP_SECONDS = 0.08
DELETE_SEEN_TTL_SECONDS = 20
MAX_QUEUE_SIZE = 500

_ACTION_DEBOUNCE = {}
ACTION_DEBOUNCE_TTL_SECONDS = 8


def _cleanup_seen(now=None):
    now = now or time.monotonic()

    try:
        for key, ts in list(_DELETE_SEEN.items()):
            if now - ts > DELETE_SEEN_TTL_SECONDS:
                _DELETE_SEEN.pop(key, None)
    except Exception:
        pass

    try:
        for key, ts in list(_ACTION_DEBOUNCE.items()):
            if now - ts > ACTION_DEBOUNCE_TTL_SECONDS:
                _ACTION_DEBOUNCE.pop(key, None)
    except Exception:
        pass


async def _delete_worker():
    while True:
        try:
            if not _DELETE_QUEUE:
                await asyncio.sleep(0.05)
                continue

            bot, chat_id, message_id = _DELETE_QUEUE.popleft()

            try:
                await bot.delete_message(chat_id, int(message_id))
            except Exception:
                pass

            await asyncio.sleep(DELETE_WORKER_SLEEP_SECONDS)

        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(0.1)


def start_delete_worker():
    global _DELETE_WORKER_TASK

    try:
        if _DELETE_WORKER_TASK and not _DELETE_WORKER_TASK.done():
            return _DELETE_WORKER_TASK

        _DELETE_WORKER_TASK = asyncio.create_task(_delete_worker())
        return _DELETE_WORKER_TASK
    except Exception:
        return None


def schedule_delete_message(bot, chat_id, message_id):
    try:
        if not bot or not chat_id or not message_id:
            return False

        now = time.monotonic()
        _cleanup_seen(now)

        key = (int(chat_id), int(message_id))

        if key in _DELETE_SEEN:
            return False

        _DELETE_SEEN[key] = now

        if len(_DELETE_QUEUE) >= MAX_QUEUE_SIZE:
            try:
                _DELETE_QUEUE.popleft()
            except Exception:
                pass

        _DELETE_QUEUE.append((bot, int(chat_id), int(message_id)))
        start_delete_worker()
        return True

    except Exception:
        return False


def schedule_delete_messages(bot, chat_id, message_ids, max_items=25):
    count = 0

    try:
        for mid in list(message_ids or [])[-int(max_items):]:
            if schedule_delete_message(bot, chat_id, mid):
                count += 1
    except Exception:
        pass

    return count


def is_fast_duplicate_action(user_id, action_key, seconds=0.7):
    try:
        now = time.monotonic()
        _cleanup_seen(now)

        key = (int(user_id), str(action_key or ""))
        last = _ACTION_DEBOUNCE.get(key)

        if last and now - last < float(seconds):
            return True

        _ACTION_DEBOUNCE[key] = now
        return False

    except Exception:
        return False


def delete_queue_size():
    try:
        return len(_DELETE_QUEUE)
    except Exception:
        return 0
