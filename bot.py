import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 מוצרים")],
            [KeyboardButton(text="📞 שירות לקוחות")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "ברוך הבא ל-Vendora Shop 🔥\nחנות ציוד הובלות ושילוח",
        reply_markup=keyboard
    )


@dp.message()
async def messages(message: Message):
    if message.text == "📦 מוצרים":
        await message.answer(
            "המוצרים שלנו:\n\n"
            "📦 קרטונים\n"
            "🧻 ניילון פצפצים\n"
            "📍 סרט הדבקה\n"
            "🚚 חבילת מעבר דירה"
        )

    elif message.text == "📞 שירות לקוחות":
        await message.answer("כתוב לנו כאן ונחזור אליך.")

    else:
        await bot.send_message(
            ADMIN_ID,
            f"📩 הודעה חדשה:\n\n"
            f"👤 {message.from_user.full_name}\n"
            f"💬 {message.text}"
        )
        await message.answer("✅ קיבלנו את פנייתך.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
