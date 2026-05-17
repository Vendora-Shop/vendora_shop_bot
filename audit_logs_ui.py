from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

from audit_logger import list_audit_files, format_audit_files


# AUDIT_LOGS_UI_V2


def audit_logs_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 רשימת Audit Logs")],
            [KeyboardButton(text="📥 הורד Audit אחרון")],
            [KeyboardButton(text="⬅️ חזרה להגדרות מערכת")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


async def send_audit_logs_list(message, rtl=None, parse_mode="HTML"):
    files = list_audit_files(20)

    if not files:
        text = "<b>📜 Audit Logs</b>\n\nאין עדיין קבצי Audit."

        await message.answer(
            rtl(text) if rtl else text,
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
        rtl(text) if rtl else text,
        reply_markup=audit_logs_menu_keyboard(),
        parse_mode=parse_mode
    )


async def send_latest_audit_log(message, rtl=None, parse_mode="HTML"):
    files = list_audit_files(1)

    if not files:
        text = "<b>⚠️ אין עדיין Audit Logs.</b>"

        await message.answer(
            rtl(text) if rtl else text,
            reply_markup=audit_logs_menu_keyboard(),
            parse_mode=parse_mode
        )

        return None

    latest = files[0]

    path = latest.get("path")
    filename = latest.get("filename") or "audit_log.jsonl"

    await message.answer_document(
        FSInputFile(path),
        caption=(
            rtl(f"<b>📥 Audit Log אחרון</b>\n\n{filename}")
            if rtl else
            f"📥 Audit Log אחרון\n\n{filename}"
        ),
        parse_mode=parse_mode
    )

    return latest
