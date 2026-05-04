import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from bidi.algorithm import get_display

FONT_PATH = "fonts/DejaVuSans.ttf"
LOGO_PATH = "assets/logo.jpg"


def rtl(text):
    return get_display(str(text), base_dir="R")


def draw_rtl(draw, x, y, text, font, fill, anchor="ra"):
    draw.text((x, y), rtl(text), font=font, fill=fill, anchor=anchor)


def money_text(value):
    value = float(value)
    num = int(value) if value.is_integer() else value
    return f"{num} ₪"


def create_invoice_pdf(order):
    img_path = f"/tmp/{order['order_number']}.png"
    pdf_path = f"/tmp/{order['order_number']}.pdf"

    W, H = 1240, 1754
    img = Image.new("RGB", (W, H), "#050505")
    draw = ImageDraw.Draw(img)

    # =========================
    # COLORS
    # =========================
    green = "#9CFF2E"
    white = "#FFFFFF"
    gray = "#CFCFCF"
    dark = "#101010"
    row_dark = "#080808"
    border_dark = "#1F3315"

    # =========================
    # LINE CONTROLS
    # =========================
    LINE_W = 1
    BOX_W = 1

    # =========================
    # FONT SIZE CONTROLS
    # =========================

    # כחול — כותרות: סיכום הזמנה / פרטי מוצרים
    blue_title_font = ImageFont.truetype(FONT_PATH, 30)

    # אדום — שמות שדות + כותרות טבלה + סיכום מוצרים / דמי משלוח
    red_label_font = ImageFont.truetype(FONT_PATH, 26)

    # לבן — כל הערכים: מספר הזמנה, שם, טלפון, כתובת, מוצר, כמות, מחיר
    white_value_font = ImageFont.truetype(FONT_PATH, 22)

    # כתום — הטקסט: סה״כ לתשלום:
    orange_total_label_font = ImageFont.truetype(FONT_PATH, 34)

    # אפור — הסכום הסופי הגדול
    gray_total_number_font = ImageFont.truetype(FONT_PATH, 30)

    # הערות ותחתית
    note_font = ImageFont.truetype(FONT_PATH, 24)

    # =========================
    # HEADER
    # =========================
    draw.rectangle((0, 0, W, 260), fill="#000000")

    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGB")
        logo.thumbnail((380, 380))
        img.paste(logo, (55, 0))

    draw.line((55, 265, W - 55, 300), fill=green, width=LINE_W)

    # =========================
    # TITLE - כחול
    # =========================
    y = 320
    draw_rtl(draw, W - 70, y, "סיכום הזמנה", blue_title_font, green)

    # =========================
    # CUSTOMER DETAILS BOX
    # =========================
    y = 380
    box_h = 300

    draw.rectangle(
        (55, y, W - 55, y + box_h),
        fill=dark,
        outline=green,
        width=BOX_W
    )

    label_x = W - 95
    value_x = W - 430

    details = [
        ("מספר הזמנה", order["order_number"]),
        ("שם לקוח", order["customer_name"]),
        ("טלפון", order["phone"]),
    ]

    row_y = y + 55

    for label, value in details:
        # אדום
        draw_rtl(draw, label_x, row_y, f"{label}:", red_label_font, green)

        # לבן
        draw_rtl(draw, value_x, row_y, value, white_value_font, white)

        row_y += 60

    # כתובת
    draw_rtl(draw, label_x, row_y, "כתובת:", red_label_font, green)
    draw_rtl(draw, value_x, row_y, order["address"], white_value_font, white)

    # =========================
    # PRODUCTS TITLE - כחול
    # =========================
    y = 720
    draw_rtl(draw, W - 70, y, "פרטי מוצרים", blue_title_font, green)
    y += 60

    # =========================
    # PRODUCTS TABLE
    # =========================
    table_x1, table_x2 = 55, W - 55

    product_x = W - 200
    qty_x = 450
    price_x = 265
    total_x = 110

    header_h = 70

    draw.rectangle(
        (table_x1, y, table_x2, y + header_h),
        fill=dark,
        outline=green,
        width=BOX_W
    )

    header_y = y + header_h / 2

    # אדום — כותרות טבלה
    draw.text((product_x, header_y), rtl("מוצר"), font=red_label_font, fill=green, anchor="mm")
    draw.text((qty_x, header_y), rtl("כמות"), font=red_label_font, fill=green, anchor="mm")
    draw.text((price_x, header_y), rtl("מחיר"), font=red_label_font, fill=green, anchor="mm")
    draw.text((total_x, header_y), rtl("סה״כ"), font=red_label_font, fill=green, anchor="mm")

    y += header_h + 10

    for item in order["cart"]:
        name = item["name"]
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty

        row_h = 70

        draw.rectangle(
            (table_x1, y, table_x2, y + row_h),
            fill=row_dark,
            outline=border_dark,
            width=BOX_W
        )

        row_center = y + row_h / 2

        # לבן — ערכי מוצר
        draw.text((product_x, row_center), rtl(name), font=white_value_font, fill=white, anchor="mm")
        draw.text((qty_x, row_center), str(qty), font=white_value_font, fill=white, anchor="mm")
        draw.text((price_x, row_center), money_text(price), font=white_value_font, fill=white, anchor="mm")
        draw.text((total_x, row_center), money_text(total), font=white_value_font, fill=white, anchor="mm")

        y += row_h + 8

    # =========================
    # SUMMARY
    # =========================
    y += 25
    draw.line((55, y, W - 55, y), fill=green, width=LINE_W)
    y += 50

    # אדום
    draw_rtl(draw, W - 95, y, "סה״כ מוצרים:", red_label_font, green)
    # לבן
    draw.text((365, y), money_text(order["products_total"]), font=white_value_font, fill=white, anchor="mm")

    y += 50

    # אדום
    draw_rtl(draw, W - 95, y, "דמי משלוח:", red_label_font, green)
    # לבן
    draw.text((365, y), money_text(order["delivery_price"]), font=white_value_font, fill=white, anchor="mm")

    # =========================
    # FINAL TOTAL BOX
    # =========================
    y += 80
    total_box_h = 120

    draw.rectangle(
        (55, y, W - 55, y + total_box_h),
        fill="#071007",
        outline=green,
        width=BOX_W
    )

    final_y = y + total_box_h / 2

    # כתום — סה״כ לתשלום
    draw.text(
        (W - 260, final_y),
        rtl("סה״כ לתשלום:"),
        font=orange_total_label_font,
        fill=green,
        anchor="mm"
    )

    # אפור — הסכום הסופי
    draw.text(
        (330, final_y),
        money_text(order["final_total"]),
        font=gray_total_number_font,
        fill=green,
        anchor="mm"
    )

    # =========================
    # NOTES
    # =========================
    y += 150

    draw_rtl(draw, W - 95, y, "המסמך מהווה סיכום הזמנה בלבד.", note_font, gray)
    y += 30
    draw_rtl(draw, W - 95, y, "התשלום יתבצע לאחר אישור נציג.", note_font, gray)

    # =========================
    # FOOTER
    # =========================
    draw.line((55, H - 150, W - 55, H - 150), fill="#222222", width=LINE_W)

    draw.text((70, H - 105), "Vendora Shop ©", font=note_font, fill=green)
    draw_rtl(draw, W - 95, H - 105, "תודה שקנית ב Vendora", note_font, white)

    # =========================
    # SAVE
    # =========================
    img.save(img_path, "PNG")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
