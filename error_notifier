from html import escape

from config import ADMIN_ID


def short_error_text(error, context=""):
    err_type = type(error).__name__
    err_message = str(error)

    text = (
        "<b>🚨 שגיאת מערכת ב־Vendora</b>\n\n"
        f"<b>Context:</b> {escape(str(context or '-'))}\n"
        f"<b>Type:</b> {escape(err_type)}\n"
        f"<b>Error:</b> {escape(err_message[:1200])}\n\n"
        "הפרטים המלאים נשמרו בקובץ הלוג."
    )

    return text


async def notify_admin_error(bot, error, context=""):
    """
    שולח התראת שגיאה לאדמין בטלגרם.
    לא זורק exception החוצה כדי לא להפיל את הבוט שוב.
    """
    try:
        await bot.send_message(
            ADMIN_ID,
            short_error_text(error, context),
            parse_mode="HTML"
        )
        return True
    except Exception:
        return False
