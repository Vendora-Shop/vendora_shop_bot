from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID


def support_tickets_button_text():
    try:
        from database import get_open_support_tickets_count
        count = get_open_support_tickets_count()
    except Exception:
        count = 0

    if count > 0:
        return f"📩 פניות שירות ({count})"

    return "📩 פניות שירות"



def compact_menu_keyboard():
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()



def main_menu_inline_keyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton(text="חנות 🛒", callback_data="main_menu:shop")],
        [InlineKeyboardButton(text="ההזמנות שלי 📦", callback_data="main_menu:orders")],
        [InlineKeyboardButton(text="הפרטים שלי 👤", callback_data="main_menu:profile")],
        [InlineKeyboardButton(text="הכתובות שלי 🏠", callback_data="main_menu:addresses")],
        [InlineKeyboardButton(text="שירות לקוחות 📞", callback_data="main_menu:support")]
    ]

    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text="פאנל ניהול 🔐", callback_data="main_menu:admin")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def main_keyboard(user_id=None):
    keyboard = [
        [KeyboardButton(text="חנות 🛒")],
        [KeyboardButton(text="ההזמנות שלי 📦")],
        [KeyboardButton(text="הפרטים שלי 👤")],
        [KeyboardButton(text="הכתובות שלי 🏠")],
        [KeyboardButton(text="שירות לקוחות 📞")]
    ]

    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="פאנל ניהול 🔐")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="בחר פעולה מהתפריט"
    )



def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 ניהול הזמנות")],
            [KeyboardButton(text="🧾 הזמנות אחרונות"), KeyboardButton(text="🆕 הזמנות חדשות")],
            [KeyboardButton(text="🔎 חפש הזמנה"), KeyboardButton(text="📞 חפש לפי טלפון")],
            [KeyboardButton(text="📊 מצב העסק"), KeyboardButton(text="📅 סטטיסטיקה לפי תאריך")],
            [KeyboardButton(text="📢 שלח הודעה ללקוחות")],
            [KeyboardButton(text="👥 לקוחות")],
            [KeyboardButton(text=support_tickets_button_text())],
            [KeyboardButton(text="🔄 עדכן סטטוס הזמנה")],
            [KeyboardButton(text="🧹 איפוס מערכת הזמנות")],
            [KeyboardButton(text="➕ הוסף מוצר"), KeyboardButton(text="📦 רשימת מוצרים")],
            [KeyboardButton(text="✏️ שנה מחיר"), KeyboardButton(text="📝 שנה תיאור")],
            [KeyboardButton(text="✏️ אפס והגדר מלאי חדש"), KeyboardButton(text="➕ הגדל מלאי קיים")],
            [KeyboardButton(text="🖼️ עדכן תמונה")],
            [KeyboardButton(text="🔴 כבה מוצר"), KeyboardButton(text="🟢 הפעל מוצר")],
            [KeyboardButton(text="🗑️ מחק מוצר")],
            [KeyboardButton(text="⬅️ יציאה מניהול")]
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
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 הזמן שוב", callback_data="cust_btn:reorder")],
            [InlineKeyboardButton(text="⬅️ חזרה לתפריט", callback_data="cust_btn:main_menu")]
        ]
    )



def addresses_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 הצג כתובות", callback_data="cust_btn:show_addresses")],
            [InlineKeyboardButton(text="➕ הוסף כתובת", callback_data="cust_btn:add_address")],
            [InlineKeyboardButton(text="⬅️ חזרה לתפריט", callback_data="cust_btn:main_menu")]
        ]
    )


def address_select_keyboard(addresses):
    keyboard = []

    for address in addresses:
        address_id = address.get("id")
        label = address.get("label") or "כתובת"
        city = address.get("city") or "-"
        street = address.get("street") or "-"
        keyboard.append([KeyboardButton(text=f"🏠 {address_id} | {label} | {city}, {street}")])

    keyboard.append([KeyboardButton(text="➕ הוסף כתובת")])
    keyboard.append([KeyboardButton(text="⬅️ חזרה לכתובות")])
    keyboard.append([KeyboardButton(text="חזרה לתפריט הראשי ↩️")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def address_actions_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗑️ מחק כתובת")],
            [KeyboardButton(text="⬅️ חזרה לרשימת כתובות")],
            [KeyboardButton(text="חזרה לתפריט הראשי ↩️")]
        ],
        resize_keyboard=True
    )




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
    keyboard = []

    for order in orders:
        order_number = order.get("order_number")
        total = int(float(order.get("final_total") or 0))
        status = translate_order_status_for_keyboard(order.get("status"))

        keyboard.append([
            KeyboardButton(text=f"🔁 {order_number} | {total}₪ | {status}")
        ])

    keyboard.append([KeyboardButton(text="⬅️ חזרה להזמנות שלי")])
    keyboard.append([KeyboardButton(text="חזרה לתפריט הראשי ↩️")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )



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
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 שאלה על הזמנה קיימת", callback_data="cust_text:support_order")],
            [InlineKeyboardButton(text="🚚 משלוח / איסוף", callback_data="cust_text:support_fulfillment")],
            [InlineKeyboardButton(text="💳 תשלום", callback_data="cust_text:support_payment")],
            [InlineKeyboardButton(text="🛍️ מוצר / מלאי", callback_data="cust_text:support_product")],
            [InlineKeyboardButton(text="📝 שינוי פרטים", callback_data="cust_text:support_details")],
            [InlineKeyboardButton(text="❓ אחר", callback_data="cust_text:support_other")],
            [InlineKeyboardButton(text="⬅️ חזרה לתפריט", callback_data="cust_btn:main_menu")]
        ]
    )


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
