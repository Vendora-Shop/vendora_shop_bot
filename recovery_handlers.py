import asyncio

from aiogram import Router, F
from aiogram.types import Message

from config import ADMIN_ID
from keyboards import admin_keyboard
from recovery_keyboard import rtl


# GLOBAL_RECOVERY_HANDLERS_V2_OFFICIAL_MENU_FIX
# כפתורי חילוץ גלובליים.
# חשוב:
# לא שולחים תפריט טקסט פשוט.
# כפתור "פתח תפריט מחדש" מפעיל את מסך הבית הרשמי של shop_handlers,
# עם הבאנר, הניקוי והעיצוב הקיים של Vendora.


router = Router()


async def _delete_message_safely(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, int(message_id))
    except Exception:
        pass


@router.message(F.text == "🔄 פתח תפריט מחדש")
async def recovery_open_main_menu(message: Message):
    """
    כפתור חילוץ ללקוח/אדמין:
    מחזיר למסך הראשי הרשמי של החנות.
    """
    try:
        asyncio.create_task(
            _delete_message_safely(
                message.bot,
                message.chat.id,
                message.message_id
            )
        )
    except Exception:
        pass

    try:
        # import מאוחר כדי למנוע circular import בזמן עליית הבוט.
        from shop_handlers import reset_customer_to_main_menu

        await reset_customer_to_main_menu(message)
        return

    except Exception as e:
        # fallback אחרון בלבד אם מסך הבית הרשמי נכשל.
        # גם כאן לא משתמשים בתפריט הישן/הגדול.
        try:
            await message.answer(
                rtl(
                    "<b>⚠️ לא הצלחתי לפתוח את התפריט הראשי.</b>\n\n"
                    "נסה לשלוח /start פעם אחת."
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.message(F.text == "🛡️ פאנל ניהול")
async def recovery_open_admin_panel(message: Message):
    """
    כפתור חילוץ לאדמין:
    מחזיר לפאנל ניהול.
    """
    if int(message.from_user.id) != int(ADMIN_ID):
        return

    try:
        asyncio.create_task(
            _delete_message_safely(
                message.bot,
                message.chat.id,
                message.message_id
            )
        )
    except Exception:
        pass

    try:
        from admin_handlers import admin_states
        admin_states[message.from_user.id] = {"step": "admin"}
    except Exception:
        pass

    await message.answer(
        rtl("<b>🔐 פאנל ניהול Vendora</b>\n\nבחר פעולה מהתפריט למטה."),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )
