import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from html import escape
from datetime import datetime
import calendar
import json

from config import ADMIN_ID
from keyboards import admin_keyboard, main_keyboard, order_status_keyboard, broadcast_confirm_keyboard, customers_menu_keyboard, customer_actions_keyboard, customer_select_keyboard, support_tickets_menu_keyboard, support_ticket_actions_keyboard, closed_support_ticket_actions_keyboard, support_ticket_select_keyboard
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
    get_all_customer_telegram_ids,
    get_customers_list,
    search_customers,
    get_customer_by_id,
    get_orders_by_customer_telegram_id,
    clear_all_orders_for_testing,
    get_support_tickets_by_status,
    get_support_ticket,
    get_support_messages,
    add_support_message,
    close_support_ticket,
)

router = Router()
admin_states = {}


# ================== CUSTOMER STATUS MENU BOTTOM FIX V3 ==================
# שומר ומוחק את תפריט הלקוח האחרון גם אם הוא נשלח מ-shop_handlers.
CUSTOMER_MENU_STORE_FILE = "customer_menu_messages.json"


def load_customer_menu_store():
    try:
        if os.path.exists(CUSTOMER_MENU_STORE_FILE):
            with open(CUSTOMER_MENU_STORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_customer_menu_store(store):
    try:
        with open(CUSTOMER_MENU_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False)
    except Exception as e:
        print(f"CUSTOMER_MENU_STORE_SAVE_ERROR: {type(e).__name__}: {e}")


async def delete_customer_last_menu(bot, customer_telegram_id):
    store = load_customer_menu_store()
    old_menu_id = store.pop(str(customer_telegram_id), None)
    save_customer_menu_store(store)

    if old_menu_id:
        try:
            await bot.delete_message(customer_telegram_id, int(old_menu_id))
        except Exception:
            pass








def status_customer_inline_main_keyboard(customer_telegram_id=None):
    """
    STATUS_CUSTOMER_INLINE_MAIN_KEYBOARD_FIX
    תפריט לקוח Inline בתוך הצ'אט, לא ReplyKeyboard תחתון.
    זה העיצוב הירוק/זכוכית כמו בתפריט הראשי.
    """
    keyboard = [
        [InlineKeyboardButton(text="חנות 🛒", callback_data="ui:main:shop")],
        [
            InlineKeyboardButton(text="הפרופיל שלי 👤", callback_data="ui:main:details"),
            InlineKeyboardButton(text="ההזמנות שלי 📋", callback_data="ui:main:orders"),
        ],
        [
            InlineKeyboardButton(text="הכתובות שלי 📍", callback_data="ui:main:addresses"),
            InlineKeyboardButton(text="שירות לקוחות 💬", callback_data="ui:main:support"),
        ],
    ]

    try:
        if customer_telegram_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton(text="פאנל ניהול 🛡️", callback_data="ui:main:admin")])
    except Exception:
        pass

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def send_customer_main_menu_bottom(bot, customer_telegram_id):
    try:
        menu_text = widen_inline_screen_text(rtl(
            "<b>🏠 תפריט ראשי</b>\n\n"
            "בחר פעולה מהתפריט שלך:"
        ))

        sent_menu = await bot.send_message(
            customer_telegram_id,
            menu_text,
            reply_markup=status_customer_inline_main_keyboard(customer_telegram_id),
            parse_mode="HTML"
        )

        store = load_customer_menu_store()
        store[str(customer_telegram_id)] = int(sent_menu.message_id)
        save_customer_menu_store(store)

        return sent_menu
    except Exception as e:
        print(f"CUSTOMER_MENU_BOTTOM_SEND_ERROR: {type(e).__name__}: {e}")
        return None


async def send_customer_status_with_menu(bot, customer_telegram_id, status_text):
    """
    STATUS_MENU_DELETE_AND_RESEND_FIX_V3
    מוחק תפריט קודם, שולח סטטוס, ואז שולח תפריט חדש בתחתית.
    """
    await delete_customer_last_menu(bot, customer_telegram_id)

    try:
        await bot.send_message(
            customer_telegram_id,
            rtl(status_text),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"CUSTOMER_STATUS_SEND_ERROR: {type(e).__name__}: {e}")
        return

    await send_customer_main_menu_bottom(bot, customer_telegram_id)




def support_reply_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ בטל תשובה")],
            [KeyboardButton(text="⬅️ חזרה לניהול")]
        ],
        resize_keyboard=True
    )


RTL = "\u200F"


def widen_inline_screen_text(text):
    """
    מרחיב הודעות עם InlineKeyboard כדי שהכפתורים ייפתחו רחב יותר.
    """
    invisible = "\u2063" * 140
    return f"{text}\n{invisible}"


# ================== ADMIN SAFE INPUT CLEANUP ==================
async def delete_admin_message(message: Message):
    try:
        await message.delete()
    except Exception:
        pass


def is_admin_button_only_step(step):
    return step in {
        "admin",
        "orders_section",
        "orders_select",
        "order_actions",
        "customers_menu",
        "customers_select",
        "customer_profile",
        "broadcast_confirm",
        "status_value",
        "image_photo",
    }


def is_valid_admin_button_text(text):
    text = clean_admin_text(text)

    fixed_buttons = {
        "🔐 פאנל ניהול",
        "📦 ניהול הזמנות",
        "🧾 הזמנות אחרונות",
        "🆕 הזמנות חדשות",
        "🔎 חפש הזמנה",
        "📞 חפש לפי טלפון",
        "📊 מצב העסק",
        "📅 סטטיסטיקה לפי תאריך",
        "📢 שלח הודעה ללקוחות",
        "👥 לקוחות",
        "לקוחות 👥",
        "🔄 עדכן סטטוס הזמנה",
        "➕ הוסף מוצר",
        "📦 רשימת מוצרים",
        "✏️ שנה מחיר",
        "📝 שנה תיאור",
        "✏️ אפס והגדר מלאי חדש",
        "➕ הגדל מלאי קיים",
        "🖼️ עדכן תמונה",
        "🔴 כבה מוצר",
        "🟢 הפעל מוצר",
        "🗑️ מחק מוצר",
        "⬅️ יציאה מניהול",
        "⬅️ חזרה לניהול",
        "⬅️ חזרה לניהול הזמנות",
        "⬅️ חזרה לרשימת הזמנות",
        "📋 הזמנות פתוחות",
        "🆕 חדשות",
        "✅ אושרו",
        "📦 בטיפול",
        "🚚 במשלוח",
        "🧾 הושלמו",
        "❌ בוטלו",
        "✅ אשר הזמנה",
        "📦 העבר לטיפול",
        "📦 העבר להכנה",
        "🚚 סמן כיצא למשלוח",
        "🛍️ מוכן לאיסוף",
        "✅ סמן כהושלם",
        "✅ סמן כנאסף",
        "❌ בטל הזמנה",
        "📋 רשימת לקוחות",
        "🔎 חפש לקוח",
        "⬅️ חזרה ללקוחות",
        "⬅️ חזרה לרשימת לקוחות",
        "📦 היסטוריית הזמנות לקוח",
        "✅ אשר ושלח ללקוחות",
        "✏️ ערוך הודעה",
        "❌ בטל שליחה",
        "✅ אושרה",
        "📦 בטיפול",
        "🚚 יצאה למשלוח",
        "✅ הושלמה",
        "❌ בוטלה",
        "◀️ חודש קודם",
        "📍 היום",
        "📩 פניות שירות",
        "📬 פניות פתוחות",
        "📁 פניות סגורות",
        "🔍 חיפוש פנייה",
        "↩️ השב ללקוח",
        "📄 ייצוא TXT",
        "✅ סגור פנייה",
        "⬅️ חזרה לפניות שירות",
        "▶️ חודש הבא",
    }

    if text in fixed_buttons:
        return True

    if text.startswith("📩 פניות שירות"):
        return True

    if text.startswith("🧾 "):
        return True

    if text.startswith("👤 "):
        return True

    if text.startswith("📅 "):
        return True

    return False


# ============================================================
# CUSTOMERS + BROADCAST CLEAN FEATURE
# ============================================================

def clean_admin_text(text):
    return str(text or "").replace("\u200f", "").replace("\u200e", "").strip()


def is_customers_list_button(text):
    text = clean_admin_text(text)
    return "רשימת לקוחות" in text


def is_customer_search_button(text):
    text = clean_admin_text(text)
    return "חפש לקוח" in text


def is_customers_menu_button(text):
    text = clean_admin_text(text)
    return text in {"👥 לקוחות", "לקוחות 👥"}


def is_broadcast_button(text):
    text = clean_admin_text(text)
    return "שלח הודעה ללקוחות" in text


async def open_customers_menu_screen(message: Message):
    admin_states[message.from_user.id] = {"step": "customers_menu"}

    await message.answer(
        rtl(
            "<b>👥 ניהול לקוחות</b>\n\n"
            "בחר פעולה מהתפריט."
        ),
        reply_markup=customers_menu_keyboard(),
        parse_mode="HTML"
    )


async def open_customers_list_screen(message: Message):
    customers = get_customers_list(50)

    if not customers:
        admin_states[message.from_user.id] = {"step": "customers_menu"}
        await message.answer(
            rtl(
                "<b>👥 רשימת לקוחות</b>\n\n"
                "אין עדיין לקוחות שמורים במערכת."
            ),
            reply_markup=customers_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    admin_states[message.from_user.id] = {
        "step": "customers_select",
        "customers_last_mode": "list"
    }

    await message.answer(
        rtl(
            "<b>👥 רשימת לקוחות</b>\n\n"
            f"נמצאו {len(customers)} לקוחות.\n"
            "בחר לקוח מהרשימה כדי לפתוח כרטיס."
        ),
        reply_markup=customer_select_keyboard(customers),
        parse_mode="HTML"
    )


async def open_customer_search_screen(message: Message):
    admin_states[message.from_user.id] = {"step": "customers_search"}

    await message.answer(
        rtl(
            "<b>🔎 חיפוש לקוח</b>\n\n"
            "רשום שם, טלפון או שם Telegram לחיפוש."
        ),
        parse_mode="HTML"
    )


async def run_customer_search_screen(message: Message):
    uid = message.from_user.id
    query = clean_admin_text(message.text)

    if len(query) < 2:
        await message.answer(
            rtl(
                "<b>⚠️ חיפוש קצר מדי</b>\n\n"
                "רשום לפחות 2 תווים לחיפוש."
            ),
            parse_mode="HTML"
        )
        return

    customers = search_customers(query, 50)

    if not customers:
        admin_states[uid] = {"step": "customers_menu"}
        await message.answer(
            rtl(
                "<b>🔎 תוצאות חיפוש</b>\n\n"
                "לא נמצאו לקוחות לפי החיפוש הזה."
            ),
            reply_markup=customers_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    admin_states[uid] = {
        "step": "customers_select",
        "customers_last_mode": "search",
        "customers_last_query": query
    }

    await message.answer(
        rtl(
            "<b>🔎 תוצאות חיפוש</b>\n\n"
            f"נמצאו {len(customers)} לקוחות.\n"
            "בחר לקוח מהרשימה כדי לפתוח כרטיס."
        ),
        reply_markup=customer_select_keyboard(customers),
        parse_mode="HTML"
    )


async def open_broadcast_screen(message: Message):
    customer_ids = get_all_customer_telegram_ids()

    if not customer_ids:
        admin_states[message.from_user.id] = {"step": "admin"}
        await message.answer(
            rtl(
                "<b>📢 שליחת הודעה ללקוחות</b>\n\n"
                "אין כרגע לקוחות שמורים לשליחה."
            ),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    admin_states[message.from_user.id] = {
        "step": "broadcast_text",
        "broadcast_customer_count": len(customer_ids)
    }

    await message.answer(
        rtl(
            "<b>📢 שליחת הודעה ללקוחות</b>\n\n"
            f"{field('לקוחות זמינים לשליחה', len(customer_ids))}\n\n"
            "רשום עכשיו את ההודעה שברצונך לשלוח.\n\n"
            "<b>חשוב:</b>\n"
            "ההודעה לא תישלח מיד.\n"
            "קודם תקבל תצוגה מקדימה ותצטרך לאשר שליחה."
        ),
        parse_mode="HTML"
    )


async def handle_broadcast_text_screen(message: Message):
    uid = message.from_user.id
    state = admin_states.get(uid)

    if not state:
        return

    broadcast_text = clean_broadcast_text(clean_admin_text(message.text))
    is_valid, error_text = validate_broadcast_text(broadcast_text)

    if not is_valid:
        await message.answer(
            rtl(
                "<b>⚠️ הודעה לא תקינה</b>\n\n"
                f"{h(error_text)}\n\n"
                "רשום הודעה חדשה או לחץ: ⬅️ חזרה לניהול."
            ),
            parse_mode="HTML"
        )
        return

    customer_ids = get_all_customer_telegram_ids()

    if not customer_ids:
        admin_states[uid] = {"step": "admin"}
        await message.answer(
            rtl(
                "<b>⚠️ אין לקוחות לשליחה</b>\n\n"
                "לא נמצאו לקוחות שמורים במערכת."
            ),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    state["broadcast_text"] = broadcast_text
    state["broadcast_customer_ids"] = customer_ids
    state["step"] = "broadcast_confirm"

    await message.answer(
        format_broadcast_preview(broadcast_text, len(customer_ids)),
        reply_markup=broadcast_confirm_keyboard(),
        parse_mode="HTML"
    )


async def handle_broadcast_confirm_screen(message: Message):
    uid = message.from_user.id
    state = admin_states.get(uid)
    txt = clean_admin_text(message.text)

    if not state:
        return

    if txt == "❌ בטל שליחה":
        admin_states[uid] = {"step": "admin"}
        await message.answer(
            rtl(
                "<b>✅ השליחה בוטלה</b>\n\n"
                "ההודעה לא נשלחה לאף לקוח."
            ),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    if txt == "✏️ ערוך הודעה":
        state.pop("broadcast_text", None)
        state.pop("broadcast_customer_ids", None)
        state["step"] = "broadcast_text"

        await message.answer(
            rtl(
                "<b>✏️ עריכת הודעה</b>\n\n"
                "רשום את ההודעה החדשה לשליחה."
            ),
            parse_mode="HTML"
        )
        return

    if txt != "✅ אשר ושלח ללקוחות":
        await message.answer(
            rtl(
                "<b>⚠️ פעולה לא תקינה</b>\n\n"
                "בחר פעולה מתוך הכפתורים בלבד."
            ),
            reply_markup=broadcast_confirm_keyboard(),
            parse_mode="HTML"
        )
        return

    if state.get("broadcast_sent"):
        admin_states[uid] = {"step": "admin"}
        await message.answer(
            rtl(
                "<b>⚠️ הפעולה כבר בוצעה</b>\n\n"
                "ההודעה כבר נשלחה ללקוחות."
            ),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    broadcast_text = state.get("broadcast_text")
    customer_ids = state.get("broadcast_customer_ids") or []

    if not broadcast_text or not customer_ids:
        admin_states[uid] = {"step": "admin"}
        await message.answer(
            rtl(
                "<b>⚠️ לא ניתן לבצע שליחה</b>\n\n"
                "חסרים נתוני שליחה. התחל את התהליך מחדש."
            ),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    state["broadcast_sent"] = True

    sent_count = 0
    failed_count = 0

    for customer_id in customer_ids:
        try:
            await message.bot.send_message(
                customer_id,
                rtl(broadcast_text),
                parse_mode="HTML"
            )
            sent_count += 1
        except Exception:
            failed_count += 1

    admin_states[uid] = {"step": "admin"}

    await message.answer(
        rtl(
            "<b>✅ שליחת הודעה הסתיימה</b>\n\n"
            f"{field('נשלחו בהצלחה', sent_count)}\n"
            f"{field('נכשלו', failed_count)}"
        ),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )



# ================== SUPPORT TICKETS ADMIN ==================

def extract_ticket_number_from_button(text):
    text = str(text or "").strip()

    if text.startswith("📩 "):
        text = text.replace("📩 ", "", 1)

    if "|" in text:
        return text.split("|", 1)[0].strip()

    return text.strip()


def support_status_label(status):
    return "פתוחה" if status == "open" else "סגורה"


def support_ticket_keyboard_by_status(ticket):
    if ticket and ticket.get("status") == "closed":
        return closed_support_ticket_actions_keyboard()

    return support_ticket_actions_keyboard()


def support_ticket_text(ticket):
    if not ticket:
        return rtl("<b>⚠️ הפנייה לא נמצאה.</b>")

    messages = get_support_messages(ticket["ticket_number"])

    text = (
        "<b>📩 פנייה לשירות לקוחות</b>\n\n"
        f"{field('מספר פנייה', ticket.get('ticket_number'))}\n"
        f"{field('סטטוס', support_status_label(ticket.get('status')))}\n"
        f"{field('נושא פנייה', ticket.get('subject') or 'ללא נושא')}\n"
        f"{field('שם Telegram', ticket.get('telegram_name') or '-')}\n"
        f"{field('Telegram ID', ticket.get('telegram_id') or '-')}\n"
        f"{field('פלאפון', ticket.get('phone') or '-')}\n"
        f"{field('נפתחה בתאריך', ticket.get('created_at') or '-')}\n"
    )

    if ticket.get("closed_at"):
        text += f"{field('נסגרה בתאריך', ticket.get('closed_at'))}\n"

    text += "\n<b>שיחה:</b>\n"

    if not messages:
        text += "אין עדיין הודעות בפנייה."
        return rtl(text)

    for msg in messages[-20:]:
        sender = "לקוח" if msg.get("sender_type") == "customer" else "אדמין"
        text += (
            f"\n<b>{h(sender)} | {h(msg.get('created_at') or '-')}</b>\n"
            f"{h(msg.get('message_text') or '')}\n"
        )

    return rtl(text)


def export_support_ticket_to_txt(ticket_number):
    ticket = get_support_ticket(ticket_number)
    messages = get_support_messages(ticket_number)

    if not ticket:
        return None

    file_path = os.path.join("/tmp", f"support_ticket_{ticket_number}.txt")

    lines = [
        f"Support Ticket: {ticket.get('ticket_number')}",
        f"Status: {support_status_label(ticket.get('status'))}",
        f"Subject: {ticket.get('subject') or '-'}",
        f"Telegram Name: {ticket.get('telegram_name') or '-'}",
        f"Telegram ID: {ticket.get('telegram_id') or '-'}",
        f"Phone: {ticket.get('phone') or '-'}",
        f"Created At: {ticket.get('created_at') or '-'}",
        f"Closed At: {ticket.get('closed_at') or '-'}",
        "",
        "Messages:",
        ""
    ]

    for msg in messages:
        sender = "Customer" if msg.get("sender_type") == "customer" else "Admin"
        lines.append(f"[{msg.get('created_at')}] {sender} ({msg.get('sender_name') or '-'}):")
        lines.append(msg.get("message_text") or "")
        lines.append("")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return file_path


# ================== PICKUP DISPLAY SETTINGS ==================
# תצוגת איסוף עצמי בפאנל אדמין.
# אם שינית את הכתובת ב־shop_handlers.py, עדכן גם כאן כדי שהתצוגה באדמין תהיה זהה.
ADMIN_PICKUP_POINT_NAME = "Vendora"
ADMIN_PICKUP_POINT_ADDRESS = "אשדוד - הבנאים 2"
ADMIN_PICKUP_PREP_TIME = "כ־30 דקות"
ADMIN_PICKUP_HOURS = "א׳-ה׳ 10:00-19:00, ו׳ 09:00-13:00"
ADMIN_PICKUP_NAVIGATION_URL = "https://www.google.com/maps/search/?api=1&query=אשדוד%20הבנאים%202"


STATUS_TEXT = {
    "new": "🆕 חדשה",
    "approved": "✅ אושרה",
    "processing": "📦 בטיפול",
    "shipping": "🚚 יצאה למשלוח",
    "done": "✅ הושלמה",
    "cancelled": (
        "❌ ההזמנה בוטלה לאחר בדיקה.\n\n"
        "ייתכן שהביטול בוצע בעקבות בעיית תשלום, מלאי או פרט נוסף בהזמנה.\n"
        "לפרטים נוספים ניתן לפנות לשירות לקוחות."
    ),
}

STATUS_BY_BUTTON = {
    "✅ אושרה": "approved",
    "📦 בטיפול": "processing",
    "🚚 יצאה למשלוח": "shipping",
    "✅ הושלמה": "done",
    "❌ בוטלה": "cancelled",
}

CLIENT_STATUS_MESSAGE = {
    "approved": "<b>✅ ההזמנה שלך אושרה.</b>\n\nנציג ייצור איתך קשר להמשך טיפול.",

    "processing": "📦 ההזמנה שלך בטיפול.",

    "shipping": "🚚 ההזמנה שלך יצאה למשלוח.",

    "done": "✅ ההזמנה הושלמה. תודה שקנית ב־ Vendora Shop!",

    "cancelled": "❌ ההזמנה בוטלה. לפרטים נוספים ניתן לפנות לשירות לקוחות.",
}




# ================== REAL TIME ORDER NOTIFICATIONS ==================
NOTIFICATION_ACTION_BY_BUTTON = {
    "approve": "approved",
    "processing": "processing",
    "shipping": "shipping",
    "done": "done",
    "cancel": "cancelled",
}


def order_notification_keyboard(order_number, status):
    order = get_order_by_number(order_number)
    pickup = is_order_pickup(order) if order else False

    buttons = []

    if status == "new":
        buttons.append([
            InlineKeyboardButton(text="✅ אשר הזמנה", callback_data=f"order_action:approve:{order_number}"),
            InlineKeyboardButton(text="❌ בטל", callback_data=f"order_action:cancel:{order_number}")
        ])

    elif status == "approved":
        if pickup:
            buttons.append([
                InlineKeyboardButton(text="📦 העבר להכנה", callback_data=f"order_action:processing:{order_number}"),
                InlineKeyboardButton(text="❌ בטל", callback_data=f"order_action:cancel:{order_number}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="📦 העבר לטיפול", callback_data=f"order_action:processing:{order_number}"),
                InlineKeyboardButton(text="❌ בטל", callback_data=f"order_action:cancel:{order_number}")
            ])

    elif status == "processing":
        if pickup:
            buttons.append([
                InlineKeyboardButton(text="🛍️ מוכן לאיסוף", callback_data=f"order_action:shipping:{order_number}"),
                InlineKeyboardButton(text="❌ בטל", callback_data=f"order_action:cancel:{order_number}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="🚚 יצא למשלוח", callback_data=f"order_action:shipping:{order_number}"),
                InlineKeyboardButton(text="❌ בטל", callback_data=f"order_action:cancel:{order_number}")
            ])

    elif status == "shipping":
        if pickup:
            buttons.append([
                InlineKeyboardButton(text="✅ נאסף", callback_data=f"order_action:done:{order_number}"),
                InlineKeyboardButton(text="❌ בטל", callback_data=f"order_action:cancel:{order_number}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="✅ הושלמה", callback_data=f"order_action:done:{order_number}"),
                InlineKeyboardButton(text="❌ בטל", callback_data=f"order_action:cancel:{order_number}")
            ])

    else:
        # בסטטוס סופי אין צורך בכפתור "צפייה בלבד".
        # ההזמנה נשארת מוצגת כהודעה רגילה ללא כפתורים.
        return None

    return InlineKeyboardMarkup(inline_keyboard=buttons)


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


# ============================================================
# MISSING ADMIN HELPERS — CUSTOMERS / BROADCAST / PRODUCTS
# ============================================================

def format_product_row(row):
    product_id, category, name, price, description, max_qty, stock, sku, image_file_id, active = row

    status = "פעיל 🟢" if int(active or 0) == 1 else "כבוי 🔴"

    return (
        f"<b>📦 {h(name)}</b>\n\n"
        f"{field('קטגוריה', category)}\n"
        f"{field('מחיר', money(price))}\n"
        f"{field('מלאי', stock)}\n"
        f"{field('מקסימום להזמנה', max_qty)}\n"
        f"{field('מק״ט', sku or '-')}\n"
        f"{field('סטטוס', status)}\n"
        f"{field('תיאור', description or '-')}"
    )


def extract_customer_id_from_button(text):
    text = str(text or "").strip()

    if text.startswith("👤"):
        text = text.replace("👤", "", 1).strip()

    if "|" in text:
        first = text.split("|", 1)[0].strip()
    else:
        first = text.strip()

    try:
        return int(first)
    except Exception:
        return None


def format_customer_profile(customer):
    return rtl(
        "<b>👤 כרטיס לקוח</b>\n\n"
        f"{field('שם לקוח', customer.get('customer_name') or '-')}\n"
        f"{field('טלפון', customer.get('phone') or '-')}\n"
        f"{field('Telegram', customer.get('telegram_name') or '-')}\n"
        f"{field('Telegram ID', customer.get('telegram_id') or '-')}\n\n"
        f"{field('עיר', customer.get('city') or '-')}\n"
        f"{field('רחוב', customer.get('street') or '-')}\n"
        f"{field('קומה', customer.get('floor') or '-')}\n"
        f"{field('דירה', customer.get('apartment') or '-')}\n\n"
        f"{field('הזמנה אחרונה', customer.get('last_order_number') or '-')}\n"
        f"{field('סה״כ הזמנות', customer.get('total_orders') or 0)}\n"
        f"{field('סה״כ רכישות', money(customer.get('total_spent') or 0))}"
    )


def format_customer_orders_summary(customer, orders):
    text = (
        "<b>📦 היסטוריית הזמנות לקוח</b>\n\n"
        f"{field('לקוח', customer.get('customer_name') or '-')}\n"
        f"{field('טלפון', customer.get('phone') or '-')}\n\n"
    )

    if not orders:
        return rtl(text + "אין הזמנות להצגה עבור הלקוח הזה.")

    for order in orders[:10]:
        text += (
            f"🧾 <b>{h(order.get('order_number'))}</b>\n"
            f"{field('תאריך', order.get('created_at') or '-')}\n"
            f"{field('סטטוס', status_label_for_order(order))}\n"
            f"{field('סה״כ', money(order.get('final_total') or 0))}\n\n"
        )

    return rtl(text)


def clean_broadcast_text(text):
    return str(text or "").strip()


def validate_broadcast_text(text):
    text = str(text or "").strip()

    if len(text) < 2:
        return False, "ההודעה קצרה מדי."

    if len(text) > 3500:
        return False, "ההודעה ארוכה מדי. קצר אותה לפני השליחה."

    return True, ""


def format_broadcast_preview(text, count):
    return rtl(
        "<b>📢 תצוגה מקדימה לשליחה</b>\n\n"
        f"{field('לקוחות לשליחה', count)}\n\n"
        "<b>תוכן ההודעה:</b>\n"
        f"{h(text)}\n\n"
        "בחר אם לאשר שליחה, לערוך או לבטל."
    )


async def send_broadcast_to_customers(bot, text, customer_ids):
    sent = 0
    failed = 0

    for customer_id in customer_ids:
        try:
            await bot.send_message(
                int(customer_id),
                rtl(text),
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            failed += 1

    return sent, failed



def is_admin(user_id):
    return user_id == ADMIN_ID



def is_customer_navigation_button_for_admin_guard(text):
    text = clean_admin_text(text)

    return text in {
        "🛒 חנות",
        "🛒 הסל שלי",
        "📦 ההזמנות שלי",
        "🏠 הכתובות שלי",
        "👤 הפרטים שלי",
        "📞 שירות לקוחות",
        "⬅️ חזרה",
        "⬅️ חזרה לקטגוריות",
        "⬅️ חזרה לתפריט",
        "➕ הוסף עוד מוצר",
        "✅ המשך להזמנה",
        "🧹 רוקן סל",
        "❌ בטל הזמנה",
        "✅ אשר הזמנה",
        "✏️ שנה פרטים",
        "🚚 משלוח עד הבית",
        "🛍️ איסוף עצמי מהחנות",
        "✅ המשך עם הפרטים השמורים",
        "✅ חזור לפרטים השמורים",
        "✏️ הזן פרטים חדשים",
        "✅ סימולציית תשלום הצליחה",
        "⬅️ חזרה לסיכום הזמנה",
        "❌ ביטול תשלום",
        "🔁 הזמן שוב",
        "⬅️ חזרה להזמנות שלי",
        "📋 הצג כתובות",
        "➕ הוסף כתובת",
        "🗑️ מחק כתובת",
        "⬅️ חזרה לכתובות",
        "⬅️ חזרה לרשימת כתובות",
        "✅ הבעיה נפתרה",
        "📦 שאלה על הזמנה קיימת",
        "🚚 משלוח / איסוף",
        "💳 תשלום",
        "🛍️ מוצר / מלאי",
        "📝 שינוי פרטים",
        "❓ אחר",
    }


def is_admin_active_step(message: Message):
    uid = message.from_user.id

    if not is_admin(uid):
        return False

    txt = clean_admin_text(message.text)

    if txt.startswith("/"):
        return False

    state = admin_states.get(uid)

    if not state:
        return False

    step = state.get("step")

    if step == "admin":
        return False

    # כפתורי פעולת הזמנה באדמין חופפים לכפתורי לקוח.
    # כשהאדמין נמצא בכרטיס הזמנה, חייבים לתת עדיפות ל-admin_flow.
    if step == "order_actions" and txt in ORDER_ACTION_BY_BUTTON:
        return True

    if step == "orders_section" and txt in ORDER_SECTION_BY_BUTTON:
        return True

    # אם האדמין משתמש בצד הלקוח, לא לתת ל-admin_handlers
    # לתפוס כפתורי חנות/חזרה ולהחזיר אותו לבד לפאנל ניהול.
    if is_customer_navigation_button_for_admin_guard(txt):
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


def order_action_keyboard(order_status, pickup=False):
    if order_status in {"done", "cancelled"}:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⬅️ חזרה לרשימת הזמנות")],
                [KeyboardButton(text="⬅️ חזרה לניהול")]
            ],
            resize_keyboard=True
        )

    keyboard = []

    if order_status == "new":
        keyboard.append([KeyboardButton(text="✅ אשר הזמנה"), KeyboardButton(text="❌ בטל הזמנה")])

    elif order_status == "approved":
        if pickup:
            keyboard.append([KeyboardButton(text="📦 העבר להכנה"), KeyboardButton(text="❌ בטל הזמנה")])
        else:
            keyboard.append([KeyboardButton(text="📦 העבר לטיפול"), KeyboardButton(text="❌ בטל הזמנה")])

    elif order_status == "processing":
        if pickup:
            keyboard.append([KeyboardButton(text="🛍️ מוכן לאיסוף"), KeyboardButton(text="❌ בטל הזמנה")])
        else:
            keyboard.append([KeyboardButton(text="🚚 סמן כיצא למשלוח"), KeyboardButton(text="❌ בטל הזמנה")])

    elif order_status == "shipping":
        if pickup:
            keyboard.append([KeyboardButton(text="✅ סמן כנאסף"), KeyboardButton(text="❌ בטל הזמנה")])
        else:
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
    "📦 העבר להכנה": "processing",
    "🚚 סמן כיצא למשלוח": "shipping",
    "🛍️ מוכן לאיסוף": "shipping",
    "✅ סמן כהושלם": "done",
    "✅ סמן כנאסף": "done",
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


def status_label_for_order(order):
    status = order.get("status") if order else ""

    if is_order_pickup(order):
        pickup_statuses = {
            "new": "🆕 חדשה",
            "approved": "✅ אושרה",
            "processing": "📦 בהכנה",
            "shipping": "🛍️ מוכן לאיסוף",
            "done": "✅ נאספה",
            "cancelled": "❌ בוטלה",
        }
        return pickup_statuses.get(status, status)

    return status_label(status)



def is_order_pickup(order):
    return (
        str(order.get("base_city", "")).strip() == "איסוף עצמי"
        or str(order.get("city", "")).strip() == "איסוף עצמי"
    )


def order_fulfillment_text(order):
    if is_order_pickup(order):
        navigation = ""
        if ADMIN_PICKUP_NAVIGATION_URL:
            navigation = f'\n📍 <a href="{h(ADMIN_PICKUP_NAVIGATION_URL)}">פתח ניווט לנקודת האיסוף</a>'

        return (
            "<b>🛍️ איסוף עצמי מהחנות</b>\n"
            f"{field('נקודת איסוף', ADMIN_PICKUP_POINT_NAME)}\n"
            f"{field('כתובת', ADMIN_PICKUP_POINT_ADDRESS)}\n"
            f"{field('שעות איסוף', ADMIN_PICKUP_HOURS)}\n"
            f"{field('זמן הכנה משוער', ADMIN_PICKUP_PREP_TIME)}"
            f"{navigation}"
        )

    return (
        "<b>🚚 משלוח עד הבית</b>\n"
        f"{field('כתובת', order.get('address', '-'))}\n"
        f"{field('אזור משלוח', order.get('base_city') or '-')}"
    )


def format_order(order):
    text = (
        f"<b>🧾 הזמנה {h(order['order_number'])}</b>\n\n"
        f"{field('סטטוס', status_label_for_order(order))}\n"
        f"{field('תאריך', order.get('created_at'))}\n\n"
        f"{field('שם לקוח', order.get('customer_name'))}\n"
        f"{field('טלפון', order.get('phone'))}\n\n"
        f"{order_fulfillment_text(order)}\n\n"
        "<b>🛒 מוצרים</b>\n"
    )

    total_units = 0

    for index, item in enumerate(order.get("cart", []), start=1):
        qty = int(item.get("qty", 0))
        price = float(item.get("price", 0))
        item_total = qty * price
        total_units += qty

        text += (
            f"\n<b>{index}. {h(item.get('name'))}</b>\n"
            f"{field('כמות', qty)}\n"
            f"{field('סה״כ מוצר', money(item_total))}\n"
        )

    text += (
        "\n"
        f"{field('כמות מוצרים', total_units)}\n"
        f"{field('סה״כ מוצרים', money(order.get('products_total') or 0))}\n"
        f"{field('משלוח', money(order.get('delivery_price') or 0))}\n"
        f"{field('סה״כ לתשלום', money(order.get('final_total') or 0))}\n\n"
        f"{field('Telegram ID', order.get('telegram_id'))}\n"
        f"{field('Telegram', order.get('telegram_name') or '-')}"
    )

    return rtl(text)



@router.callback_query(F.data.startswith("order_action:"))
async def order_notification_action(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("אין לך הרשאה לבצע פעולה זו.", show_alert=True)
        return

    parts = (callback.data or "").split(":")

    if len(parts) != 3:
        await callback.answer("פעולה לא תקינה.", show_alert=True)
        return

    _, action, order_number = parts

    order_before = get_order_by_number(order_number)

    if not order_before:
        await callback.answer("ההזמנה לא נמצאה במערכת.", show_alert=True)
        return

    current_status = order_before.get("status")

    if action == "view":
        await callback.answer("הזמנה זו לצפייה בלבד.", show_alert=True)
        return

    if action not in NOTIFICATION_ACTION_BY_BUTTON:
        await callback.answer("פעולה לא תקינה.", show_alert=True)
        return

    new_status = NOTIFICATION_ACTION_BY_BUTTON[action]

    is_valid, reason_text = validate_status_change(current_status, new_status)

    if not is_valid:
        clean_reason = (
            reason_text
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("\\n", "\n")
        )
        await callback.answer(clean_reason, show_alert=True)
        return

    ok = update_order_status(order_number, new_status)
    order = get_order_by_number(order_number)

    if not ok or not order:
        await callback.answer("לא הצלחתי לעדכן את ההזמנה.", show_alert=True)
        return

    if is_order_pickup(order):
        pickup_client_messages = {
            "approved": (
                "<b>✅ ההזמנה שלך אושרה.</b>\n\n"
                "ברגע שההזמנה תהיה מוכנה, תקבלו הודעה לאיסוף "
            
            ),
            "processing": "📦 ההזמנה שלך בהכנה.",
            "shipping": (
                "<b>🛍️ ההזמנה שלך מוכנה לאיסוף.</b>\n\n"
                "ניתן להגיע לנקודת האיסוף בשעות הפעילות."
            ),
            "done": "✅ ההזמנה נאספה. תודה שקנית ב־Vendora Shop!",
            "cancelled": "❌ ההזמנה בוטלה. לפרטים נוספים ניתן לפנות לשירות לקוחות.",
        }
        client_msg = pickup_client_messages.get(new_status, "סטטוס ההזמנה שלך עודכן.")
    else:
        client_msg = CLIENT_STATUS_MESSAGE.get(new_status, "סטטוס ההזמנה שלך עודכן.")

    try:
        await send_customer_status_with_menu(
            callback.bot,
            order["telegram_id"],
            f"{client_msg}\n\n{field('מספר הזמנה', order_number)}"
        )
    except Exception:
        pass

    await callback.answer("סטטוס ההזמנה עודכן בהצלחה.", show_alert=False)

    try:
        await callback.message.edit_text(
            format_order(order),
            reply_markup=order_notification_keyboard(order_number, order.get("status")),
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            format_order(order),
            reply_markup=order_notification_keyboard(order_number, order.get("status")),
            parse_mode="HTML"
        )




@router.callback_query(F.data.startswith("support_reply:"))
async def start_support_reply(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    try:
        customer_id = int((callback.data or "").split(":", 1)[1])
    except Exception:
        await callback.answer("שגיאה בזיהוי הלקוח.", show_alert=True)
        return

    admin_states[callback.from_user.id] = {
        "step": "support_reply",
        "support_reply_customer_id": customer_id
    }

    await callback.message.answer(
        rtl(
            "<b>↩️ תשובה ללקוח</b>\n\n"
            f"{field('Telegram ID', customer_id)}\n\n"
            "כתוב עכשיו את ההודעה שתרצה לשלוח ללקוח."
        ),
        reply_markup=support_reply_cancel_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


@router.message(F.text == "❌ בטל תשובה")
async def cancel_support_reply(message: Message):
    if not is_admin(message.from_user.id):
        return

    state = admin_states.get(message.from_user.id, {})

    if state.get("step") in {"support_reply", "support_ticket_reply"}:
        ticket_number = state.get("support_ticket_number")

        if ticket_number:
            admin_states[message.from_user.id] = {
                "step": "support_ticket_view",
                "support_ticket_number": ticket_number
            }

            ticket = get_support_ticket(ticket_number)

            await message.answer(
                support_ticket_text(ticket),
                reply_markup=support_ticket_actions_keyboard(),
                parse_mode="HTML"
            )
            return

        admin_states[message.from_user.id] = {"step": "admin"}

        await message.answer(
            rtl("<b>✅ התשובה בוטלה.</b>"),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )


@router.message(lambda message: is_admin(message.from_user.id) and admin_states.get(message.from_user.id, {}).get("step") == "support_reply")
async def send_support_reply_to_customer(message: Message):
    state = admin_states.get(message.from_user.id, {})
    customer_id = state.get("support_reply_customer_id")
    reply_text = (message.text or "").strip()

    if not customer_id:
        admin_states[message.from_user.id] = {"step": "admin"}
        await message.answer(
            rtl("<b>⚠️ לא נמצא לקוח לשליחת תשובה.</b>"),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    if not reply_text or reply_text in {"⬅️ חזרה לניהול", "❌ בטל תשובה"}:
        return

    await message.bot.send_message(
        customer_id,
        rtl(
            "<b>📩 תשובה משירות הלקוחות</b>\n\n"
            f"{h(reply_text)}"
        ),
        parse_mode="HTML"
    )

    admin_states[message.from_user.id] = {"step": "admin"}

    await message.answer(
        rtl("<b>✅ התשובה נשלחה ללקוח.</b>"),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🔐 פאנל ניהול")
async def admin_panel_button(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "admin"}

    await message.answer(
        rtl("<b>🔐 פאנל ניהול Vendora</b>\n\nבחר פעולה מהתפריט למטה."),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
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




@router.message(F.text.in_({"👥 לקוחות", "לקוחות 👥"}))
async def customers_panel_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "customers_menu"}

    await message.answer(
        rtl(
            "<b>👥 ניהול לקוחות</b>\n\n"
            "בחר פעולה מהתפריט."
        ),
        reply_markup=customers_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text.in_({"📢 שלח הודעה ללקוחות", "שלח הודעה ללקוחות 📢"}))
async def broadcast_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    customer_ids = get_all_customer_telegram_ids()

    if not customer_ids:
        await message.answer(
            rtl(
                "<b>📢 שליחת הודעה ללקוחות</b>\n\n"
                "אין כרגע לקוחות שמורים לשליחה.\n"
                "לאחר שלקוחות יבצעו הזמנות, הם יופיעו ברשימת השליחה."
            ),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    admin_states[message.from_user.id] = {
        "step": "broadcast_text",
        "broadcast_customer_count": len(customer_ids)
    }

    await message.answer(
        rtl(
            "<b>📢 שליחת הודעה ללקוחות</b>\n\n"
            f"{field('לקוחות זמינים לשליחה', len(customer_ids))}\n\n"
            "רשום עכשיו את ההודעה שברצונך לשלוח.\n\n"
            "<b>חשוב:</b>\n"
            "ההודעה לא תישלח מיד.\n"
            "קודם תקבל תצוגה מקדימה ותצטרך לאשר שליחה."
        ),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ יציאה מניהול")
async def exit_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states.pop(message.from_user.id, None)

    await message.answer(
        rtl("<b>✅ יצאת מפאנל הניהול.</b>"),
        reply_markup=main_keyboard(message.from_user.id),
        parse_mode="HTML"
    )



@router.message(lambda message: clean_admin_text(message.text).startswith("📩 פניות שירות"))
async def support_tickets_menu(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "support_tickets_menu"}

    await message.answer(
        rtl("<b>📩 פניות שירות</b>\n\nבחר פעולה מהתפריט."),
        reply_markup=support_tickets_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ חזרה לפניות שירות")
async def back_to_support_tickets_menu(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "support_tickets_menu"}

    await message.answer(
        rtl("<b>📩 פניות שירות</b>\n\nבחר פעולה מהתפריט."),
        reply_markup=support_tickets_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text.in_({"📬 פניות פתוחות", "📁 פניות סגורות"}))
async def list_support_tickets(message: Message):
    if not is_admin(message.from_user.id):
        return

    status = "open" if message.text == "📬 פניות פתוחות" else "closed"
    tickets = get_support_tickets_by_status(status, 30)

    admin_states[message.from_user.id] = {
        "step": "support_ticket_select",
        "support_ticket_status": status
    }

    title = "📬 פניות פתוחות" if status == "open" else "📁 פניות סגורות"

    if not tickets:
        await message.answer(
            rtl(f"<b>{title}</b>\n\nאין פניות להצגה."),
            reply_markup=support_tickets_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    await message.answer(
        rtl(f"<b>{title}</b>\n\nבחר פנייה מהרשימה כדי לראות את כל ההודעות."),
        reply_markup=support_ticket_select_keyboard(tickets),
        parse_mode="HTML"
    )


@router.message(F.text == "🔍 חיפוש פנייה")
async def search_support_ticket_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "support_ticket_search"}

    await message.answer(
        rtl("<b>🔍 חיפוש פנייה</b>\n\nרשום מספר פנייה. לדוגמה: T1001"),
        parse_mode="HTML"
    )


@router.message(lambda message: is_admin(message.from_user.id) and admin_states.get(message.from_user.id, {}).get("step") == "support_ticket_search")
async def search_support_ticket_run(message: Message):
    ticket_number = clean_admin_text(message.text).upper()
    ticket = get_support_ticket(ticket_number)

    if not ticket:
        admin_states[message.from_user.id] = {"step": "support_tickets_menu"}
        await message.answer(
            rtl("<b>⚠️ הפנייה לא נמצאה.</b>"),
            reply_markup=support_tickets_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    admin_states[message.from_user.id] = {
        "step": "support_ticket_view",
        "support_ticket_number": ticket_number
    }

    await message.answer(
        support_ticket_text(ticket),
        reply_markup=support_ticket_keyboard_by_status(ticket),
        parse_mode="HTML"
    )


@router.message(lambda message: is_admin(message.from_user.id) and admin_states.get(message.from_user.id, {}).get("step") == "support_ticket_select")
async def open_support_ticket_from_list(message: Message):
    ticket_number = extract_ticket_number_from_button(message.text)
    ticket = get_support_ticket(ticket_number)

    if not ticket:
        await message.answer(
            rtl("<b>⚠️ בחר פנייה מתוך הרשימה בלבד.</b>"),
            parse_mode="HTML"
        )
        return

    admin_states[message.from_user.id] = {
        "step": "support_ticket_view",
        "support_ticket_number": ticket_number
    }

    await message.answer(
        support_ticket_text(ticket),
        reply_markup=support_ticket_keyboard_by_status(ticket),
        parse_mode="HTML"
    )


@router.message(F.text == "↩️ השב ללקוח")
async def support_ticket_reply_from_view(message: Message):
    if not is_admin(message.from_user.id):
        return

    state = admin_states.get(message.from_user.id, {})
    ticket_number = state.get("support_ticket_number")
    ticket = get_support_ticket(ticket_number) if ticket_number else None

    if not ticket:
        await message.answer(
            rtl("<b>⚠️ אין פנייה פעילה לתשובה.</b>"),
            reply_markup=support_tickets_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    if ticket.get("status") != "open":
        await message.answer(
            rtl("<b>⚠️ לא ניתן להשיב לפנייה סגורה.</b>"),
            reply_markup=support_ticket_actions_keyboard(),
            parse_mode="HTML"
        )
        return

    admin_states[message.from_user.id] = {
        "step": "support_ticket_reply",
        "support_ticket_number": ticket_number
    }

    await message.answer(
        rtl(
            "<b>↩️ תשובה ללקוח</b>\n\n"
            f"{field('מספר פנייה', ticket_number)}\n"
            f"{field('נושא פנייה', ticket.get('subject') or 'ללא נושא')}\n"
            "כתוב עכשיו את ההודעה שתרצה לשלוח ללקוח."
        ),
        reply_markup=support_reply_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(lambda message: is_admin(message.from_user.id) and admin_states.get(message.from_user.id, {}).get("step") == "support_ticket_reply")
async def send_support_ticket_reply(message: Message):
    state = admin_states.get(message.from_user.id, {})
    ticket_number = state.get("support_ticket_number")
    ticket = get_support_ticket(ticket_number) if ticket_number else None
    reply_text = clean_admin_text(message.text)

    if reply_text in {"❌ בטל תשובה", "⬅️ חזרה לניהול"}:
        return

    if not ticket:
        admin_states[message.from_user.id] = {"step": "admin"}
        await message.answer(
            rtl("<b>⚠️ הפנייה לא נמצאה.</b>"),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    if ticket.get("status") != "open":
        admin_states[message.from_user.id] = {
            "step": "support_ticket_view",
            "support_ticket_number": ticket_number
        }
        await message.answer(
            rtl("<b>⚠️ הפנייה כבר סגורה.</b>"),
            reply_markup=support_ticket_actions_keyboard(),
            parse_mode="HTML"
        )
        return

    if len(reply_text) < 1:
        return

    add_support_message(
        ticket_number,
        "admin",
        message.from_user.full_name,
        reply_text
    )

    await message.bot.send_message(
        int(ticket["telegram_id"]),
        rtl(
            "<b>📩 תשובה משירות הלקוחות</b>\n\n"
            f"{h(reply_text)}"
        ),
        parse_mode="HTML"
    )

    admin_states[message.from_user.id] = {
        "step": "support_ticket_view",
        "support_ticket_number": ticket_number
    }

    await message.answer(
        rtl("<b>✅ התשובה נשלחה ללקוח.</b>"),
        reply_markup=support_ticket_keyboard_by_status(ticket),
        parse_mode="HTML"
    )


@router.message(F.text == "📄 ייצוא TXT")
async def export_support_ticket_txt(message: Message):
    if not is_admin(message.from_user.id):
        return

    state = admin_states.get(message.from_user.id, {})
    ticket_number = state.get("support_ticket_number")

    if not ticket_number:
        await message.answer(
            rtl("<b>⚠️ אין פנייה פעילה לייצוא.</b>"),
            reply_markup=support_tickets_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    file_path = export_support_ticket_to_txt(ticket_number)

    if not file_path:
        await message.answer(
            rtl("<b>⚠️ לא הצלחתי לייצא את הפנייה.</b>"),
            reply_markup=support_ticket_actions_keyboard(),
            parse_mode="HTML"
        )
        return

    await message.answer_document(
        FSInputFile(file_path),
        caption=rtl(f"📄 <b>ייצוא פנייה</b> {h(ticket_number)}"),
        parse_mode="HTML"
    )


@router.message(F.text == "✅ סגור פנייה")
async def close_support_ticket_from_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    state = admin_states.get(message.from_user.id, {})
    ticket_number = state.get("support_ticket_number")
    ticket = get_support_ticket(ticket_number) if ticket_number else None

    if not ticket:
        await message.answer(
            rtl("<b>⚠️ אין פנייה פעילה לסגירה.</b>"),
            reply_markup=support_tickets_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    if ticket.get("status") == "closed":
        admin_states[message.from_user.id] = {"step": "support_tickets_menu"}

        await message.answer(
            rtl(
                "<b>ℹ️ הפנייה כבר סגורה.</b>\n\n"
                f"{field('מספר פנייה', ticket_number)}"
            ),
            reply_markup=support_ticket_keyboard_by_status(ticket),
            parse_mode="HTML"
        )
        return

    ok = close_support_ticket(ticket_number)

    if ok:
        add_support_message(
            ticket_number,
            "admin",
            message.from_user.full_name,
            "הפנייה נסגרה על ידי שירות הלקוחות."
        )

        try:
            await message.bot.send_message(
                int(ticket["telegram_id"]),
                rtl("<b>✅ הפנייה נסגרה.</b>\nתודה שפנית אלינו."),
                parse_mode="HTML"
            )
        except Exception:
            pass

    admin_states[message.from_user.id] = {"step": "support_tickets_menu"}

    await message.answer(
        rtl(
            "<b>✅ הפנייה נסגרה בהצלחה.</b>\n\n"
            f"{field('מספר פנייה', ticket_number)}\n"
            "הפנייה עברה לפניות סגורות."
        ),
        reply_markup=support_tickets_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🧹 מחק את כל ההזמנות")
async def ask_clear_all_orders(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "confirm_clear_all_orders"}

    await message.answer(
        rtl(
            "<b>⚠️ מחיקת כל ההזמנות</b>\n\n"
            "הפעולה תמחק את כל ההזמנות מהמערכת:\n"
            "הזמנות חדשות, אחרונות, פתוחות, הושלמו ובוטלו.\n\n"
            "<b>הלקוחות והמוצרים לא יימחקו.</b>\n\n"
            "לאישור סופי לחץ על הכפתור למטה."
        ),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ כן, מחק את כל ההזמנות")],
                [KeyboardButton(text="❌ ביטול מחיקה")],
                [KeyboardButton(text="⬅️ חזרה לניהול")]
            ],
            resize_keyboard=True
        ),
        parse_mode="HTML"
    )


@router.message(F.text == "❌ ביטול מחיקה")
async def cancel_clear_all_orders(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "admin"}

    await message.answer(
        rtl("<b>✅ המחיקה בוטלה.</b>"),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "✅ כן, מחק את כל ההזמנות")
async def confirm_clear_all_orders(message: Message):
    if not is_admin(message.from_user.id):
        return

    state = admin_states.get(message.from_user.id, {})

    if state.get("step") != "confirm_clear_all_orders":
        await message.answer(
            rtl("<b>⚠️ כדי למחוק הזמנות יש להתחיל מהכפתור: 🧹 מחק את כל ההזמנות.</b>"),
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )
        return

    deleted_count = clear_all_orders_for_testing()

    admin_states[message.from_user.id] = {"step": "admin"}

    await message.answer(
        rtl(
            "<b>✅ כל ההזמנות נמחקו בהצלחה.</b>\n\n"
            f"{field('נמחקו הזמנות', deleted_count)}\n\n"
            "הלקוחות והמוצרים נשארו במערכת."
        ),
        reply_markup=admin_keyboard(),
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

    admin_states[message.from_user.id] = {"step": "admin"}
    orders = get_recent_orders(10)

    if not orders:
        await message.answer(rtl("<b>🧾 הזמנות אחרונות</b>\n\nאין הזמנות במערכת."), parse_mode="HTML")
        return

    await message.answer(
        rtl(f"<b>🧾 הזמנות אחרונות</b>\n\nנמצאו {len(orders)} הזמנות אחרונות."),
        parse_mode="HTML"
    )

    for order in reversed(orders):
        await message.answer(format_order(order), parse_mode="HTML")


@router.message(F.text == "🆕 הזמנות חדשות")
async def new_orders(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "admin"}
    orders = get_orders_by_status("new", 20)

    if not orders:
        await message.answer(rtl("<b>🆕 הזמנות חדשות</b>\n\nאין הזמנות חדשות כרגע."), parse_mode="HTML")
        return

    await message.answer(
        rtl(f"<b>🆕 הזמנות חדשות</b>\n\nנמצאו {len(orders)} הזמנות חדשות."),
        parse_mode="HTML"
    )

    for order in reversed(orders):
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


@router.message(F.text.in_({"📊 עדכן מלאי", "✏️ אפס והגדר מלאי חדש"}))
async def stock_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "stock_name"}

    await message.answer(
        rtl("<b>✏️ אפס והגדר מלאי חדש</b>\n\nבחר מוצר לקביעת מלאי סופי:"),
        reply_markup=product_names_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text.in_({"➕ הוסף למלאי", "➕ הגדל מלאי קיים"}))
async def add_stock_start(message: Message):
    if not is_admin(message.from_user.id):
        return

    admin_states[message.from_user.id] = {"step": "add_stock_name"}

    await message.answer(
        rtl("<b>➕ הגדל מלאי קיים</b>\n\nבחר מוצר להוספת יחידות למלאי:"),
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



@router.message(lambda message: is_admin(message.from_user.id) and admin_states.get(message.from_user.id, {}).get("step") == "order_actions" and clean_admin_text(message.text) in ORDER_ACTION_BY_BUTTON)
async def admin_order_action_direct_guard(message: Message):
    await admin_flow(message)


@router.message(is_admin_active_step)
async def admin_flow(message: Message):
    # PRIORITY CUSTOMER BROADCAST STATES
    uid = message.from_user.id
    txt = clean_admin_text(message.text)

    if txt == "🧾 הזמנות אחרונות":
        admin_states[uid] = {"step": "admin"}
        orders = get_recent_orders(20)

        if not orders:
            await message.answer(rtl("<b>🧾 הזמנות אחרונות</b>\n\nאין הזמנות במערכת."), parse_mode="HTML")
            return

        await message.answer(
            rtl(f"<b>🧾 הזמנות אחרונות</b>\n\nנמצאו {len(orders)} הזמנות אחרונות."),
            parse_mode="HTML"
        )

        for order in reversed(orders):
            await message.answer(format_order(order), parse_mode="HTML")
        return

    if txt == "🆕 הזמנות חדשות":
        admin_states[uid] = {"step": "admin"}
        orders = get_orders_by_status("new", 30)

        if not orders:
            await message.answer(rtl("<b>🆕 הזמנות חדשות</b>\n\nאין הזמנות חדשות כרגע."), parse_mode="HTML")
            return

        await message.answer(
            rtl(f"<b>🆕 הזמנות חדשות</b>\n\nנמצאו {len(orders)} הזמנות חדשות."),
            parse_mode="HTML"
        )

        for order in reversed(orders):
            await message.answer(format_order(order), parse_mode="HTML")
        return

    state = admin_states.get(uid) or {}
    step = state.get("step")

    # ADMIN_FLOW_SAFE_DELETE_MARKER
    if is_admin_button_only_step(step) and not is_valid_admin_button_text(txt):
        await delete_admin_message(message)
        return

    if step == "broadcast_text":
        await handle_broadcast_text_screen(message)
        return

    if step == "broadcast_confirm":
        await handle_broadcast_confirm_screen(message)
        return

    if step == "customers_search":
        await run_customer_search_screen(message)
        return

    uid = message.from_user.id
    txt = clean_admin_text(message.text)
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




    if step == "customers_menu":
        if txt == "📋 רשימת לקוחות":
            customers = get_customers_list(30)

            if not customers:
                await message.answer(
                    rtl(
                        "<b>👥 רשימת לקוחות</b>\n\n"
                        "אין עדיין לקוחות שמורים במערכת."
                    ),
                    reply_markup=customers_menu_keyboard(),
                    parse_mode="HTML"
                )
                return

            state["step"] = "customers_select"
            state["customers_last_mode"] = "list"

            await message.answer(
                rtl(
                    "<b>👥 רשימת לקוחות</b>\n\n"
                    f"נמצאו {len(customers)} לקוחות.\n"
                    "בחר לקוח מהרשימה כדי לפתוח כרטיס."
                ),
                reply_markup=customer_select_keyboard(customers),
                parse_mode="HTML"
            )
            return

        if txt == "🔎 חפש לקוח":
            state["step"] = "customers_search"

            await message.answer(
                rtl(
                    "<b>🔎 חיפוש לקוח</b>\n\n"
                    "רשום שם, טלפון או שם Telegram לחיפוש."
                ),
                parse_mode="HTML"
            )
            return

        await message.answer(
            rtl("<b>⚠️ בחר פעולה מתוך הכפתורים בלבד.</b>"),
            reply_markup=customers_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    if step == "customers_search":
        query = clean_admin_text(txt)

        if len(query) < 2:
            await message.answer(
                rtl(
                    "<b>⚠️ חיפוש קצר מדי</b>\n\n"
                    "רשום לפחות 2 תווים לחיפוש."
                ),
                parse_mode="HTML"
            )
            return

        customers = search_customers(query, 30)

        if not customers:
            state["step"] = "customers_menu"
            await message.answer(
                rtl(
                    "<b>🔎 תוצאות חיפוש</b>\n\n"
                    "לא נמצאו לקוחות לפי החיפוש הזה."
                ),
                reply_markup=customers_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        state["step"] = "customers_select"
        state["customers_last_mode"] = "search"
        state["customers_last_query"] = query

        await message.answer(
            rtl(
                "<b>🔎 תוצאות חיפוש</b>\n\n"
                f"נמצאו {len(customers)} לקוחות.\n"
                "בחר לקוח מהרשימה כדי לפתוח כרטיס."
            ),
            reply_markup=customer_select_keyboard(customers),
            parse_mode="HTML"
        )
        return

    if step == "customers_select":
        if txt == "⬅️ חזרה ללקוחות":
            state["step"] = "customers_menu"
            await message.answer(
                rtl("<b>👥 ניהול לקוחות</b>\n\nבחר פעולה מהתפריט."),
                reply_markup=customers_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        customer_id = extract_customer_id_from_button(txt)

        if not customer_id:
            await message.answer(
                rtl("<b>⚠️ בחר לקוח מתוך הרשימה בלבד.</b>"),
                parse_mode="HTML"
            )
            return

        customer = get_customer_by_id(customer_id)

        if not customer:
            await message.answer(
                rtl("<b>⚠️ הלקוח לא נמצא במערכת.</b>"),
                reply_markup=customers_menu_keyboard(),
                parse_mode="HTML"
            )
            state["step"] = "customers_menu"
            return

        state["step"] = "customer_profile"
        state["customer_id"] = customer_id

        await message.answer(
            format_customer_profile(customer),
            reply_markup=customer_actions_keyboard(),
            parse_mode="HTML"
        )
        return

    if step == "customer_profile":
        customer_id = state.get("customer_id")
        customer = get_customer_by_id(customer_id) if customer_id else None

        if not customer:
            state["step"] = "customers_menu"
            await message.answer(
                rtl("<b>⚠️ הלקוח לא נמצא במערכת.</b>"),
                reply_markup=customers_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        if txt == "📦 היסטוריית הזמנות לקוח":
            orders = get_orders_by_customer_telegram_id(customer["telegram_id"], 30)

            await message.answer(
                format_customer_orders_summary(customer, orders),
                reply_markup=customer_actions_keyboard(),
                parse_mode="HTML"
            )
            return

        if txt == "⬅️ חזרה לרשימת לקוחות":
            customers = get_customers_list(30)

            state["step"] = "customers_select"

            await message.answer(
                rtl("<b>👥 רשימת לקוחות</b>\n\nבחר לקוח מהרשימה."),
                reply_markup=customer_select_keyboard(customers),
                parse_mode="HTML"
            )
            return

        await message.answer(
            rtl("<b>⚠️ בחר פעולה מתוך הכפתורים בלבד.</b>"),
            reply_markup=customer_actions_keyboard(),
            parse_mode="HTML"
        )
        return

    if step == "broadcast_text":
        broadcast_text = clean_broadcast_text(txt)
        is_valid, error_text = validate_broadcast_text(broadcast_text)

        if not is_valid:
            await message.answer(
                rtl(
                    "<b>⚠️ הודעה לא תקינה</b>\n\n"
                    f"{h(error_text)}\n\n"
                    "רשום הודעה חדשה או לחץ: ⬅️ חזרה לניהול."
                ),
                parse_mode="HTML"
            )
            return

        customer_ids = get_all_customer_telegram_ids()

        if not customer_ids:
            admin_states[uid] = {"step": "admin"}
            await message.answer(
                rtl(
                    "<b>⚠️ אין לקוחות לשליחה</b>\n\n"
                    "לא נמצאו לקוחות שמורים במערכת."
                ),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            return

        state["broadcast_text"] = broadcast_text
        state["broadcast_customer_ids"] = customer_ids
        state["step"] = "broadcast_confirm"

        await message.answer(
            format_broadcast_preview(broadcast_text, len(customer_ids)),
            reply_markup=broadcast_confirm_keyboard(),
            parse_mode="HTML"
        )
        return

    if step == "broadcast_confirm":
        if txt == "❌ בטל שליחה":
            admin_states[uid] = {"step": "admin"}
            await message.answer(
                rtl(
                    "<b>✅ השליחה בוטלה</b>\n\n"
                    "ההודעה לא נשלחה לאף לקוח."
                ),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            return

        if txt == "✏️ ערוך הודעה":
            state.pop("broadcast_text", None)
            state.pop("broadcast_customer_ids", None)
            state["step"] = "broadcast_text"

            await message.answer(
                rtl(
                    "<b>✏️ עריכת הודעה</b>\n\n"
                    "רשום את ההודעה החדשה לשליחה."
                ),
                parse_mode="HTML"
            )
            return

        if txt != "✅ אשר ושלח ללקוחות":
            await message.answer(
                rtl(
                    "<b>⚠️ פעולה לא תקינה</b>\n\n"
                    "בחר פעולה מתוך הכפתורים בלבד."
                ),
                reply_markup=broadcast_confirm_keyboard(),
                parse_mode="HTML"
            )
            return

        if state.get("broadcast_sent"):
            await message.answer(
                rtl(
                    "<b>⚠️ הפעולה כבר בוצעה</b>\n\n"
                    "ההודעה כבר נשלחה ללקוחות.\n"
                    "אין צורך לאשר שוב."
                ),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            admin_states[uid] = {"step": "admin"}
            return

        broadcast_text = state.get("broadcast_text")
        customer_ids = state.get("broadcast_customer_ids") or []

        if not broadcast_text or not customer_ids:
            admin_states[uid] = {"step": "admin"}
            await message.answer(
                rtl(
                    "<b>⚠️ לא ניתן לבצע שליחה</b>\n\n"
                    "חסרים נתוני שליחה. התחל את התהליך מחדש."
                ),
                reply_markup=admin_keyboard(),
                parse_mode="HTML"
            )
            return

        state["broadcast_sent"] = True

        await message.answer(
            rtl(
                "<b>📢 השליחה התחילה</b>\n\n"
                "הבוט שולח עכשיו את ההודעה ללקוחות.\n"
                "בסיום תקבל סיכום."
            ),
            parse_mode="HTML"
        )

        sent, failed = await send_broadcast_to_customers(
            message.bot,
            broadcast_text,
            customer_ids
        )

        admin_states[uid] = {"step": "admin"}

        await message.answer(
            rtl(
                "<b>✅ השליחה הסתיימה</b>\n\n"
                f"{field('נשלחו בהצלחה', sent)}\n"
                f"{field('נכשלו', failed)}\n"
                f"{field('סה״כ לקוחות', len(customer_ids))}"
            ),
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
            reply_markup=order_action_keyboard(order.get("status"), is_order_pickup(order)),
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
                    reply_markup=order_action_keyboard(order.get("status"), is_order_pickup(order)),
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
            await send_customer_status_with_menu(
                message.bot,
                order["telegram_id"],
                f"{client_msg}\n\n{field('מספר הזמנה', order_number)}"
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
            reply_markup=order_action_keyboard(order.get("status"), is_order_pickup(order)),
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
            await send_customer_status_with_menu(
                message.bot,
                order["telegram_id"],
                f"{client_msg}\n\n{field('מספר הזמנה', order_number)}"
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
