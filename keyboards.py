from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID



def _inline_customer(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _ibtn(text, data):
    return InlineKeyboardButton(text=text, callback_data=data)


def support_tickets_button_text():
    try:
        from database import get_open_support_tickets_count
        count = get_open_support_tickets_count()
    except Exception:
        count = 0

    if count > 0:
        return f"📩 פניות שירות ({count})"

    return "📩 פניות שירות"



def main_keyboard(user_id=None):
    """תפריט לקוח Inline — בלי מקלדת שקופצת למטה."""
    keyboard = [
        [InlineKeyboardButton(text="🛒 חנות", callback_data="ui:main:shop")],
        [InlineKeyboardButton(text="👤 הפרטים שלי", callback_data="ui:main:details")],
        [InlineKeyboardButton(text="📦 ההזמנות שלי", callback_data="ui:main:orders")],
        [InlineKeyboardButton(text="🏠 הכתובות שלי", callback_data="ui:main:addresses")],
        [InlineKeyboardButton(text="📞 שירות לקוחות", callback_data="ui:main:support")],
    ]

    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text="🔐 פאנל ניהול", callback_data="ui:main:admin")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def admin_keyboard():
    # ADMIN_PANEL_CATEGORIES_V1
    # תפריט ראשי נקי — רק קטגוריות. כל הפעולות הישנות נשארות בתתי־תפריטים.
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 ניהול הזמנות")],
            [KeyboardButton(text="🛍️ ניהול מוצרים"), KeyboardButton(text="📊 ניהול מלאי")],
            [KeyboardButton(text="👥 ניהול לקוחות"), KeyboardButton(text="🏷️ קופונים ומבצעים")],
            [KeyboardButton(text="🎧 שירות לקוחות"), KeyboardButton(text="📢 שיווק והודעות")],
            [KeyboardButton(text="📊 סטטיסטיקה ודוחות"), KeyboardButton(text="⚙️ הגדרות מערכת")],
            [KeyboardButton(text="⬅️ יציאה מניהול")]
        ],
        resize_keyboard=True
    )


def admin_orders_menu_keyboard():
    # ADMIN_ORDERS_MENU_NO_DUPLICATES_FINAL
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 הזמנות פתוחות")],
            [KeyboardButton(text="🆕 הזמנות חדשות"), KeyboardButton(text="🧾 הזמנות אחרונות")],
            [KeyboardButton(text="🔎 חפש הזמנה"), KeyboardButton(text="📞 חפש לפי טלפון")],
            [KeyboardButton(text="🔄 עדכן סטטוס הזמנה")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def admin_products_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ הוסף מוצר"), KeyboardButton(text="📦 רשימת מוצרים")],
            [KeyboardButton(text="✏️ שנה מחיר"), KeyboardButton(text="📝 שנה תיאור")],
            [KeyboardButton(text="🖼️ עדכן תמונה")],
            [KeyboardButton(text="🔴 כבה מוצר"), KeyboardButton(text="🟢 הפעל מוצר")],
            [KeyboardButton(text="🗑️ מחק מוצר")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def admin_stock_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ אפס והגדר מלאי חדש")],
            [KeyboardButton(text="➕ הגדל מלאי קיים")],
            [KeyboardButton(text="📦 רשימת מוצרים")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def admin_customers_menu_root_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 לקוחות")],
            [KeyboardButton(text="🔎 חפש לקוח")],
            [KeyboardButton(text="📢 שלח הודעה ללקוחות")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def admin_coupons_root_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏷️ ניהול קופונים")],
            [KeyboardButton(text="➕ צור קופון")],
            [KeyboardButton(text="📋 רשימת קופונים")],
            [KeyboardButton(text="🔴 כבה קופון"), KeyboardButton(text="🟢 הפעל קופון")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def admin_marketing_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 שלח הודעה ללקוחות")],
            [KeyboardButton(text="👥 לקוחות")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def admin_support_root_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=support_tickets_button_text())],
            [KeyboardButton(text="📬 פניות פתוחות"), KeyboardButton(text="📁 פניות סגורות")],
            [KeyboardButton(text="🔍 חיפוש פנייה")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def admin_reports_menu_keyboard():
    # ADMIN_REPORTS_MENU_NO_DUPLICATES_FINAL
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 מצב העסק")],
            [KeyboardButton(text="📅 סטטיסטיקה לפי תאריך")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def admin_settings_menu_keyboard():
    # ADMIN_SYSTEM_RESET_ONLY_HERE_FINAL
    # ADMIN_BACKUP_MANAGER_BUTTONS_FIX
    # SETTINGS_MENU_NO_PRODUCT_ACTIONS_FIX
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💾 צור גיבוי DB")],
            [KeyboardButton(text="📋 רשימת גיבויים")],
            [KeyboardButton(text="📄 רשימת לוגים")],
            [KeyboardButton(text="🧹 איפוס מערכת הזמנות")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )




def order_status_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ אושרה"), KeyboardButton(text="📦 בטיפול")],
            [KeyboardButton(text="🚚 יצאה למשלוח")],
            [KeyboardButton(text="✅ הושלמה"), KeyboardButton(text="❌ בוטלה")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )

def broadcast_confirm_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ אשר ושלח ללקוחות")],
            [KeyboardButton(text="✏️ ערוך הודעה")],
            [KeyboardButton(text="❌ בטל שליחה")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )

def customers_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 רשימת לקוחות")],
            [KeyboardButton(text="🔎 חפש לקוח")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def customer_actions_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 היסטוריית הזמנות לקוח")],
            [KeyboardButton(text="⬅️ חזרה לרשימת לקוחות")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )

def my_orders_keyboard():
    return _inline_customer([
        [_ibtn("🔁 הזמנה חוזרת", "ui:orders:reorder")],
        [_ibtn("⬅️ חזרה לתפריט", "ui:nav:main")],
    ])

def addresses_menu_keyboard():
    return _inline_customer([
        [_ibtn("📋 הצג כתובות", "ui:addr:show")],
        [_ibtn("➕ הוסף כתובת", "ui:addr:add")],
        [_ibtn("⬅️ חזרה לתפריט", "ui:nav:main")],
    ])

def address_select_keyboard(addresses):
    rows = []

    for address in addresses:
        address_id = address.get("id")
        label = address.get("label") or "כתובת"
        city = address.get("city") or "-"
        street = address.get("street") or "-"
        rows.append([_ibtn(f"🏠 {address_id} | {label} | {city}, {street}", f"ui:addr:id:{address_id}")])

    rows.append([_ibtn("➕ הוסף כתובת", "ui:addr:add")])
    rows.append([_ibtn("⬅️ חזרה לכתובות", "ui:addr:menu")])
    rows.append([_ibtn("⬅️ חזרה לתפריט", "ui:nav:main")])

    return _inline_customer(rows)

def address_actions_keyboard():
    return _inline_customer([
        [_ibtn("🗑️ מחק כתובת", "ui:addr:delete")],
        [_ibtn("⬅️ חזרה לרשימת כתובות", "ui:addr:back_list")],
        [_ibtn("⬅️ חזרה לתפריט", "ui:nav:main")],
    ])

def translate_order_status_for_keyboard(status):
    statuses = {
        "new": "חדשה",
        "approved": "אושרה",
        "processing": "בטיפול",
        "shipping": "בדרך",
        "done": "הושלמה",
        "completed": "הושלמה",
        "cancelled": "בוטלה",
        "canceled": "בוטלה"
    }

    return statuses.get(str(status or "").lower(), str(status or "-"))


def reorder_select_keyboard(orders):
    rows = []

    for order in orders:
        order_number = order.get("order_number")
        total = int(float(order.get("final_total") or 0))
        status = translate_order_status_for_keyboard(order.get("status"))
        rows.append([_ibtn(f"🔁 {order_number} | {total}₪ | {status}", f"ui:reorder:{order_number}")])

    rows.append([_ibtn("⬅️ חזרה להזמנות שלי", "ui:orders:back_my_orders")])
    rows.append([_ibtn("⬅️ חזרה לתפריט", "ui:nav:main")])

    return _inline_customer(rows)

def customer_select_keyboard(customers):
    keyboard = []

    for customer in customers:
        customer_id = customer.get("id")
        name = customer.get("customer_name") or customer.get("telegram_name") or "לקוח"
        phone = customer.get("phone") or "-"
        total_orders = customer.get("total_orders") or 0

        keyboard.append([
            KeyboardButton(text=f"👤 {customer_id} | {name} | {phone} | {total_orders} הזמנות")
        ])

    keyboard.append([KeyboardButton(text="⬅️ חזרה ללקוחות")])
    keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )



def support_subject_keyboard():
    subjects = [
        "📦 שאלה על הזמנה קיימת",
        "🚚 משלוח / איסוף",
        "💳 תשלום",
        "🛍️ מוצר / מלאי",
        "📝 שינוי פרטים",
        "❓ אחר",
    ]
    rows = [[_ibtn(subject, f"ui:support:subject:{i}")] for i, subject in enumerate(subjects)]
    rows.append([_ibtn("⬅️ חזרה לתפריט", "ui:nav:main")])
    return _inline_customer(rows)

def support_tickets_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📬 פניות פתוחות")],
            [KeyboardButton(text="📁 פניות סגורות")],
            [KeyboardButton(text="🔍 חיפוש פנייה")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def support_ticket_actions_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="↩️ השב ללקוח")],
            [KeyboardButton(text="📄 ייצוא TXT")],
            [KeyboardButton(text="✅ סגור פנייה")],
            [KeyboardButton(text="⬅️ חזרה לפניות שירות")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )



def closed_support_ticket_actions_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 ייצוא TXT")],
            [KeyboardButton(text="⬅️ חזרה לפניות שירות")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


def support_ticket_select_keyboard(tickets, back_text="⬅️ חזרה לפניות שירות"):
    keyboard = []

    for ticket in tickets:
        ticket_number = ticket.get("ticket_number")
        subject = ticket.get("subject") or "ללא נושא"
        phone = ticket.get("phone") or "-"
        name = ticket.get("telegram_name") or "לקוח"
        status = "פתוחה" if ticket.get("status") == "open" else "סגורה"

        keyboard.append([
            KeyboardButton(text=f"📩 {ticket_number} | {subject} | {phone} | {name} | {status}")
        ])

    keyboard.append([KeyboardButton(text=back_text)])
    keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )
