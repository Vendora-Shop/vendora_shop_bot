import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import create_tables

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def main():
    create_tables()
    print("Vendora Shop Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
