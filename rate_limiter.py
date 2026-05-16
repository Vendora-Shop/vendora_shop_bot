import time
from collections import defaultdict, deque


# RATE_LIMITER_V1
# מנגנון הגבלת פעולות פשוט בזיכרון.
# מתאים לבוט ב-Railway כל עוד יש instance אחד.
# בעתיד, אם יהיו כמה instances, כדאי להעביר ל-Redis.

_ACTIONS = defaultdict(deque)


DEFAULT_LIMITS = {
    "start": (5, 60),              # עד 5 פעמים בדקה
    "coupon_attempt": (5, 300),    # עד 5 ניסיונות קופון ב-5 דקות
    "support_ticket": (3, 3600),   # עד 3 פניות שירות בשעה
    "checkout": (5, 300),          # עד 5 ניסיונות checkout ב-5 דקות
    "callback": (40, 60),          # עד 40 callbacks בדקה
    "text": (30, 60),              # עד 30 הודעות טקסט בדקה
}


def _key(user_id, action):
    return f"{int(user_id)}:{str(action)}"


def is_rate_limited(user_id, action, limit=None, window_seconds=None):
    """
    מחזיר:
    True  = חסום זמנית
    False = מותר
    """
    now = time.time()

    if limit is None or window_seconds is None:
        limit, window_seconds = DEFAULT_LIMITS.get(action, (20, 60))

    key = _key(user_id, action)
    bucket = _ACTIONS[key]

    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()

    if len(bucket) >= int(limit):
        return True

    bucket.append(now)
    return False


def get_retry_after(user_id, action, window_seconds=None):
    if window_seconds is None:
        _, window_seconds = DEFAULT_LIMITS.get(action, (20, 60))

    key = _key(user_id, action)
    bucket = _ACTIONS.get(key)

    if not bucket:
        return 0

    now = time.time()
    oldest = bucket[0]
    retry_after = int(max(0, window_seconds - (now - oldest)))
    return retry_after


def clear_user_limits(user_id):
    prefix = f"{int(user_id)}:"
    for key in list(_ACTIONS.keys()):
        if key.startswith(prefix):
            _ACTIONS.pop(key, None)


def rate_limit_message(action):
    messages = {
        "start": "⚠️ יותר מדי לחיצות על Start. נסה שוב בעוד רגע.",
        "coupon_attempt": "⚠️ יותר מדי ניסיונות קופון. נסה שוב מאוחר יותר.",
        "support_ticket": "⚠️ נפתחו יותר מדי פניות בזמן קצר. נסה שוב מאוחר יותר.",
        "checkout": "⚠️ יותר מדי ניסיונות הזמנה בזמן קצר. נסה שוב בעוד רגע.",
        "callback": "⚠️ יותר מדי לחיצות בזמן קצר. נסה שוב בעוד רגע.",
        "text": "⚠️ נשלחו יותר מדי הודעות בזמן קצר. נסה שוב בעוד רגע.",
    }
    return messages.get(action, "⚠️ יותר מדי פעולות בזמן קצר. נסה שוב בעוד רגע.")
