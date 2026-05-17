import json
import asyncio
from pathlib import Path
from html import escape

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

from audit_logger import list_audit_files, format_audit_files


# AUDIT_LOGS_UI_V5_FINAL
# Audit Logs מתקדם עם חיפוש יציב:
# - חיפוש לפי אדמין
# - חיפוש לפי מוצר
# - חיפוש לפי פעולה
# - אם אין תוצאות: הערה נקייה אחת, והקודמת נמחקת
# - בלי כפתור חילוץ במסך חיפוש רגיל
# - הגנה מאורך הודעה ו-HTML לא תקין


AUDIT_SEARCH_MESSAGE_STORE_FILE = "audit_search_messages.json"
MAX_TELEGRAM_TEXT = 3800


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


def _rtl_wrap(text, rtl=None):
    return rtl(text) if rtl else text


def _safe_text(value):
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


def _load_search_store():
    try:
        path = Path(AUDIT_SEARCH_MESSAGE_STORE_FILE)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _save_search_store(store):
    try:
        with open(AUDIT_SEARCH_MESSAGE_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(store or {}, f, ensure_ascii=False)
    except Exception:
        pass


def _remember_search_message(user_id, message_obj):
    try:
        if not message_obj:
            return
        mid = getattr(message_obj, "message_id", None)
        if not mid:
            return

        store = _load_search_store()
        key = str(user_id)
        ids = store.get(key, [])
        if not isinstance(ids, list):
            ids = []

        mid = int(mid)
        if mid not in ids:
            ids.append(mid)

        store[key] = ids[-5:]
        _save_search_store(store)
    except Exception:
        pass


async def _delete_message_safely(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, int(message_id))
    except Exception:
        pass


async def _cleanup_previous_search_messages(message):
    try:
        user_id = message.from_user.id
        store = _load_search_store()
        ids = store.pop(str(user_id), [])
        _save_search_store(store)

        if not ids:
            return

        await asyncio.gather(
            *[_delete_message_safely(message.bot, message.chat.id, mid) for mid in ids[-5:]],
            return_exceptions=True
        )
    except Exception:
        pass


def _read_audit_events(limit_files=20):
    events = []
    files = list_audit_files(limit_files)

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


def _event_matches(event, mode, query):
    q = str(query or "").strip().lower()

    if not q:
        return False

    if mode == "admin":
        return q in str(event.get("admin_id", "")).lower()

    if mode == "product":
        entity_id = str(event.get("entity_id", "")).lower()
        entity_type = str(event.get("entity_type", "")).lower()
        action = str(event.get("action", "")).lower()
        whole = json.dumps(event, ensure_ascii=False).lower()

        return (
            q in entity_id
            or ("product" in entity_type and q in whole)
            or ("product" in action and q in whole)
        )

    if mode == "action":
        return q in str(event.get("action", "")).lower()

    return q in json.dumps(event, ensure_ascii=False).lower()


def _not_found_text(mode, query):
    q = _safe_text(query)

    if mode == "product":
        return (
            "<b>⚠️ לא נמצא מוצר כזה ב־Audit.</b>\n\n"
            f"השם ששלחת: <code>{q}</code>\n\n"
            "בדוק את שם המוצר ונסה שוב.\n"
            "אפשר לשלוח גם חלק משם המוצר."
        )

    if mode == "admin":
        return (
            "<b>⚠️ לא נמצאו פעולות לאדמין הזה.</b>\n\n"
            f"Admin ID ששלחת: <code>{q}</code>\n\n"
            "בדוק את המספר ונסה שוב."
        )

    if mode == "action":
        return (
            "<b>⚠️ לא נמצאה פעולה כזאת ב־Audit.</b>\n\n"
            f"הפעולה ששלחת: <code>{q}</code>\n\n"
            "לדוגמה:\n"
            "<code>product_price_changed</code>\n"
            "<code>product_stock_changed</code>\n"
            "<code>order_status_changed</code>"
        )

    return "<b>⚠️ לא נמצאו תוצאות.</b>\n\nנסה שוב עם טקסט אחר."


def _fit_text(text):
    text = str(text or "")
    if len(text) <= MAX_TELEGRAM_TEXT:
        return text
    return text[:MAX_TELEGRAM_TEXT] + "\n\n<b>…התוצאה קוצרה כדי למנוע שגיאת Telegram.</b>"


def format_audit_events(events, title="📊 Audit Logs", limit=10):
    if not events:
        return f"<b>{escape(title)}</b>\n\nלא נמצאו פעולות להצגה."

    events = list(events)[-int(limit):]
    events.reverse()

    text = f"<b>{escape(title)}</b>\n\n"

    for idx, event in enumerate(events, start=1):
        block = (
            f"<b>{idx}. {_safe_text(event.get('action'))}</b>\n"
            f"🕒 {_safe_text(event.get('timestamp'))}\n"
            f"👤 Admin: <code>{_safe_text(event.get('admin_id'))}</code>\n"
            f"📌 Type: {_safe_text(event.get('entity_type'))}\n"
            f"🆔 Entity: {_safe_text(event.get('entity_id'))}\n"
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
            block += f"📝 Details: {_safe_text(details[:180])}\n"

        block += "\n"

        if len(text) + len(block) > MAX_TELEGRAM_TEXT:
            text += "<b>…יש עוד תוצאות. צמצם את החיפוש כדי לראות יותר.</b>"
            break

        text += block

    return _fit_text(text.strip())


async def send_audit_logs_list(message, rtl=None, parse_mode="HTML"):
    files = list_audit_files(20)

    if not files:
        text = "<b>📜 Audit Logs</b>\n\nאין עדיין קבצי Audit."
        await message.answer(
            _rtl_wrap(text, rtl),
            reply_markup=audit_logs_menu_keyboard(),
            parse_mode=parse_mode
        )
        return

    text = (
        "<b>📜 רשימת Audit Logs</b>\n\n"
        f"{escape(format_audit_files(files))}\n\n"
        "כדי להוריד את הקובץ האחרון לחץ: 📥 הורד Audit אחרון"
    )

    await message.answer(
        _rtl_wrap(_fit_text(text), rtl),
        reply_markup=audit_logs_menu_keyboard(),
        parse_mode=parse_mode
    )


async def send_latest_audit_log(message, rtl=None, parse_mode="HTML"):
    files = list_audit_files(1)

    if not files:
        text = "<b>⚠️ אין עדיין Audit Logs.</b>"

        await message.answer(
            _rtl_wrap(text, rtl),
            reply_markup=audit_logs_menu_keyboard(),
            parse_mode=parse_mode
        )

        return None

    latest = files[0]
    path = latest.get("path")
    filename = latest.get("filename") or "audit_log.jsonl"

    await message.answer_document(
        FSInputFile(path),
        caption=_rtl_wrap(f"<b>📥 Audit Log אחרון</b>\n\n{_safe_text(filename)}", rtl),
        parse_mode=parse_mode
    )

    return latest


async def send_recent_audit_events(message, rtl=None, parse_mode="HTML", limit=10):
    await _cleanup_previous_search_messages(message)

    events = _read_audit_events(limit_files=20)
    text = format_audit_events(events, title=f"📊 {limit} פעולות אחרונות", limit=limit)

    sent = await message.answer(
        _rtl_wrap(text, rtl),
        reply_markup=audit_logs_menu_keyboard(),
        parse_mode=parse_mode
    )

    _remember_search_message(message.from_user.id, sent)
    return len(events)


async def send_audit_search_results(message, mode, query, rtl=None, parse_mode="HTML", limit=10):
    await _cleanup_previous_search_messages(message)

    events = _read_audit_events(limit_files=20)
    filtered = [event for event in events if _event_matches(event, mode, query)]

    if not filtered:
        sent = await message.answer(
            _rtl_wrap(_not_found_text(mode, query), rtl),
            reply_markup=audit_search_back_keyboard(),
            parse_mode=parse_mode
        )
        _remember_search_message(message.from_user.id, sent)
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
        _rtl_wrap(text, rtl),
        reply_markup=audit_search_back_keyboard(),
        parse_mode=parse_mode
    )

    _remember_search_message(message.from_user.id, sent)
    return len(filtered)
