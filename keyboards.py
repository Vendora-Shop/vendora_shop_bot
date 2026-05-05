from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 חנות")],
            [KeyboardButton(text="👤 הפרטים שלי"), KeyboardButton(text="📞 שירות לקוחות")]
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
