from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 חנות")],
            [KeyboardButton(text="📞 שירות לקוחות")]
        ],
        resize_keyboard=True
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
            [KeyboardButton(text="📋 הזמנות אחרונות"), KeyboardButton(text="🆕 הזמנות חדשות")],
            [KeyboardButton(text="🔄 עדכן סטטוס הזמנה")],
            [KeyboardButton(text="⬅️ יציאה מניהול")]
        ],
        resize_keyboard=True
    )


def order_status_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ אושרה"), KeyboardButton(text="📦 בטיפול")],
            [KeyboardButton(text="🚚 יצאה למשלוח"), KeyboardButton(text="💰 שולם")],
            [KeyboardButton(text="🏁 הושלמה"), KeyboardButton(text="❌ בוטלה")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )
