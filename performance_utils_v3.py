import asyncio
import time
from collections import deque


# PERFORMANCE_V3_1_FAST_DELETE
# שיפור ל־V3:
# - מחיקות רגילות עדיין עוברות queue מבוקר.
# - מחיקות של מסך קודם מקבלות urgent=True ונכנסות לראש התור.
# - worker מהיר יותר כדי שלא יהיה דיליי של 1-2 שניות במחיקת המסך הקודם.


_DELETE_QUEUE = deque()
_DELETE_SEEN = {}
_DELETE_WORKER_TASK = None

DELETE_WORKER_SLEEP_SECONDS = 0.025
DELETE_SEEN_TTL_SECONDS = 20
MAX_QUEUE_SIZE = 700

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
                await asyncio.sleep(0.03)
                continue

            # מוחקים עד 3 הודעות בכל סיבוב כדי לצמצם דיליי ויזואלי,
            # אבל עדיין לא יורים עשרות מחיקות בבת אחת.
            batch = []
            for _ in range(min(3, len(_DELETE_QUEUE))):
                try:
                    batch.append(_DELETE_QUEUE.popleft())
                except Exception:
                    break

            if not batch:
                await asyncio.sleep(0.03)
                continue

            await asyncio.gather(
                *[_delete_one(bot, chat_id, message_id) for bot, chat_id, message_id in batch],
                return_exceptions=True
            )

            await asyncio.sleep(DELETE_WORKER_SLEEP_SECONDS)

        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(0.08)


async def _delete_one(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, int(message_id))
    except Exception:
        pass


def start_delete_worker():
    global _DELETE_WORKER_TASK

    try:
        if _DELETE_WORKER_TASK and not _DELETE_WORKER_TASK.done():
            return _DELETE_WORKER_TASK

        _DELETE_WORKER_TASK = asyncio.create_task(_delete_worker())
        return _DELETE_WORKER_TASK
    except Exception:
        return None


def schedule_delete_message(bot, chat_id, message_id, urgent=False):
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

        item = (bot, int(chat_id), int(message_id))

        if urgent:
            _DELETE_QUEUE.appendleft(item)
        else:
            _DELETE_QUEUE.append(item)

        start_delete_worker()
        return True

    except Exception:
        return False


def schedule_delete_messages(bot, chat_id, message_ids, max_items=25, urgent=False):
    count = 0

    try:
        clean = list(message_ids or [])[-int(max_items):]

        # urgent=True: שומרים סדר מחיקה טבעי למרות appendleft.
        if urgent:
            clean = list(reversed(clean))

        for mid in clean:
            if schedule_delete_message(bot, chat_id, mid, urgent=urgent):
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
