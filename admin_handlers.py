from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

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
    get_today_statistics,
)

router = Router()
admin_states = {}


STATUS_TEXT = {
    "new": "🆕 הזמנה חדשה",
    "approved": "✅ אושרה",
    "processing": "📦 בטיפול",
    "shipping": "🚚 יצאה למשלוח",
    "paid": "💰 שולם",
    "done": "✅ הושלמה",
    "cancelled": "❌ בוטלה",
}

STATUS_BY_BUTTON = {
    "✅ אושרה": "approved",
    "📦 בטיפול": "processing",
    "🚚 יצאה למשלוח": "shipping",
    "💰 שולם": "paid",
    "✅ הושלמה": "done",
    "❌ בוטלה": "cancelled",
}

CLIENT_STATUS_MESSAGE = {
    "approved": "✅ ההזמנה שלך אושרה. נציג ייצור איתך קשר להמשך טיפול.",
    "processing": "📦 ההזמנה שלך בטיפול.",
    "shipping": "🚚 ההזמנה שלך יצאה למשלוח.",
    "paid": "💰 התשלום עבור ההזמנה התקבל. תודה!",
    "done": "✅ ההזמנה הושלמה. תודה שקנית ב־Vendora Shop!",
    "cancelled": "❌ ההזמנה בוטלה. לפרטים נוספים ניתן לפנות לשירות לקוחות.",
}


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


def format_order(order):
    status = STATUS_TEXT.get(order["status"], order["status"])

    text = f"🧾 הזמנה {order['order_number']}\n"
    text += f"סטטוס: {status}\n"
    text += f"👤 לקוח: {order['customer_name']}\n"
    text += f"📞 טלפון: {order['phone']}\n"
    text += f"📍 כתובת: {order['address']}\n"
    text += f"💰 סה״כ: ₪{float(order['final_total']):g}\n"
    text += f"🕒 נוצרה: {order['created_at']}\n\n"
    text += "🛒 מוצרים:\n"

    for item in order["cart"]:
        total = float(item["price"]) * int(item["qty"])
        text += f"• {item['name']} × {item['qty']} = ₪{total:g}\n"

    return text


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


@router.message(F.text == "🧾 הזמנות אחרונות")
async def recent_orders(message: Message):
    if not is_admin(message.from_user.id):
        return

    orders = get_recent_orders(10)

    if not orders:
        await message.answer("אין הזמנות במערכת.")
        return

    for order in orders:
        await message.answer(format_order(order))


@router.message(F.text == "🆕 הזמנות חדשות")
async def new_orders(message: Message):
    if not is_admin(message.from_user.id):
        return

    orders = get_orders_by_status("new", 20)

    if not orders:
        await message.answer("אין הזמנות חדשות.")
        return

    for order in orders:
        await message.answer(format_order(order))


@router.message(F.text == "🔎 חפש הזמנה")
async def search_order_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "search_order"}
    await message.answer("רשום מספר הזמנה. לדוגמה: V1001")


@router.message(F.text == "📞 חפש לפי טלפון")
async def search_by_phone_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "search_phone"}
    await message.answer("רשום מספר טלפון לחיפוש.\nלדוגמה: 0547937503")


@router.message(F.text == "📊 סטטיסטיקה יומית")
async def daily_statistics(message: Message):
    if not is_admin(message.from_user.id):
        return

    stats = get_today_statistics()

    top_product = stats["top_product"] or "אין עדיין"
    top_qty = stats["top_qty"]

    text = (
        f"📊 סטטיסטיקה יומית\n"
        f"📅 תאריך: {stats['date']}\n\n"
        f"🧾 סה״כ הזמנות: {stats['total_orders']}\n"
        f"💰 סה״כ מחזור: ₪{stats['total_money']:g}\n\n"
        f"🆕 חדשות: {stats['new']}\n"
        f"✅ אושרו: {stats['approved']}\n"
        f"📦 בטיפול: {stats['processing']}\n"
        f"🚚 במשלוח: {stats['shipping']}\n"
        f"💰 שולמו: {stats['paid']}\n"
        f"✅ הושלמו: {stats['done']}\n"
        f"❌ בוטלו: {stats['cancelled']}\n\n"
        f"🏆 מוצר מוביל: {top_product}\n"
        f"🔢 כמות נמכרת: {top_qty}"
    )

    await message.answer(text)


@router.message(F.text == "🔄 עדכן סטטוס הזמנה")
async def update_order_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "status_order_number"}
    await message.answer("רשום מספר הזמנה לעדכון סטטוס. לדוגמה: V1001")


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


@router.message(is_admin_active_step)
async def admin_flow(message: Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    state = admin_states.get(uid)
    step = state.get("step")

    if step == "search_order":
        order = get_order_by_number(txt)

        admin_states[uid] = {"step": "admin"}

        if not order:
            await message.answer("ההזמנה לא נמצאה.", reply_markup=admin_keyboard())
            return

        await message.answer(format_order(order), reply_markup=admin_keyboard())
        return

    if step == "search_phone":
        orders = get_orders_by_phone(txt, 20)

        admin_states[uid] = {"step": "admin"}

        if not orders:
            await message.answer("לא נמצאו הזמנות למספר הזה.", reply_markup=admin_keyboard())
            return

        await message.answer(f"נמצאו {len(orders)} הזמנות למספר {txt}:", reply_markup=admin_keyboard())

        for order in orders:
            await message.answer(format_order(order))

        return

    if step == "status_order_number":
        order = get_order_by_number(txt)

        if not order:
            await message.answer("ההזמנה לא נמצאה. רשום מספר הזמנה תקין.")
            return

        state["order_number"] = txt
        state["step"] = "status_value"

        await message.answer(
            f"נבחרה הזמנה {txt}\nבחר סטטוס חדש:",
            reply_markup=order_status_keyboard()
        )
        return

    if step == "status_value":
        if txt not in STATUS_BY_BUTTON:
            await message.answer("בחר סטטוס מתוך הכפתורים.")
            return

        order_number = state["order_number"]
        new_status = STATUS_BY_BUTTON[txt]

        ok = update_order_status(order_number, new_status)
        order = get_order_by_number(order_number)

        admin_states[uid] = {"step": "admin"}

        if not ok or not order:
            await message.answer("לא הצלחתי לעדכן את ההזמנה.", reply_markup=admin_keyboard())
            return

        client_msg = CLIENT_STATUS_MESSAGE.get(new_status, "סטטוס ההזמנה שלך עודכן.")

        try:
            await message.bot.send_message(
                order["telegram_id"],
                f"{client_msg}\n\n🧾 מספר הזמנה: {order_number}"
            )
        except Exception:
            pass

        await message.answer(
            f"✅ סטטוס ההזמנה עודכן:\n"
            f"{order_number} → {STATUS_TEXT.get(new_status, new_status)}",
            reply_markup=admin_keyboard()
        )
        return

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

        await message.answer(
            f"✅ המחיר עודכן ל־₪{price:g}" if ok else "המוצר לא נמצא.",
            reply_markup=admin_keyboard()
        )
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

        await message.answer(
            "✅ התיאור עודכן." if ok else "המוצר לא נמצא.",
            reply_markup=admin_keyboard()
        )
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

        await message.answer(
            "✅ המלאי עודכן." if ok else "המוצר לא נמצא.",
            reply_markup=admin_keyboard()
        )
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

        await message.answer(
            f"✅ נוספו {txt} יחידות למלאי." if ok else "המוצר לא נמצא.",
            reply_markup=admin_keyboard()
        )
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

        await message.answer(
            "✅ המוצר כובה." if ok else "המוצר לא נמצא.",
            reply_markup=admin_keyboard()
        )
        return

    if step == "on_name":
        ok = set_product_active(txt, 1)
        admin_states[uid] = {"step": "admin"}

        await message.answer(
            "✅ המוצר הופעל." if ok else "המוצר לא נמצא.",
            reply_markup=admin_keyboard()
        )
        return

    if step == "delete_name":
        ok = delete_product(txt)
        admin_states[uid] = {"step": "admin"}

        await message.answer(
            "🗑️ המוצר נמחק." if ok else "המוצר לא נמצא.",
            reply_markup=admin_keyboard()
        )
        return
