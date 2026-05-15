import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, MenuButtonCommands

from config import BOT_TOKEN
from database import create_tables
from admin_handlers import router as admin_router
from shop_handlers import router as shop_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(shop_router)


async def main():
    create_tables()

    # מנקה פקודות ישנות כדי ש-/start לא יופיע בכפתור הכחול.
    await bot.delete_my_commands()

    # בכפתור Menu הרשמי של Telegram תופיע רק פקודת התפריט הראשי.
    await bot.set_my_commands([
        BotCommand(command="menu", description="תפריט ראשי"),
    ])

    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    print("Vendora Shop Running...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
