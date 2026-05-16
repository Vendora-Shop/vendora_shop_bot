import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonDefault

from config import BOT_TOKEN
from database import create_tables
from admin_handlers import router as admin_router
from shop_handlers import router as shop_router
from auto_backup_scheduler import automatic_backup_loop
from logger import log_info, log_error

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(shop_router)


async def main():
    try:
        log_info("Vendora startup started", kind="system")

        create_tables()
        log_info("Database tables initialized", kind="system")

        # STABLE_UI_V2:
        # לא מגדירים פקודות קבועות בכפתור Menu הרשמי של Telegram.
        # כך מצמצמים הופעה של הכפתור הכחול התחתון במכשירים שונים.
        await bot.delete_my_commands()
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())

        asyncio.create_task(automatic_backup_loop())
        log_info("Automatic backup loop started", kind="backup")

        print("Vendora Shop Running...")
        log_info("Vendora polling started", kind="system")

        await dp.start_polling(bot)

    except Exception as e:
        log_error(e, context="main polling/startup")
        raise


if __name__ == "__main__":
    asyncio.run(main())
