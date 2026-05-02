from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_ID
from keyboards import admin_keyboard, main_keyboard
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
)

router = Router()
admin_states = {}


def is_admin(user_id):
    return user_id == ADMIN_ID


def product_names_keyboard():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

    rows = get_all_products()
    keyboard = []

    for row in rows:
        product_id, category, name, price, description, max_qty, stock, sku, image_file_id, active = row
        keyboard.append([KeyboardButton(text=name)])

    keyboard.append([KeyboardButton(text="⬅️ חזרה לניהול")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "admin"}
    await message.answer("🔐 פאנל ניהול Vendora", reply_markup=admin_keyboard())


@router.message(F.text == "⬅️ יציאה מניהול")
async def exit_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states.pop(message.from_user.id, None)
    await message.answer("יצאת מפאנל הניהול.", reply_markup=main_keyboard())


@router.message(F.text == "⬅️ חזרה לניהול")
async def back_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "admin"}
    await message.answer("חזרת לפאנל הניהול.", reply_markup=admin_keyboard())


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
        image = "🖼️ יש תמונה" if image_file_id else "⚠️ ללא תמונה"
        stock_text = "❌ אזל מהמלאי" if int(stock) <= 0 else f"📦 מלאי: {stock}"

        text += (
            f"━━━━━━━━━━━━\n"
            f"🛍️ {name}\n"
            f"{status} | {image}\n"
            f"קטגוריה: {category}\n"
            f"מק״ט: {sku or '-'}\n"
            f"💰 מחיר: ₪{float(price):g}\n"
            f"{stock_text}\n"
            f"🔢 מקסימום להזמנה: {max_qty}\n"
            f"📝 תיאור: {description or '-'}\n\n"
        )

    await message.answer(text)


@router.message(F.text == "➕ הוסף מוצר")
async def add_product_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "add_category"}
    await message.answer("רשום קטגוריה למוצר.\nלדוגמה: תיק משלוחים")


@router.message(F.text == "✏️ שנה מחיר")
async def price_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "price_name"}
    await message.answer("בחר מוצר לשינוי מחיר:", reply_markup=product_names_keyboard())


@router.message(F.text == "📝 שנה תיאור")
async def description_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "description_name"}
    await message.answer("בחר מוצר לשינוי תיאור:", reply_markup=product_names_keyboard())


@router.message(F.text == "📊 עדכן מלאי")
async def stock_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "stock_name"}
    await message.answer("בחר מוצר לעדכון מלאי:", reply_markup=product_names_keyboard())


@router.message(F.text == "➕ הוסף למלאי")
async def add_stock_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "add_stock_name"}
    await message.answer("בחר מוצר להוספת מלאי:", reply_markup=product_names_keyboard())


@router.message(F.text == "🖼️ עדכן תמונה")
async def image_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "image_name"}
    await message.answer("בחר מוצר לעדכון תמונה:", reply_markup=product_names_keyboard())


@router.message(F.text == "🔴 כבה מוצר")
async def off_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "off_name"}
    await message.answer("בחר מוצר לכיבוי:", reply_markup=product_names_keyboard())


@router.message(F.text == "🟢 הפעל מוצר")
async def on_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "on_name"}
    await message.answer("בחר מוצר להפעלה:", reply_markup=product_names_keyboard())


@router.message(F.text == "🗑️ מחק מוצר")
async def delete_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "delete_name"}
    await message.answer("בחר מוצר למחיקה:", reply_markup=product_names_keyboard())


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

    await message.answer(
        f"✅ התמונה עודכנה למוצר:\n{product_name}" if ok else "המוצר לא נמצא.",
        reply_markup=admin_keyboard()
    )


@router.message()
async def admin_flow(message: Message):
    uid = message.from_user.id

    if not is_admin(uid):
        return

    state = admin_states.get(uid)
    if not state:
        return

    txt = (message.text or "").strip()
    step = state.get("step")

    if step == "add_category":
        state["category"] = txt
        state["step"] = "add_name"
        await message.answer("רשום שם מוצר.")
        return

    if step == "add_name":
        state["name"] = txt
        state["step"] = "add_price"
        await message.answer("רשום מחיר בשקלים. לדוגמה: 548")
        return

    if step == "add_price":
        try:
            price = float(txt)
            if price <= 0:
                raise ValueError
        except Exception:
            await message.answer("נא לרשום מחיר תקין במספרים בלבד.")
            return

        state["price"] = price
        state["step"] = "add_description"
        await message.answer("רשום תיאור קצר למוצר.")
        return

    if step == "add_description":
        state["description"] = txt
        state["step"] = "add_max_qty"
        await message.answer("רשום כמות מקסימלית להזמנה אחת. לדוגמה: 10")
        return

    if step == "add_max_qty":
        if not txt.isdigit() or int(txt) <= 0:
            await message.answer("נא לרשום מספר תקין.")
            return

        state["max_qty"] = int(txt)
        state["step"] = "add_stock"
        await message.answer("רשום מלאי נוכחי. לדוגמה: 37")
        return

    if step == "add_stock":
        if not txt.isdigit() or int(txt) < 0:
            await message.answer("נא לרשום מלאי תקין במספרים בלבד.")
            return

        state["stock"] = int(txt)
        state["step"] = "add_sku"
        await message.answer("רשום מק״ט / קוד מוצר. אם אין, רשום 0")
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

        await message.answer(
            f"✅ המוצר נוסף בהצלחה:\n\n"
            f"קטגוריה: {state['category']}\n"
            f"מוצר: {state['name']}\n"
            f"מחיר: ₪{float(state['price']):g}\n"
            f"מלאי: {state['stock']}\n"
            f"מקסימום להזמנה: {state['max_qty']}\n\n"
            f"כדי להוסיף תמונה לחץ: 🖼️ עדכן תמונה",
            reply_markup=admin_keyboard()
        )
        return

    if step == "price_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
            return

        state["product_name"] = txt
        state["step"] = "price_value"
        await message.answer(f"מחיר נוכחי: ₪{float(product['price']):g}\nרשום מחיר חדש.")
        return

    if step == "price_value":
        try:
            price = float(txt)
            if price <= 0:
                raise ValueError
        except Exception:
            await message.answer("נא לרשום מחיר תקין.")
            return

        ok = set_product_price(state["product_name"], price)
        admin_states[uid] = {"step": "admin"}
        await message.answer(f"✅ המחיר עודכן ל־₪{price:g}" if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
        return

    if step == "description_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
            return

        state["product_name"] = txt
        state["step"] = "description_text"
        await message.answer("רשום תיאור חדש למוצר.")
        return

    if step == "description_text":
        ok = set_product_description(state["product_name"], txt)
        admin_states[uid] = {"step": "admin"}
        await message.answer("✅ התיאור עודכן." if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
        return

    if step == "stock_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
            return

        state["product_name"] = txt
        state["step"] = "stock_value"
        await message.answer(f"מלאי נוכחי: {product['stock']}\nרשום מלאי חדש.")
        return

    if step == "stock_value":
        if not txt.isdigit() or int(txt) < 0:
            await message.answer("נא לרשום מלאי תקין.")
            return

        ok = set_product_stock(state["product_name"], int(txt))
        admin_states[uid] = {"step": "admin"}
        await message.answer("✅ המלאי עודכן." if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
        return

    if step == "add_stock_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
            return

        state["product_name"] = txt
        state["step"] = "add_stock_value"
        await message.answer(f"מלאי נוכחי: {product['stock']}\nכמה יחידות להוסיף למלאי?")
        return

    if step == "add_stock_value":
        if not txt.isdigit() or int(txt) <= 0:
            await message.answer("נא לרשום מספר חיובי.")
            return

        ok = add_stock(state["product_name"], int(txt))
        admin_states[uid] = {"step": "admin"}
        await message.answer(f"✅ נוספו {txt} יחידות למלאי." if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
        return

    if step == "image_name":
        product = get_product_by_name(txt)
        if not product:
            await message.answer("המוצר לא נמצא. בחר מוצר מהרשימה.", reply_markup=product_names_keyboard())
            return

        state["product_name"] = txt
        state["step"] = "image_photo"
        await message.answer(f"נבחר מוצר: {txt}\nעכשיו שלח תמונה של המוצר.")
        return

    if step == "off_name":
        ok = set_product_active(txt, 0)
        admin_states[uid] = {"step": "admin"}
        await message.answer("✅ המוצר כובה." if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
        return

    if step == "on_name":
        ok = set_product_active(txt, 1)
        admin_states[uid] = {"step": "admin"}
        await message.answer("✅ המוצר הופעל." if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
        return

    if step == "delete_name":
        ok = delete_product(txt)
        admin_states[uid] = {"step": "admin"}
        await message.answer("🗑️ המוצר נמחק." if ok else "המוצר לא נמצא.", reply_markup=admin_keyboard())
        return
