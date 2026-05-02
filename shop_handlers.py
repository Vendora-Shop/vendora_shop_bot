from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from config import ADMIN_ID
from keyboards import main_keyboard
from database import get_active_products, reduce_stock
from delivery import get_delivery_price

router = Router()
users = {}


@router.message(CommandStart())
async def start(message: Message):
    users.pop(message.from_user.id, None)

    await message.answer(
        "🔥 ברוך הבא ל-Vendora Shop\n"
        "חנות לציוד הובלות, שילוח ושליחים.",
        reply_markup=main_keyboard()
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
        if int(product.get("stock", 0)) <= 0:
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
            [KeyboardButton(text="❌ בטל הזמנה")]
        ],
        resize_keyboard=True
    )


def clean_product_name(text):
    return text.replace("❌ ", "").replace(" - אזל מהמלאי", "").strip()


def find_product(name):
    name = clean_product_name(name)
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
        total = float(item["price"]) * int(item["qty"])
        text += f"• {item['name']} × {item['qty']} = ₪{total:g}\n"

    text += f"\n💰 סה״כ מוצרים: ₪{cart_total(cart):g}"
    return text


def clean_phone(phone):
    return phone.strip().replace(" ", "").replace("-", "").replace("+972", "0")


def valid_phone(phone):
    phone = clean_phone(phone)
    return phone.isdigit() and phone.startswith("05") and len(phone) == 10


def has_digit(text):
    return any(ch.isdigit() for ch in text)


async def send_product_card(message: Message, product):
    stock = int(product.get("stock", 0))
    stock_text = "❌ אזל מהמלאי" if stock <= 0 else f"📦 מלאי זמין: {stock}"

    caption = (
        f"🛒 {product['name']}\n\n"
        f"{product.get('description', '')}\n\n"
        f"💰 מחיר: ₪{float(product['price']):g}\n"
        f"{stock_text}\n"
        f"🔢 מקסימום להזמנה: {product.get('max_qty', 100)}"
    )

    image = product.get("image_file_id")

    if image:
        await message.answer_photo(photo=image, caption=caption)
    else:
        await message.answer(caption)


@router.message(F.text == "🛒 חנות")
async def shop(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})

    products = get_active_products()

    if not products:
        await message.answer("כרגע אין מוצרים זמינים בחנות.")
        return

    await message.answer("בחר קטגוריה:", reply_markup=categories_keyboard())


@router.message(F.text == "⬅️ חזרה")
async def back_main(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("חזרת לתפריט הראשי.", reply_markup=main_keyboard())


@router.message(F.text == "⬅️ חזרה לקטגוריות")
async def back_categories(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})
    users[uid]["step"] = None
    await message.answer("בחר קטגוריה:", reply_markup=categories_keyboard())


@router.message(F.text == "➕ הוסף עוד מוצר")
async def add_more(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})
    users[uid]["step"] = None
    await message.answer("בחר קטגוריה:", reply_markup=categories_keyboard())


@router.message(F.text == "🛒 הסל שלי")
async def show_cart(message: Message):
    uid = message.from_user.id
    data = users.setdefault(uid, {"cart": [], "step": None})
    await message.answer(cart_text(data["cart"]), reply_markup=cart_keyboard())


@router.message(F.text == "❌ בטל הזמנה")
async def cancel_order(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer("ההזמנה בוטלה.", reply_markup=main_keyboard())


@router.message(F.text == "✅ המשך להזמנה")
async def checkout(message: Message):
    uid = message.from_user.id
    data = users.get(uid)

    if not data or not data.get("cart"):
        await message.answer("הסל שלך ריק. קודם בחר מוצר.")
        return

    data["step"] = "name"
    await message.answer("מה השם המלא שלך?")


@router.message(F.text == "📞 שירות לקוחות")
async def support(message: Message):
    uid = message.from_user.id
    users[uid] = {"cart": [], "step": "support"}
    await message.answer("כתוב כאן את ההודעה שלך ונעביר אותה לנציג.")


@router.message()
async def handle_shop(message: Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    data = users.get(uid)

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

        await send_product_card(message, product)

        if int(product.get("stock", 0)) <= 0:
            await message.answer("המוצר אזל מהמלאי כרגע ולא ניתן להזמין אותו.")
            users[uid]["step"] = None
            return

        users[uid]["step"] = "qty"
        await message.answer("כמה יחידות תרצה?")
        return

    if not data:
        return

    if data.get("step") == "support":
        if len(txt) < 2:
            await message.answer("נא לרשום הודעה לנציג.")
            return

        await message.bot.send_message(
            ADMIN_ID,
            f"📩 פנייה חדשה לשירות לקוחות\n\n"
            f"👤 שם: {message.from_user.full_name}\n"
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

        data["cart"].append({
            "name": product["name"],
            "price": float(product["price"]),
            "qty": qty
        })

        data["step"] = None
        data.pop("selected_product", None)

        await message.answer(
            f"✅ נוסף לסל:\n"
            f"{product['name']} × {qty}\n\n"
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
            await message.answer("נא לרשום מספר פלאפון ישראלי תקין.")
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
            f"🚚 דמי משלוח ל{txt}: ₪{float(delivery_price):g}\n\n"
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
                reply_markup=cart_keyboard()
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

        await message.bot.send_message(ADMIN_ID, order)

        users.pop(uid, None)

        await message.answer(
            f"✅ ההזמנה התקבלה!\n"
            f"סה״כ כולל משלוח: ₪{final_total:g}",
            reply_markup=main_keyboard()
        )
