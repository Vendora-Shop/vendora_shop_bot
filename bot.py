import os
import json
import math
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from database import (
    create_tables,
    add_product,
    get_active_products,
    get_all_products,
    set_product_price,
    set_product_active,
    delete_product
)

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

create_tables()


def is_admin_id(user_id):
    return user_id == ADMIN_ID


def load_json(filename, default=None):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def load_locations():
    return load_json("settlements_locations.json", {})


def load_central_zones():
    return load_json("central_delivery_zones.json", {})


def load_manual_prices():
    return load_json("manual_delivery_prices.json", {})


def distance_km(lat1, lng1, lat2, lng2):
    r = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )

    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_delivery_price(city):
    locations = load_locations()
    central_zones = load_central_zones()
    manual_prices = load_manual_prices()

    if city not in locations:
        return None, None, "city_not_found"

    if city in manual_prices:
        return float(manual_prices[city]), "מחיר ידני", "ok"

    city_location = locations[city]
    best = None

    for central_city, zone in central_zones.items():
        if central_city not in locations:
            continue

        central_location = locations[central_city]

        dist = distance_km(
            city_location["lat"],
            city_location["lng"],
            central_location["lat"],
            central_location["lng"]
        )

        radius = float(zone.get("radius_km", 0))

        if dist <= radius:
            if best is None or dist < best["distance"]:
                best = {
                    "price": float(zone["price"]),
                    "base_city": central_city,
                    "distance": round(dist, 1)
                }

    if best:
        return best["price"], best["base_city"], "ok"

    return None, None, "no_delivery_price"


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
    keyboard = [[KeyboardButton(text=cat)] for cat in products.keys()]
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


def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 רשימת מוצרים", callback_data="admin_products")],
            [InlineKeyboardButton(text="➕ הוסף מוצר", callback_data="admin_add_product_help")],
            [InlineKeyboardButton(text="✏️ שנה מחיר", callback_data="admin_set_price_help")],
            [InlineKeyboardButton(text="🔴 כבה מוצר", callback_data="admin_off_help")],
            [InlineKeyboardButton(text="🟢 הפעל מוצר", callback_data="admin_on_help")],
            [InlineKeyboardButton(text="🗑️ מחק מוצר", callback_data="admin_delete_help")]
        ]
    )


def find_product(name):
    products = get_active_products()

    for category, items in products.items():
        for item in items:
            if item["name"] == name:
                return item

    return None


def cart_total(cart):
    return sum(float(item["price"]) * int(item["qty"]) for item in cart)


def cart_text(cart):
    if not cart:
        return "🛒 הסל שלך ריק."

    text = "🛒 הסל שלך:\n\n"

    for item in cart:
        line_total = float(item["price"]) * int(item["qty"])
        text += f"• {item['name']} × {item['qty']} = ₪{line_total:g}\n"

    text += f"\n💰 סה״כ מוצרים: ₪{cart_total(cart):g}"
    return text


def clean_phone(phone):
    return phone.strip().replace(" ", "").replace("-", "").replace("+972", "0")


def valid_phone(phone):
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


@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin_id(message.from_user.id):
        return

    await message.answer(
        "🔐 לוח ניהול Vendora Shop\nבחר פעולה:",
        reply_markup=admin_keyboard()
    )


@dp.callback_query(F.data == "admin_products")
async def admin_products_button(callback: CallbackQuery):
    if not is_admin_id(callback.from_user.id):
        return

    rows = get_all_products()

    if not rows:
        await callback.message.answer("אין מוצרים במערכת.")
        await callback.answer()
        return

    text = "📦 רשימת מוצרים:\n\n"

    for row in rows:
        product_id, category, name, price, description, max_qty, active = row
        status = "✅ פעיל" if active else "❌ כבוי"
        text += (
            f"{status}\n"
            f"קטגוריה: {category}\n"
            f"מוצר: {name}\n"
            f"מחיר: ₪{price:g}\n"
            f"מקסימום להזמנה: {max_qty}\n\n"
        )

    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "admin_add_product_help")
async def admin_add_product_help(callback: CallbackQuery):
    if not is_admin_id(callback.from_user.id):
        return

    await callback.message.answer(
        "➕ להוספת מוצר תשלח:\n\n"
        "/add_product קטגוריה | שם מוצר | מחיר | תיאור | כמות מקסימלית\n\n"
        "דוגמה:\n"
        "/add_product 📦 מוצרי הובלות ואריזה | רצ׳ט 5 מטר | 45 | רצ׳ט איכותי לקשירה | 50"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_set_price_help")
async def admin_set_price_help(callback: CallbackQuery):
    if not is_admin_id(callback.from_user.id):
        return

    await callback.message.answer(
        "✏️ לשינוי מחיר תשלח:\n\n"
        "/set_price שם מוצר | מחיר חדש\n\n"
        "דוגמה:\n"
        "/set_price קרטונים | 10"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_off_help")
async def admin_off_help(callback: CallbackQuery):
    if not is_admin_id(callback.from_user.id):
        return

    await callback.message.answer(
        "🔴 לכיבוי מוצר תשלח:\n\n"
        "/off שם מוצר\n\n"
        "דוגמה:\n"
        "/off קרטונים"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_on_help")
async def admin_on_help(callback: CallbackQuery):
    if not is_admin_id(callback.from_user.id):
        return

    await callback.message.answer(
        "🟢 להפעלת מוצר תשלח:\n\n"
        "/on שם מוצר\n\n"
        "דוגמה:\n"
        "/on קרטונים"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_delete_help")
async def admin_delete_help(callback: CallbackQuery):
    if not is_admin_id(callback.from_user.id):
        return

    await callback.message.answer(
        "🗑️ למחיקת מוצר תשלח:\n\n"
        "/delete_product שם מוצר\n\n"
        "דוגמה:\n"
        "/delete_product קרטונים"
    )
    await callback.answer()


@dp.message(Command("products"))
async def admin_products_command(message: Message):
    if not is_admin_id(message.from_user.id):
        return

    rows = get_all_products()

    if not rows:
        await message.answer("אין מוצרים במערכת.")
        return

    text = "📦 רשימת מוצרים:\n\n"

    for row in rows:
        product_id, category, name, price, description, max_qty, active = row
        status = "✅ פעיל" if active else "❌ כבוי"
        text += (
            f"{status}\n"
            f"קטגוריה: {category}\n"
            f"מוצר: {name}\n"
            f"מחיר: ₪{price:g}\n"
            f"מקסימום להזמנה: {max_qty}\n\n"
        )

    await message.answer(text)


@dp.message(Command("add_product"))
async def admin_add_product(message: Message):
    if not is_admin_id(message.from_user.id):
        return

    try:
        raw = message.text.replace("/add_product", "", 1).strip()
        category, name, price, description, max_qty = [x.strip() for x in raw.split("|")]

        add_product(
            category=category,
            name=name,
            price=float(price),
            description=description,
            max_qty=int(max_qty),
            active=1
        )

        await message.answer(f"✅ המוצר נוסף/עודכן:\n{name} - ₪{float(price):g}")

    except Exception:
        await message.answer(
            "שימוש נכון:\n"
            "/add_product קטגוריה | שם מוצר | מחיר | תיאור | כמות מקסימלית\n\n"
            "דוגמה:\n"
            "/add_product 📦 מוצרי הובלות ואריזה | קרטונים | 8 | קרטון איכותי | 100"
        )


@dp.message(Command("set_price"))
async def admin_set_price(message: Message):
    if not is_admin_id(message.from_user.id):
        return

    try:
        raw = message.text.replace("/set_price", "", 1).strip()
        name, price = [x.strip() for x in raw.split("|")]

        ok = set_product_price(name, float(price))

        if ok:
            await message.answer(f"✅ המחיר עודכן:\n{name} → ₪{float(price):g}")
        else:
            await message.answer("המוצר לא נמצא.")

    except Exception:
        await message.answer("שימוש נכון:\n/set_price שם מוצר | מחיר חדש")


@dp.message(Command("off"))
async def admin_off(message: Message):
    if not is_admin_id(message.from_user.id):
        return

    name = message.text.replace("/off", "", 1).strip()

    if not name:
        await message.answer("שימוש נכון:\n/off שם מוצר")
        return

    ok = set_product_active(name, 0)
    await message.answer("✅ המוצר כובה." if ok else "המוצר לא נמצא.")


@dp.message(Command("on"))
async def admin_on(message: Message):
    if not is_admin_id(message.from_user.id):
        return

    name = message.text.replace("/on", "", 1).strip()

    if not name:
        await message.answer("שימוש נכון:\n/on שם מוצר")
        return

    ok = set_product_active(name, 1)
    await message.answer("✅ המוצר הופעל." if ok else "המוצר לא נמצא.")


@dp.message(Command("delete_product"))
async def admin_delete_product(message: Message):
    if not is_admin_id(message.from_user.id):
        return

    name = message.text.replace("/delete_product", "", 1).strip()

    if not name:
        await message.answer("שימוש נכון:\n/delete_product שם מוצר")
        return

    ok = delete_product(name)
    await message.answer("🗑️ המוצר נמחק." if ok else "המוצר לא נמצא.")


@dp.message(F.text == "🛒 חנות")
async def shop(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})

    products = get_active_products()

    if not products:
        await message.answer("כרגע אין מוצרים זמינים בחנות.")
        return

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


@dp.message()
async def handle_message(message: Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()

    products = get_active_products()

    if txt in products:
        users.setdefault(uid, {"cart": [], "step": None})
        users[uid]["step"] = None
        await message.answer(f"בחר מוצר מתוך {txt}:", reply_markup=products_keyboard(txt))
        return

    product = find_product(txt)

    if product:
        users.setdefault(uid, {"cart": [], "step": None})
        users[uid]["selected_product"] = product
        users[uid]["step"] = "qty"

        await message.answer(
            f"בחרת: {product['name']}\n"
            f"{product.get('description', '')}\n\n"
            f"מחיר ליחידה: ₪{product['price']:g}\n"
            f"כמות מקסימלית להזמנה: {product.get('max_qty', 100)}\n\n"
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
        await message.answer("✅ קיבלנו את הפנייה שלך.", reply_markup=main_keyboard())
        return

    if data.get("step") == "qty":
        if not txt.isdigit():
            await message.answer("נא לרשום כמות במספרים בלבד.")
            return

        qty = int(txt)
        product = data.get("selected_product")

        if not product:
            data["step"] = None
            await message.answer("בחר מוצר מחדש.", reply_markup=categories_keyboard())
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
            "price": float(product["price"]),
            "qty": qty
        })

        data["step"] = None
        data.pop("selected_product", None)

        await message.answer(
            f"✅ נוסף לסל:\n"
            f"{product['name']} × {qty} = ₪{float(product['price']) * qty:g}\n\n"
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

        if not valid_phone(phone):
            await message.answer("נא לרשום מספר פלאפון ישראלי תקין. לדוגמה: 0547937503")
            return

        data["phone"] = phone
        data["step"] = "city"
        await message.answer("באיזה יישוב המשלוח? לדוגמה: אשדוד")
        return

    if data.get("step") == "city":
        if len(txt) < 2 or has_digit(txt):
            await message.answer("נא לרשום שם יישוב תקין.")
            return

        delivery_price, base_city, status = get_delivery_price(txt)

        if status == "city_not_found":
            await message.answer("היישוב לא נמצא במאגר. נא לרשום יישוב תקין.")
            return

        if status == "no_delivery_price":
            await message.answer("אין מחיר משלוח אוטומטי לאזור הזה. פנה לשירות לקוחות.")
            return

        data["city"] = txt
        data["delivery_price"] = float(delivery_price)
        data["base_city"] = base_city
        data["step"] = "street"

        await message.answer(
            f"דמי משלוח ל{txt}: ₪{float(delivery_price):g}\n\n"
            "רחוב ומספר בית?"
        )
        return

    if data.get("step") == "street":
        if len(txt) < 5 or not has_digit(txt):
            await message.answer("נא לרשום רחוב + מספר בית.")
            return

        data["street"] = txt
        data["step"] = "floor"
        await message.answer("איזו קומה? אם זה קרקע תרשום 0")
        return

    if data.get("step") == "floor":
        if not txt.lstrip("-").isdigit():
            await message.answer("נא לרשום קומה במספרים בלבד.")
            return

        data["floor"] = txt
        data["step"] = "apartment"
        await message.answer("מספר דירה? אם אין דירה תרשום 0")
        return

    if data.get("step") == "apartment":
        if not txt.isdigit():
            await message.answer("נא לרשום מספר דירה במספרים בלבד.")
            return

        data["apartment"] = txt

        products_total = cart_total(data["cart"])
        delivery_price = float(data["delivery_price"])
        final_total = products_total + delivery_price

        address = f"{data['city']}, {data['street']}, קומה {data['floor']}, דירה {data['apartment']}"

        order = "📦 הזמנה חדשה מ-Vendora Shop\n\n"
        order += f"👤 שם: {data['name']}\n"
        order += f"📞 טלפון: {data['phone']}\n"
        order += f"📍 כתובת: {address}\n\n"
        order += cart_text(data["cart"])
        order += f"\n🚚 משלוח: ₪{delivery_price:g}"
        order += f"\n💳 סה״כ לתשלום: ₪{final_total:g}"
        order += f"\n\n📍 אזור/עיר בסיס: {data['base_city']}"
        order += f"\n🆔 Telegram ID: {uid}"
        order += f"\n👤 Telegram: {message.from_user.full_name}"

        await bot.send_message(ADMIN_ID, order)

        users.pop(uid, None)

        await message.answer(
            f"✅ ההזמנה התקבלה!\n"
            f"סה״כ כולל משלוח: ₪{final_total:g}",
            reply_markup=main_keyboard()
        )
        return

    await message.answer("בחר פעולה מהתפריט.", reply_markup=main_keyboard())


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
