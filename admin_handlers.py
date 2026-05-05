from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from html import escape
from datetime import datetime
import calendar

from config import ADMIN_ID
from keyboards import admin_keyboard, main_keyboard, order_status_keyboard
from database import (
    add_product,
    get_all_products,
    get_product_by_name,
    set_product_price,
    set_product_description,
    set_product_stock,
    add_stock,
    set_product_image,
    set_product_active,
    delete_product,
    get_recent_orders,
    get_orders_by_status,
    get_order_by_number,
    update_order_status,
    get_orders_by_phone,
    get_dashboard_statistics,
    get_statistics_by_date,
    get_open_orders,
    get_done_orders,
    get_cancelled_orders,
    get_orders_status_summary,
)

router = Router()
admin_states = {}

RTL = "\u200F"


STATUS_TEXT = {
    "new": "🆕 חדשה",
    "approved": "✅ אושרה",
    "processing": "📦 בטיפול",
    "shipping": "🚚 יצאה למשלוח",
    "done": "✅ הושלמה",
    "cancelled": "❌ בוטלה",
}

STATUS_BY_BUTTON = {
    "✅ אושרה": "approved",
    "📦 בטיפול": "processing",
    "🚚 יצאה למשלוח": "shipping",
    "✅ הושלמה": "done",
    "❌ בוטלה": "cancelled",
}

CLIENT_STATUS_MESSAGE = {
    "approved": "✅ ההזמנה שלך אושרה. נציג ייצור איתך קשר להמשך טיפול.",
    "processing": "📦 ההזמנה שלך בטיפול.",
    "shipping": "🚚 ההזמנה שלך יצאה למשלוח.",
    "done": "✅ ההזמנה הושלמה. תודה שקנית ב־Vendora Shop!",
    "cancelled": "❌ ההזמנה בוטלה. לפרטים נוספים ניתן לפנות לשירות לקוחות.",
}


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


def is_admin(user_id):
    return user_id == ADMIN_ID


def is_admin_active_step(message: Message):
    uid = message.from_user.id

    if not is_admin(uid):
        return False

    txt = (message.text or "").strip()

    if txt.startswith("/"):
        return False

    state = admin_states.get(uid)

    if not state:
        return False

    step = state.get("step")

    if step == "admin":
        return False

    return True


def product_names_keyboard():
    rows = get_all_products()
    keyboard = []

    for row in rows:
        product_id, category, name, price, description, max_qty, stock, sku, image_file_id, active = row
        keyboard.append([KeyboardButton(text=name)])

    keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)



def statistics_calendar_keyboard(year=None, month=None):
    today = datetime.now()

    if year is None:
        year = today.year

    if month is None:
        month = today.month

    days_in_month = calendar.monthrange(year, month)[1]

    keyboard = [
        [KeyboardButton(text=f"📅 {month:02d}.{year}")],
        [
            KeyboardButton(text="◀️ חודש קודם"),
            KeyboardButton(text="📍 היום"),
            KeyboardButton(text="▶️ חודש הבא")
        ]
    ]

    row = []
    for day in range(1, days_in_month + 1):
        row.append(KeyboardButton(text=f"{day:02d}.{month:02d}.{year}"))

        if len(row) == 4:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def shift_month(year, month, step):
    month += step

    if month > 12:
        month = 1
        year += 1

    if month < 1:
        month = 12
        year -= 1

    return year, month


def parse_calendar_date(text):
    clean = str(text).replace("📅", "").strip()

    for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass

    return None


def format_date_he(date_text):
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return date_text



def orders_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 הזמנות פתוחות")],
            [KeyboardButton(text="🆕 חדשות"), KeyboardButton(text="✅ אושרו")],
            [KeyboardButton(text="📦 בטיפול"), KeyboardButton(text="🚚 במשלוח")],
            [KeyboardButton(text="🧾 הושלמו"), KeyboardButton(text="❌ בוטלו")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def order_select_keyboard(orders, back_text="⬅️ חזרה לניהול הזמנות"):
    keyboard = []

    for order in orders:
        order_number = order.get("order_number", "")
        customer_name = order.get("customer_name", "")
        final_total = money(order.get("final_total", 0))
        status = status_label(order.get("status", ""))
        keyboard.append([KeyboardButton(text=f"🧾 {order_number} | {final_total} | {customer_name} | {status}")])

    keyboard.append([KeyboardButton(text=back_text)])
    keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def order_action_keyboard(order_status):
    if order_status in {"done", "cancelled"}:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="👁️ צפייה בלבד")],
                [KeyboardButton(text="⬅️ חזרה לרשימת הזמנות")],
                [KeyboardButton(text="⬅️ חזרה לניהול")]
            ],
            resize_keyboard=True
        )

    keyboard = []

    if order_status == "new":
        keyboard.append([KeyboardButton(text="✅ אשר הזמנה"), KeyboardButton(text="❌ בטל הזמנה")])
    elif order_status == "approved":
        keyboard.append([KeyboardButton(text="📦 העבר לטיפול"), KeyboardButton(text="❌ בטל הזמנה")])
    elif order_status == "processing":
        keyboard.append([KeyboardButton(text="🚚 סמן כיצא למשלוח"), KeyboardButton(text="❌ בטל הזמנה")])
    elif order_status == "shipping":
        keyboard.append([KeyboardButton(text="✅ סמן כהושלם"), KeyboardButton(text="❌ בטל הזמנה")])
    else:
        keyboard.append([KeyboardButton(text="❌ בטל הזמנה")])

    keyboard.append([KeyboardButton(text="⬅️ חזרה לרשימת הזמנות")])
    keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


ORDER_SECTION_BY_BUTTON = {
    "📋 הזמנות פתוחות": "open",
    "🆕 חדשות": "new",
    "✅ אושרו": "approved",
    "📦 בטיפול": "processing",
    "🚚 במשלוח": "shipping",
    "🧾 הושלמו": "done",
    "❌ בוטלו": "cancelled",
}


ORDER_ACTION_BY_BUTTON = {
    "✅ אשר הזמנה": "approved",
    "📦 העבר לטיפול": "processing",
    "🚚 סמן כיצא למשלוח": "shipping",
    "✅ סמן כהושלם": "done",
    "❌ בטל הזמנה": "cancelled",
}


def extract_order_number_from_button(text):
    text = str(text or "").strip()

    if text.startswith("🧾 "):
        text = text.replace("🧾 ", "", 1)

    if "|" in text:
        return text.split("|", 1)[0].strip()

    return text.strip()


def get_orders_for_section(section, limit=30):
    if section == "open":
        return get_open_orders(limit)

    if section == "done":
        return get_done_orders(limit)

    if section == "cancelled":
        return get_cancelled_orders(limit)

    return get_orders_by_status(section, limit)


def section_title(section):
    titles = {
        "open": "📋 הזמנות פתוחות",
        "new": "🆕 הזמנות חדשות",
        "approved": "✅ הזמנות שאושרו",
        "processing": "📦 הזמנות בטיפול",
        "shipping": "🚚 הזמנות במשלוח",
        "done": "🧾 הזמנות שהושלמו",
        "cancelled": "❌ הזמנות שבוטלו",
    }
    return titles.get(section, "📦 ניהול הזמנות")


def orders_summary_text():
    counts = get_orders_status_summary()

    return (
        "<b>📦 ניהול הזמנות</b>\n\n"
        "<b>📋 פתוחות לעבודה</b>\n"
        f"{field('סה״כ פתוחות', counts['open'])}\n"
        f"{field('חדשות', counts['new'])}\n"
        f"{field('אושרו', counts['approved'])}\n"
        f"{field('בטיפול', counts['processing'])}\n"
        f"{field('במשלוח', counts['shipping'])}\n\n"
        "<b>📁 ארכיון</b>\n"
        f"{field('הושלמו', counts['done'])}\n"
        f"{field('בוטלו', counts['cancelled'])}\n\n"
        "בחר קטגוריה להצגה."
    )


# ================== ORDER STATUS LOGIC ==================
FINAL_ORDER_STATUSES = {"done", "cancelled"}

STATUS_FLOW_LEVEL = {
    "new": 1,
    "approved": 2,
    "processing": 3,
    "shipping": 4,
    "done": 5,
    "cancelled": 99,
}


def validate_status_change(current_status, new_status):
    if current_status == new_status:
        return False, (
            "<b>⚠️ הפעולה כבר בוצעה</b>\n\n"
            "ההזמנה כבר נמצאת בסטטוס שבחרת.\n"
            "אין צורך לבצע את אותה פעולה פעם נוספת."
        )

    if current_status in FINAL_ORDER_STATUSES:
        return False, (
            "<b>🔒 לא ניתן לשנות סטטוס</b>\n\n"
            "ההזמנה נמצאת בסטטוס סופי ולכן נעולה לשינויים רגילים.\n"
            "הזמנות שהושלמו או בוטלו נשמרות בארכיון לצפייה בלבד."
        )

    if new_status == "cancelled":
        return True, ""

    current_level = STATUS_FLOW_LEVEL.get(current_status, 0)
    new_level = STATUS_FLOW_LEVEL.get(new_status, 0)

    if new_level < current_level:
        return False, (
            "<b>⚠️ פעולה לא תקינה</b>\n\n"
            "לא ניתן להחזיר הזמנה לשלב קודם בתהליך."
        )

    if current_status == "new" and new_status not in {"approved", "cancelled"}:
        return False, (
            "<b>⚠️ סדר פעולה לא תקין</b>\n\n"
            "הזמנה חדשה חייבת לעבור קודם אישור.\n"
            "בחר: ✅ אשר הזמנה או ❌ בטל הזמנה."
        )

    if current_status == "approved" and new_status not in {"processing", "cancelled"}:
        return False, (
            "<b>⚠️ סדר פעולה לא תקין</b>\n\n"
            "אחרי אישור הזמנה, השלב הבא הוא העברה לטיפול.\n"
            "בחר: 📦 העבר לטיפול או ❌ בטל הזמנה."
        )

    if current_status == "processing" and new_status not in {"shipping", "cancelled"}:
        return False, (
            "<b>⚠️ סדר פעולה לא תקין</b>\n\n"
            "הזמנה שבטיפול יכולה לעבור לשלב משלוח או להתבטל.\n"
            "בחר: 🚚 סמן כיצא למשלוח או ❌ בטל הזמנה."
        )

    if current_status == "shipping" and new_status not in {"done", "cancelled"}:
        return False, (
            "<b>⚠️ סדר פעולה לא תקין</b>\n\n"
            "אחרי שההזמנה יצאה למשלוח, השלב הבא הוא סימון כהושלמה.\n"
            "בחר: ✅ סמן כהושלם או ❌ בטל הזמנה."
        )

    return True, ""


async def send_status_blocked_message(message, order_number, current_status, reason_text, reply_markup):
    await message.answer(
        rtl(
            f"{reason_text}\n\n"
            f"{field('מספר הזמנה', order_number)}\n"
            f"{field('סטטוס נוכחי', status_label(current_status))}"
        ),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


def status_label(status):
    return STATUS_TEXT.get(status, status)


def format_order(order):
    text = (
        f"<b>🧾 הזמנה {h(order['order_number'])}</b>\n\n"
        f"{field('סטטוס', status_label(order['status']))}\n"
        f"{field('תאריך', order['created_at'])}\n\n"
        f"{field('שם לקוח', order['customer_name'])}\n"
        f"{field('טלפון', order['phone'])}\n"
        f"{field('כתובת', order['address'])}\n\n"
        "<b>🛒 מוצרים</b>\n\n"
    )

    total_units = 0

    for index, item in enumerate(order["cart"], start=1):
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty
        total_units += qty

        text += (
            f"<b>{index}. {h(item['name'])}</b>\n"
            f"{field('כמות', qty)}\n"
            f"{field('סה״כ מוצר', money(total))}\n\n"
        )

    text += (
        f"{field('כמות מוצרים', total_units)}\n"
        f"{field('סה״כ מוצרים', money(order['products_total']))}\n"
        f"{field('משלוח', money(order['delivery_price']))}\n"
        f"{field('סה״כ לתשלום', money(order['final_total']))}\n\n"
        f"{field('Telegram ID', order['telegram_id'])}\n"
        f"{field('Telegram', order['telegram_name'] or '-')}"
    )

    return rtl(text)


def format_product_row(row):
    product_id, category, name, price, description, max_qty, stock, sku, image_file_id, active = row

    status = "פעיל ✅" if active else "כבוי ❌"
    image = "יש תמונה 🖼️" if image_file_id else "ללא תמונה ⚠️"
    stock_text = "אזל מהמלאי ❌" if int(stock) <= 0 else f"{stock}"

    return (
        f"<b>🛍️ {h(name)}</b>\n"
        f"{field('סטטוס', status)}\n"
        f"{field('קטגוריה', category)}\n"
        f"{field('מחיר', money(price))}\n"
        f"{field('מלאי', stock_text)}\n"
        f"{field('מקסימום להזמנה', max_qty)}\n"
        f"{field('מק״ט', sku or '-')}\n"
        f"{field('תמונה', image)}\n"
        f"{field('תיאור', description or '-')}"
    )


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "admin"}

    await message.answer(
        rtl(
            "<b>🔐 פאנל ניהול Vendora</b>\n\n"
            "בחר פעולה מהתפריט למטה."
        ),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ יציאה מניהול")
async def exit_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states.pop(message.from_user.id, None)

    await message.answer(
        rtl("<b>✅ יצאת מפאנל הניהול.</b>"),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ חזרה לניהול")
async def back_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "admin"}

    await message.answer(
        rtl("<b>🔐 חזרת לפאנל הניהול.</b>"),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )



@router.message(F.text == "📦 ניהול הזמנות")
async def orders_management_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {
        "step": "orders_section",
        "orders_section": "open"
    }

    await message.answer(
        rtl(orders_summary_text()),
        reply_markup=orders_main_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🧾 הזמנות אחרונות")
async def recent_orders(message: Message):
    if not is_admin(message.from_user.id):
        return

    orders = get_recent_orders(10)

    if not orders:
        await message.answer(rtl("<b>🧾 הזמנות אחרונות</b>\n\nאין הזמנות במערכת."), parse_mode="HTML")
        return

    await message.answer(
        rtl(f"<b>🧾 הזמנות אחרונות</b>\n\nנמצאו {len(orders)} הזמנות אחרונות."),
        parse_mode="HTML"
    )

    for order in orders:
        await message.answer(format_order(order), parse_mode="HTML")


@router.message(F.text == "🆕 הזמנות חדשות")
async def new_orders(message: Message):
    if not is_admin(message.from_user.id):
        return

    orders = get_orders_by_status("new", 20)

    if not orders:
        await message.answer(rtl("<b>🆕 הזמנות חדשות</b>\n\nאין הזמנות חדשות כרגע."), parse_mode="HTML")
        return

    await message.answer(
        rtl(f"<b>🆕 הזמנות חדשות</b>\n\nנמצאו {len(orders)} הזמנות חדשות."),
        parse_mode="HTML"
    )

    for order in orders:
        await message.answer(format_order(order), parse_mode="HTML")


@router.message(F.text == "🔎 חפש הזמנה")
async def search_order_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "search_order"}

    await message.answer(
        rtl("<b>🔎 חיפוש הזמנה</b>\n\nרשום מספר הזמנה.\nלדוגמה: V1001"),
        parse_mode="HTML"
    )


@router.message(F.text == "📞 חפש לפי טלפון")
async def search_by_phone_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "search_phone"}

    await message.answer(
        rtl("<b>📞 חיפוש לפי טלפון</b>\n\nרשום מספר טלפון לחיפוש.\nלדוגמה: 0547937503"),
        parse_mode="HTML"
    )



@router.message(F.text == "📊 מצב העסק")
async def business_dashboard(message: Message):
    if not is_admin(message.from_user.id):
        return

    stats = get_dashboard_statistics()

    text = (
        "<b>📊 מצב העסק — Vendora</b>\n\n"

        "🟢 <b>היום</b>\n"
        f"{field('הכנסות', money(stats['today_money']))}\n"
        f"{field('הזמנות', stats['today_orders'])}\n"
        f"{field('לקוחות חדשים', stats['today_customers'])}\n"
        f"{field('ממוצע להזמנה', money(stats['today_avg_order']))}\n\n"

        "🔵 <b>החודש</b>\n"
        f"{field('הכנסות', money(stats['month_money']))}\n"
        f"{field('הזמנות', stats['month_orders'])}\n"
        f"{field('לקוחות חדשים', stats['month_customers'])}\n"
        f"{field('ממוצע להזמנה', money(stats['month_avg_order']))}\n\n"

        "🟣 <b>השנה</b>\n"
        f"{field('הכנסות', money(stats['year_money']))}\n"
        f"{field('הזמנות', stats['year_orders'])}\n"
        f"{field('לקוחות חדשים', stats['year_customers'])}\n"
        f"{field('ממוצע להזמנה', money(stats['year_avg_order']))}\n\n"

        "🔥 <b>מוצרים מובילים</b>\n"
        f"{field('היום', stats['today_top_product'])} ({stats['today_top_qty']})\n"
        f"{field('החודש', stats['month_top_product'])} ({stats['month_top_qty']})\n"
        f"{field('השנה', stats['year_top_product'])} ({stats['year_top_qty']})"
    )

    await message.answer(
        rtl(text),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "📅 סטטיסטיקה לפי תאריך")
async def statistics_by_date_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    today = datetime.now()

    admin_states[message.from_user.id] = {
        "step": "statistics_calendar",
        "calendar_year": today.year,
        "calendar_month": today.month
    }

    await message.answer(
        rtl(
            "<b>📅 סטטיסטיקה לפי תאריך</b>\n\n"
            "בחר יום מתוך לוח השנה.\n"
            "אפשר לעבור בין חודשים עם הכפתורים למטה."
        ),
        reply_markup=statistics_calendar_keyboard(today.year, today.month),
        parse_mode="HTML"
    )


@router.message(F.text == "🔄 עדכן סטטוס הזמנה")
async def update_order_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "status_order_number"}

    await message.answer(
        rtl("<b>🔄 עדכון סטטוס הזמנה</b>\n\nרשום מספר הזמנה לעדכון.\nלדוגמה: V1001"),
        parse_mode="HTML"
    )


@router.message(F.text == "📦 רשימת מוצרים")
async def products_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = get_all_products()

    if not rows:
        await message.answer(rtl("<b>📦 רשימת מוצרים</b>\n\nאין מוצרים במערכת."), parse_mode="HTML")
        return

    await message.answer(
        rtl(f"<b>📦 רשימת מוצרים</b>\n\nנמצאו {len(rows)} מוצרים."),
        parse_mode="HTML"
    )

    for row in rows:
        await message.answer(rtl(format_product_row(row)), parse_mode="HTML")


@router.message(F.text == "➕ הוסף מוצר")
async def add_product_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "add_category"}

    await message.answer(
        rtl("<b>➕ הוספת מוצר</b>\n\nרשום קטגוריה למוצר.\nלדוגמה: תיק משלוחים"),
        parse_mode="HTML"
    )


@router.message(F.text == "✏️ שנה מחיר")
async def price_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "price_name"}

    await message.answer(
        rtl("<b>✏️ שינוי מחיר</b>\n\nבחר מוצר לשינוי מחיר:"),
        reply_markup=product_names_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "📝 שנה תיאור")
async def description_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "description_name"}

    await message.answer(
        rtl("<b>📝 שינוי תיאור</b>\n\nבחר מוצר לשינוי תיאור:"),
        reply_markup=product_names_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "📊 עדכן מלאי")
async def stock_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "stock_name"}

    await message.answer(
        rtl("<b>📊 עדכון מלאי</b>\n\nבחר מוצר לעדכון מלאי:"),
        reply_markup=product_names_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "➕ הוסף למלאי")
async def add_stock_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "add_stock_name"}

    await message.answer(
        rtl("<b>➕ הוספה למלאי</b>\n\nבחר מוצר להוספת מלאי:"),
        reply_markup=product_names_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🖼️ עדכן תמונה")
async def image_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "image_name"}

    await message.answer(
        rtl("<b>🖼️ עדכון תמונה</b>\n\nבחר מוצר לעדכון תמונה:"),
        reply_markup=product_names_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🔴 כבה מוצר")
async def off_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "off_name"}

    await message.answer(
        rtl("<b>🔴 כיבוי מוצר</b>\n\nבחר מוצר לכיבוי:"),
        reply_markup=product_names_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🟢 הפעל מוצר")
async def on_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "on_name"}

    await message.answer(
        rtl("<b>🟢 הפעלת מוצר</b>\n\nבחר מוצר להפעלה:"),
        reply_markup=product_names_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🗑️ מחק מוצר")
async def delete_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "delete_name"}

    await message.answer(
        rtl("<b>🗑️ מחיקת מוצר</b>\n\nבחר מוצר למחיקה:"),
        reply_markup=product_names_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.photo)
async def handle_photo(message: Message):
    uid = message.from_user.id

    if not is_admin(uid):
        return

    state = admin_states.get(uid)

    if not state or state.get("step") != "image_photo":
        return

    file_id = message.photo[-1].file_id
    product_name = state["product_name"]

    ok = set_product_image(product_name, file_id)
    admin_states[uid] = {"step": "admin"}

    if ok:
        text = f"<b>✅ התמונה עודכנה בהצלחה</b>\n\n{field('מוצר', product_name)}"
    else:
        text = "<b>⚠️ המוצר לא נמצא.</b>"

    await message.answer(rtl(text), reply_markup=admin_keyboard(), parse_mode="HTML")


@router.message(is_admin_active_step)
async def admin_flow(message: Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    state = admin_states.get(uid)
    step = state.get("step")

    if step == "statistics_calendar":
        year = int(state.get("calendar_year", datetime.now().year))
        month = int(state.get("calendar_month", datetime.now().month))

        if txt == "◀️ חודש קודם":
            year, month = shift_month(year, month, -1)
            state["calendar_year"] = year
            state["calendar_month"] = month

            await message.answer(
                rtl(
                    "<b>📅 סטטיסטיקה לפי תאריך</b>\n\n"
                    f"מציג חודש: <b>{month:02d}.{year}</b>\n"
                    "בחר יום לבדיקה."
                ),
                reply_markup=statistics_calendar_keyboard(year, month),
                parse_mode="HTML"
            )
            return

        if txt == "▶️ חודש הבא":
            year, month = shift_month(year, month, 1)
            state["calendar_year"] = year
            state["calendar_month"] = month

            await message.answer(
                rtl(
                    "<b>📅 סטטיסטיקה לפי תאריך</b>\n\n"
                    f"מציג חודש: <b>{month:02d}.{year}</b>\n"
                    "בחר יום לבדיקה."
                ),
                reply_markup=statistics_calendar_keyboard(year, month),
                parse_mode="HTML"
            )
            return

        if txt == "📍 היום":
            date_value = datetime.now().strftime("%Y-%m-%d")
        else:
            date_value = parse_calendar_date(txt)

        if not date_value:
            await message.answer(
                rtl(
                    "<b>⚠️ בחר יום מתוך לוח השנה.</b>\n\n"
                    "אפשר לעבור חודש קדימה או אחורה."
                ),
                reply_markup=statistics_calendar_keyboard(year, month),
                parse_mode="HTML"
            )
            return

        stats = get_statistics_by_date(date_value)
        admin_states[uid] = {"step": "admin"}

        text = (
            "<b>📅 סטטיסטיקה לפי תאריך</b>\n\n"
            f"{field('תאריך', format_date_he(stats['date']))}\n\n"
            "💰 <b>הכנסות</b>\n"
            f"{field('סה״כ הכנסות', money(stats['total_money']))}\n\n"
            "📦 <b>הזמנות</b>\n"
            f"{field('סה״כ הזמנות', stats['total_orders'])}\n\n"
            "🔄 <b>סטטוסים</b>\n"
            f"{field('חדשות', stats['new'])}\n"
            f"{field('אושרו', stats['approved'])}\n"
            f"{field('בטיפול', stats['processing'])}\n"
            f"{field('במשלוח', stats['shipping'])}\n"
                f"{field('הושלמו', stats['done'])}\n"
            f"{field('בוטלו', stats['cancelled'])}\n\n"
            "🔥 <b>מוצר מוביל</b>\n"
            f"{field('שם מוצר', stats['top_product'])}\n"
            f"{field('כמות נמכרה', stats['top_qty'])}"
        )

        await message.answer(
            rtl(text),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return


    if step == "orders_section":
        if txt not in ORDER_SECTION_BY_BUTTON:
            await message.answer(
                rtl("<b>⚠️ בחר קטגוריה מתוך הכפתורים בלבד.</b>"),
                reply_markup=orders_main_keyboard(),
                parse_mode="HTML"
            )
            return

        section = ORDER_SECTION_BY_BUTTON[txt]
        orders = get_orders_for_section(section, 30)

        state["orders_section"] = section
        state["step"] = "orders_select"

        if not orders:
            state["step"] = "orders_section"
            await message.answer(
                rtl(
                    f"<b>{section_title(section)}</b>\n\n"
                    "לא נמצאו הזמנות בקטגוריה הזו."
                ),
                reply_markup=orders_main_keyboard(),
                parse_mode="HTML"
            )
            return

        await message.answer(
            rtl(
                f"<b>{section_title(section)}</b>\n\n"
                f"נמצאו {len(orders)} הזמנות.\n"
                "בחר הזמנה מהרשימה כדי לצפות בפרטים."
            ),
            reply_markup=order_select_keyboard(orders),
            parse_mode="HTML"
        )
        return

    if step == "orders_select":
        if txt == "⬅️ חזרה לניהול הזמנות":
            state["step"] = "orders_section"
            await message.answer(
                rtl(orders_summary_text()),
                reply_markup=orders_main_keyboard(),
                parse_mode="HTML"
            )
            return

        order_number = extract_order_number_from_button(txt)
        order = get_order_by_number(order_number)

        if not order:
            await message.answer(
                rtl("<b>⚠️ ההזמנה לא נמצאה.</b>\nבחר הזמנה מהרשימה."),
                parse_mode="HTML"
            )
            return

        state["step"] = "order_actions"
        state["order_number"] = order_number

        await message.answer(
            format_order(order),
            reply_markup=order_action_keyboard(order.get("status")),
            parse_mode="HTML"
        )
        return

    if step == "order_actions":
        if txt == "⬅️ חזרה לרשימת הזמנות":
            section = state.get("orders_section", "open")
            orders = get_orders_for_section(section, 30)

            state["step"] = "orders_select"

            if not orders:
                state["step"] = "orders_section"
                await message.answer(
                    rtl(
                        f"<b>{section_title(section)}</b>\n\n"
                        "לא נמצאו הזמנות בקטגוריה הזו."
                    ),
                    reply_markup=orders_main_keyboard(),
                    parse_mode="HTML"
                )
                return

            await message.answer(
                rtl(
                    f"<b>{section_title(section)}</b>\n\n"
                    "בחר הזמנה מהרשימה."
                ),
                reply_markup=order_select_keyboard(orders),
                parse_mode="HTML"
            )
            return

        if txt == "👁️ צפייה בלבד":
            order_number = state.get("order_number")
            order = get_order_by_number(order_number)

            if order:
                await message.answer(
                    rtl(
                        "<b>👁️ צפייה בלבד</b>\n\n"
                        "הזמנה זו נמצאת בסטטוס סופי ונשמרת בארכיון.\n"
                        "לא ניתן לשנות אותה מכאן."
                    ),
                    reply_markup=order_action_keyboard(order.get("status")),
                    parse_mode="HTML"
                )
            return

        if txt not in ORDER_ACTION_BY_BUTTON:
            order_number = state.get("order_number")
            order = get_order_by_number(order_number)
            order_status = order.get("status") if order else "new"

            await message.answer(
                rtl("<b>⚠️ בחר פעולה מתוך הכפתורים בלבד.</b>"),
                reply_markup=order_action_keyboard(order_status),
                parse_mode="HTML"
            )
            return

        order_number = state.get("order_number")
        new_status = ORDER_ACTION_BY_BUTTON[txt]

        order_before = get_order_by_number(order_number)

        if not order_before:
            await message.answer(
                rtl("<b>⚠️ ההזמנה לא נמצאה במערכת.</b>"),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            admin_states[uid] = {"step": "admin"}
            return

        current_status = order_before.get("status")

        is_valid, reason_text = validate_status_change(current_status, new_status)

        if not is_valid:
            await send_status_blocked_message(
                message,
                order_number,
                current_status,
                reason_text,
                order_action_keyboard(current_status)
            )
            return

        ok = update_order_status(order_number, new_status)
        order = get_order_by_number(order_number)

        if not ok or not order:
            await message.answer(
                rtl("<b>⚠️ לא הצלחתי לעדכן את ההזמנה.</b>"),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            admin_states[uid] = {"step": "admin"}
            return

        client_msg = CLIENT_STATUS_MESSAGE.get(new_status, "סטטוס ההזמנה שלך עודכן.")

        try:
            await message.bot.send_message(
                order["telegram_id"],
                rtl(f"{client_msg}\n\n{field('מספר הזמנה', order_number)}"),
                parse_mode="HTML"
            )
        except Exception:
            pass

        await message.answer(
            rtl(
                "<b>✅ סטטוס ההזמנה עודכן בהצלחה</b>\n\n"
                f"{field('מספר הזמנה', order_number)}\n"
                f"{field('סטטוס חדש', status_label(new_status))}"
            ),
            parse_mode="HTML"
        )

        if new_status in FINAL_ORDER_STATUSES:
            state["step"] = "orders_section"
            await message.answer(
                rtl(
                    "<b>📁 ההזמנה עברה לארכיון</b>\n\n"
                    "הזמנות שהושלמו או בוטלו לא מופיעות יותר ברשימת ההזמנות הפתוחות.\n"
                    "ניתן למצוא אותן דרך: 🧾 הושלמו או ❌ בוטלו."
                ),
                reply_markup=orders_main_keyboard(),
                parse_mode="HTML"
            )
            return

        state["step"] = "order_actions"
        await message.answer(
            format_order(order),
            reply_markup=order_action_keyboard(order.get("status")),
            parse_mode="HTML"
        )
        return

    if step == "search_order":
        order = get_order_by_number(txt)

        admin_states[uid] = {"step": "admin"}

        if not order:
            await message.answer(
                rtl("<b>⚠️ ההזמנה לא נמצאה.</b>"),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            return

        await message.answer(format_order(order), reply_markup=admin_keyboard(), parse_mode="HTML")
        return

    if step == "search_phone":
        orders = get_orders_by_phone(txt, 20)

        admin_states[uid] = {"step": "admin"}

        if not orders:
            await message.answer(
                rtl("<b>⚠️ לא נמצאו הזמנות למספר הזה.</b>"),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            return

        await message.answer(
            rtl(f"<b>📞 תוצאות חיפוש</b>\n\nנמצאו {len(orders)} הזמנות למספר {h(txt)}."),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )

        for order in orders:
            await message.answer(format_order(order), parse_mode="HTML")

        return

    if step == "status_order_number":
        order = get_order_by_number(txt)

        if not order:
            await message.answer(rtl("<b>⚠️ ההזמנה לא נמצאה.</b>\nרשום מספר הזמנה תקין."), parse_mode="HTML")
            return

        state["order_number"] = txt
        state["step"] = "status_value"

        await message.answer(
            rtl(
                f"<b>🔄 עדכון סטטוס</b>\n\n"
                f"{field('הזמנה', txt)}\n"
                f"{field('סטטוס נוכחי', status_label(order['status']))}\n\n"
                "בחר סטטוס חדש:"
            ),
            reply_markup=order_status_keyboard(),
            parse_mode="HTML"
        )
        return

    if step == "status_value":
        if txt not in STATUS_BY_BUTTON:
            await message.answer(
                rtl("<b>⚠️ בחר סטטוס מתוך הכפתורים בלבד.</b>"),
                reply_markup=order_status_keyboard(),
                parse_mode="HTML"
            )
            return

        order_number = state["order_number"]
        new_status = STATUS_BY_BUTTON[txt]

        order_before = get_order_by_number(order_number)

        if not order_before:
            admin_states[uid] = {"step": "admin"}
            await message.answer(
                rtl("<b>⚠️ ההזמנה לא נמצאה במערכת.</b>"),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            return

        current_status = order_before.get("status")

        is_valid, reason_text = validate_status_change(current_status, new_status)

        if not is_valid:
            await send_status_blocked_message(
                message,
                order_number,
                current_status,
                reason_text,
                order_status_keyboard()
            )
            return

        ok = update_order_status(order_number, new_status)
        order = get_order_by_number(order_number)

        admin_states[uid] = {"step": "admin"}

        if not ok or not order:
            await message.answer(
                rtl("<b>⚠️ לא הצלחתי לעדכן את ההזמנה.</b>"),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            return

        client_msg = CLIENT_STATUS_MESSAGE.get(new_status, "סטטוס ההזמנה שלך עודכן.")

        try:
            await message.bot.send_message(
                order["telegram_id"],
                rtl(f"{client_msg}\n\n{field('מספר הזמנה', order_number)}"),
                parse_mode="HTML"
            )
        except Exception:
            pass

        await message.answer(
            rtl(
                "<b>✅ סטטוס ההזמנה עודכן</b>\n\n"
                f"{field('מספר הזמנה', order_number)}\n"
                f"{field('סטטוס חדש', status_label(new_status))}"
            ),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    if step == "add_category":
        if len(txt) < 2:
            await message.answer(rtl("<b>⚠️ נא לרשום קטגוריה תקינה.</b>"), parse_mode="HTML")
            return

        state["category"] = txt
        state["step"] = "add_name"
        await message.answer(rtl("<b>➕ הוספת מוצר</b>\n\nרשום שם מוצר."), parse_mode="HTML")
        return

    if step == "add_name":
        if len(txt) < 2:
            await message.answer(rtl("<b>⚠️ נא לרשום שם מוצר תקין.</b>"), parse_mode="HTML")
            return

        state["name"] = txt
        state["step"] = "add_price"
        await message.answer(rtl("<b>💰 מחיר מוצר</b>\n\nרשום מחיר בשקלים.\nלדוגמה: 548"), parse_mode="HTML")
        return

    if step == "add_price":
        try:
            price = float(txt)
            if price <= 0:
                raise ValueError
        except Exception:
            await message.answer(rtl("<b>⚠️ נא לרשום מחיר תקין במספרים בלבד.</b>"), parse_mode="HTML")
            return

        state["price"] = price
        state["step"] = "add_description"
        await message.answer(rtl("<b>📝 תיאור מוצר</b>\n\nרשום תיאור קצר למוצר."), parse_mode="HTML")
        return

    if step == "add_description":
        state["description"] = txt
        state["step"] = "add_max_qty"
        await message.answer(rtl("<b>🔢 כמות מקסימלית</b>\n\nרשום כמות מקסימלית להזמנה אחת.\nלדוגמה: 10"), parse_mode="HTML")
        return

    if step == "add_max_qty":
        if not txt.isdigit() or int(txt) <= 0:
            await message.answer(rtl("<b>⚠️ נא לרשום מספר תקין.</b>"), parse_mode="HTML")
            return

        state["max_qty"] = int(txt)
        state["step"] = "add_stock"
        await message.answer(rtl("<b>📦 מלאי נוכחי</b>\n\nרשום מלאי נוכחי.\nלדוגמה: 37"), parse_mode="HTML")
        return

    if step == "add_stock":
        if not txt.isdigit() or int(txt) < 0:
            await message.answer(rtl("<b>⚠️ נא לרשום מלאי תקין במספרים בלבד.</b>"), parse_mode="HTML")
            return

        state["stock"] = int(txt)
        state["step"] = "add_sku"
        await message.answer(rtl("<b>🏷️ מק״ט</b>\n\nרשום מק״ט / קוד מוצר.\nאם אין, רשום 0"), parse_mode="HTML")
        return

    if step == "add_sku":
        sku = "" if txt == "0" else txt

        add_product(
            category=state["category"],
            name=state["name"],
            price=float(state["price"]),
            description=state["description"],
            max_qty=int(state["max_qty"]),
            stock=int(state["stock"]),
            sku=sku,
            image_file_id="",
            active=1,
        )

        admin_states[uid] = {"step": "admin"}

        text = (
            "<b>✅ המוצר נוסף בהצלחה</b>\n\n"
            f"{field('קטגוריה', state['category'])}\n"
            f"{field('מוצר', state['name'])}\n"
            f"{field('מחיר', money(state['price']))}\n"
            f"{field('מלאי', state['stock'])}\n"
            f"{field('מקסימום להזמנה', state['max_qty'])}\n\n"
            "כדי להוסיף תמונה לחץ על: 🖼️ עדכן תמונה"
        )

        await message.answer(rtl(text), reply_markup=admin_keyboard(), parse_mode="HTML")
        return

    if step == "price_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer(
                rtl("<b>⚠️ המוצר לא נמצא.</b>\nבחר מוצר מהרשימה."),
                reply_markup=product_names_keyboard(),
                parse_mode="HTML"
            )
            return

        state["product_name"] = txt
        state["step"] = "price_value"

        await message.answer(
            rtl(f"<b>✏️ שינוי מחיר</b>\n\n{field('מחיר נוכחי', money(product['price']))}\nרשום מחיר חדש."),
            parse_mode="HTML"
        )
        return

    if step == "price_value":
        try:
            price = float(txt)
            if price <= 0:
                raise ValueError
        except Exception:
            await message.answer(rtl("<b>⚠️ נא לרשום מחיר תקין.</b>"), parse_mode="HTML")
            return

        ok = set_product_price(state["product_name"], price)
        admin_states[uid] = {"step": "admin"}

        text = f"<b>✅ המחיר עודכן</b>\n\n{field('מחיר חדש', money(price))}" if ok else "<b>⚠️ המוצר לא נמצא.</b>"
        await message.answer(rtl(text), reply_markup=admin_keyboard(), parse_mode="HTML")
        return

    if step == "description_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer(
                rtl("<b>⚠️ המוצר לא נמצא.</b>\nבחר מוצר מהרשימה."),
                reply_markup=product_names_keyboard(),
                parse_mode="HTML"
            )
            return

        state["product_name"] = txt
        state["step"] = "description_text"
        await message.answer(rtl("<b>📝 שינוי תיאור</b>\n\nרשום תיאור חדש למוצר."), parse_mode="HTML")
        return

    if step == "description_text":
        ok = set_product_description(state["product_name"], txt)
        admin_states[uid] = {"step": "admin"}

        text = "<b>✅ התיאור עודכן.</b>" if ok else "<b>⚠️ המוצר לא נמצא.</b>"
        await message.answer(rtl(text), reply_markup=admin_keyboard(), parse_mode="HTML")
        return

    if step == "stock_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer(
                rtl("<b>⚠️ המוצר לא נמצא.</b>\nבחר מוצר מהרשימה."),
                reply_markup=product_names_keyboard(),
                parse_mode="HTML"
            )
            return

        state["product_name"] = txt
        state["step"] = "stock_value"

        await message.answer(
            rtl(f"<b>📊 עדכון מלאי</b>\n\n{field('מלאי נוכחי', product['stock'])}\nרשום מלאי חדש."),
            parse_mode="HTML"
        )
        return

    if step == "stock_value":
        if not txt.isdigit() or int(txt) < 0:
            await message.answer(rtl("<b>⚠️ נא לרשום מלאי תקין.</b>"), parse_mode="HTML")
            return

        ok = set_product_stock(state["product_name"], int(txt))
        admin_states[uid] = {"step": "admin"}

        text = f"<b>✅ המלאי עודכן</b>\n\n{field('מלאי חדש', txt)}" if ok else "<b>⚠️ המוצר לא נמצא.</b>"
        await message.answer(rtl(text), reply_markup=admin_keyboard(), parse_mode="HTML")
        return

    if step == "add_stock_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer(
                rtl("<b>⚠️ המוצר לא נמצא.</b>\nבחר מוצר מהרשימה."),
                reply_markup=product_names_keyboard(),
                parse_mode="HTML"
            )
            return

        state["product_name"] = txt
        state["step"] = "add_stock_value"

        await message.answer(
            rtl(f"<b>➕ הוספה למלאי</b>\n\n{field('מלאי נוכחי', product['stock'])}\nכמה יחידות להוסיף?"),
            parse_mode="HTML"
        )
        return

    if step == "add_stock_value":
        if not txt.isdigit() or int(txt) <= 0:
            await message.answer(rtl("<b>⚠️ נא לרשום מספר חיובי.</b>"), parse_mode="HTML")
            return

        ok = add_stock(state["product_name"], int(txt))
        admin_states[uid] = {"step": "admin"}

        text = f"<b>✅ המלאי עודכן</b>\n\n{field('נוספו יחידות', txt)}" if ok else "<b>⚠️ המוצר לא נמצא.</b>"
        await message.answer(rtl(text), reply_markup=admin_keyboard(), parse_mode="HTML")
        return

    if step == "image_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer(
                rtl("<b>⚠️ המוצר לא נמצא.</b>\nבחר מוצר מהרשימה."),
                reply_markup=product_names_keyboard(),
                parse_mode="HTML"
            )
            return

        state["product_name"] = txt
        state["step"] = "image_photo"

        await message.answer(
            rtl(f"<b>🖼️ עדכון תמונה</b>\n\n{field('מוצר', txt)}\nעכשיו שלח תמונה של המוצר."),
            parse_mode="HTML"
        )
        return

    if step == "off_name":
        ok = set_product_active(txt, 0)
        admin_states[uid] = {"step": "admin"}

        text = f"<b>🔴 המוצר כובה</b>\n\n{field('מוצר', txt)}" if ok else "<b>⚠️ המוצר לא נמצא.</b>"
        await message.answer(rtl(text), reply_markup=admin_keyboard(), parse_mode="HTML")
        return

    if step == "on_name":
        ok = set_product_active(txt, 1)
        admin_states[uid] = {"step": "admin"}

        text = f"<b>🟢 המוצר הופעל</b>\n\n{field('מוצר', txt)}" if ok else "<b>⚠️ המוצר לא נמצא.</b>"
        await message.answer(rtl(text), reply_markup=admin_keyboard(), parse_mode="HTML")
        return

    if step == "delete_name":
        ok = delete_product(txt)
        admin_states[uid] = {"step": "admin"}

        text = f"<b>🗑️ המוצר נמחק</b>\n\n{field('מוצר', txt)}" if ok else "<b>⚠️ המוצר לא נמצא.</b>"
        await message.answer(rtl(text), reply_markup=admin_keyboard(), parse_mode="HTML")
        return
