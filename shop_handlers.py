from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from html import escape

from config import ADMIN_ID
from keyboards import main_keyboard
from database import (
    get_active_products,
    get_product_by_name,
    reduce_stock,
    create_order,
    get_order_by_number
)
from delivery import get_delivery_price
from pdf_generator import create_invoice_pdf

router = Router()
users = {}

RTL = "\u200F"


def h(text):
    return escape(str(text))


def rtl(text):
    return RTL + str(text)


def money(value):
    value = float(value)
    if value.is_integer():
        return f"{int(value)}₪"
    return f"{value:g}₪"


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
            [KeyboardButton(text="🧹 רוקן סל")],
            [KeyboardButton(text="❌ בטל הזמנה")]
        ],
        resize_keyboard=True
    )


def confirm_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ אשר הזמנה")],
            [KeyboardButton(text="✏️ שנה פרטים")],
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


def product_qty_in_cart(cart, product_name):
    return sum(int(item["qty"]) for item in cart if item["name"] == product_name)


def clean_phone(phone):
    return phone.strip().replace(" ", "").replace("-", "").replace("+972", "0")


def valid_phone(phone):
    phone = clean_phone(phone)
    return phone.isdigit() and phone.startswith("05") and len(phone) == 10


def has_digit(text):
    return any(ch.isdigit() for ch in text)


def cart_text(cart):
    if not cart:
        return rtl(
            "<b>🛒 הסל שלך</b>\n\n"
            "הסל שלך ריק כרגע."
        )

    text = "<b>🛒 הסל שלך</b>\n\n"

    for item in cart:
        total = float(item["price"]) * int(item["qty"])
        text += (
            f"• <b>{h(item['name'])}</b>\n"
            f"  כמות: <b>{int(item['qty'])}</b>\n"
            f"  סה״כ: <b>{money(total)}</b>\n\n"
        )

    text += f"<b>💰 סה״כ מוצרים: {money(cart_total(cart))}</b>"
    return rtl(text)


async def send_product_card(message: Message, product):
    stock = int(product.get("stock", 0))
    stock_text = "❌ אזל מהמלאי" if stock <= 0 else f"📦 מלאי זמין: {stock}"

    caption = rtl(
        f"<b>🛍️ {h(product['name'])}</b>\n\n"
        f"{h(product.get('description', ''))}\n\n"
        f"<b>💰 מחיר:</b> {money(product['price'])}\n"
        f"<b>{stock_text}</b>\n"
        f"<b>🔢 מקסימום להזמנה:</b> {h(product.get('max_qty', 100))}"
    )

    image = product.get("image_file_id")

    if image:
        await message.answer_photo(photo=image, caption=caption, parse_mode="HTML")
    else:
        await message.answer(caption, parse_mode="HTML")


def build_order_summary(data):
    products_total = cart_total(data["cart"])
    delivery_price = float(data["delivery_price"])
    final_total = products_total + delivery_price
    address = f"{data['city']}, {data['street']}, קומה {data['floor']}, דירה {data['apartment']}"

    text = (
        "<b>📦 סיכום הזמנה</b>\n\n"
        f"<b>👤 שם לקוח:</b> {h(data['name'])}\n"
        f"<b>📞 טלפון:</b> {h(data['phone'])}\n"
        f"<b>📍 כתובת:</b> {h(address)}\n\n"
        f"{cart_text(data['cart']).replace(RTL, '')}\n"
        f"\n<b>🚚 דמי משלוח:</b> {money(delivery_price)}"
        f"\n<b>💳 סה״כ לתשלום:</b> {money(final_total)}"
        "\n\n<b>✅ אם הכול נכון לחץ על אשר הזמנה.</b>"
    )

    return rtl(text)


@router.message(CommandStart())
async def start(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer(
        rtl(
            "<b>🔥 ברוך הבא ל־Vendora Shop</b>\n\n"
            "חנות חכמה לציוד הובלות, שילוח ושליחים.\n"
            "בחר פעולה מהתפריט למטה."
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🛒 חנות")
async def shop(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})

    products = get_active_products()

    if not products:
        await message.answer(
            rtl("<b>🛒 החנות</b>\n\nכרגע אין מוצרים זמינים בחנות."),
            parse_mode="HTML"
        )
        return

    await message.answer(
        rtl("<b>🛒 החנות</b>\n\nבחר קטגוריה:"),
        reply_markup=categories_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ חזרה")
async def back_main(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer(
        rtl("<b>↩️ חזרת לתפריט הראשי</b>"),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ חזרה לקטגוריות")
async def back_categories(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})
    users[uid]["step"] = None
    await message.answer(
        rtl("<b>📂 קטגוריות</b>\n\nבחר קטגוריה:"),
        reply_markup=categories_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "➕ הוסף עוד מוצר")
async def add_more(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})
    users[uid]["step"] = None
    await message.answer(
        rtl("<b>➕ הוספת מוצר</b>\n\nבחר קטגוריה:"),
        reply_markup=categories_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🛒 הסל שלי")
async def show_cart(message: Message):
    uid = message.from_user.id
    data = users.setdefault(uid, {"cart": [], "step": None})
    await message.answer(cart_text(data["cart"]), reply_markup=cart_keyboard(), parse_mode="HTML")


@router.message(F.text == "🧹 רוקן סל")
async def clear_cart(message: Message):
    uid = message.from_user.id
    users[uid] = {"cart": [], "step": None}
    await message.answer(
        rtl("<b>🧹 הסל התרוקן בהצלחה.</b>"),
        reply_markup=categories_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "❌ בטל הזמנה")
async def cancel_order(message: Message):
    users.pop(message.from_user.id, None)
    await message.answer(
        rtl("<b>❌ ההזמנה בוטלה.</b>"),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "✏️ שנה פרטים")
async def edit_details(message: Message):
    uid = message.from_user.id
    data = users.get(uid)

    if not data or not data.get("cart"):
        await message.answer(
            rtl("<b>⚠️ אין הזמנה פעילה.</b>"),
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )
        return

    data["step"] = "name"
    await message.answer(
        rtl("<b>✏️ עדכון פרטים</b>\n\nרשום את השם המלא שלך:"),
        parse_mode="HTML"
    )


@router.message(F.text == "✅ המשך להזמנה")
async def checkout(message: Message):
    uid = message.from_user.id
    data = users.get(uid)

    if not data or not data.get("cart"):
        await message.answer(
            rtl("<b>🛒 הסל שלך ריק.</b>\n\nקודם בחר מוצר."),
            parse_mode="HTML"
        )
        return

    data["step"] = "name"
    await message.answer(
        rtl("<b>📝 פרטי הזמנה</b>\n\nרשום את השם המלא שלך:"),
        parse_mode="HTML"
    )


@router.message(F.text == "✅ אשר הזמנה")
async def confirm_order(message: Message):
    uid = message.from_user.id
    data = users.get(uid)

    if not data or not data.get("cart"):
        await message.answer(
            rtl("<b>⚠️ אין הזמנה פעילה.</b>"),
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )
        return

    required = ["name", "phone", "city", "street", "floor", "apartment", "delivery_price", "base_city"]
    if any(key not in data for key in required):
        data["step"] = "name"
        await message.answer(
            rtl("<b>⚠️ חסרים פרטים להזמנה.</b>\n\nנרשום מחדש את הפרטים.\nמה השם המלא שלך?"),
            parse_mode="HTML"
        )
        return

    stock_ok, problem_product = reduce_stock(data["cart"])

    if not stock_ok:
        await message.answer(
            rtl(
                "<b>⚠️ בעיית מלאי</b>\n\n"
                f"המוצר <b>{h(problem_product)}</b> אינו זמין בכמות המבוקשת.\n"
                "נא לעדכן את הסל."
            ),
            reply_markup=cart_keyboard(),
            parse_mode="HTML"
        )
        return

    products_total = cart_total(data["cart"])
    delivery_price = float(data["delivery_price"])
    final_total = products_total + delivery_price

    order_number = create_order(
        telegram_id=uid,
        telegram_name=message.from_user.full_name,
        customer_name=data["name"],
        phone=data["phone"],
        city=data["city"],
        street=data["street"],
        floor=data["floor"],
        apartment=data["apartment"],
        cart=data["cart"],
        products_total=products_total,
        delivery_price=delivery_price,
        final_total=final_total,
        base_city=data["base_city"]
    )

    address = f"{data['city']}, {data['street']}, קומה {data['floor']}, דירה {data['apartment']}"

    admin_order = rtl(
        f"<b>📦 הזמנה חדשה מ־Vendora Shop</b>\n\n"
        f"<b>🧾 מספר הזמנה:</b> {h(order_number)}\n\n"
        f"<b>👤 שם לקוח:</b> {h(data['name'])}\n"
        f"<b>📞 טלפון:</b> {h(data['phone'])}\n"
        f"<b>📍 כתובת:</b> {h(address)}\n\n"
        f"{cart_text(data['cart']).replace(RTL, '')}\n\n"
        f"<b>🚚 משלוח:</b> {money(delivery_price)}\n"
        f"<b>💳 סה״כ לתשלום:</b> {money(final_total)}\n\n"
        f"<b>📍 אזור/עיר בסיס:</b> {h(data['base_city'])}\n"
        f"<b>🆔 Telegram ID:</b> {h(uid)}\n"
        f"<b>👤 Telegram:</b> {h(message.from_user.full_name)}\n\n"
        f"<b>סטטוס:</b> 🆕 הזמנה חדשה"
    )

    await message.bot.send_message(ADMIN_ID, admin_order, parse_mode="HTML")

    saved_order = get_order_by_number(order_number)
    if saved_order:
        try:
            pdf_path = create_invoice_pdf(saved_order)
            await message.answer_document(
                FSInputFile(pdf_path),
                caption=rtl(f"📄 <b>סיכום הזמנה {h(order_number)}</b>"),
                parse_mode="HTML"
            )
        except Exception:
            await message.answer(
                rtl("<b>⚠️ ההזמנה נשמרה, אבל לא הצלחתי ליצור PDF כרגע.</b>"),
                parse_mode="HTML"
            )

    users.pop(uid, None)

    await message.answer(
        rtl(
            "<b>✅ ההזמנה התקבלה!</b>\n\n"
            f"<b>🧾 מספר הזמנה:</b> {h(order_number)}\n\n"
            "נציג יחזור אליך לאישור סופי ותשלום.\n"
            f"<b>סה״כ כולל משלוח:</b> {money(final_total)}"
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "📞 שירות לקוחות")
async def support(message: Message):
    uid = message.from_user.id
    users[uid] = {"cart": [], "step": "support"}
    await message.answer(
        rtl("<b>📞 שירות לקוחות</b>\n\nכתוב כאן את ההודעה שלך ונעביר אותה לנציג."),
        parse_mode="HTML"
    )


@router.message()
async def handle_shop(message: Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    data = users.get(uid)

    products = get_active_products()

    if txt in products:
        users.setdefault(uid, {"cart": [], "step": None})
        users[uid]["step"] = None
        await message.answer(
            rtl(f"<b>📂 {h(txt)}</b>\n\nבחר מוצר:"),
            reply_markup=products_keyboard(txt),
            parse_mode="HTML"
        )
        return

    product = find_product(txt)

    if product:
        users.setdefault(uid, {"cart": [], "step": None})
        data = users[uid]

        fresh_product = get_product_by_name(product["name"])
        if fresh_product:
            product.update(fresh_product)

        await send_product_card(message, product)

        stock = int(product.get("stock", 0))
        if stock <= 0:
            await message.answer(
                rtl("<b>❌ המוצר אזל מהמלאי כרגע.</b>"),
                parse_mode="HTML"
            )
            data["step"] = None
            return

        already_in_cart = product_qty_in_cart(data["cart"], product["name"])
        available_left = stock - already_in_cart

        if available_left <= 0:
            await message.answer(
                rtl("<b>📦 כל המלאי הזמין של המוצר כבר נמצא אצלך בסל.</b>"),
                parse_mode="HTML"
            )
            return

        data["selected_product"] = product
        data["step"] = "qty"

        await message.answer(
            rtl(
                "<b>🔢 בחירת כמות</b>\n\n"
                f"כמה יחידות תרצה?\n"
                f"<b>זמין להזמנה כרגע:</b> {available_left}"
            ),
            parse_mode="HTML"
        )
        return

    if not data:
        return

    if data.get("step") == "support":
        if len(txt) < 2:
            await message.answer(
                rtl("<b>⚠️ נא לרשום הודעה לנציג.</b>"),
                parse_mode="HTML"
            )
            return

        await message.bot.send_message(
            ADMIN_ID,
            rtl(
                "<b>📩 פנייה חדשה לשירות לקוחות</b>\n\n"
                f"<b>👤 שם:</b> {h(message.from_user.full_name)}\n"
                f"<b>🆔 Telegram ID:</b> {h(uid)}\n"
                f"<b>💬 הודעה:</b> {h(txt)}"
            ),
            parse_mode="HTML"
        )

        users.pop(uid, None)
        await message.answer(
            rtl("<b>✅ קיבלנו את הפנייה שלך.</b>\nנציג יחזור אליך בהקדם."),
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "qty":
        if not txt.isdigit():
            await message.answer(
                rtl("<b>⚠️ נא לרשום כמות במספרים בלבד.</b>"),
                parse_mode="HTML"
            )
            return

        qty = int(txt)
        product = data.get("selected_product")

        if not product:
            await message.answer(
                rtl("<b>⚠️ בחר מוצר מחדש.</b>"),
                reply_markup=categories_keyboard(),
                parse_mode="HTML"
            )
            return

        fresh_product = get_product_by_name(product["name"])
        if not fresh_product or int(fresh_product.get("active", 0)) != 1:
            data["step"] = None
            await message.answer(
                rtl("<b>❌ המוצר לא זמין כרגע.</b>"),
                parse_mode="HTML"
            )
            return

        max_qty = int(fresh_product.get("max_qty", 100))
        stock = int(fresh_product.get("stock", 0))
        already_in_cart = product_qty_in_cart(data["cart"], product["name"])
        available_left = stock - already_in_cart

        if qty <= 0:
            await message.answer(
                rtl("<b>⚠️ הכמות חייבת להיות גדולה מ־0.</b>"),
                parse_mode="HTML"
            )
            return

        if qty > max_qty:
            await message.answer(
                rtl(f"<b>⚠️ ניתן להזמין עד {max_qty} יחידות מהמוצר הזה.</b>"),
                parse_mode="HTML"
            )
            return

        if qty > available_left:
            await message.answer(
                rtl(f"<b>⚠️ כרגע ניתן להוסיף עוד {available_left} יחידות בלבד.</b>"),
                parse_mode="HTML"
            )
            return

        data["cart"].append({
            "name": fresh_product["name"],
            "price": float(fresh_product["price"]),
            "qty": qty
        })

        data["step"] = None
        data.pop("selected_product", None)

        await message.answer(
            rtl(
                "<b>✅ נוסף לסל</b>\n\n"
                f"<b>{h(fresh_product['name'])}</b>\n"
                f"כמות: <b>{qty}</b>\n\n"
                f"{cart_text(data['cart']).replace(RTL, '')}"
            ),
            reply_markup=cart_keyboard(),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "name":
        if len(txt) < 2:
            await message.answer(rtl("<b>⚠️ נא לרשום שם מלא תקין.</b>"), parse_mode="HTML")
            return

        data["name"] = txt
        data["step"] = "phone"
        await message.answer(
            rtl("<b>📞 מספר פלאפון</b>\n\nרשום מספר פלאפון תקין.\nלדוגמה: <b>0547937503</b>"),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "phone":
        phone = clean_phone(txt)

        if not valid_phone(phone):
            await message.answer(
                rtl("<b>⚠️ מספר פלאפון לא תקין.</b>\n\nלדוגמה: <b>0547937503</b>"),
                parse_mode="HTML"
            )
            return

        data["phone"] = phone
        data["step"] = "city"
        await message.answer(
            rtl("<b>📍 יישוב למשלוח</b>\n\nבאיזה יישוב המשלוח?\nלדוגמה: <b>אשדוד</b>"),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "city":
        if len(txt) < 2 or has_digit(txt):
            await message.answer(rtl("<b>⚠️ נא לרשום שם יישוב תקין.</b>"), parse_mode="HTML")
            return

        delivery_price, base_city, status = get_delivery_price(txt)

        if status == "city_not_found":
            await message.answer(rtl("<b>⚠️ היישוב לא נמצא במאגר.</b>\nנא לרשום יישוב תקין."), parse_mode="HTML")
            return

        if status == "no_delivery_price":
            await message.answer(rtl("<b>⚠️ אין מחיר משלוח אוטומטי לאזור הזה.</b>\nפנה לשירות לקוחות."), parse_mode="HTML")
            return

        data["city"] = txt
        data["delivery_price"] = float(delivery_price)
        data["base_city"] = base_city
        data["step"] = "street"

        await message.answer(
            rtl(
                f"<b>🚚 דמי משלוח ל{h(txt)}:</b> {money(delivery_price)}\n\n"
                "<b>📍 כתובת למשלוח</b>\n"
                "רשום רחוב ומספר בית."
            ),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "street":
        if len(txt) < 5 or not has_digit(txt):
            await message.answer(rtl("<b>⚠️ נא לרשום רחוב + מספר בית.</b>"), parse_mode="HTML")
            return

        data["street"] = txt
        data["step"] = "floor"
        await message.answer(
            rtl("<b>🏢 קומה</b>\n\nאיזו קומה?\nאם זה קרקע, רשום <b>0</b>."),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "floor":
        if not txt.lstrip("-").isdigit():
            await message.answer(rtl("<b>⚠️ נא לרשום קומה במספרים בלבד.</b>"), parse_mode="HTML")
            return

        data["floor"] = txt
        data["step"] = "apartment"
        await message.answer(
            rtl("<b>🚪 דירה</b>\n\nמספר דירה?\nאם אין דירה, רשום <b>0</b>."),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "apartment":
        if not txt.isdigit():
            await message.answer(rtl("<b>⚠️ נא לרשום מספר דירה במספרים בלבד.</b>"), parse_mode="HTML")
            return

        data["apartment"] = txt
        data["step"] = "confirm"

        await message.answer(build_order_summary(data), reply_markup=confirm_keyboard(), parse_mode="HTML")
        return
