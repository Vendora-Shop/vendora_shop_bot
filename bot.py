import os
import json
import math
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database import (
    create_tables,
    add_product,
    get_active_products,
    get_all_products,
    get_product_by_name,
    set_product_price,
    set_product_description,
    set_product_stock,
    add_stock,
    set_product_image,
    set_product_active,
    delete_product,
    reduce_stock,
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


def is_admin(user_id: int) -> bool:
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
            central_location["lng"],
        )

        radius = float(zone.get("radius_km", 0))

        if dist <= radius:
            if best is None or dist < best["distance"]:
                best = {
                    "price": float(zone["price"]),
                    "base_city": central_city,
                    "distance": round(dist, 1),
                }

    if best:
        return best["price"], best["base_city"], "ok"

    return None, None, "no_delivery_price"


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 חנות")],
            [KeyboardButton(text="📞 שירות לקוחות")],
        ],
        resize_keyboard=True,
    )


def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ הוסף מוצר"), KeyboardButton(text="📦 רשימת מוצרים")],
            [KeyboardButton(text="✏️ שנה מחיר"), KeyboardButton(text="📝 שנה תיאור")],
            [KeyboardButton(text="📊 עדכן מלאי"), KeyboardButton(text="➕ הוסף למלאי")],
            [KeyboardButton(text="🖼️ עדכן תמונה")],
            [KeyboardButton(text="🔴 כבה מוצר"), KeyboardButton(text="🟢 הפעל מוצר")],
            [KeyboardButton(text="🗑️ מחק מוצר")],
            [KeyboardButton(text="⬅️ יציאה מניהול")],
        ],
        resize_keyboard=True,
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
        stock = int(product.get("stock", 0))

        if stock <= 0:
            keyboard.append([KeyboardButton(text=f"❌ {product['name']} - אזל מהמלאי")])
        else:
            keyboard.append([KeyboardButton(text=product["name"])])

    keyboard.append([KeyboardButton(text="🛒 הסל שלי")])
    keyboard.append([KeyboardButton(text="⬅️ חזרה לקטגוריות")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def cart_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ הוסף עוד מוצר")],
            [KeyboardButton(text="✅ המשך להזמנה")],
            [KeyboardButton(text="❌ בטל הזמנה")],
        ],
        resize_keyboard=True,
    )


def product_names_keyboard():
    rows = get_all_products()
    keyboard = []

    for row in rows:
        product_id, category, name, price, description, max_qty, stock, sku, image_file_id, active = row
        keyboard.append([KeyboardButton(text=name)])

    keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def clean_product_button_name(text):
    return text.replace("❌ ", "").replace(" - אזל מהמלאי", "").strip()


def find_product(name):
    products = get_active_products()
    clean_name = clean_product_button_name(name)

    for category, items in products.items():
        for item in items:
            if item["name"] == clean_name:
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


async def send_products_list(message: Message):
    rows = get_all_products()

    if not rows:
        await message.answer("אין מוצרים במערכת.")
        return

    text = "📦 רשימת מוצרים:\n\n"

    for row in rows:
        product_id, category, name, price, description, max_qty, stock, sku, image_file_id, active = row

        status = "✅ פעיל" if active else "❌ כבוי"
        stock_status = "❌ אזל מהמלאי" if int(stock) <= 0 else f"📦 מלאי: {stock}"
        image_status = "🖼️ יש תמונה" if image_file_id else "⚠️ ללא תמונה"

        text += (
            f"━━━━━━━━━━━━\n"
            f"🛍️ {name}\n"
            f"{status} | {image_status}\n"
            f"קטגוריה: {category}\n"
            f"מק״ט: {sku or '-'}\n"
            f"💰 מחיר: ₪{float(price):g}\n"
            f"{stock_status}\n"
            f"🔢 מקסימום להזמנה: {max_qty}\n"
            f"📝 תיאור: {description or '-'}\n\n"
        )

    await message.answer(text)


async def send_product_card(message: Message, product):
    stock = int(product.get("stock", 0))
    stock_text = "❌ אזל מהמלאי" if stock <= 0 else f"📦 במלאי: {stock} יח׳"

    caption = (
        f"🛍️ {product['name']}\n\n"
        f"{product.get('description', '')}\n\n"
        f"💰 מחיר: ₪{float(product['price']):g}\n"
        f"{stock_text}\n"
        f"🔢 מקסימום להזמנה: {product.get('max_qty', 100)}"
    )

    image_file_id = product.get("image_file_id")

    if image_file_id:
        await message.answer_photo(photo=image_file_id, caption=caption)
    else:
        await message.answer(caption)


@dp.message(CommandStart())
async def start(message: Message):
    users.pop(message.from_user.id, None)

    await message.answer(
        "🔥 ברוך הבא ל-Vendora Shop\n"
        "חנות לציוד הובלות, שילוח ושליחים.",
        reply_markup=main_keyboard(),
    )


@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin"}
    await message.answer("🔐 לוח ניהול Vendora Shop", reply_markup=admin_keyboard())


@dp.message(Command("products"))
async def products_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    await send_products_list(message)


@dp.message(F.text == "⬅️ יציאה מניהול")
async def exit_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    users.pop(message.from_user.id, None)
    await message.answer("יצאת מלוח הניהול.", reply_markup=main_keyboard())


@dp.message(F.text == "⬅️ חזרה לניהול")
async def back_to_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin"}
    await message.answer("חזרת ללוח הניהול.", reply_markup=admin_keyboard())


@dp.message(F.text == "📦 רשימת מוצרים")
async def products_button(message: Message):
    if not is_admin(message.from_user.id):
        return

    await send_products_list(message)


@dp.message(F.text == "➕ הוסף מוצר")
async def add_product_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin_add_category"}
    await message.answer("רשום קטגוריה למוצר.\nלדוגמה: 📦 מוצרי הובלות ואריזה")


@dp.message(F.text == "✏️ שנה מחיר")
async def change_price_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin_price_name"}
    await message.answer("בחר מוצר לשינוי מחיר:", reply_markup=product_names_keyboard())


@dp.message(F.text == "📝 שנה תיאור")
async def change_description_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin_description_name"}
    await message.answer("בחר מוצר לשינוי תיאור:", reply_markup=product_names_keyboard())


@dp.message(F.text == "📊 עדכן מלאי")
async def set_stock_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin_stock_name"}
    await message.answer("בחר מוצר לעדכון מלאי:", reply_markup=product_names_keyboard())


@dp.message(F.text == "➕ הוסף למלאי")
async def add_stock_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin_add_stock_name"}
    await message.answer("בחר מוצר להוספת מלאי:", reply_markup=product_names_keyboard())


@dp.message(F.text == "🖼️ עדכן תמונה")
async def set_image_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin_image_name"}
    await message.answer("בחר מוצר לעדכון תמונה:", reply_markup=product_names_keyboard())


@dp.message(F.text == "🔴 כבה מוצר")
async def off_product_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin_off_name"}
    await message.answer("בחר מוצר לכיבוי:", reply_markup=product_names_keyboard())


@dp.message(F.text == "🟢 הפעל מוצר")
async def on_product_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin_on_name"}
    await message.answer("בחר מוצר להפעלה:", reply_markup=product_names_keyboard())


@dp.message(F.text == "🗑️ מחק מוצר")
async def delete_product_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    users[message.from_user.id] = {"step": "admin_delete_name"}
    await message.answer("בחר מוצר למחיקה:", reply_markup=product_names_keyboard())


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
async def add_more_product(message: Message):
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


@dp.message(F.photo)
async def handle_photo(message: Message):
    uid = message.from_user.id
    data = users.get(uid)

    if not is_admin(uid) or not data or data.get("step") != "admin_image_photo":
        await message.answer("התמונה התקבלה, אבל לא נבחר מוצר לעדכון תמונה.")
        return

    file_id = message.photo[-1].file_id
    product_name = data["product_name"]

    ok = set_product_image(product_name, file_id)
    users[uid] = {"step": "admin"}

    await message.answer(
        f"✅ התמונה עודכנה למוצר:\n{product_name}" if ok else "המוצר לא נמצא.",
        reply_markup=admin_keyboard(),
    )


@dp.message()
async def handle_message(message: Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    data = users.get(uid)

    if is_admin(uid) and data:
        step = data.get("step")

        if step == "admin_add_category":
            if len(txt) < 2:
                await message.answer("נא לרשום קטגוריה תקינה.")
                return

            data["category"] = txt
            data["step"] = "admin_add_name"
            await message.answer("רשום שם מוצר.")
            return

        if step == "admin_add_name":
            if len(txt) < 2:
                await message.answer("נא לרשום שם מוצר תקין.")
                return

            data["name"] = txt
            data["step"] = "admin_add_price"
            await message.answer("רשום מחיר בשקלים. לדוגמה: 45")
            return

        if step == "admin_add_price":
            try:
                price = float(txt)
                if price <= 0:
                    raise ValueError
            except Exception:
                await message.answer("נא לרשום מחיר תקין במספרים בלבד.")
                return

            data["price"] = price
            data["step"] = "admin_add_description"
            await message.answer("רשום תיאור קצר למוצר.")
            return

        if step == "admin_add_description":
            data["description"] = txt
            data["step"] = "admin_add_max_qty"
            await message.answer("רשום כמות מקסימלית להזמנה אחת. לדוגמה: 10")
            return

        if step == "admin_add_max_qty":
            if not txt.isdigit() or int(txt) <= 0:
                await message.answer("נא לרשום מספר תקין.")
                return

            data["max_qty"] = int(txt)
            data["step"] = "admin_add_stock"
            await message.answer("רשום מלאי נוכחי. לדוגמה: 50")
            return

        if step == "admin_add_stock":
            if not txt.isdigit() or int(txt) < 0:
                await message.answer("נא לרשום מלאי תקין במספרים בלבד.")
                return

            data["stock"] = int(txt)
            data["step"] = "admin_add_sku"
            await message.answer("רשום מק״ט / קוד מוצר. אם אין, רשום 0")
            return

        if step == "admin_add_sku":
            sku = "" if txt == "0" else txt

            add_product(
                category=data["category"],
                name=data["name"],
                price=float(data["price"]),
                description=data["description"],
                max_qty=int(data["max_qty"]),
                stock=int(data["stock"]),
                sku=sku,
                image_file_id="",
                active=1,
            )

            users[uid] = {"step": "admin"}

            await message.answer(
                f"✅ המוצר נוסף בהצלחה:\n\n"
                f"קטגוריה: {data['category']}\n"
                f"מוצר: {data['name']}\n"
                f"מחיר: ₪{float(data['price']):g}\n"
                f"מלאי: {data['stock']}\n"
                f"מקסימום להזמנה: {data['max_qty']}\n\n"
                f"כדי להוסיף תמונה לחץ: 🖼️ עדכן תמונה",
                reply_markup=admin_keyboard(),
            )
            return

        if step == "admin_price_name":
            product = get_product_by_name(txt)
            if not product:
                await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
                return

            data["product_name"] = txt
            data["step"] = "admin_price_value"
            await message.answer(f"מחיר נוכחי: ₪{float(product['price']):g}\nרשום מחיר חדש.")
            return

        if step == "admin_price_value":
            try:
                price = float(txt)
                if price <= 0:
                    raise ValueError
            except Exception:
                await message.answer("נא לרשום מחיר תקין.")
                return

            ok = set_product_price(data["product_name"], price)
            users[uid] = {"step": "admin"}

            await message.answer(
                f"✅ המחיר עודכן ל־₪{price:g}" if ok else "המוצר לא נמצא.",
                reply_markup=admin_keyboard(),
            )
            return

        if step == "admin_description_name":
            product = get_product_by_name(txt)
            if not product:
                await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
                return

            data["product_name"] = txt
            data["step"] = "admin_description_text"
            await message.answer("רשום תיאור חדש למוצר.")
            return

        if step == "admin_description_text":
            ok = set_product_description(data["product_name"], txt)
            users[uid] = {"step": "admin"}

            await message.answer(
                "✅ התיאור עודכן." if ok else "המוצר לא נמצא.",
                reply_markup=admin_keyboard(),
            )
            return

        if step == "admin_stock_name":
            product = get_product_by_name(txt)
            if not product:
                await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
                return

            data["product_name"] = txt
            data["step"] = "admin_stock_value"
            await message.answer(f"מלאי נוכחי: {product['stock']}\nרשום מלאי חדש.")
            return

        if step == "admin_stock_value":
            if not txt.isdigit() or int(txt) < 0:
                await message.answer("נא לרשום מלאי תקין.")
                return

            ok = set_product_stock(data["product_name"], int(txt))
            users[uid] = {"step": "admin"}

            await message.answer(
                "✅ המלאי עודכן." if ok else "המוצר לא נמצא.",
                reply_markup=admin_keyboard(),
            )
            return

        if step == "admin_add_stock_name":
            product = get_product_by_name(txt)
            if not product:
                await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
                return

            data["product_name"] = txt
            data["step"] = "admin_add_stock_value"
            await message.answer(f"מלאי נוכחי: {product['stock']}\nכמה יחידות להוסיף למלאי?")
            return

        if step == "admin_add_stock_value":
            if not txt.isdigit() or int(txt) <= 0:
                await message.answer("נא לרשום מספר חיובי.")
                return

            ok = add_stock(data["product_name"], int(txt))
            users[uid] = {"step": "admin"}

            await message.answer(
                f"✅ נוספו {txt} יחידות למלאי." if ok else "המוצר לא נמצא.",
                reply_markup=admin_keyboard(),
            )
            return

        if step == "admin_image_name":
            product = get_product_by_name(txt)
            if not product:
                await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
                return

            data["product_name"] = txt
            data["step"] = "admin_image_photo"
            await message.answer(f"נבחר מוצר: {txt}\nעכשיו שלח תמונה של המוצר.")
            return

        if step == "admin_off_name":
            ok = set_product_active(txt, 0)
            users[uid] = {"step": "admin"}
            await message.answer("✅ המוצר כובה." if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
            return

        if step == "admin_on_name":
            ok = set_product_active(txt, 1)
            users[uid] = {"step": "admin"}
            await message.answer("✅ המוצר הופעל." if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
            return

        if step == "admin_delete_name":
            ok = delete_product(txt)
            users[uid] = {"step": "admin"}
            await message.answer("🗑️ המוצר נמחק." if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
            return

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

        await send_product_card(message, product)

        if int(product.get("stock", 0)) <= 0:
            await message.answer("המוצר אזל מהמלאי כרגע ולא ניתן להזמין אותו.")
            users[uid]["step"] = None
            return

        await message.answer("כמה יחידות תרצה?")
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
            f"💬 הודעה: {txt}",
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
        stock = int(product.get("stock", 0))

        if qty <= 0:
            await message.answer("הכמות חייבת להיות גדולה מ־0.")
            return

        if qty > max_qty:
            await message.answer(f"ניתן להזמין עד {max_qty} יחידות מהמוצר הזה.")
            return

        if qty > stock:
            await message.answer(f"כרגע יש במלאי רק {stock} יחידות.")
            return

        data["cart"].append(
            {
                "name": product["name"],
                "price": float(product["price"]),
                "qty": qty,
            }
        )

        data["step"] = None
        data.pop("selected_product", None)

        await message.answer(
            f"✅ נוסף לסל:\n"
            f"{product['name']} × {qty} = ₪{float(product['price']) * qty:g}\n\n"
            f"{cart_text(data['cart'])}",
            reply_markup=cart_keyboard(),
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

        stock_ok, problem_product = reduce_stock(data["cart"])

        if not stock_ok:
            await message.answer(
                f"יש בעיית מלאי במוצר: {problem_product}\n"
                f"נא לעדכן את ההזמנה.",
                reply_markup=cart_keyboard(),
            )
            return

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
            reply_markup=main_keyboard(),
        )
        return

    await message.answer("בחר פעולה מהתפריט.", reply_markup=main_keyboard())


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
