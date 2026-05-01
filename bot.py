import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in Railway Variables")

if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID is missing in Railway Variables")

ADMIN_ID = int(ADMIN_ID_RAW)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users = {}

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 מוצרים")],
        [KeyboardButton(text="📞 שירות לקוחות")]
    ],
    resize_keyboard=True
)

products_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 קרטונים")],
        [KeyboardButton(text="🧻 ניילון פצפצים")],
        [KeyboardButton(text="📍 סרט הדבקה")],
        [KeyboardButton(text="🚚 חבילת מעבר דירה")],
        [KeyboardButton(text="⬅️ חזרה")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer(
        "🔥 ברוך הבא ל-Vendora Shop\nחנות ציוד הובלות ושילוח",
        reply_markup=main_kb
    )

@dp.message(F.text == "⬅️ חזרה")
async def back(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("חזרת לתפריט הראשי.", reply_markup=main_kb)

@dp.message(F.text == "📦 מוצרים")
async def products(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("בחר מוצר:", reply_markup=products_kb)

@dp.message(F.text.in_(["📦 קרטונים", "🧻 ניילון פצפצים", "📍 סרט הדבקה", "🚚 חבילת מעבר דירה"]))
async def choose_product(message: Message):
    users[message.from_user.id] = {
        "step": "qty",
        "product": message.text
    }
    await message.answer("כמה יחידות תרצה?")

@dp.message(F.text == "📞 שירות לקוחות")
async def support(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("כתוב כאן את ההודעה שלך ונעביר אותה לנציג.")

@dp.message()
async def flow(message: Message):
    uid = message.from_user.id
    text = message.text or ""

    if uid not in users:
        await bot.send_message(
            ADMIN_ID,
            f"📩 פנייה חדשה מהבוט\n\n"
            f"👤 שם בטלגרם: {message.from_user.full_name}\n"
            f"🆔 Telegram ID: {uid}\n"
            f"💬 הודעה: {text}"
        )
        await message.answer("✅ קיבלנו את הפנייה שלך. נחזור אליך בהקדם.")
        return

    data = users[uid]

    if data["step"] == "qty":
        if not text.isdigit():
            await message.answer("נא לרשום כמות במספרים בלבד. לדוגמה: 10")
            return
        data["qty"] = int(text)
        data["step"] = "name"
        await message.answer("מה השם שלך?")
        return

    if data["step"] == "name":
        data["name"] = text
        data["step"] = "phone"
        await message.answer("מה מספר הטלפון שלך?")
        return

    if data["step"] == "phone":
        data["phone"] = text
        data["step"] = "address"
        await message.answer("מה כתובת המשלוח?")
        return

    if data["step"] == "address":
        data["address"] = text

        order_text = f"""📦 הזמנה חדשה מ-Vendora Shop

👤 שם: {data['name']}
📞 טלפון: {data['phone']}
📍 כתובת: {data['address']}

🛒 מוצר: {data['product']}
🔢 כמות: {data['qty']}

🆔 Telegram ID: {uid}
👤 Telegram: {message.from_user.full_name}
"""

        await bot.send_message(ADMIN_ID, order_text)
        await message.answer("✅ ההזמנה התקבלה! נחזור אליך לאישור משלוח.", reply_markup=main_kb)
        users.pop(uid, None)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
