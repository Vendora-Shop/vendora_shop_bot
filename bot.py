import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import create_tables
from shop_handlers import router as shop_router
from admin_handlers import router as admin_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# חשוב מאוד: קודם החנות, אחרי זה האדמין
dp.include_router(shop_router)
dp.include_router(admin_router)


async def main():
    create_tables()
    print("Vendora Shop Running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
