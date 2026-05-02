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
            [KeyboardButton(text="⬅️ יציאה מניהול")]
        ],
        resize_keyboard=True
    )
