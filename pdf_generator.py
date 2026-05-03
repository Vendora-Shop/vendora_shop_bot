import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from bidi.algorithm import get_display

FONT_PATH = "fonts/DejaVuSans.ttf"
LOGO_PATH = "assets/logo.jpg"


def rtl(text):
    return get_display(str(text), base_dir="R")


def money(value):
    value = float(value)
    return f"{int(value) if value.is_integer() else value:g} ₪"


def draw_rtl(draw, x, y, text, font, fill, anchor="ra"):
    draw.text((x, y), rtl(text), font=font, fill=fill, anchor=anchor)


def create_invoice_pdf(order):
    img_path = f"/tmp/{order['order_number']}.png"
    pdf_path = f"/tmp/{order['order_number']}.pdf"

    W, H = 1240, 1754
    img = Image.new("RGB", (W, H), "#050505")
    draw = ImageDraw.Draw(img)

    green = "#9CFF2E"
    white = "#FFFFFF"
    gray = "#CFCFCF"
    dark = "#0D0D0D"
    dark_box = "#111111"
    muted = "#294015"

    title_font = ImageFont.truetype(FONT_PATH, 58)
    label_font = ImageFont.truetype(FONT_PATH, 34)
    value_font = ImageFont.truetype(FONT_PATH, 36)
    section_font = ImageFont.truetype(FONT_PATH, 44)
    table_font = ImageFont.truetype(FONT_PATH, 30)
    table_bold = ImageFont.truetype(FONT_PATH, 32)
    total_font = ImageFont.truetype(FONT_PATH, 64)
    note_font = ImageFont.truetype(FONT_PATH, 26)
    small_font = ImageFont.truetype(FONT_PATH, 24)

    # ===== HEADER =====
    draw.rectangle((0, 0, W, 250), fill="#000000")

    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGB")
        logo.thumbnail((240, 160))
        img.paste(logo, (W - 300, 35))

    draw.text((70, 70), "VENDORA", font=title_font, fill=white)
    draw_rtl(draw, 70, 145, "חנות אספקה חכמה", label_font, green, anchor="la")

    draw.line((55, 260, W - 55, 260), fill=green, width=4)

    # ===== CUSTOMER DETAILS =====
    y = 320
    draw.rectangle((55, y, W - 55, y + 310), fill=dark_box, outline=green, width=4)

    details = [
        ("מספר הזמנה", order["order_number"]),
        ("שם לקוח", order["customer_name"]),
        ("טלפון", order["phone"]),
        ("כתובת", order["address"]),
    ]

    row_y = y + 55
    for label, value in details:
        draw_rtl(draw, W - 95, row_y, f"{label}:", label_font, green)
        draw_rtl(draw, W - 380, row_y, value, value_font, white)
        row_y += 68

    # ===== PRODUCTS TABLE =====
    y = 690
    draw_rtl(draw, W - 70, y, "פרטי מוצרים", section_font, green)
    y += 60

    table_x1, table_x2 = 55, W - 55
    col_product = W - 95
    col_qty = 445
    col_price = 250
    col_total = 105

    draw.rectangle((table_x1, y, table_x2, y + 70), fill=dark, outline=green, width=3)

    draw_rtl(draw, col_product, y + 45, "מוצר", table_bold, green)
    draw.text((col_qty, y + 42), rtl("כמות"), font=table_bold, fill=green, anchor="mm")
    draw.text((col_price, y + 42), rtl("מחיר"), font=table_bold, fill=green, anchor="mm")
    draw.text((col_total, y + 42), rtl("סה״כ"), font=table_bold, fill=green, anchor="mm")

    y += 78

    for item in order["cart"]:
        name = item["name"]
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty

        draw.rectangle((table_x1, y, table_x2, y + 74), fill="#090909", outline=muted, width=2)

        draw_rtl(draw, col_product, y + 47, name, table_font, white)
        draw.text((col_qty, y + 43), str(qty), font=table_font, fill=white, anchor="mm")
        draw.text((col_price, y + 43), money(price), font=table_font, fill=white, anchor="mm")
        draw.text((col_total, y + 43), money(total), font=table_font, fill=white, anchor="mm")

        y += 82

    # ===== SUMMARY =====
    y += 35
    draw.line((55, y, W - 55, y), fill=green, width=4)
    y += 55

    summary = [
        ("סה״כ מוצרים", money(order["products_total"])),
        ("דמי משלוח", money(order["delivery_price"])),
    ]

    for label, value in summary:
        draw_rtl(draw, W - 95, y, f"{label}:", label_font, green)
        draw.text((420, y), value, font=value_font, fill=white, anchor="mm")
        y += 58

    # ===== FINAL TOTAL =====
    y += 25
    draw.rectangle((55, y, W - 55, y + 135), fill="#071007", outline=green, width=6)

    draw_rtl(draw, W - 95, y + 82, "סה״כ לתשלום:", total_font, green)
    draw.text((360, y + 82), money(order["final_total"]), font=total_font, fill=green, anchor="mm")

    # ===== NOTES =====
    y += 185
    draw_rtl(draw, W - 95, y, "המסמך מהווה סיכום הזמנה בלבד.", note_font, gray)
    y += 36
    draw_rtl(draw, W - 95, y, "התשלום יתבצע לאחר אישור נציג.", note_font, gray)

    # ===== FOOTER =====
    draw.line((55, H - 150, W - 55, H - 150), fill="#222222", width=2)
    draw.text((70, H - 105), "Vendora Shop ©", font=small_font, fill=green)
    draw_rtl(draw, W - 95, H - 105, "תודה שקנית ב Vendora", small_font, white)

    img.save(img_path, "PNG", quality=95)

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
