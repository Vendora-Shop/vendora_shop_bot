import json
from pathlib import Path

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

from audit_logger import list_audit_files, format_audit_files


# AUDIT_LOGS_UI_V3_ADVANCED
# צפייה, הורדה וחיפוש Audit Logs מתוך פאנל האדמין.


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
        resize_keyboard=True
    )


def _rtl_wrap(text, rtl=None):
    return rtl(text) if rtl else text


def _safe_text(value):
    if value is None:
        return "-"
    return str(value)


def _short_json(value, max_len=350):
    if value in [None, "", {}, []]:
        return "-"

    try:
        text = json.dumps(value, ensure_ascii=False)
    except Exception:
        text = str(value)

    text = text.strip()

    if len(text) > max_len:
        text = text[:max_len] + "..."

    return text


def _read_audit_events(limit_files=10):
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
        entity_type = str(event.get("entity_type", "")).lower()
        entity_id = str(event.get("entity_id", "")).lower()
        action = str(event.get("action", "")).lower()

        # מאפשר גם מוצר לפי entity_type וגם לפי action/entity_id.
        return (
            q in entity_id
            or ("product" in entity_type and q in str(event).lower())
            or ("product" in action and q in str(event).lower())
        )

    if mode == "action":
        return q in str(event.get("action", "")).lower()

    return q in str(event).lower()


def format_audit_events(events, title="📊 Audit Logs", limit=10):
    if not events:
        return (
            f"<b>{title}</b>\n\n"
            "לא נמצאו פעולות להצגה."
        )

    # החדשים בסוף הקובץ, לכן מציגים מהסוף להתחלה.
    events = list(events)[-int(limit):]
    events.reverse()

    text = f"<b>{title}</b>\n\n"

    for idx, event in enumerate(events, start=1):
        text += (
            f"<b>{idx}. { _safe_text(event.get('action')) }</b>\n"
            f"🕒 { _safe_text(event.get('timestamp')) }\n"
            f"👤 Admin: <code>{ _safe_text(event.get('admin_id')) }</code>\n"
            f"📌 Type: { _safe_text(event.get('entity_type')) }\n"
            f"🆔 Entity: { _safe_text(event.get('entity_id')) }\n"
        )

        old_value = _short_json(event.get("old_value"))
        new_value = _short_json(event.get("new_value"))

        if old_value != "-" or new_value != "-":
            text += (
                f"⬅️ Old: <code>{old_value}</code>\n"
                f"➡️ New: <code>{new_value}</code>\n"
            )

        details = str(event.get("details") or "").strip()
        if details:
            text += f"📝 Details: {details[:300]}\n"

        text += "\n"

    return text.strip()


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
        f"{format_audit_files(files)}\n\n"
        "כדי להוריד את הקובץ האחרון לחץ: 📥 הורד Audit אחרון"
    )

    await message.answer(
        _rtl_wrap(text, rtl),
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
        caption=_rtl_wrap(f"<b>📥 Audit Log אחרון</b>\n\n{filename}", rtl),
        parse_mode=parse_mode
    )

    return latest


async def send_recent_audit_events(message, rtl=None, parse_mode="HTML", limit=10):
    events = _read_audit_events(limit_files=10)
    text = format_audit_events(events, title=f"📊 {limit} פעולות אחרונות", limit=limit)

    await message.answer(
        _rtl_wrap(text, rtl),
        reply_markup=audit_logs_menu_keyboard(),
        parse_mode=parse_mode
    )


async def send_audit_search_results(message, mode, query, rtl=None, parse_mode="HTML", limit=10):
    events = _read_audit_events(limit_files=20)
    filtered = [event for event in events if _event_matches(event, mode, query)]

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

    await message.answer(
        _rtl_wrap(text, rtl),
        reply_markup=audit_search_back_keyboard(),
        parse_mode=parse_mode
    )

    return len(filtered)
