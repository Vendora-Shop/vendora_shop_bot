import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_invoice_pdf(order):
    try:
        file_name = f"{order['order_id']}.pdf"
        file_path = os.path.join("/tmp", file_name)

        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        y = height - 50

        c.setFont("Helvetica-Bold", 18)
        c.drawRightString(550, y, "Vendora Shop חשבונית")
        y -= 40

        c.setFont("Helvetica", 12)
        c.drawRightString(550, y, f"מספר הזמנה: {order['order_id']}")
        y -= 25

        c.drawRightString(550, y, f"שם לקוח: {order['name']}")
        y -= 25

        c.drawRightString(550, y, f"טלפון: {order['phone']}")
        y -= 25

        c.drawRightString(550, y, f"כתובת: {order['address']}")
        y -= 40

        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(550, y, "מוצרים:")
        y -= 30

        c.setFont("Helvetica", 12)

        for item in order["items"]:
            line = f"{item['name']} x {item['qty']} = ₪{item['price'] * item['qty']}"
            c.drawRightString(550, y, line)
            y -= 25

        y -= 20

        c.drawRightString(550, y, f"סה״כ מוצרים: ₪{order['subtotal']}")
        y -= 25

        c.drawRightString(550, y, f"משלוח: ₪{order['delivery']}")
        y -= 25

        c.drawRightString(550, y, f"סה״כ לתשלום: ₪{order['total']}")
        y -= 50

        c.drawRightString(550, y, "תודה שקנית אצל Vendora Shop")

        c.save()

        return file_path

    except Exception as e:
        print("PDF ERROR:", e)
        return None
