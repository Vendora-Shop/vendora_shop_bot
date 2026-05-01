import os
import json
import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID is missing")

ADMIN_ID = int(ADMIN_ID_RAW)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users = {}


def load_products():
    with open("products.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_active_products():
    products = load_products()
    active = {}

    for category, items in products.items():
        active_items = [item for item in items if item.get("active", True)]
        if active_items:
            active[category] = active_items

    return active


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 חנות")],
            [KeyboardButton(text="📞 שירות לקוחות")]
        ],
        resize_keyboard=True
    )


def categories_keyboard():
    products = get_active_products()
    keyboard = [[KeyboardButton(text=category)] for category in products.keys()]
    keyboard.append([KeyboardButton(text="🛒 הסל שלי")])
    keyboard.append([KeyboardButton(text="⬅️ חזרה")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def products_keyboard(category):
    products = get_active_products()
    keyboard = []

    for product in products.get(category, []):
        keyboard.append([KeyboardButton(text=product["name"])])

    keyboard.append([KeyboardButton(text="🛒 הסל שלי")])
    keyboard.append([KeyboardButton(text="⬅️ חזרה לקטגוריות")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def cart_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ הוסף עוד מוצר")],
            [KeyboardButton(text="✅ המשך להזמנה")],
            [KeyboardButton(text="❌ בטל הזמנה")]
        ],
        resize_keyboard=True
    )


def find_product(product_name):
    products = get_active_products()

    for category, items in products.items():
        for item in items:
            if item["name"] == product_name:
                return item, category

    return None, None


def calc_cart_total(cart):
    return sum(item["price"] * item["qty"] for item in cart)


def cart_text(cart):
    if not cart:
        return "🛒 הסל שלך ריק."

    text = "🛒 הסל שלך:\n\n"

    for item in cart:
        line_total = item["price"] * item["qty"]
        text += f"• {item['name']} × {item['qty']} = ₪{line_total}\n"

    text += f"\n💰 סה״כ: ₪{calc_cart_total(cart)}"
    return text


def clean_phone(phone):
    phone = phone.strip()
    phone = phone.replace(" ", "").replace("-", "")
    phone = phone.replace("+972", "0")
    return phone


def is_valid_phone(phone):
    phone = clean_phone(phone)
    return phone.isdigit() and phone.startswith("05") and len(phone) == 10


def has_digit(text):
    return any(ch.isdigit() for ch in text)


@dp.message(CommandStart())
async def start(message: Message):
    users.pop(message.from_user.id, None)

    await message.answer(
        "🔥 ברוך הבא ל-Vendora Shop\n"
        "חנות לציוד הובלות, שילוח ושליחים.",
        reply_markup=main_keyboard()
    )


@dp.message(F.text == "🛒 חנות")
async def shop(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})

    await message.answer("בחר קטגוריה:", reply_markup=categories_keyboard())


@dp.message(F.text == "⬅️ חזרה")
async def back_main(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("חזרת לתפריט הראשי.", reply_markup=main_keyboard())


@dp.message(F.text == "⬅️ חזרה לקטגוריות")
async def back_categories(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})
    users[uid]["step"] = None
    await message.answer("בחר קטגוריה:", reply_markup=categories_keyboard())


@dp.message(F.text == "➕ הוסף עוד מוצר")
async def add_more(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})
    users[uid]["step"] = None
    await message.answer("בחר קטגוריה:", reply_markup=categories_keyboard())


@dp.message(F.text == "🛒 הסל שלי")
async def show_cart(message: Message):
    uid = message.from_user.id
    data = users.setdefault(uid, {"cart": [], "step": None})

    await message.answer(cart_text(data["cart"]), reply_markup=cart_keyboard())


@dp.message(F.text == "❌ בטל הזמנה")
async def cancel_order(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("ההזמנה בוטלה.", reply_markup=main_keyboard())


@dp.message(F.text == "📞 שירות לקוחות")
async def support(message: Message):
    uid = message.from_user.id
    users[uid] = {"cart": [], "step": "support"}
    await message.answer("כתוב כאן את ההודעה שלך ונעביר אותה לנציג.")


@dp.message(F.text == "✅ המשך להזמנה")
async def checkout(message: Message):
    uid = message.from_user.id
    data = users.get(uid)

    if not data or not data.get("cart"):
        await message.answer("הסל שלך ריק. קודם בחר מוצר.")
        return

    data["step"] = "name"
    await message.answer("מה השם המלא שלך?")
    return


@dp.message()
async def handle_message(message: Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()

    active_products = get_active_products()

    if txt in active_products.keys():
        users.setdefault(uid, {"cart": [], "step": None})
        users[uid]["category"] = txt
        users[uid]["step"] = None

        await message.answer(
            f"בחר מוצר מתוך {txt}:",
            reply_markup=products_keyboard(txt)
        )
        return

    product, category = find_product(txt)

    if product:
        users.setdefault(uid, {"cart": [], "step": None})
        users[uid]["selected_product"] = product
        users[uid]["step"] = "qty"

        description = product.get("description", "")
        max_qty = int(product.get("max_qty", 100))

        await message.answer(
            f"בחרת: {product['name']}\n"
            f"{description}\n\n"
            f"מחיר ליחידה: ₪{product['price']}\n"
            f"כמות מקסימלית להזמנה: {max_qty}\n\n"
            f"כמה יחידות תרצה?"
        )
        return

    data = users.get(uid)

    if not data:
        await message.answer("בחר פעולה מהתפריט.", reply_markup=main_keyboard())
        return

    if data.get("step") == "support":
        if len(txt) < 2:
            await message.answer("נא לרשום הודעה לנציג.")
            return

        await bot.send_message(
            ADMIN_ID,
            f"📩 פנייה חדשה לשירות לקוחות\n\n"
            f"👤 שם בטלגרם: {message.from_user.full_name}\n"
            f"🆔 Telegram ID: {uid}\n"
            f"💬 הודעה: {txt}"
        )

        users.pop(uid, None)
        await message.answer(
            "✅ קיבלנו את הפנייה שלך. נחזור אליך בהקדם.",
            reply_markup=main_keyboard()
        )
        return

    if data.get("step") == "qty":
        if not txt.isdigit():
            await message.answer("נא לרשום כמות במספרים בלבד. לדוגמה: 2")
            return

        qty = int(txt)
        product = data.get("selected_product")

        if not product:
            data["step"] = None
            await message.answer("אירעה תקלה בבחירת המוצר. בחר מוצר מחדש.", reply_markup=categories_keyboard())
            return

        max_qty = int(product.get("max_qty", 100))

        if qty <= 0:
            await message.answer("הכמות חייבת להיות גדולה מ־0.")
            return

        if qty > max_qty:
            await message.answer(f"ניתן להזמין עד {max_qty} יחידות מהמוצר הזה.")
            return

        data["cart"].append({
            "name": product["name"],
            "price": product["price"],
            "qty": qty
        })

        data["step"] = None
        data.pop("selected_product", None)

        await message.answer(
            f"✅ נוסף לסל:\n"
            f"{product['name']} × {qty} = ₪{product['price'] * qty}\n\n"
            f"{cart_text(data['cart'])}",
            reply_markup=cart_keyboard()
        )
        return

    if data.get("step") == "name":
        if len(txt) < 2:
            await message.answer("נא לרשום שם מלא תקין.")
            return

        data["name"] = txt
        data["step"] = "phone"
        await message.answer("מה מספר הפלאפון שלך? לדוגמה: 0547937503")
        return

    if data.get("step") == "phone":
        phone = clean_phone(txt)

        if not is_valid_phone(phone):
            await message.answer("נא לרשום מספר פלאפון ישראלי תקין. לדוגמה: 0547937503")
            return

        data["phone"] = phone
        data["step"] = "city"
        await message.answer("באיזו עיר המשלוח? לדוגמה: אשדוד")
        return

    if data.get("step") == "city":
        if len(txt) < 2 or has_digit(txt):
            await message.answer("נא לרשום עיר תקינה. לדוגמה: אשדוד")
            return

        data["city"] = txt
        data["step"] = "street"
        await message.answer("רחוב ומספר בית? לדוגמה: שדרות הרצל 18")
        return

    if data.get("step") == "street":
        if len(txt) < 5 or not has_digit(txt):
            await message.answer("נא לרשום רחוב + מספר בית. לדוגמה: שדרות הרצל 18")
            return

        data["street"] = txt
        data["step"] = "floor"
        await message.answer("איזו קומה? אם זה קרקע תרשום 0")
        return

    if data.get("step") == "floor":
        if not txt.lstrip("-").isdigit():
            await message.answer("נא לרשום קומה במספרים בלבד. לדוגמה: 3 או 0 לקרקע")
            return

        data["floor"] = txt
        data["step"] = "apartment"
        await message.answer("מספר דירה? אם אין דירה תרשום 0")
        return

    if data.get("step") == "apartment":
        if not txt.isdigit():
            await message.answer("נא לרשום מספר דירה במספרים בלבד. אם אין דירה תרשום 0")
            return

        data["apartment"] = txt

        full_address = (
            f"{data['city']}, {data['street']}, "
            f"קומה {data['floor']}, דירה {data['apartment']}"
        )

        order = "📦 הזמנה חדשה מ-Vendora Shop\n\n"
        order += f"👤 שם: {data['name']}\n"
        order += f"📞 טלפון: {data['phone']}\n"
        order += f"🏙 עיר: {data['city']}\n"
        order += f"🏠 רחוב ובית: {data['street']}\n"
        order += f"⬆️ קומה: {data['floor']}\n"
        order += f"🚪 דירה: {data['apartment']}\n"
        order += f"📍 כתובת מלאה: {full_address}\n\n"
        order += cart_text(data["cart"])
        order += f"\n\n🆔 Telegram ID: {uid}"
        order += f"\n👤 Telegram: {message.from_user.full_name}"

        await bot.send_message(ADMIN_ID, order)

        users.pop(uid, None)

        await message.answer(
            "✅ ההזמנה התקבלה!\nנחזור אליך לאישור משלוח.",
            reply_markup=main_keyboard()
        )
        return

    await message.answer("בחר פעולה מהתפריט.", reply_markup=main_keyboard())


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
