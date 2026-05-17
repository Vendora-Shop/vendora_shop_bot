import json
import asyncio
from pathlib import Path
from html import escape

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

from audit_logger import list_audit_files, format_audit_files


# AUDIT_LOGS_UI_REAL_FIX_V2
# חיפוש Audit יציב:
# - אין תוצאות = הודעה נקייה
# - הקשקוש הבא מוחק את ההודעה הקודמת
# - HTML בטוח
# - בלי כפתור חילוץ במסך חיפוש רגיל

AUDIT_SEARCH_MESSAGE_STORE_FILE = "audit_search_messages.json"
AUDIT_SEARCH_STORE_MEMORY_CACHE = None
AUDIT_SEARCH_STORE_SAVE_TASK = None
MAX_TELEGRAM_TEXT = 3600


def audit_logs_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 10 פעולות אחרונות")],
            [KeyboardButton(text="📜 רשימת Audit Logs"), KeyboardButton(text="📥 הורד Audit אחרון")],
            [KeyboardButton(text="👤 חיפוש לפי אדמין")],
            [KeyboardButton(text="🛍️ חיפוש לפי מוצר")],
            [KeyboardButton(text="⚙️ חיפוש לפי פעולה")],
            [KeyboardButton(text="⬅️ חזרה להגדרות מערכת")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def audit_search_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ חזרה ל־Audit Logs")],
            [KeyboardButton(text="⬅️ חזרה להגדרות מערכת")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True,
        input_field_placeholder="הקלד חיפוש או בחר פעולה..."
    )


def _rtl(text, rtl=None):
    return rtl(text) if rtl else text


def _safe(value):
    if value is None:
        return "-"
    return escape(str(value))


def _short_json(value, max_len=220):
    if value in [None, "", {}, []]:
        return "-"

    try:
        text = json.dumps(value, ensure_ascii=False)
    except Exception:
        text = str(value)

    text = text.strip()

    if len(text) > max_len:
        text = text[:max_len] + "..."

    return escape(text)


def _fit(text):
    text = str(text or "")
    if len(text) <= MAX_TELEGRAM_TEXT:
        return text
    return text[:MAX_TELEGRAM_TEXT] + "\n\n<b>…התוצאה קוצרה כדי למנוע שגיאת Telegram.</b>"


def _load_store():
    global AUDIT_SEARCH_STORE_MEMORY_CACHE

    if AUDIT_SEARCH_STORE_MEMORY_CACHE is not None:
        return AUDIT_SEARCH_STORE_MEMORY_CACHE

    try:
        path = Path(AUDIT_SEARCH_MESSAGE_STORE_FILE)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                AUDIT_SEARCH_STORE_MEMORY_CACHE = data if isinstance(data, dict) else {}
                return AUDIT_SEARCH_STORE_MEMORY_CACHE
    except Exception:
        pass

    AUDIT_SEARCH_STORE_MEMORY_CACHE = {}
    return AUDIT_SEARCH_STORE_MEMORY_CACHE


async def _save_store_async(snapshot):
    try:
        await asyncio.sleep(0.25)
        with open(AUDIT_SEARCH_MESSAGE_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot or {}, f, ensure_ascii=False)
    except Exception:
        pass


def _save_store(store):
    global AUDIT_SEARCH_STORE_MEMORY_CACHE, AUDIT_SEARCH_STORE_SAVE_TASK

    try:
        AUDIT_SEARCH_STORE_MEMORY_CACHE = dict(store or {})

        if AUDIT_SEARCH_STORE_SAVE_TASK and not AUDIT_SEARCH_STORE_SAVE_TASK.done():
            AUDIT_SEARCH_STORE_SAVE_TASK.cancel()

        AUDIT_SEARCH_STORE_SAVE_TASK = asyncio.create_task(
            _save_store_async(dict(AUDIT_SEARCH_STORE_MEMORY_CACHE))
        )
    except Exception:
        try:
            with open(AUDIT_SEARCH_MESSAGE_STORE_FILE, "w", encoding="utf-8") as f:
                json.dump(store or {}, f, ensure_ascii=False)
        except Exception:
            pass


def _remember(user_id, message_obj):
    try:
        if not message_obj:
            return
        mid = getattr(message_obj, "message_id", None)
        if not mid:
            return

        store = _load_store()
        key = str(user_id)
        ids = store.get(key, [])
        if not isinstance(ids, list):
            ids = []

        mid = int(mid)
        if mid not in ids:
            ids.append(mid)

        store[key] = ids[-5:]
        _save_store(store)
    except Exception:
        pass


async def _delete_safely(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, int(message_id))
    except Exception:
        pass


async def _cleanup_old(message):
    try:
        user_id = message.from_user.id
        store = _load_store()
        ids = store.pop(str(user_id), [])
        _save_store(store)

        if ids:
            await asyncio.gather(
                *[_delete_safely(message.bot, message.chat.id, mid) for mid in ids[-5:]],
                return_exceptions=True
            )
    except Exception:
        pass


def _read_events(limit_files=20):
    events = []

    try:
        files = list_audit_files(limit_files)
    except Exception:
        return events

    for item in files:
        path = item.get("path")
        if not path:
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = (line or "").strip()
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                    except Exception:
                        continue

                    event["_file"] = item.get("filename") or Path(path).name
                    events.append(event)
        except Exception:
            continue

    return events


def _matches(event, mode, query):
    q = str(query or "").strip().lower()

    if not q:
        return False

    try:
        whole = json.dumps(event, ensure_ascii=False).lower()
    except Exception:
        whole = str(event).lower()

    if mode == "admin":
        return q in str(event.get("admin_id", "")).lower()

    if mode == "product":
        entity_id = str(event.get("entity_id", "")).lower()
        entity_type = str(event.get("entity_type", "")).lower()
        action = str(event.get("action", "")).lower()

        return (
            q in entity_id
            or ("product" in entity_type and q in whole)
            or ("product" in action and q in whole)
        )

    if mode == "action":
        return q in str(event.get("action", "")).lower()

    return q in whole


def _not_found(mode, query):
    q = _safe(query)

    if mode == "admin":
        return (
            "<b>⚠️ לא נמצאו פעולות לאדמין הזה.</b>\n\n"
            f"Admin ID ששלחת: <code>{q}</code>\n\n"
            "בדוק את המספר ונסה שוב."
        )

    if mode == "product":
        return (
            "<b>⚠️ לא נמצא מוצר כזה ב־Audit.</b>\n\n"
            f"השם ששלחת: <code>{q}</code>\n\n"
            "בדוק את שם המוצר ונסה שוב.\n"
            "אפשר לשלוח גם חלק משם המוצר."
        )

    if mode == "action":
        return (
            "<b>⚠️ לא נמצאה פעולה כזאת ב־Audit.</b>\n\n"
            f"הפעולה ששלחת: <code>{q}</code>\n\n"
            "דוגמאות:\n"
            "<code>product_price_changed</code>\n"
            "<code>product_stock_changed</code>\n"
            "<code>order_status_changed</code>"
        )

    return "<b>⚠️ לא נמצאו תוצאות.</b>\n\nנסה שוב עם טקסט אחר."


def format_audit_events(events, title="📊 Audit Logs", limit=10):
    if not events:
        return f"<b>{escape(str(title))}</b>\n\nלא נמצאו פעולות להצגה."

    events = list(events)[-int(limit):]
    events.reverse()

    text = f"<b>{escape(str(title))}</b>\n\n"

    for idx, event in enumerate(events, start=1):
        block = (
            f"<b>{idx}. {_safe(event.get('action'))}</b>\n"
            f"🕒 {_safe(event.get('timestamp'))}\n"
            f"👤 Admin: <code>{_safe(event.get('admin_id'))}</code>\n"
            f"📌 Type: {_safe(event.get('entity_type'))}\n"
            f"🆔 Entity: {_safe(event.get('entity_id'))}\n"
        )

        old_value = _short_json(event.get("old_value"))
        new_value = _short_json(event.get("new_value"))

        if old_value != "-" or new_value != "-":
            block += (
                f"⬅️ Old: <code>{old_value}</code>\n"
                f"➡️ New: <code>{new_value}</code>\n"
            )

        details = str(event.get("details") or "").strip()
        if details:
            block += f"📝 Details: {_safe(details[:160])}\n"

        block += "\n"

        if len(text) + len(block) > MAX_TELEGRAM_TEXT:
            text += "<b>…יש עוד תוצאות. צמצם את החיפוש.</b>"
            break

        text += block

    return _fit(text.strip())



# ================== AUDIT AUTO SELECT LISTS V1 ==================
# רשימות בחירה אוטומטיות מתוך קבצי Audit.
# אם נוסף אדמין / מוצר / פעולה חדשים — הם יופיעו לבד ברשימה.

def _unique_values_from_events(mode, limit=30):
    events = _read_events(20)
    values = []
    seen = set()

    for event in reversed(events):
        value = None

        if mode == "admin":
            value = str(event.get("admin_id") or "").strip()

        elif mode == "product":
            if str(event.get("entity_type") or "").lower() == "product":
                value = str(event.get("entity_id") or "").strip()
            elif "product" in str(event.get("action") or "").lower():
                value = str(event.get("entity_id") or "").strip()

        elif mode == "action":
            value = str(event.get("action") or "").strip()

        if not value or value == "-":
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        values.append(value)

        if len(values) >= int(limit):
            break

    return values


def audit_select_keyboard(mode, limit=25):
    values = _unique_values_from_events(mode, limit=limit)
    keyboard = []

    prefix = {
        "admin": "👤",
        "product": "🛍️",
        "action": "⚙️",
    }.get(mode, "🔎")

    for value in values:
        clean_value = str(value).strip()

        if not clean_value:
            continue

        # Telegram מגביל אורך טקסט בכפתור. שומרים את הערך מספיק קריא.
        display_value = clean_value
        if len(display_value) > 45:
            display_value = display_value[:45] + "..."

        keyboard.append([KeyboardButton(text=f"{prefix} {display_value}")])

    keyboard.append([KeyboardButton(text="✍️ הקלד ידנית")])
    keyboard.append([KeyboardButton(text="⬅️ חזרה ל־Audit Logs")])
    keyboard.append([KeyboardButton(text="⬅️ חזרה להגדרות מערכת")])
    keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="בחר מהרשימה או הקלד ידנית..."
    )


def audit_select_prompt_text(mode):
    values = _unique_values_from_events(mode, limit=25)

    if mode == "admin":
        title = "👤 חיפוש Audit לפי אדמין"
        if values:
            return (
                f"<b>{title}</b>\n\n"
                "בחר Admin ID מהרשימה למטה.\n"
                "אם האדמין לא מופיע — לחץ ✍️ הקלד ידנית."
            )
        return (
            f"<b>{title}</b>\n\n"
            "לא נמצאו עדיין אדמינים ב־Audit.\n"
            "אפשר ללחוץ ✍️ הקלד ידנית."
        )

    if mode == "product":
        title = "🛍️ חיפוש Audit לפי מוצר"
        if values:
            return (
                f"<b>{title}</b>\n\n"
                "בחר מוצר מהרשימה למטה.\n"
                "אם המוצר לא מופיע — לחץ ✍️ הקלד ידנית."
            )
        return (
            f"<b>{title}</b>\n\n"
            "לא נמצאו עדיין מוצרים ב־Audit.\n"
            "אפשר ללחוץ ✍️ הקלד ידנית."
        )

    if mode == "action":
        title = "⚙️ חיפוש Audit לפי פעולה"
        if values:
            return (
                f"<b>{title}</b>\n\n"
                "בחר פעולה מהרשימה למטה.\n"
                "אם הפעולה לא מופיעה — לחץ ✍️ הקלד ידנית."
            )
        return (
            f"<b>{title}</b>\n\n"
            "לא נמצאו עדיין פעולות ב־Audit.\n"
            "אפשר ללחוץ ✍️ הקלד ידנית."
        )

    return "<b>🔎 חיפוש Audit</b>\n\nבחר ערך או הקלד ידנית."


def audit_manual_input_text(mode):
    if mode == "admin":
        return (
            "<b>👤 הקלדה ידנית — אדמין</b>\n\n"
            "שלח Telegram ID של האדמין."
        )

    if mode == "product":
        return (
            "<b>🛍️ הקלדה ידנית — מוצר</b>\n\n"
            "שלח שם מוצר או חלק משם מוצר."
        )

    if mode == "action":
        return (
            "<b>⚙️ הקלדה ידנית — פעולה</b>\n\n"
            "שלח שם פעולה, לדוגמה:\n"
            "<code>product_price_changed</code>\n"
            "<code>product_stock_changed</code>\n"
            "<code>order_status_changed</code>"
        )

    return "<b>🔎 הקלדה ידנית</b>\n\nשלח טקסט לחיפוש."


def parse_audit_selected_value(mode, text):
    value = str(text or "").strip()

    if mode == "admin" and value.startswith("👤 "):
        return value.replace("👤 ", "", 1).strip()

    if mode == "product" and value.startswith("🛍️ "):
        return value.replace("🛍️ ", "", 1).strip()

    if mode == "action" and value.startswith("⚙️ "):
        return value.replace("⚙️ ", "", 1).strip()

    return value


async def send_audit_logs_list(message, rtl=None, parse_mode="HTML"):
    files = list_audit_files(20)

    if not files:
        text = "<b>📜 Audit Logs</b>\n\nאין עדיין קבצי Audit."
    else:
        text = (
            "<b>📜 רשימת Audit Logs</b>\n\n"
            f"{escape(format_audit_files(files))}\n\n"
            "כדי להוריד את הקובץ האחרון לחץ: 📥 הורד Audit אחרון"
        )

    await message.answer(
        _rtl(_fit(text), rtl),
        reply_markup=audit_logs_menu_keyboard(),
        parse_mode=parse_mode
    )


async def send_latest_audit_log(message, rtl=None, parse_mode="HTML"):
    files = list_audit_files(1)

    if not files:
        await message.answer(
            _rtl("<b>⚠️ אין עדיין Audit Logs.</b>", rtl),
            reply_markup=audit_logs_menu_keyboard(),
            parse_mode=parse_mode
        )
        return None

    latest = files[0]
    path = latest.get("path")
    filename = latest.get("filename") or "audit_log.jsonl"

    await message.answer_document(
        FSInputFile(path),
        caption=_rtl(f"<b>📥 Audit Log אחרון</b>\n\n{_safe(filename)}", rtl),
        parse_mode=parse_mode
    )

    return latest


async def send_recent_audit_events(message, rtl=None, parse_mode="HTML", limit=10):
    await _cleanup_old(message)

    events = _read_events(20)
    text = format_audit_events(events, title=f"📊 {limit} פעולות אחרונות", limit=limit)

    sent = await message.answer(
        _rtl(text, rtl),
        reply_markup=audit_logs_menu_keyboard(),
        parse_mode=parse_mode
    )

    _remember(message.from_user.id, sent)
    return len(events)


async def send_audit_search_results(message, mode, query, rtl=None, parse_mode="HTML", limit=10, keep_select_keyboard=True):
    # AUDIT_SELECT_LISTS_STAY_V1
    # אחרי בחירה/חיפוש משאירים את רשימת הבחירה של אותו mode,
    # כדי שאפשר יהיה לעבור מיד למוצר/אדמין/פעולה אחרים בלי לצאת ולחזור.
    await _cleanup_old(message)

    events = _read_events(20)
    filtered = [event for event in events if _matches(event, mode, query)]

    reply_keyboard = (
        audit_select_keyboard(mode)
        if keep_select_keyboard and "audit_select_keyboard" in globals()
        else audit_search_back_keyboard()
    )

    if not filtered:
        sent = await message.answer(
            _rtl(_not_found(mode, query), rtl),
            reply_markup=reply_keyboard,
            parse_mode=parse_mode
        )
        _remember(message.from_user.id, sent)
        return 0

    titles = {
        "admin": f"👤 תוצאות לפי אדמין: {query}",
        "product": f"🛍️ תוצאות לפי מוצר: {query}",
        "action": f"⚙️ תוצאות לפי פעולה: {query}",
    }

    text = format_audit_events(
        filtered,
        title=titles.get(mode, f"🔎 תוצאות חיפוש: {query}"),
        limit=limit
    )

    sent = await message.answer(
        _rtl(text, rtl),
        reply_markup=reply_keyboard,
        parse_mode=parse_mode
    )

    _remember(message.from_user.id, sent)
    return len(filtered)
