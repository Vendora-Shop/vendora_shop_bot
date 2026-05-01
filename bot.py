import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users = {}

prices = {
    "📦 קרטונים": 8,
    "🧻 ניילון פצפצים": 25,
    "📍 סרט הדבקה": 6,
    "🚚 חבילת מעבר דירה": 199
}

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

confirm_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ אשר הזמנה")],
        [KeyboardButton(text="❌ בטל")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("🔥 ברוך הבא ל-Vendora PRO", reply_markup=main_kb)

@dp.message(F.text == "📦 מוצרים")
async def products(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("בחר מוצר:", reply_markup=products_kb)

@dp.message(F.text == "⬅️ חזרה")
async def back(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("חזרת לתפריט הראשי", reply_markup=main_kb)

@dp.message(F.text.in_(prices.keys()))
async def choose_product(message: Message):
    users[message.from_user.id] = {
        "step": "qty",
        "product": message.text
    }
    await message.answer("כמה יחידות תרצה?")

@dp.message(F.text == "📞 שירות לקוחות")
async def support(message: Message):
    await message.answer("כתוב כאן הודעה ונחזור אליך.")

@dp.message(F.text == "❌ בטל")
async def cancel(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("ההזמנה בוטלה.", reply_markup=main_kb)

@dp.message(F.text == "✅ אשר הזמנה")
async def approve(message: Message):
    uid = message.from_user.id
    if uid not in users:
        return

    data = users[uid]
    data["step"] = "name"
    await message.answer("מה השם שלך?")

@dp.message()
async def flow(message: Message):
    uid = message.from_user.id
    txt = message.text

    if uid not in users:
        return

    data = users[uid]

    if data["step"] == "qty":
        if not txt.isdigit():
            await message.answer("רשום מספר בלבד.")
            return

        qty = int(txt)
        product = data["product"]
        total = qty * prices[product]

        data["qty"] = qty
        data["total"] = total
        data["step"] = "confirm"

        await message.answer(
            f"{product}\nכמות: {qty}\n\n💰 סה״כ: ₪{total}\n\nלאשר הזמנה?",
            reply_markup=confirm_kb
        )
        return

    if data["step"] == "name":
        data["name"] = txt
        data["step"] = "phone"
        await message.answer("מספר טלפון?")
        return

    if data["step"] == "phone":
        data["phone"] = txt
        data["step"] = "address"
        await message.answer("כתובת משלוח?")
        return

    if data["step"] == "address":
        data["address"] = txt

        text = f"""📦 הזמנה חדשה

👤 שם: {data['name']}
📞 טלפון: {data['phone']}
📍 כתובת: {data['address']}

🛒 מוצר: {data['product']}
🔢 כמות: {data['qty']}
💰 סה״כ: ₪{data['total']}
"""

        await bot.send_message(ADMIN_ID, text)
        await message.answer("✅ ההזמנה התקבלה!", reply_markup=main_kb)
        users.pop(uid)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
