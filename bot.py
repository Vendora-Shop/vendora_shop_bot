import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonDefault

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

    # STABLE_UI_V2:
    # לא מגדירים פקודות קבועות בכפתור Menu הרשמי של Telegram.
    # כך מצמצמים הופעה של הכפתור הכחול התחתון במכשירים שונים.
    await bot.delete_my_commands()
    await bot.set_chat_menu_button(menu_button=MenuButtonDefault())

    print("Vendora Shop Running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
