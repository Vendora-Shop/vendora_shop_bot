from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_ID


def main_keyboard(user_id=None):
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="🔐 פאנל ניהול")])

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 חנות")],
            [KeyboardButton(text="👤 הפרטים שלי"), KeyboardButton(text="📦 ההזמנות שלי")],
            [KeyboardButton(text="🏠 הכתובות שלי")],
            [KeyboardButton(text="📞 שירות לקוחות")]
        ],
        resize_keyboard=True
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
            [KeyboardButton(text="🔄 עדכן סטטוס הזמנה")],
            [KeyboardButton(text="➕ הוסף מוצר"), KeyboardButton(text="📦 רשימת מוצרים")],
            [KeyboardButton(text="✏️ שנה מחיר"), KeyboardButton(text="📝 שנה תיאור")],
            [KeyboardButton(text="📊 עדכן מלאי"), KeyboardButton(text="➕ הוסף למלאי")],
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
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔁 הזמן שוב")],
            [KeyboardButton(text="⬅️ חזרה לתפריט")]
        ],
        resize_keyboard=True
    )

def addresses_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 הצג כתובות")],
            [KeyboardButton(text="➕ הוסף כתובת")],
            [KeyboardButton(text="⬅️ חזרה לתפריט")]
        ],
        resize_keyboard=True
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
    keyboard.append([KeyboardButton(text="⬅️ חזרה לתפריט")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def address_actions_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗑️ מחק כתובת")],
            [KeyboardButton(text="⬅️ חזרה לרשימת כתובות")],
            [KeyboardButton(text="⬅️ חזרה לתפריט")]
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
    keyboard.append([KeyboardButton(text="⬅️ חזרה לתפריט")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )
