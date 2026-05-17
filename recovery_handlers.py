import asyncio

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove

from config import ADMIN_ID
from keyboards import main_keyboard, admin_keyboard
from recovery_keyboard import rtl


# GLOBAL_RECOVERY_HANDLERS_V1
# Handlers לכפתורי חילוץ גלובליים.
# לא קשור ל־Audit Search רגיל.
# מופעל רק אם הכפתור הופיע אחרי תקלה.


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
    מחזיר למסך ראשי של הלקוח.
    """
    uid = message.from_user.id

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
        remove_msg = await message.answer(
            rtl("<b>🔄 פותח תפריט מחדש...</b>"),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )

        try:
            asyncio.create_task(
                _delete_message_safely(
                    message.bot,
                    message.chat.id,
                    remove_msg.message_id
                )
            )
        except Exception:
            pass

    except Exception:
        pass

    await message.answer(
        rtl("<b>💎 תפריט ראשי</b>\n\nבחר פעולה:"),
        reply_markup=main_keyboard(uid),
        parse_mode="HTML"
    )


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
