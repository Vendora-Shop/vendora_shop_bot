from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from html import escape

from config import ADMIN_ID
from keyboards import main_keyboard, my_orders_keyboard, addresses_menu_keyboard, address_select_keyboard, address_actions_keyboard, reorder_select_keyboard
from database import (
    get_active_products,
    get_product_by_name,
    reduce_stock,
    create_order,
    get_order_by_number,
    get_customer_profile,
    save_customer_profile,
    get_orders_by_customer_telegram_id,
    save_customer_address,
    get_customer_addresses,
    get_customer_address_by_id,
    delete_customer_address,
    create_support_ticket,
    add_support_message,
    get_open_support_ticket_by_user,
    close_support_ticket,
)
from delivery import get_delivery_price
from pdf_generator import create_invoice_pdf

router = Router()


# ================== SAVED ADDRESSES UI ==================
def format_address(address):
    return (
        f"{field('שם כתובת', address.get('label') or 'כתובת')}\n"
        f"{field('עיר / יישוב', address.get('city') or '-')}\n"
        f"{field('רחוב', address.get('street') or '-')}\n"
        f"{field('קומה', address.get('floor') or '-')}\n"
        f"{field('דירה', address.get('apartment') or '-')}"
    )


def address_profile_text(address):
    return rtl(
        "<b>🏠 פרטי כתובת</b>\n\n"
        f"{format_address(address)}"
    )


def extract_address_id_from_button(text):
    text = str(text or "").strip()

    if text.startswith("🏠 "):
        text = text.replace("🏠 ", "", 1)

    if "|" in text:
        value = text.split("|", 1)[0].strip()
    else:
        value = text.strip()

    if not value.isdigit():
        return None

    return int(value)


def apply_saved_address_to_order(data, address):
    data["city"] = address["city"]
    data["street"] = address["street"]
    data["floor"] = address.get("floor") or "0"
    data["apartment"] = address.get("apartment") or "0"

    delivery_price, base_city, status = get_delivery_price(address["city"])

    if status == "ok" and delivery_price is not None:
        data["delivery_price"] = float(delivery_price)
        data["base_city"] = base_city or address["city"]
        data["delivery_pending"] = False
    else:
        data["delivery_price"] = 0
        data["base_city"] = base_city or "לתיאום מול נציג"
        data["delivery_pending"] = True




# ================== CUSTOMER ORDERS / REORDER ==================

def translate_order_status(status):
    statuses = {
        "new": "🆕 חדשה",
        "approved": "✅ אושרה",
        "processing": "📦 בטיפול",
        "shipping": "🚚 בדרך",
        "done": "✅ הושלמה",
        "completed": "✅ הושלמה",
        "cancelled": "❌ בוטלה",
        "canceled": "❌ בוטלה"
    }

    return statuses.get(str(status or "").lower(), str(status or "-"))


def customer_order_short_text(order):
    return (
        f"<b>🧾 {h(order.get('order_number'))}</b>\n"
        f"{field('תאריך', order.get('created_at') or '-')}\n"
        f"{field('סטטוס', translate_order_status(order.get('status')))}\n"
        f"{field('סה״כ', money(order.get('final_total') or 0))}"
    )


def customer_orders_text(orders):
    if not orders:
        return rtl(
            "<b>📦 ההזמנות שלי</b>\n\n"
            "עדיין לא קיימות הזמנות בחשבון שלך."
        )

    text = "<b>📦 ההזמנות שלי</b>\n\n"
    text += "אלו ההזמנות האחרונות שלך:\n\n"

    for order in orders[:5]:
        text += customer_order_short_text(order) + "\n\n"

    text += "כדי לבצע הזמנה חוזרת, לחץ על 🔁 הזמן שוב."

    return rtl(text)




def extract_order_number_from_reorder_button(text):
    text = str(text or "").strip()

    if text.startswith("🔁 "):
        text = text.replace("🔁 ", "", 1)

    if "|" in text:
        return text.split("|", 1)[0].strip()

    return text.strip()


def reorder_orders_list_text(orders):
    if not orders:
        return rtl(
            "<b>🔁 הזמנה חוזרת</b>\n\n"
            "לא נמצאו הזמנות שניתן לשחזר."
        )

    text = (
        "<b>🔁 הזמנה חוזרת</b>\n\n"
        "בחר מהרשימה איזו הזמנה תרצה לשחזר לסל.\n\n"
    )

    for order in orders[:10]:
        text += (
            f"<b>🧾 {h(order.get('order_number'))}</b>\n"
            f"{field('תאריך', order.get('created_at') or '-')}\n"
            f"{field('סטטוס', translate_order_status(order.get('status')))}\n"
            f"{field('סה״כ', money(order.get('final_total') or 0))}\n\n"
        )

    return rtl(text)

def clone_cart_from_order(order):
    cloned_cart = []
    unavailable_products = []

    for item in order.get("cart", []):
        item_name = item.get("name")
        qty = int(item.get("qty", 1))

        if not item_name:
            continue

        product = get_product_by_name(item_name)

        if not product:
            unavailable_products.append(item_name)
            continue

        is_active = product.get("active", 1)

        if is_active in [0, "0", False, "false", "False", None]:
            unavailable_products.append(item_name)
            continue

        stock = int(product.get("stock", 0) or 0)

        if stock < qty:
            unavailable_products.append(item_name)
            continue

        cloned_cart.append({
            "name": product.get("name", item_name),
            "price": float(product.get("price", item.get("price", 0))),
            "qty": qty
        })

    return cloned_cart, unavailable_products



users = {}

RTL = "\u200F"


# ================== SAFE INPUT CLEANUP ==================
# מוחק קשקושים של לקוחות רק במקומות שבהם צריך לבחור מכפתורים.
# לא מוחק סיכומי הזמנה, PDF או הודעות מעקב.
async def delete_customer_message(message: Message):
    try:
        await message.delete()
    except Exception:
        pass


def is_button_only_step_for_customer(step):
    return step in {
        None,
        "start",
        "main",
        "browse_products",
        "product_select",
        "qty",
        "cart",
        "fulfillment_choice",
        "saved_profile_choice",
        "payment_simulation",
        "confirm",
        "my_orders",
        "reorder_select",
        "addresses_menu",
        "address_select",
        "address_profile",
    }


def is_free_text_step_for_customer(step):
    return step in {
        "name",
        "phone",
        "city",
        "street",
        "floor",
        "apartment",
        "qty_manual",
        "support",
        "support_phone",
        "support_chat",
        "add_address_label",
        "add_address_city",
        "add_address_street",
        "add_address_floor",
        "add_address_apartment",
    }


def is_customer_system_button(text):
    text = str(text or "").strip()
    return text in {
        "🛒 חנות",
        "🛒 הסל שלי",
        "📦 ההזמנות שלי",
        "🏠 הכתובות שלי",
        "👤 הפרטים שלי",
        "📞 שירות לקוחות",
        "⬅️ חזרה",
        "⬅️ חזרה לקטגוריות",
        "⬅️ חזרה לתפריט",
        "➕ הוסף עוד מוצר",
        "✅ המשך להזמנה",
        "🧹 רוקן סל",
        "❌ בטל הזמנה",
        "✅ הבעיה נפתרה",
        "✅ אשר הזמנה",
        "✏️ שנה פרטים",
        "🚚 משלוח עד הבית",
        "🛍️ איסוף עצמי מהחנות",
        "✅ המשך עם הפרטים השמורים",
        "✅ חזור לפרטים השמורים",
        "✏️ הזן פרטים חדשים",
        "✅ סימולציית תשלום הצליחה",
        "⬅️ חזרה לסיכום הזמנה",
        "❌ ביטול תשלום",
        "🔁 הזמן שוב",
        "⬅️ חזרה להזמנות שלי",
        "📋 הצג כתובות",
        "➕ הוסף כתובת",
        "🗑️ מחק כתובת",
        "⬅️ חזרה לכתובות",
        "⬅️ חזרה לרשימת כתובות",
    }


def is_valid_customer_product_or_category_text(text, products):
    text = str(text or "").strip()

    if text in products:
        return True

    for items in products.values():
        for product in items:
            if text == product.get("name"):
                return True

    return False



def should_warn_customer_once(user_id, key):
    data = users.setdefault(user_id, {"cart": []})
    warn_key = f"warned_{key}"

    if data.get(warn_key):
        return False

    data[warn_key] = True
    return True


# ================== PICKUP SETTINGS ==================
# כאן מגדירים את כל פרטי האיסוף העצמי.
# אם בעתיד תרצה לשנות כתובת / שעות / ניווט — משנים רק כאן.
PICKUP_POINT_NAME = "Vendora"
PICKUP_POINT_ADDRESS = "אשדוד - הבנאים 2"
PICKUP_PREP_TIME = "כ־30 דקות"
PICKUP_HOURS = "א׳-ה׳ 10:00-19:00, ו׳ 09:00-13:00"
PICKUP_NAVIGATION_URL = "https://waze.com/ul/hsv8su3vur"

PICKUP_CITY = "איסוף עצמי"
PICKUP_BASE_CITY = "איסוף עצמי"
# ================== STORE CONTACT SETTINGS ==================
# פרטים שיוצגו ללקוח במקרה של הזמנה בכמות גדולה.
# עדכן כאן את הטלפון ויוזר הטלגרם של החנות.
STORE_CONTACT_PHONE = "054-7937503"
STORE_CONTACT_TELEGRAM = "@Vendora"


#קעקרערעק

def h(text):
    return escape(str(text))


def rtl(text):
    return RTL + str(text)


def money(value):
    value = float(value)
    if value.is_integer():
        return f"{int(value)}₪"
    return f"{value:g}₪"


def field(label, value):
    return f"<b>{h(label)}:</b> {h(value)}"



def large_quantity_contact_text(max_qty):
    return rtl(
        "<b>⚠️ להזמנות בכמות גדולה יש ליצור קשר עם החנות.</b>\n\n"
        f"{field('כמות מקסימלית להזמנה רגילה', str(max_qty) + ' יחידות')}\n"
        f"{field('טלפון', STORE_CONTACT_PHONE)}\n"
        f"{field('Telegram', STORE_CONTACT_TELEGRAM)}"
    )




def admin_new_support_ticket_keyboard(ticket_number):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📩 פתח פנייה",
                    callback_data=f"support_ticket_reply:{ticket_number}"
                )
            ]
        ]
    )


def admin_support_ticket_keyboard(ticket_number):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ השב ללקוח", callback_data=f"support_ticket_reply:{ticket_number}"),
                InlineKeyboardButton(text="✅ סגור פנייה", callback_data=f"support_ticket_close:{ticket_number}")
            ]
        ]
    )


def admin_support_reply_keyboard(telegram_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="↩️ השב ללקוח",
                    callback_data=f"support_reply:{telegram_id}"
                )
            ]
        ]
    )


def admin_new_order_keyboard(order_number):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ אשר הזמנה", callback_data=f"order_action:approve:{order_number}"),
                InlineKeyboardButton(text="❌ בטל", callback_data=f"order_action:cancel:{order_number}")
            ]
        ]
    )


def categories_keyboard():
    products = get_active_products()

    open_support_ticket = get_open_support_ticket_by_user(uid)
    if open_support_ticket and txt not in {"🛒 חנות", "👤 הפרטים שלי", "📦 ההזמנות שלי", "🏠 הכתובות שלי", "📞 שירות לקוחות", "🔐 פאנל ניהול", "✅ הבעיה נפתרה"}:
        users[uid] = {
            "cart": [],
            "step": "support_chat",
            "support_ticket_number": open_support_ticket["ticket_number"],
            "support_phone": open_support_ticket["phone"]
        }
        data = users[uid]

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



def quantity_keyboard(selected_qty, available_left, max_qty):
    selected_qty = int(selected_qty)

    keyboard = [
        [
            KeyboardButton(text="➖ פחות"),
            KeyboardButton(text=f"כמות: {selected_qty}"),
            KeyboardButton(text="➕ יותר")
        ],
        [KeyboardButton(text="🛒 הוסף לסל")],
        [KeyboardButton(text="🛒 הסל שלי")],
        [KeyboardButton(text="⬅️ חזרה לקטגוריות")]
    ]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)



def quantity_inline_keyboard(selected_qty):
    selected_qty = int(selected_qty)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➖ פחות", callback_data="qty_action:minus"),
                InlineKeyboardButton(text=f"כמות: {selected_qty}", callback_data="qty_action:manual"),
                InlineKeyboardButton(text="➕ יותר", callback_data="qty_action:plus"),
            ],
            [
                InlineKeyboardButton(text="🛒 הוסף לסל", callback_data="qty_action:add")
            ]
        ]
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



def payment_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ סימולציית תשלום הצליחה")],
            [KeyboardButton(text="⬅️ חזרה לסיכום הזמנה")],
            [KeyboardButton(text="❌ ביטול תשלום")]
        ],
        resize_keyboard=True
    )


def use_saved_details_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ המשך עם הפרטים השמורים")],
            [KeyboardButton(text="✏️ הזן פרטים חדשים")],
            [KeyboardButton(text="❌ בטל הזמנה")]
        ],
        resize_keyboard=True
    )



def manual_details_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ חזור לפרטים השמורים")],
            [KeyboardButton(text="❌ בטל הזמנה")]
        ],
        resize_keyboard=True
    )



def support_customer_keyboard(user_id=None):
    keyboard = [
        [KeyboardButton(text="✅ הבעיה נפתרה")]
    ]

    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])
        keyboard.append([KeyboardButton(text="🔐 פאנל ניהול")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def fulfillment_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚚 משלוח עד הבית")],
            [KeyboardButton(text="🛍️ איסוף עצמי מהחנות")],
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


def grouped_cart(cart):
    grouped = {}

    for item in cart:
        name = item["name"]
        if name not in grouped:
            grouped[name] = {
                "name": item["name"],
                "price": float(item["price"]),
                "qty": 0
            }

        grouped[name]["qty"] += int(item["qty"])

    return list(grouped.values())


def cart_text(cart, title="🛒 הסל שלך"):
    if not cart:
        return rtl(f"<b>{title}</b>\n\nהסל שלך ריק כרגע.")

    items = grouped_cart(cart)

    total_units = sum(int(item["qty"]) for item in items)
    total_price = sum(float(item["price"]) * int(item["qty"]) for item in items)

    text = f"<b>{title}</b>\n\n"

    for index, item in enumerate(items, start=1):
        item_total = float(item["price"]) * int(item["qty"])

        text += (
            f"<b>{index}. {h(item['name'])}</b>\n"
            f"<b>כמות:</b> {int(item['qty'])}\n"
            f"<b>סה״כ מוצר:</b> {money(item_total)}\n\n"
        )

    text += (
        f"<b>📦 כמות מוצרים בסל:</b> {total_units}\n"
        f"<b>💰 סה״כ לפני משלוח:</b> {money(total_price)}"
    )

    return rtl(text)


def saved_profile_text(profile):
    address = f"{profile['city']}, {profile['street']}, קומה {profile['floor']}, דירה {profile['apartment']}"

    text = (
        "<b>👤 הפרטים השמורים שלך</b>\n\n"
        f"{field('שם', profile['customer_name'])}\n"
        f"{field('טלפון', profile['phone'])}\n"
        f"{field('כתובת', address)}\n\n"
        f"{field('הזמנות קודמות', profile['total_orders'])}\n"
        f"{field('סה״כ קניות', money(profile['total_spent']))}"
    )

    return rtl(text)


async def send_product_card(message: Message, product):
    stock = int(product.get("stock", 0))

    if stock <= 0:
        stock_text = "<b>🔴 אזל מהמלאי</b>"
    else:
        stock_text = "<b>🟢 במלאי</b>"

    caption = rtl(
        f"<b>🛍️ {h(product['name'])}</b>\n\n"
        f"{h(product.get('description', ''))}\n\n"
        f"<b>מחיר:</b> {money(product['price'])}\n\n"
        f"{stock_text}"
    )

    image = product.get("image_file_id")

    if image:
        await message.answer_photo(photo=image, caption=caption, parse_mode="HTML")
    else:
        await message.answer(caption, parse_mode="HTML")


def set_pickup_details(data):
    data["fulfillment_type"] = "pickup"
    data["city"] = PICKUP_CITY
    data["street"] = PICKUP_POINT_ADDRESS
    data["floor"] = "0"
    data["apartment"] = "0"
    data["delivery_price"] = 0
    data["base_city"] = PICKUP_BASE_CITY
    data["delivery_pending"] = False


def is_pickup_order(data):
    return data.get("fulfillment_type") == "pickup"


def pickup_navigation_keyboard():
    if not PICKUP_NAVIGATION_URL:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 נווט עם Waze",
                    url=PICKUP_NAVIGATION_URL
                )
            ]
        ]
    )


def pickup_text():
    navigation_line = ""

    if PICKUP_NAVIGATION_URL:
        navigation_line = f'\n📍 <a href="{h(PICKUP_NAVIGATION_URL)}">פתח ניווט עם Waze</a>'

    return (
        "<b>🛍️ איסוף עצמי מהחנות</b>\n\n"
        f"{field('נקודת איסוף', PICKUP_POINT_NAME)}\n"
        f"{field('כתובת', PICKUP_POINT_ADDRESS)}\n"
        f"{field('שעות איסוף', PICKUP_HOURS)}\n"
        f"{field('זמן הכנה משוער', PICKUP_PREP_TIME)}"
        f"{navigation_line}"
    )


def order_summary_keyboard(data):
    return confirm_keyboard()


async def send_pickup_navigation_if_needed(message, data):
    # הניווט מוצג בתוך סיכום ההזמנה עצמו,
    # לכן לא שולחים הודעה נפרדת כדי לא לבלבל את הלקוח.
    return




def build_order_summary(data):
    products_total = cart_total(data["cart"])
    delivery_price = float(data["delivery_price"])
    final_total = products_total + delivery_price

    if is_pickup_order(data):
        delivery_block = (
            f"{pickup_text()}\n\n"
            f"{field('דמי משלוח', money(0))}\n"
            f"{field('סה״כ לתשלום', money(products_total))}"
        )
    else:
        address = f"{data['city']}, {data['street']}, קומה {data['floor']}, דירה {data['apartment']}"
        delivery_block = (
            "<b>🚚 משלוח עד הבית</b>\n\n"
            f"{field('כתובת', address)}\n"
            f"{field('אזור משלוח', data['base_city'])}\n\n"
            f"{field('דמי משלוח', money(delivery_price))}\n"
            f"{field('סה״כ לתשלום', money(final_total))}"
        )

    text = (
        "<b>📦 סיכום הזמנה</b>\n\n"
        f"{field('שם לקוח', data['name'])}\n"
        f"{field('טלפון', data['phone'])}\n\n"
        f"{cart_text(data['cart']).replace(RTL, '')}\n\n"
        f"{delivery_block}\n\n"
        "<b>✅ אם הכול נכון לחץ על אשר הזמנה.</b>"
    )

    return rtl(text)

def fill_saved_profile_into_data(data, profile):
    data["name"] = profile["customer_name"]
    data["phone"] = profile["phone"]
    data["city"] = profile["city"]
    data["street"] = profile["street"]
    data["floor"] = profile["floor"]
    data["apartment"] = profile["apartment"]

    delivery_price, base_city, status = get_delivery_price(profile["city"])

    if status == "city_not_found" or status == "no_delivery_price":
        return False

    data["delivery_price"] = float(delivery_price)
    data["base_city"] = base_city
    return True




async def use_saved_profile_flow(message: Message, data):
    profile = get_customer_profile(message.from_user.id)

    if not profile:
        await message.answer(
            rtl(
                "<b>⚠️ אין פרטים שמורים.</b>\n\n"
                "יש להזין פרטים חדשים כדי להמשיך."
            ),
            parse_mode="HTML"
        )
        data["step"] = "name"
        await message.answer(
            rtl("<b>📝 פרטי הזמנה חדשים</b>\n\nרשום את השם המלא שלך:"),
            reply_markup=manual_details_keyboard(),
            parse_mode="HTML"
        )
        return

    ok = fill_saved_profile_into_data(data, profile)

    if not ok:
        await message.answer(
            rtl(
                "<b>⚠️ לא ניתן לחשב משלוח לפי הפרטים השמורים.</b>\n\n"
                "יש להזין פרטים חדשים כדי להמשיך."
            ),
            parse_mode="HTML"
        )
        data["step"] = "name"
        await message.answer(
            rtl("<b>📝 פרטי הזמנה חדשים</b>\n\nרשום את השם המלא שלך:"),
            reply_markup=manual_details_keyboard(),
            parse_mode="HTML"
        )
        return

    data["step"] = "confirm"

    await message.answer(
        build_order_summary(data),
        reply_markup=order_summary_keyboard(data),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    await send_pickup_navigation_if_needed(message, data)



@router.message(CommandStart())
async def start(message: Message):
    users.pop(message.from_user.id, None)
    users[message.from_user.id] = {
        "cart": [],
        "step": "start"
    }

    customer_name = message.from_user.first_name or "לקוח יקר"

    await message.answer(
        rtl(f"<b>👋 ברוך הבא {h(customer_name)}</b>"),
        reply_markup=main_keyboard(message.from_user.id),
        parse_mode="HTML"
    )


@router.message(F.text == "👤 הפרטים שלי")
async def my_details(message: Message):
    uid = message.from_user.id
    profile = get_customer_profile(uid)

    if not profile:
        await message.answer(
            rtl(
                "<b>👤 הפרטים שלי</b>\n\n"
                "אין פרטים שמורים עדיין.\n"
                "אחרי ההזמנה הראשונה, הבוט ישמור את הפרטים שלך להזמנות הבאות."
            ),
            reply_markup=main_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        return

    await message.answer(saved_profile_text(profile), reply_markup=main_keyboard(message.from_user.id), parse_mode="HTML")


@router.message(F.text == "🛒 חנות")
async def shop(message: Message):
    uid = message.from_user.id

    if uid not in users:
        users[uid] = {"cart": []}

    users[uid]["step"] = "browse_products"

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


@router.message(F.text == "⬅️ חזרה לניהול")
async def back_to_admin_panel_from_shop(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    users.pop(message.from_user.id, None)

    from keyboards import admin_keyboard

    await message.answer(
        rtl("<b>🔐 חזרת לפאנל הניהול.</b>"),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ חזרה")
async def back_main(message: Message):
    users.pop(message.from_user.id, None)

    if message.from_user.id == ADMIN_ID:
        from keyboards import admin_keyboard

        await message.answer(
            rtl("<b>↩️ חזרת לתפריט הראשי</b>"),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    if message.from_user.id == ADMIN_ID:
        from keyboards import admin_keyboard
        await message.answer(
            rtl("<b>↩️ חזרת לתפריט הראשי</b>"),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            rtl("<b>↩️ חזרת לתפריט הראשי</b>"),
            reply_markup=main_keyboard(message.from_user.id),
            parse_mode="HTML"
        )


@router.message(F.text == "⬅️ חזרה לקטגוריות")
async def back_categories(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})
    users[uid]["step"] = "browse_products"
    await message.answer(
        rtl("<b>📂 קטגוריות</b>\n\nבחר קטגוריה:"),
        reply_markup=categories_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "➕ הוסף עוד מוצר")
async def add_more(message: Message):
    uid = message.from_user.id
    users.setdefault(uid, {"cart": [], "step": None})
    users[uid]["step"] = "browse_products"
    await message.answer(
        rtl("<b>➕ הוספת מוצר</b>\n\nבחר קטגוריה:"),
        reply_markup=categories_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🛒 הסל שלי")
async def show_cart(message: Message):
    uid = message.from_user.id
    data = users.setdefault(uid, {"cart": [], "step": None})
    await message.answer(
        cart_text(data["cart"]),
        reply_markup=cart_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🧹 רוקן סל")
async def clear_cart(message: Message):
    uid = message.from_user.id
    data = users.get(uid)

    if not data or not data.get("cart"):
        users[uid] = {"cart": [], "step": "browse_products"}
        await message.answer(
            rtl("<b>🛒 הסל שלך כבר ריק.</b>"),
            reply_markup=categories_keyboard(),
            parse_mode="HTML"
        )
        return

    users[uid] = {"cart": [], "step": "browse_products"}
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
        reply_markup=main_keyboard(message.from_user.id),
        parse_mode="HTML"
    )


@router.message(F.text == "✏️ שנה פרטים")
async def edit_details(message: Message):
    uid = message.from_user.id
    data = users.get(uid)

    if not data or not data.get("cart"):
        await message.answer(
            rtl("<b>⚠️ אין הזמנה פעילה.</b>"),
            reply_markup=main_keyboard(message.from_user.id),
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

    data["step"] = "fulfillment_choice"
    data["saved_profile"] = get_customer_profile(uid)

    await message.answer(
        rtl(
            "<b>📦 איך תרצה לקבל את ההזמנה?</b>\n\n"
            "בחר אחת מהאפשרויות:"
        ),
        reply_markup=fulfillment_keyboard(),
        parse_mode="HTML"
    )

async def submit_paid_order(message: Message, data):
    uid = message.from_user.id

    if data.get("order_submitting"):
        await message.answer(
            rtl(
                "<b>⚠️ הפעולה כבר בוצעה</b>\n\n"
                "ההזמנה כבר נקלטה במערכת ונמצאת בטיפול."
            ),
            reply_markup=main_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        return

    data["order_submitting"] = True

    stock_ok, problem_product = reduce_stock(data["cart"])

    if not stock_ok:
        data.pop("order_submitting", None)
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

    profile_for_save = get_customer_profile(uid)

    if is_pickup_order(data) and profile_for_save:
        save_city = profile_for_save.get("city") or data["city"]
        save_street = profile_for_save.get("street") or data["street"]
        save_floor = profile_for_save.get("floor") or data["floor"]
        save_apartment = profile_for_save.get("apartment") or data["apartment"]
    else:
        save_city = data["city"]
        save_street = data["street"]
        save_floor = data["floor"]
        save_apartment = data["apartment"]

    save_customer_profile(
        telegram_id=uid,
        telegram_name=message.from_user.full_name,
        customer_name=data["name"],
        phone=data["phone"],
        city=save_city,
        street=save_street,
        floor=save_floor,
        apartment=save_apartment,
        last_order_number=order_number,
        order_total=final_total
    )

    if is_pickup_order(data):
        fulfillment_admin_text = (
            "<b>🛍️ איסוף עצמי מהחנות</b>\n\n"
            f"{field('נקודת איסוף', PICKUP_POINT_NAME)}\n"
            f"{field('כתובת', PICKUP_POINT_ADDRESS)}\n"
            f"{field('שעות איסוף', PICKUP_HOURS)}\n"
            f"{field('זמן הכנה משוער', PICKUP_PREP_TIME)}\n"
        )
    else:
        address = f"{data['city']}, {data['street']}, קומה {data['floor']}, דירה {data['apartment']}"
        fulfillment_admin_text = (
            f"{field('שיטת קבלה', 'משלוח עד הבית')}\n"
            f"{field('כתובת משלוח', address)}\n"
            f"{field('אזור משלוח', data['base_city'])}"
        )

    admin_order = rtl(
        f"<b>📦 הזמנה חדשה מ־Vendora Shop</b>\n\n"
        f"{field('מספר הזמנה', order_number)}\n\n"
        f"{field('שם לקוח', data['name'])}\n"
        f"{field('טלפון', data['phone'])}\n"
        f"{fulfillment_admin_text}\n"
        f"{cart_text(data['cart']).replace(RTL, '')}\n\n"
        f"{field('משלוח', money(delivery_price))}\n"
        f"{field('סה״כ שולם', money(final_total))}\n\n"
        f"{field('Telegram ID', uid)}\n"
        f"{field('Telegram', message.from_user.full_name)}\n\n"
        f"<b>סטטוס:</b> 🆕 הזמנה חדשה"
    )

    await message.bot.send_message(
        ADMIN_ID,
        admin_order,
        reply_markup=admin_new_order_keyboard(order_number),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    saved_order = get_order_by_number(order_number)
    if saved_order:
        try:
            pdf_path = create_invoice_pdf(saved_order)
            await message.answer_document(
                FSInputFile(pdf_path),
                caption=rtl(f"📄 <b>סיכום הזמנה</b> {h(order_number)}"),
                parse_mode="HTML"
            )
        except Exception:
            await message.answer(
                rtl("<b>⚠️ ההזמנה נשמרה, אבל לא הצלחתי ליצור PDF כרגע.</b>"),
                parse_mode="HTML"
            )

    users.pop(uid, None)

    if is_pickup_order(data):
        customer_success_text = (
            "<b>✅ ההזמנה התקבלה בהצלחה!</b>\n\n"
            "<b>🛍️ איסוף עצמי</b>\n\n"
            "ברגע שההזמנה תהיה מוכנה, "
            "תישלח אליך הודעה אוטומטית לאיסוף.\n\n"
            f"{field('מספר הזמנה', order_number)}"
        )
    else:
        customer_success_text = (
            "<b>✅ ההזמנה התקבלה בהצלחה!</b>\n\n"
            "<b>🚚 משלוח</b>\n\n"
            "ברגע שההזמנה תאושר ותצא למשלוח, "
            "תישלח אליך הודעה אוטומטית.\n\n"
            f"{field('מספר הזמנה', order_number)}"
        )

    await message.answer(
        rtl(customer_success_text),
        reply_markup=main_keyboard(message.from_user.id),
        parse_mode="HTML"
    )


@router.message(F.text == "✅ אשר הזמנה")
async def confirm_order(message: Message):
    uid = message.from_user.id
    data = users.get(uid)

    if not data or not data.get("cart"):
        await message.answer(
            rtl("<b>⚠️ אין הזמנה פעילה.</b>"),
            reply_markup=main_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        return

    required = ["name", "phone", "city", "street", "floor", "apartment", "delivery_price", "base_city", "fulfillment_type"]
    if any(key not in data for key in required):
        data["step"] = "name"
        await message.answer(
            rtl("<b>⚠️ חסרים פרטים להזמנה.</b>\n\nנרשום מחדש את הפרטים.\nמה השם המלא שלך?"),
            parse_mode="HTML"
        )
        return

    if data.get("order_submitting"):
        await message.answer(
            rtl(
                "<b>⚠️ הפעולה כבר בוצעה</b>\n\n"
                "ההזמנה כבר נקלטה במערכת ונמצאת בטיפול."
            ),
            reply_markup=main_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        return

    products_total = cart_total(data["cart"])
    delivery_price = float(data["delivery_price"])
    final_total = products_total + delivery_price

    data["step"] = "payment_simulation"

    order_type_text = "🛍️ איסוף עצמי" if is_pickup_order(data) else "🚚 משלוח עד הבית"

    await message.answer(
        rtl(
            "<b>💳 תשלום הזמנה</b>\n\n"
            f"{field('סוג הזמנה', order_type_text)}\n"
            f"{field('סה״כ לתשלום', money(final_total))}\n\n"
            "<b>מצב בדיקות:</b>\n"
            "לחץ על ✅ סימולציית תשלום הצליחה כדי להמשיך.\n\n"
            "בעתיד הכפתור הזה יוחלף בסליקה אמיתית."
        ),
        reply_markup=payment_keyboard(),
        parse_mode="HTML"
    )



@router.callback_query(F.data.startswith("qty_action:"))
async def quantity_inline_action(callback: CallbackQuery):
    uid = callback.from_user.id
    data = users.get(uid)

    if not data or data.get("step") not in {"qty", "qty_manual"} or not data.get("selected_product"):
        await callback.answer("אין מוצר פעיל לבחירת כמות.", show_alert=True)
        return

    data["step"] = "qty"

    action = (callback.data or "").split(":", 1)[1]
    product = data.get("selected_product")

    fresh_product = get_product_by_name(product["name"])
    if not fresh_product or int(fresh_product.get("active", 0)) != 1:
        data["step"] = None
        data.pop("selected_product", None)
        data.pop("selected_qty", None)
        await callback.answer("המוצר לא זמין כרגע.", show_alert=True)
        return

    product.update(fresh_product)

    max_qty = int(fresh_product.get("max_qty", 100))
    stock = int(fresh_product.get("stock", 0))
    already_in_cart = product_qty_in_cart(data["cart"], product["name"])
    available_left = stock - already_in_cart
    selected_qty = int(data.get("selected_qty", 1))

    if available_left <= 0:
        data["step"] = None
        data.pop("selected_product", None)
        data.pop("selected_qty", None)
        await callback.message.answer(
            rtl("<b>📦 כל המלאי הזמין של המוצר כבר נמצא אצלך בסל.</b>"),
            reply_markup=cart_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    max_allowed_now = min(available_left, max_qty)

    if selected_qty > max_allowed_now:
        selected_qty = max_allowed_now
        data["selected_qty"] = selected_qty

    if action == "plus":
        requested_qty = selected_qty + 1

        if requested_qty > max_allowed_now:
            if max_qty <= available_left and selected_qty >= max_qty:
                await callback.message.answer(
                    large_quantity_contact_text(max_qty),
                    parse_mode="HTML"
                )
            else:
                await callback.answer("לא ניתן לבחור כמות מעבר למלאי הזמין.", show_alert=True)
            return

        selected_qty = requested_qty
        data["selected_qty"] = selected_qty

        await callback.message.edit_text(
            rtl(
                "<b>🔢 בחירת כמות</b>\n\n"
                f"{field('כמות נבחרת', selected_qty)}\n\n"
                "בחר את הכמות הרצויה להזמנה.\n"
                "אפשר לשנות את הכמות באמצעות ➖ פחות או ➕ יותר.\n"
                "רק לאחר בחירת הכמות ולחיצה על 🛒 הוסף לסל,\n"
                "המוצרים יתווספו לסל ותוכל להמשיך."
            ),
            reply_markup=quantity_inline_keyboard(selected_qty),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    if action == "minus":
        if selected_qty > 1:
            selected_qty -= 1

        data["selected_qty"] = selected_qty

        await callback.message.edit_text(
            rtl(
                "<b>🔢 בחירת כמות</b>\n\n"
                f"{field('כמות נבחרת', selected_qty)}\n\n"
                "בחר את הכמות הרצויה להזמנה.\n"
                "אפשר לשנות את הכמות באמצעות ➖ פחות או ➕ יותר.\n"
                "רק לאחר בחירת הכמות ולחיצה על 🛒 הוסף לסל,\n"
                "המוצרים יתווספו לסל ותוכל להמשיך למשלוח או לאיסוף."
            ),
            reply_markup=quantity_inline_keyboard(selected_qty),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    if action == "manual":
        data["step"] = "qty_manual"
        await callback.message.answer(
            rtl(
                "<b>✏️ הזנת כמות</b>\n\n"
                "רשום את הכמות הרצויה במספרים בלבד."
            ),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    if action == "add":
        qty = selected_qty

        if qty <= 0:
            await callback.answer("הכמות חייבת להיות גדולה מ־0.", show_alert=True)
            return

        if qty > max_qty:
            await callback.message.answer(
                large_quantity_contact_text(max_qty),
                parse_mode="HTML"
            )
            return

        if qty > available_left:
            await callback.answer("לא ניתן לבחור כמות מעבר למלאי הזמין.", show_alert=True)
            return

        data["cart"].append({
            "name": fresh_product["name"],
            "price": float(fresh_product["price"]),
            "qty": qty
        })

        data["step"] = None
        data.pop("selected_product", None)
        data.pop("selected_qty", None)

        await callback.message.answer(
            cart_text(data["cart"], title="✅ נוסף לסל"),
            reply_markup=cart_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("המוצר נוסף לסל.")
        return

    await callback.answer("פעולה לא תקינה.", show_alert=True)


@router.message(F.text == "📞 שירות לקוחות")
async def support(message: Message):
    uid = message.from_user.id

    existing_ticket = get_open_support_ticket_by_user(uid)

    if existing_ticket:
        users[uid] = {
            "cart": [],
            "step": "support_chat",
            "support_ticket_number": existing_ticket["ticket_number"],
            "support_phone": existing_ticket["phone"]
        }

        await message.answer(
            rtl(
                "<b>📞 שירות לקוחות</b>\n\n"
                f"{field('מספר פנייה', existing_ticket['ticket_number'])}\n"
                "יש לך פנייה פתוחה. כתוב את ההודעה שלך כאן והיא תועבר לנציג."
            ),
            reply_markup=support_customer_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        return

    users[uid] = {
        "cart": [],
        "step": "support_phone"
    }

    await message.answer(
        rtl(
            "<b>📞 שירות לקוחות</b>\n\n"
            "כדי לפתוח פנייה לשירות לקוחות, רשום מספר פלאפון תקין.\n"
            "לדוגמה: 0547937503"
        ),
        reply_markup=support_customer_keyboard(message.from_user.id),
        parse_mode="HTML"
    )

@router.message(F.text == "📦 ההזמנות שלי")
async def my_orders(message: Message):
    uid = message.from_user.id

    if uid not in users:
        users[uid] = {"cart": []}

    orders = get_orders_by_customer_telegram_id(uid, 10)

    if orders:
        users[uid]["last_order_number"] = orders[0].get("order_number")

    users[uid]["step"] = "my_orders"

    await message.answer(
        customer_orders_text(orders),
        reply_markup=my_orders_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🔁 הזמן שוב")
async def reorder_choose_order(message: Message):
    uid = message.from_user.id

    if uid not in users:
        users[uid] = {"cart": []}

    orders = get_orders_by_customer_telegram_id(uid, 10)

    if not orders:
        await message.answer(
            rtl(
                "<b>⚠️ אין הזמנות קודמות לשחזור.</b>\n\n"
                "אפשר להיכנס לחנות ולבצע הזמנה חדשה."
            ),
            reply_markup=main_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        return

    users[uid]["step"] = "reorder_select"

    await message.answer(
        reorder_orders_list_text(orders),
        reply_markup=reorder_select_keyboard(orders),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ חזרה לתפריט")
async def back_to_main_menu(message: Message):
    uid = message.from_user.id

    if uid not in users:
        users[uid] = {"cart": []}

    users[uid]["step"] = "main"

    if uid == ADMIN_ID:
        from keyboards import admin_keyboard

        await message.answer(
            rtl("<b>🏠 תפריט ראשי</b>\n\nבחר פעולה מהתפריט למטה."),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    await message.answer(
        rtl("<b>🏠 תפריט ראשי</b>\n\nבחר פעולה מהתפריט למטה."),
        reply_markup=main_keyboard(message.from_user.id),
        parse_mode="HTML"
    )



@router.message(F.text == "🏠 הכתובות שלי")
async def my_addresses(message: Message):
    uid = message.from_user.id

    if uid not in users:
        users[uid] = {"cart": []}

    users[uid]["step"] = "addresses_menu"

    await message.answer(
        rtl("<b>🏠 הכתובות שלי</b>\n\nבחר פעולה מהתפריט."),
        reply_markup=addresses_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "📋 הצג כתובות")
async def show_my_addresses(message: Message):
    uid = message.from_user.id

    addresses = get_customer_addresses(uid, 10)

    if not addresses:
        await message.answer(
            rtl(
                "<b>🏠 הכתובות שלי</b>\n\n"
                "לא שמורות עדיין כתובות בחשבון שלך."
            ),
            reply_markup=addresses_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    users.setdefault(uid, {"cart": []})
    users[uid]["step"] = "address_select"

    await message.answer(
        rtl(
            "<b>🏠 הכתובות שלי</b>\n\n"
            "בחר כתובת מהרשימה כדי לצפות בפרטים."
        ),
        reply_markup=address_select_keyboard(addresses),
        parse_mode="HTML"
    )


@router.message(F.text == "➕ הוסף כתובת")
async def add_address_start(message: Message):
    uid = message.from_user.id

    users.setdefault(uid, {"cart": []})
    users[uid]["step"] = "add_address_label"
    users[uid]["new_address"] = {}

    await message.answer(
        rtl(
            "<b>➕ הוספת כתובת חדשה</b>\n\n"
            "רשום שם לכתובת.\n"
            "לדוגמה: בית / עבודה / הורים"
        ),
        parse_mode="HTML"
    )

@router.message()
async def handle_shop(message: Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    data = users.get(uid)

    products = get_active_products()

    if txt in {"✅ המשך עם הפרטים השמורים", "✅ חזור לפרטים השמורים"} and data and data.get("cart"):
        await use_saved_profile_flow(message, data)
        return

    if data:
        step = data.get("step")
        if not is_free_text_step_for_customer(step):
            if is_customer_system_button(txt):
                pass
            elif step in {"browse_products", "product_select", None, "start", "main"} and is_valid_customer_product_or_category_text(txt, products):
                pass
            else:
                await delete_customer_message(message)
                return

    if not data and not is_customer_system_button(txt) and not is_valid_customer_product_or_category_text(txt, products):
        await delete_customer_message(message)
        return

    if txt in products:
        users.setdefault(uid, {"cart": [], "step": None})
        users[uid]["step"] = "product_select"
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

        stock = int(product.get("stock", 0))

        if stock <= 0:
            data["step"] = None
            data.pop("selected_product", None)

            await message.answer(
                rtl(
                    "<b>❌ המוצר אזל מהמלאי כרגע.</b>\n\n"
                    "בחר מוצר אחר מהקטגוריות."
                ),
                reply_markup=categories_keyboard(),
                parse_mode="HTML"
            )
            return

        already_in_cart = product_qty_in_cart(data["cart"], product["name"])
        available_left = stock - already_in_cart

        if available_left <= 0:
            data["step"] = None
            data.pop("selected_product", None)

            await message.answer(
                rtl(
                    "<b>📦 כל המלאי הזמין של המוצר כבר נמצא אצלך בסל.</b>\n\n"
                    "אפשר להמשיך להזמנה או לבחור מוצר אחר."
                ),
                reply_markup=cart_keyboard(),
                parse_mode="HTML"
            )
            return

        await send_product_card(message, product)

        data["selected_product"] = product
        data["step"] = "qty"

        data["selected_qty"] = 1

        await message.answer(
            rtl(
                "<b>🔢 בחירת כמות</b>\n\n"
                f"{field('כמות נבחרת', data['selected_qty'])}\n\n"
                "בחר את הכמות הרצויה להזמנה.\n"
                "אפשר לשנות את הכמות באמצעות ➖ פחות או ➕ יותר.\n"
                "רק לאחר בחירת הכמות ולחיצה על 🛒 הוסף לסל,\n"
                "המוצרים יתווספו לסל ותוכל להמשיך למשלוח או לאיסוף."
            ),
            reply_markup=quantity_inline_keyboard(data["selected_qty"]),
            parse_mode="HTML"
        )
        return

    if not data:
        return

    if data.get("step") == "payment_simulation":
        if txt == "✅ סימולציית תשלום הצליחה":
            await submit_paid_order(message, data)
            return

        if txt == "⬅️ חזרה לסיכום הזמנה":
            data["step"] = "confirm"
            await message.answer(
                build_order_summary(data),
                reply_markup=order_summary_keyboard(data),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return

        if txt == "❌ ביטול תשלום":
            data["step"] = "confirm"
            await message.answer(
                rtl("<b>❌ התשלום בוטל.</b>\n\nאפשר לחזור לסיכום ההזמנה או לבטל את ההזמנה."),
                reply_markup=confirm_keyboard(),
                parse_mode="HTML"
            )
            return

        await message.answer(
            rtl("<b>⚠️ בחר פעולה מתוך כפתורי התשלום בלבד.</b>"),
            reply_markup=payment_keyboard(),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "fulfillment_choice":
        if txt == "🚚 משלוח עד הבית":
            data["fulfillment_type"] = "delivery"
            profile = data.get("saved_profile") or get_customer_profile(uid)

            if profile and profile.get("customer_name") and profile.get("phone") and profile.get("city"):
                data["saved_profile"] = profile
                data["step"] = "saved_profile_choice"

                await message.answer(
                    saved_profile_text(profile),
                    reply_markup=use_saved_details_keyboard(),
                    parse_mode="HTML"
                )
                return

            data["step"] = "name"
            await message.answer(
                rtl("<b>📝 פרטי הזמנה</b>\n\nרשום את השם המלא שלך:"),
                parse_mode="HTML"
            )
            return

        if txt == "🛍️ איסוף עצמי מהחנות":
            data["fulfillment_type"] = "pickup"
            set_pickup_details(data)

            profile = data.get("saved_profile") or get_customer_profile(uid)

            if profile and profile.get("customer_name") and profile.get("phone"):
                data["name"] = profile["customer_name"]
                data["phone"] = profile["phone"]
                data["step"] = "confirm"

                await message.answer(
                    build_order_summary(data),
                    reply_markup=order_summary_keyboard(data),
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                await send_pickup_navigation_if_needed(message, data)
                return

            data["step"] = "name"
            await message.answer(
                rtl(
                    f"{pickup_text()}\n\n"
                    "<b>📝 פרטי לקוח</b>\n"
                    "רשום את השם המלא שלך:"
                ),
                parse_mode="HTML"
            )
            return

        await message.answer(
            rtl("<b>⚠️ בחר אפשרות מתוך הכפתורים בלבד.</b>"),
            reply_markup=fulfillment_keyboard(),
            parse_mode="HTML"
        )
        return



    if data.get("step") == "reorder_select":
        if txt == "⬅️ חזרה להזמנות שלי":
            orders = get_orders_by_customer_telegram_id(uid, 10)

            await message.answer(
                customer_orders_text(orders),
                reply_markup=my_orders_keyboard(),
                parse_mode="HTML"
            )
            data["step"] = "my_orders"
            return

        order_number = extract_order_number_from_reorder_button(txt)

        if not order_number:
            await message.answer(
                rtl("<b>⚠️ בחר הזמנה מתוך הרשימה בלבד.</b>"),
                parse_mode="HTML"
            )
            return

        order = get_order_by_number(order_number)

        if not order or int(order.get("telegram_id") or 0) != uid:
            await message.answer(
                rtl("<b>⚠️ ההזמנה לא נמצאה או אינה שייכת לחשבון שלך.</b>"),
                parse_mode="HTML"
            )
            return

        cloned_cart, unavailable_products = clone_cart_from_order(order)

        if not cloned_cart:
            await message.answer(
                rtl("<b>⚠️ המוצר שבחרת אזל מהמלאי.</b>"),
                parse_mode="HTML"
            )
            return

        users[uid]["cart"] = cloned_cart
        users[uid]["step"] = "cart"

        if unavailable_products:
            await message.answer(
                rtl("<b>⚠️ חלק מהמוצרים אזלו מהמלאי ולא נוספו לסל.</b>"),
                parse_mode="HTML"
            )

        await message.answer(
            rtl(
                "<b>✅ ההזמנה שוחזרה לסל</b>\n\n"
                f"{field('שוחזר מהזמנה', order_number)}\n\n"
                "המוצרים הזמינים נוספו לסל הקניות שלך.\n"
                "לאחר אישור ההזמנה ייווצר מספר הזמנה חדש."
            ),
            reply_markup=cart_keyboard(),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "address_select":
        if txt == "⬅️ חזרה לכתובות":
            data["step"] = "addresses_menu"
            await message.answer(
                rtl("<b>🏠 הכתובות שלי</b>\n\nבחר פעולה מהתפריט."),
                reply_markup=addresses_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        address_id = extract_address_id_from_button(txt)

        if not address_id:
            await delete_customer_message(message)
            return

        address = get_customer_address_by_id(uid, address_id)

        if not address:
            await message.answer(
                rtl("<b>⚠️ הכתובת לא נמצאה.</b>"),
                reply_markup=addresses_menu_keyboard(),
                parse_mode="HTML"
            )
            data["step"] = "addresses_menu"
            return

        data["step"] = "address_profile"
        data["selected_address_id"] = address_id

        await message.answer(
            address_profile_text(address),
            reply_markup=address_actions_keyboard(),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "address_profile":
        if txt == "⬅️ חזרה לרשימת כתובות":
            addresses = get_customer_addresses(uid, 10)
            data["step"] = "address_select"

            await message.answer(
                rtl("<b>🏠 הכתובות שלי</b>\n\nבחר כתובת מהרשימה."),
                reply_markup=address_select_keyboard(addresses),
                parse_mode="HTML"
            )
            return

        if txt == "🗑️ מחק כתובת":
            address_id = data.get("selected_address_id")
            ok = delete_customer_address(uid, address_id)

            data["step"] = "addresses_menu"

            await message.answer(
                rtl(
                    "<b>✅ הכתובת נמחקה</b>"
                    if ok else
                    "<b>⚠️ לא הצלחתי למחוק את הכתובת.</b>"
                ),
                reply_markup=addresses_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        await delete_customer_message(message)
        return

    if data.get("step") == "add_address_label":
        label = txt.strip()

        if len(label) < 2:
            await message.answer(
                rtl("<b>⚠️ שם כתובת קצר מדי.</b>\nרשום לפחות 2 תווים."),
                parse_mode="HTML"
            )
            return

        data["new_address"]["label"] = label
        data["step"] = "add_address_city"

        await message.answer(
            rtl("<b>📍 עיר / יישוב</b>\n\nרשום את שם העיר או היישוב."),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "add_address_city":
        city = txt.strip()

        if len(city) < 2:
            await message.answer(
                rtl("<b>⚠️ שם עיר/יישוב קצר מדי.</b>"),
                parse_mode="HTML"
            )
            return

        data["new_address"]["city"] = city
        data["step"] = "add_address_street"

        await message.answer(
            rtl("<b>🏠 רחוב ומספר בית</b>\n\nלדוגמה: הרצל 10"),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "add_address_street":
        street = txt.strip()

        if len(street) < 2:
            await message.answer(
                rtl("<b>⚠️ כתובת קצרה מדי.</b>"),
                parse_mode="HTML"
            )
            return

        data["new_address"]["street"] = street
        data["step"] = "add_address_floor"

        await message.answer(
            rtl("<b>קומה</b>\n\nאם אין, רשום 0."),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "add_address_floor":
        data["new_address"]["floor"] = txt.strip()
        data["step"] = "add_address_apartment"

        await message.answer(
            rtl("<b>דירה</b>\n\nאם אין, רשום 0."),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "add_address_apartment":
        data["new_address"]["apartment"] = txt.strip()

        address = data["new_address"]

        save_customer_address(
            telegram_id=uid,
            label=address["label"],
            city=address["city"],
            street=address["street"],
            floor=address.get("floor", "0"),
            apartment=address.get("apartment", "0")
        )

        data.pop("new_address", None)
        data["step"] = "addresses_menu"

        await message.answer(
            rtl(
                "<b>✅ הכתובת נשמרה בהצלחה</b>\n\n"
                "אפשר להשתמש בה להזמנות הבאות."
            ),
            reply_markup=addresses_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "saved_profile_choice":
        if txt == "✅ המשך עם הפרטים השמורים":
            profile = data.get("saved_profile") or get_customer_profile(uid)

            if not profile:
                data["step"] = "name"
                await message.answer(
                    rtl("<b>⚠️ לא נמצאו פרטים שמורים.</b>\n\nרשום את השם המלא שלך:"),
                    parse_mode="HTML"
                )
                return

            ok = fill_saved_profile_into_data(data, profile)

            if not ok:
                data["step"] = "city"
                await message.answer(
                    rtl(
                        "<b>⚠️ לא הצלחנו לחשב משלוח לפי הכתובת השמורה.</b>\n\n"
                        "רשום יישוב למשלוח מחדש."
                    ),
                    parse_mode="HTML"
                )
                return

            data["step"] = "confirm"
            await message.answer(
                build_order_summary(data),
                reply_markup=order_summary_keyboard(data),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await send_pickup_navigation_if_needed(message, data)
            return

        if txt == "✏️ הזן פרטים חדשים":
            data["step"] = "name"
            await message.answer(
                rtl("<b>📝 פרטי הזמנה חדשים</b>\n\nרשום את השם המלא שלך:"),
                reply_markup=manual_details_keyboard(),
                parse_mode="HTML"
            )
            return

        await message.answer(
            rtl("<b>⚠️ בחר פעולה מהכפתורים.</b>"),
            reply_markup=use_saved_details_keyboard(),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "support_phone":
        phone = clean_phone(txt)

        if not valid_phone(phone):
            await message.answer(
                rtl("<b>⚠️ מספר פלאפון לא תקין.</b>\n\nלדוגמה: 0547937503"),
                parse_mode="HTML"
            )
            return

        existing_ticket = get_open_support_ticket_by_user(uid)

        created_new_ticket = False

        if existing_ticket:
            ticket_number = existing_ticket["ticket_number"]
        else:
            ticket_number = create_support_ticket(
                telegram_id=uid,
                telegram_name=message.from_user.full_name,
                phone=phone
            )
            created_new_ticket = True


        data["step"] = "support_chat"
        data["support_ticket_number"] = ticket_number
        data["support_phone"] = phone

        await message.answer(
            rtl(
                "<b>✅ הפנייה נפתחה ונמצאת בטיפול.</b>\n\n"
                f"{field('מספר פנייה', ticket_number)}\n"
                "כתוב עכשיו את ההודעה שלך ונציג שירות יחזור אליך בהקדם."
            ),
            reply_markup=support_customer_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "support_chat":
        existing_ticket = get_open_support_ticket_by_user(uid)

        if existing_ticket:
            ticket_number = existing_ticket["ticket_number"]
            data["support_ticket_number"] = ticket_number
            data["support_phone"] = existing_ticket.get("phone") or data.get("support_phone", "-")
        else:
            ticket_number = data.get("support_ticket_number")

        if txt == "✅ הבעיה נפתרה":
            if ticket_number:
                close_support_ticket(ticket_number)
                add_support_message(
                    ticket_number,
                    "customer",
                    message.from_user.full_name,
                    "הלקוח סימן שהבעיה נפתרה."
                )

                try:
                    await message.bot.send_message(
                        ADMIN_ID,
                        rtl(
                            "<b>✅ הפנייה נסגרה על ידי הלקוח</b>\n\n"
                            f"{field('מספר פנייה', ticket_number)}\n"
                            f"{field('לקוח', message.from_user.full_name)}\n"
                            f"{field('טלפון', data.get('support_phone', '-'))}"
                        ),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

            users.pop(uid, None)

            try:
                await message.delete()
            except Exception:
                pass

            await message.answer(
                rtl("<b>✅ הפנייה נסגרה.</b>\nתודה שפנית לשירות הלקוחות של Vendora."),
                reply_markup=main_keyboard(message.from_user.id),
                parse_mode="HTML"
            )
            return

        if len(txt) < 2:
            await message.answer(
                rtl("<b>⚠️ נא לרשום הודעה לנציג.</b>"),
                reply_markup=support_customer_keyboard(message.from_user.id),
                parse_mode="HTML"
            )
            return

        if not ticket_number:
            existing_ticket = get_open_support_ticket_by_user(uid)

            if existing_ticket:
                ticket_number = existing_ticket["ticket_number"]
                data["support_phone"] = existing_ticket.get("phone") or data.get("support_phone", "-")
            else:
                await message.answer(
                    rtl(
                        "<b>📞 שירות לקוחות</b>\n\n"
                        "כדי לפתוח פנייה לשירות לקוחות, רשום מספר פלאפון תקין.\n"
                        "לדוגמה: 0547937503"
                    ),
                    reply_markup=support_customer_keyboard(message.from_user.id),
                    parse_mode="HTML"
                )
                data["step"] = "support_phone"
                return

        add_support_message(
            ticket_number,
            "customer",
            message.from_user.full_name,
            txt
        )

        await message.answer(
            rtl(
                "<b>✅ ההודעה התקבלה ונמצאת בטיפול.</b>\n"
                "נציג שירות יחזור אליך בהקדם האפשרי."
            ),
            reply_markup=support_customer_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "_old_support_disabled":
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
                f"{field('שם', message.from_user.full_name)}\n"
                f"{field('Telegram ID', uid)}\n"
                f"{field('הודעה', txt)}"
            ),
            reply_markup=admin_support_reply_keyboard(uid),
            parse_mode="HTML"
        )

        users.pop(uid, None)

        if uid == ADMIN_ID:
            from keyboards import admin_keyboard
            finish_keyboard = admin_keyboard()
        else:
            finish_keyboard = main_keyboard(message.from_user.id)

        await message.answer(
            rtl(
                "<b>✅ הפנייה התקבלה ונמצאת בטיפול.</b>\n"
                "נציג שירות יחזור אליך בהקדם האפשרי."
            ),
            reply_markup=finish_keyboard,
            parse_mode="HTML"
        )
        return

    if data.get("step") == "qty_manual":
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
            data.pop("selected_product", None)
            data.pop("selected_qty", None)
            await message.answer(
                rtl("<b>❌ המוצר לא זמין כרגע.</b>"),
                parse_mode="HTML"
            )
            return

        product.update(fresh_product)

        max_qty = int(fresh_product.get("max_qty", 100))
        stock = int(fresh_product.get("stock", 0))
        already_in_cart = product_qty_in_cart(data["cart"], product["name"])
        available_left = stock - already_in_cart

        if not txt.isdigit():
            await message.answer(
                rtl("<b>⚠️ נא לרשום כמות במספרים בלבד.</b>"),
                parse_mode="HTML"
            )
            return

        selected_qty = int(txt)

        if selected_qty <= 0:
            await message.answer(
                rtl("<b>⚠️ הכמות חייבת להיות גדולה מ־0.</b>"),
                parse_mode="HTML"
            )
            return

        if selected_qty > max_qty:
            await message.answer(
                large_quantity_contact_text(max_qty),
                reply_markup=quantity_inline_keyboard(int(data.get("selected_qty", 1))),
                parse_mode="HTML"
            )
            data["step"] = "qty"
            return

        if selected_qty > available_left:
            await message.answer(
                rtl("<b>⚠️ לא ניתן לבחור כמות מעבר למלאי הזמין.</b>"),
                reply_markup=quantity_inline_keyboard(int(data.get("selected_qty", 1))),
                parse_mode="HTML"
            )
            data["step"] = "qty"
            return

        data["selected_qty"] = selected_qty
        data["step"] = "qty"

        await message.answer(
            rtl(
                "<b>🔢 בחירת כמות</b>\n\n"
                f"{field('כמות נבחרת', selected_qty)}\n\n"
                "בחר את הכמות הרצויה להזמנה.\n"
                "אפשר לשנות את הכמות באמצעות ➖ פחות או ➕ יותר.\n"
                "רק לאחר בחירת הכמות ולחיצה על 🛒 הוסף לסל,\n"
                "המוצרים יתווספו לסל ותוכל להמשיך למשלוח או לאיסוף."
            ),
            reply_markup=quantity_inline_keyboard(selected_qty),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "qty":
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
            data.pop("selected_product", None)
            data.pop("selected_qty", None)
            await message.answer(
                rtl("<b>❌ המוצר לא זמין כרגע.</b>"),
                parse_mode="HTML"
            )
            return

        product.update(fresh_product)

        max_qty = int(fresh_product.get("max_qty", 100))
        stock = int(fresh_product.get("stock", 0))
        already_in_cart = product_qty_in_cart(data["cart"], product["name"])
        available_left = stock - already_in_cart
        selected_qty = int(data.get("selected_qty", 1))

        if available_left <= 0:
            data["step"] = None
            data.pop("selected_product", None)
            data.pop("selected_qty", None)

            await message.answer(
                rtl("<b>📦 כל המלאי הזמין של המוצר כבר נמצא אצלך בסל.</b>"),
                reply_markup=cart_keyboard(),
                parse_mode="HTML"
            )
            return

        max_allowed_now = min(available_left, max_qty)

        if selected_qty > max_allowed_now:
            selected_qty = max_allowed_now
            data["selected_qty"] = selected_qty

        if txt == "➕ יותר":
            requested_qty = selected_qty + 1

            if requested_qty > max_allowed_now:
                if max_qty <= available_left and selected_qty >= max_qty:
                    await message.answer(
                        large_quantity_contact_text(max_qty),
                        reply_markup=quantity_inline_keyboard(selected_qty),
                        parse_mode="HTML"
                    )
                else:
                    await message.answer(
                        rtl("<b>⚠️ לא ניתן לבחור כמות מעבר למלאי הזמין.</b>"),
                        reply_markup=quantity_inline_keyboard(selected_qty),
                        parse_mode="HTML"
                    )
                return

            data["selected_qty"] = requested_qty

            await message.answer(
                rtl(
                    "<b>🔢 בחירת כמות</b>\n\n"
                    f"{field('כמות נבחרת', requested_qty)}\n\n"
                    "בחר את הכמות הרצויה להזמנה.\n"
                    "אפשר לשנות את הכמות באמצעות ➖ פחות או ➕ יותר.\n"
                    "רק לאחר בחירת הכמות ולחיצה על 🛒 הוסף לסל,\n"
                "המוצרים יתווספו לסל ותוכל להמשיך למשלוח או לאיסוף."
                ),
                reply_markup=quantity_inline_keyboard(requested_qty),
                parse_mode="HTML"
            )
            return

        if txt == "➖ פחות":
            if selected_qty > 1:
                selected_qty -= 1

            data["selected_qty"] = selected_qty

            await message.answer(
                rtl(
                    "<b>🔢 בחירת כמות</b>\n\n"
                    f"{field('כמות נבחרת', selected_qty)}\n\n"
                    "בחר את הכמות הרצויה להזמנה.\n"
                    "אפשר לשנות את הכמות באמצעות ➖ פחות או ➕ יותר.\n"
                    "רק לאחר בחירת הכמות ולחיצה על 🛒 הוסף לסל,\n"
                "המוצרים יתווספו לסל ותוכל להמשיך למשלוח או לאיסוף."
                ),
                reply_markup=quantity_inline_keyboard(selected_qty),
                parse_mode="HTML"
            )
            return

        if txt.startswith("כמות:"):
            data["step"] = "qty_manual"
            await message.answer(
                rtl(
                    "<b>✏️ הזנת כמות</b>\n\n"
                    "רשום את הכמות הרצויה במספרים בלבד."
                ),
                parse_mode="HTML"
            )
            return

        if txt != "🛒 הוסף לסל":
            await delete_customer_message(message)
            return

        qty = selected_qty

        if qty <= 0:
            await message.answer(
                rtl("<b>⚠️ הכמות חייבת להיות גדולה מ־0.</b>"),
                reply_markup=quantity_inline_keyboard(selected_qty),
                parse_mode="HTML"
            )
            return

        if qty > max_qty:
            await message.answer(
                large_quantity_contact_text(max_qty),
                reply_markup=quantity_inline_keyboard(selected_qty),
                parse_mode="HTML"
            )
            return

        if qty > available_left:
            await message.answer(
                rtl("<b>⚠️ לא ניתן לבחור כמות מעבר למלאי הזמין.</b>"),
                reply_markup=quantity_inline_keyboard(selected_qty),
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
        data.pop("selected_qty", None)

        await message.answer(
            cart_text(data["cart"], title="✅ נוסף לסל"),
            reply_markup=cart_keyboard(),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "name":
        if len(txt) < 2:
            await message.answer(
                rtl("<b>⚠️ נא לרשום שם מלא תקין.</b>"),
                parse_mode="HTML"
            )
            return

        data["name"] = txt
        data["step"] = "phone"
        await message.answer(
            rtl("<b>📞 מספר פלאפון</b>\n\nרשום מספר פלאפון תקין.\nלדוגמה: 0547937503"),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "phone":
        phone = clean_phone(txt)

        if not valid_phone(phone):
            await message.answer(
                rtl("<b>⚠️ מספר פלאפון לא תקין.</b>\n\nלדוגמה: 0547937503"),
                parse_mode="HTML"
            )
            return

        data["phone"] = phone

        if is_pickup_order(data):
            set_pickup_details(data)
            data["step"] = "confirm"

            await message.answer(
                build_order_summary(data),
                reply_markup=order_summary_keyboard(data),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await send_pickup_navigation_if_needed(message, data)
            return

        data["step"] = "city"
        await message.answer(
            rtl(
                "<b>📍 עיר / יישוב למשלוח</b>\n\n"
                "רשום את שם העיר, המושב או הקיבוץ למשלוח.\n"
                "לדוגמה: אשדוד"
            ),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "city":
        if len(txt) < 2 or has_digit(txt):
            await message.answer(
                rtl("<b>⚠️ נא לרשום שם יישוב תקין.</b>"),
                parse_mode="HTML"
            )
            return

        delivery_price, base_city, status = get_delivery_price(txt)

        if status == "city_not_found":
            await message.answer(
                rtl("<b>⚠️ היישוב לא נמצא במאגר.</b>\nנא לרשום יישוב תקין."),
                parse_mode="HTML"
            )
            return

        data["city"] = txt

        if status == "no_delivery_price" or delivery_price is None:
            data["delivery_price"] = 0
            data["base_city"] = base_city or "לתיאום מול נציג"
            data["delivery_pending"] = True
            delivery_message = (
                "<b>ℹ️ מחיר משלוח לתיאום</b>\n\n"
                "לא נמצא מחיר משלוח אוטומטי לאזור הזה.\n"
                "אפשר להמשיך בהזמנה, ונציג יעדכן אותך במחיר המשלוח לפני סגירה סופית.\n\n"
            )
        else:
            data["delivery_price"] = float(delivery_price)
            data["base_city"] = base_city
            data["delivery_pending"] = False
            delivery_message = f"<b>דמי משלוח ל{h(txt)}:</b> {money(delivery_price)}\n\n"

        data["step"] = "street"

        await message.answer(
            rtl(
                delivery_message
                + "<b>📍 כתובת למשלוח</b>\n"
                "רשום רחוב ומספר בית."
            ),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "street":
        if len(txt) < 5 or not has_digit(txt):
            await message.answer(
                rtl("<b>⚠️ נא לרשום רחוב + מספר בית.</b>"),
                parse_mode="HTML"
            )
            return

        data["street"] = txt
        data["step"] = "floor"
        await message.answer(
            rtl("<b>🏢 קומה</b>\n\nאיזו קומה?\nאם זה קרקע, רשום 0."),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "floor":
        if not txt.lstrip("-").isdigit():
            await message.answer(
                rtl("<b>⚠️ נא לרשום קומה במספרים בלבד.</b>"),
                parse_mode="HTML"
            )
            return

        data["floor"] = txt
        data["step"] = "apartment"
        await message.answer(
            rtl("<b>🚪 דירה</b>\n\nמספר דירה?\nאם אין דירה, רשום 0."),
            parse_mode="HTML"
        )
        return

    if data.get("step") == "apartment":
        if not txt.isdigit():
            await message.answer(
                rtl("<b>⚠️ נא לרשום מספר דירה במספרים בלבד.</b>"),
                parse_mode="HTML"
            )
            return

        data["apartment"] = txt
        data["step"] = "confirm"

        await message.answer(
            build_order_summary(data),
            reply_markup=order_summary_keyboard(data),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        await send_pickup_navigation_if_needed(message, data)
        return

    # CUSTOMER_FALLBACK_DELETE_MARKER
    if data and not is_free_text_step_for_customer(data.get("step")):
        await delete_customer_message(message)
        return
