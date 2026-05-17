from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from audit_logger import list_audit_files, format_audit_files

# AUDIT_LOGS_UI_V1

def audit_logs_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 רשימת Audit Logs")],
            [KeyboardButton(text="📥 הורד Audit אחרון")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


async def send_audit_logs_list(message):
    files = list_audit_files(20)

    if not files:
        await message.answer(
            "אין עדיין קבצי Audit."
        )
        return

    await message.answer(
        format_audit_files(files)
    )
