import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonDefault

from config import BOT_TOKEN
from database import create_tables
from admin_handlers import router as admin_router
from shop_handlers import router as shop_router
from auto_backup_scheduler import automatic_backup_loop
from logger import log_info, log_error
from error_notifier import notify_admin_error
from health_monitor import health_monitor_loop
from recovery_handlers import router as recovery_router
from recovery_keyboard import send_recovery_from_update

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# GLOBAL_RECOVERY_HANDLERS_V1
# חשוב שיהיה לפני admin/shop כדי שכפתורי חילוץ ייתפסו תמיד.
dp.include_router(recovery_router)
dp.include_router(admin_router)
dp.include_router(shop_router)


@dp.errors()
async def global_recovery_error_handler(event):
    # GLOBAL_RECOVERY_ERROR_HANDLER_V1
    # במקרה של תקלה לא צפויה — שולח כפתור חילוץ למשתמש,
    # ובמקביל שומר לוג ושולח התראה לאדמין.
    error = getattr(event, "exception", None)
    update = getattr(event, "update", None)

    try:
        if error:
            log_error(error, context="global_update_error")
            await notify_admin_error(bot, error, context="global_update_error")
    except Exception:
        pass

    try:
        if update:
            await send_recovery_from_update(
                bot,
                update,
                text=(
                    "<b>⚠️ אירעה תקלה בפעולה.</b>\n\n"
                    "המערכת לא הצליחה להמשיך מהנקודה הזו.\n"
                    "לחץ 🔄 פתח תפריט מחדש כדי להתחיל מחדש."
                )
            )
    except Exception:
        pass

    return True


async def main():
    try:
        log_info("Vendora startup started", kind="system")

        create_tables()
        log_info("Database tables initialized", kind="system")
        log_info("Performance Safe V1 active", kind="system")

        # STABLE_UI_V2:
        # לא מגדירים פקודות קבועות בכפתור Menu הרשמי של Telegram.
        # כך מצמצמים הופעה של הכפתור הכחול התחתון במכשירים שונים.
        await bot.delete_my_commands()
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())

        asyncio.create_task(automatic_backup_loop())
        log_info("Automatic backup loop started", kind="backup")

        asyncio.create_task(health_monitor_loop())
        log_info("Health monitor loop started", kind="system")

        print("Vendora Shop Running...")
        log_info("Vendora polling started", kind="system")

        await dp.start_polling(bot)

    except Exception as e:
        log_error(e, context="main polling/startup")
        await notify_admin_error(bot, e, context="main polling/startup")
        raise


if __name__ == "__main__":
    asyncio.run(main())
