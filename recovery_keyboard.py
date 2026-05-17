from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from config import ADMIN_ID


# GLOBAL_RECOVERY_KEYBOARD_V1
# כפתור חילוץ גלובלי למצבי תקלה בלבד.
# לא מוצג במסכים רגילים.


RTL = "\u200F"


def rtl(text):
    return RTL + str(text)


def recovery_keyboard(user_id=None):
    rows = [
        [KeyboardButton(text="🔄 פתח תפריט מחדש")]
    ]

    try:
        if int(user_id) == int(ADMIN_ID):
            rows.append([KeyboardButton(text="🛡️ פאנל ניהול")])
    except Exception:
        pass

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="בחר פעולה..."
    )


async def send_recovery_message(bot, chat_id, user_id=None, text=None):
    """
    שולח הודעת חילוץ במקרה של תקלה אמיתית.
    """
    try:
        await bot.send_message(
            chat_id,
            rtl(
                text or
                "<b>⚠️ הפעולה נתקעה או לא הושלמה.</b>\n\n"
                "לחץ 🔄 פתח תפריט מחדש כדי להתחיל מחדש."
            ),
            reply_markup=recovery_keyboard(user_id),
            parse_mode="HTML"
        )
        return True
    except Exception:
        return False


async def send_recovery_from_update(bot, update, text=None):
    """
    מנסה למצוא chat/user מתוך update של aiogram ולשלוח כפתור חילוץ.
    מתאים ל־Global error handler.
    """
    try:
        message = getattr(update, "message", None)
        callback_query = getattr(update, "callback_query", None)

        if message:
            chat_id = message.chat.id
            user_id = message.from_user.id if message.from_user else None
            return await send_recovery_message(bot, chat_id, user_id, text=text)

        if callback_query and callback_query.message:
            chat_id = callback_query.message.chat.id
            user_id = callback_query.from_user.id if callback_query.from_user else None

            try:
                await callback_query.answer("אירעה תקלה. נשלח כפתור חילוץ.", show_alert=True)
            except Exception:
                pass

            return await send_recovery_message(bot, chat_id, user_id, text=text)

    except Exception:
        pass

    return False
