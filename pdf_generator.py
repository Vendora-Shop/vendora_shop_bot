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

    green = "#9CFF2E"
    white = "#FFFFFF"
    gray = "#CFCFCF"
    dark = "#101010"
    row_dark = "#080808"
    border_dark = "#1F3315"

    # קווים דקים יותר
    LINE_W = 1
    BOX_W = 2

    label_font = ImageFont.truetype(FONT_PATH, 30)
    value_font = ImageFont.truetype(FONT_PATH, 26)
    address_font = ImageFont.truetype(FONT_PATH, 26)
    section_font = ImageFont.truetype(FONT_PATH, 36)
    table_font = ImageFont.truetype(FONT_PATH, 36)
    total_label_font = ImageFont.truetype(FONT_PATH, 36)
    total_font = ImageFont.truetype(FONT_PATH, 30)
    note_font = ImageFont.truetype(FONT_PATH, 26)

    # ==================================================
    # HEADER
    # ==================================================
    draw.rectangle((0, 0, W, 260), fill="#000000")

    # לוגו מוגדל משמעותית
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGB")
        logo.thumbnail((340, 340))
        img.paste(logo, (55, 8))

    draw.line((55, 265, W - 55, 265), fill=green, width=LINE_W)

    # ==================================================
    # TITLE
    # ==================================================
    y = 320
    draw_rtl(draw, W - 70, y, "סיכום הזמנה", section_font, green)

    # ==================================================
    # CUSTOMER DETAILS
    # ==================================================
    y = 385
    box_h = 315
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

    row_y = y + 60
    for label, value in details:
        draw_rtl(draw, label_x, row_y, f"{label}:", label_font, green)
        draw_rtl(draw, value_x, row_y, value, value_font, white)
        row_y += 68

    draw_rtl(draw, label_x, row_y, "כתובת:", label_font, green)
    draw_rtl(draw, value_x, row_y, order["address"], address_font, white)

    # ==================================================
    # PRODUCTS TITLE
    # ==================================================
    y = 770
    draw_rtl(draw, W - 70, y, "פרטי מוצרים", section_font, green)
    y += 70

    # ==================================================
    # TABLE
    # ==================================================
    table_x1, table_x2 = 55, W - 55

    product_x = W - 185
    qty_x = 450
    price_x = 265
    total_x = 110

    header_h = 76
    draw.rectangle(
        (table_x1, y, table_x2, y + header_h),
        fill=dark,
        outline=green,
        width=BOX_W
    )

    header_y = y + 38

    draw.text((product_x, header_y), rtl("מוצר"),
              font=table_font, fill=green, anchor="mm")
    draw.text((qty_x, header_y), rtl("כמות"),
              font=table_font, fill=green, anchor="mm")
    draw.text((price_x, header_y), rtl("מחיר"),
              font=table_font, fill=green, anchor="mm")
    draw.text((total_x, header_y), rtl("סה״כ"),
              font=table_font, fill=green, anchor="mm")

    y += header_h + 12

    for item in order["cart"]:
        name = item["name"]
        qty = int(item["qty"])
        price = float(item["price"])
        total = price * qty

        row_h = 72

        draw.rectangle(
            (table_x1, y, table_x2, y + row_h),
            fill=row_dark,
            outline=border_dark,
            width=1
        )

        row_center = y + 36

        draw.text((product_x, row_center), rtl(name),
                  font=table_font, fill=white, anchor="mm")
        draw.text((qty_x, row_center), str(qty),
                  font=table_font, fill=white, anchor="mm")
        draw.text((price_x, row_center), money_text(price),
                  font=table_font, fill=white, anchor="mm")
        draw.text((total_x, row_center), money_text(total),
                  font=table_font, fill=white, anchor="mm")

        y += row_h + 10

    # ==================================================
    # SUMMARY
    # ==================================================
    y += 30
    draw.line((55, y, W - 55, y), fill=green, width=LINE_W)
    y += 65

    draw_rtl(draw, W - 95, y, "סה״כ מוצרים:", label_font, green)
    draw.text((365, y), money_text(order["products_total"]),
              font=value_font, fill=white, anchor="mm")

    y += 62

    draw_rtl(draw, W - 95, y, "דמי משלוח:", label_font, green)
    draw.text((365, y), money_text(order["delivery_price"]),
              font=value_font, fill=white, anchor="mm")

    # ==================================================
    # FINAL TOTAL
    # ==================================================
    y += 95
    total_box_h = 135

    draw.rectangle(
        (55, y, W - 55, y + total_box_h),
        fill="#071007",
        outline=green,
        width=BOX_W
    )

    final_y = y + 70

    draw.text((W - 255, final_y), rtl("סה״כ לתשלום:"),
              font=total_label_font, fill=green, anchor="mm")

    draw.text((330, final_y), money_text(order["final_total"]),
              font=total_font, fill=green, anchor="mm")

    # ==================================================
    # NOTES
    # ==================================================
    y += 185
    draw_rtl(draw, W - 95, y, "המסמך מהווה סיכום הזמנה בלבד.", note_font, gray)
    y += 36
    draw_rtl(draw, W - 95, y, "התשלום יתבצע לאחר אישור נציג.", note_font, gray)

    # ==================================================
    # FOOTER
    # ==================================================
    draw.line((55, H - 150, W - 55, H - 150), fill="#222222", width=1)

    draw.text((70, H - 105), "Vendora Shop ©",
              font=note_font, fill=green)

    draw_rtl(draw, W - 95, H - 105,
             "תודה שקנית ב Vendora",
             note_font, white)

    # ==================================================
    # SAVE
    # ==================================================
    img.save(img_path, "PNG")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(img_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    return pdf_path
