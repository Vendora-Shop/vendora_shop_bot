from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_ID
from keyboards import admin_keyboard, main_keyboard
from database import get_all_products

router = Router()


def is_admin(user_id):
    return user_id == ADMIN_ID


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🔐 פאנל ניהול Vendora",
        reply_markup=admin_keyboard()
    )


@router.message(F.text == "⬅️ יציאה מניהול")
async def exit_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "יצאת מפאנל הניהול.",
        reply_markup=main_keyboard()
    )


@router.message(F.text == "📦 רשימת מוצרים")
async def products_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = get_all_products()

    if not rows:
        await message.answer("אין מוצרים במערכת.")
        return

    text = "📦 רשימת מוצרים:\n\n"

    for row in rows:
        product_id, category, name, price, description, max_qty, stock, sku, image_file_id, active = row

        status = "✅ פעיל" if active else "❌ כבוי"

        text += (
            f"🛍 {name}\n"
            f"קטגוריה: {category}\n"
            f"מחיר: ₪{price}\n"
            f"מלאי: {stock}\n"
            f"{status}\n\n"
        )

    await message.answer(text)
